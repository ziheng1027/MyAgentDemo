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


plan_system_prompt = """
你是任务规划器，负责把用户问题拆解成可执行的子步骤。

这些步骤将会被系统下一层的执行器执行/回答，请确保每个步骤都是具体且可执行的。

执行要求：
1. 不要生成“向用户追问信息”的步骤。
2. 如果用户提供的信息不足，请基于合理默认假设继续规划，而不是停下来等待补充信息。
3. 步骤数量尽量精简，控制在3-5个之间为最佳。

用户问题：
{user_query}
"""


class Planer:
    """任务规划器。"""
    def __init__(self) -> None:
        llm_client = LLMClient("zhipu")
        self.llm = llm_client.get_llm("glm-4.5-air").with_structured_output(
            PlanResult,
            method="function_calling"
        )

    async def plan(self, user_query: str) -> PlanResult:
        """根据用户问题规划任务。"""

        prompt = plan_system_prompt.format(user_query=user_query)
        response = await self.llm.ainvoke(prompt)

        return response


execute_system_prompt = """
你是任务执行器，你的职责是根据给定的任务上下文完成当前步骤。

你可以使用工具，但必须遵守以下规则：

1. 只围绕当前步骤执行，不要擅自扩展任务。
2. 优先使用已提供的历史步骤结果，避免重复调用工具。
3. 如果当前信息不足，可以调用工具补充。
4. 只输出当前步骤的简洁结论。
"""

execute_query_template = """
原始问题：
{user_query}

最近已完成的任务与结果：
{recent_steps}

当前步骤的任务：[{step.step}/{total_steps}]: 
{step.task}

请只完成当前步骤的任务。
如果最近已完成任务已经提供足够信息，请不要重复调用工具。
只输出当前任务的结论摘要。
"""


class Executor:
    """任务执行器"""
    def __init__(self) -> None:
        llm_client = LLMClient("zhipu")
        self.llm = llm_client.get_llm("glm-4.5-air")
        self.executor = create_agent(
            model=self.llm,
            system_prompt=execute_system_prompt,
            tools=[
                get_weather, 
                get_pois, 
                get_location,
                get_distance,
                get_text_content, 
                tavily_search
            ]
        )
    
    async def execute(self, user_query: str, total_steps: int, recent_steps: str, current_step: PlanStep) -> str:
        """执行任务"""

        query = {
            "messages": [{
                "role": "user", 
                "content": execute_query_template.format(
                    user_query=user_query, 
                    recent_steps=recent_steps,
                    step=current_step,
                    total_steps=total_steps
                )
            }]
        }
        response = await self.executor.ainvoke(query)
        messages = response.get("messages", [])
        # 跳过中间的AI思考与工具调用消息，只取最后一个AI消息作为执行结果
        result = messages[-1].content

        return result
    
    @staticmethod
    def _format_plan(plan: PlanResult) -> str:
        """格式化计划方便注入提示词"""

        return "\n".join([f"步骤 {step.step}: {step.task}" for step in plan.steps])


summarize_system_prompt = """
你是一个任务总结专员，你的职责是根据用户问题、任务计划以及每一步的执行结果，生成最终回答。

执行要求：
1. 只能基于已提供的步骤结果进行总结，不要补充未出现的信息。
3. 最终回答必须直接回应用户原始问题。
4. 如果步骤结果不足以支持完整回答，要明确说明信息不足。
5. 输出保持简洁、清晰、自然。

用户问题：
{user_query}

任务计划：
{plan}

已完成的步骤与结果：
{completed_steps}

请输出最终回答。
"""


class Summarizer:
    """任务总结器"""
    def __init__(self) -> None:
        llm_client = LLMClient("dashscope")
        self.llm = llm_client.get_llm("qwen3.5-flash")
    
    async def summarize(self, user_query: str, plan: PlanResult, completed_steps: str) -> str:
        """总结任务执行结果"""

        prompt = summarize_system_prompt.format(
            user_query=user_query, 
            plan=self._format_plan(plan), 
            completed_steps=completed_steps
        )
        response = await self.llm.ainvoke(prompt)

        return response.content
    
    @staticmethod
    def _format_plan(plan: PlanResult) -> str:
        """格式化计划方便注入提示词"""

        return "\n".join([f"步骤 {step.step}: {step.task}" for step in plan.steps])


class PlanExecuteAgent:
    """任务规划执行器"""
    def __init__(self) -> None:
        self.planner = Planer()
        self.executor = Executor()
        self.summarizer = Summarizer()

    async def run(self, user_query: str) -> str:
        """运行任务规划执行器"""
       
        print("正在制定计划...")
        plan = await self.planner.plan(user_query)
        print(plan)

        if not plan.steps:
            return "用户问题无法规划出可执行的步骤"
        
        # 已完成步骤与结果列表
        completed_steps: list[dict] = []

        for i, step in enumerate(plan.steps):
            print(f"正在执行步骤 {i+1}：{step.task}")
            result = await self.executor.execute(
                user_query=user_query,
                total_steps=len(plan.steps),
                # 只考虑最近已完成的步骤与结果, 避免步骤过长导致上下文过长, token成本增加
                recent_steps=self._format_completed_steps(completed_steps[-2:]),
                current_step=step
            )
            completed_steps.append({"step": step.step, "task": step.task, "result": result})
            # print(f"步骤 {step.step} 结果: {result}\n")
        
        # 总结任务执行结果
        content = await self.summarizer.summarize(
            user_query=user_query,
            plan=plan,
            completed_steps=self._format_completed_steps(completed_steps)
        )
        
        return content
        
    
    @staticmethod
    def _format_completed_steps(completed_steps: list[dict]) -> str:
        """格式化已完成步骤与结果"""

        return "\n".join([f"步骤 {step['step']}: {step['task']}\n结果: {step['result']}\n" for step in completed_steps])


plan_execute_agent = PlanExecuteAgent()