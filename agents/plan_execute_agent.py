import json
from pydantic import BaseModel, Field
from langchain.agents import create_agent

from client import LLMClient
from services import (
    get_weather, 
    get_pois, 
    get_location,
    get_distance,
    get_text_content, 
    tavily_search
)


class PlanStep(BaseModel):
    step: int = Field(description="步骤编号")
    task: str = Field(description="当前步骤的执行目标")


class PlanResult(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list, description="规划出的步骤列表")


plan_prompt_template = """
你是一个专业的任务规划专家，请把用户的问题拆成独立可执行的步骤。

要求：
1. 只能输出JSON格式的计划, 不能包含任何其他内容。
2. JSON格式必须为：
{{
  "steps": [
    {{
        "step": 1, "task": "...",
        "step": 2, "task": "...",
        ...
    }}
  ]
}}
3. 每个步骤必须具体、可执行。

用户问题：
{user_query}
"""


class Planer:
    """任务规划器。"""
    def __init__(self) -> None:
        llm_client = LLMClient("deepseek")
        self.planner_llm = llm_client.get_llm("deepseek-chat")

    async def plan(self, user_query: str) -> PlanResult:
        """根据用户问题规划任务。"""

        prompt = plan_prompt_template.format(user_query=user_query)

        response = await self.planner_llm.ainvoke(prompt)
        plan_data = self._extract_json(response.content)

        return PlanResult.model_validate(plan_data)
    
    @staticmethod
    def _extract_json(content: str) -> dict:
        """从字符串中提取JSON内容。"""

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or start > end:
            raise ValueError("Planer未返回合法的JSON内容")
        
        return json.loads(content[start:end + 1])


execute_prompt_template = """
你是一个任务执行专员，你的任务是严格按照给定的计划，完成当前步骤。

你将收到原始问题、完整计划、到目前为止已经完成的步骤和结果以及当前需要完成的步骤。

原始问题：
{user_query}

完整计划：
{plan}

已完成步骤和结果：
{completed_steps}

当前步骤：
步骤 {step.step}: {step.task}

请你专注于解决“当前步骤”，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。。
"""


class Executor:
    """任务执行器"""
    def __init__(self) -> None:
        llm_client = LLMClient("zhipu")
        self.executor_llm = llm_client.get_llm("glm-5-turbo")
    
    async def execute(self, user_query: str, plan: PlanResult, completed_steps: str, step: PlanStep) -> str:
        """执行任务"""

        prompt = execute_prompt_template.format(
            user_query=user_query, 
            plan=self._format_plan(plan), 
            completed_steps=completed_steps,
            step=step,
        )
        executor = create_agent(
            model=self.executor_llm,
            system_prompt=prompt,
            tools=[
                get_weather, 
                get_pois, 
                get_location,
                get_distance,
                get_text_content, 
                tavily_search,
            ],
        )
        query = {"messages": [{"role": "user", "content": step.task}]}
        response = await executor.ainvoke(query)
        messages = response.get("messages", [])
        result = messages[-1].content

        return result
    
    @staticmethod
    def _format_plan(plan: PlanResult) -> str:
        """格式化计划"""

        return "\n".join([f"步骤 {step.step}: {step.task}" for step in plan.steps])


class PlanExecuteAgent:
    """任务规划执行器"""
    def __init__(self) -> None:
        self.planner = Planer()
        self.executor = Executor()

    async def run(self, user_query: str) -> str:
        """运行任务规划执行器"""
       
        print("正在制定计划...")
        plan = await self.planner.plan(user_query)
               
        completed_steps = ""
        for i, step in enumerate(plan.steps):
            print(f"正在执行步骤 {i+1}：{step.task}")
            result = await self.executor.execute(user_query, plan, completed_steps, step)
            completed_steps += f"步骤 {step.step} 结果: {result}\n"
            print(f"步骤 {step.step} 结果: {result}\n")
            print("-"*50)
        
        return result


plan_execute_agent = PlanExecuteAgent()