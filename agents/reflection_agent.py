from langchain.agents import create_agent

from client import LLMClient
from agents.schemas import Critique, MemoryItem
from services import (
    get_weather,
    get_pois,
    get_location,
    get_distance,
    get_text_content,
    tavily_search,
)


class ShortTermMemory:
    """短期记忆，用于存储和检索近期记录"""
    def __init__(self, capacity: int = 10) -> None:
        self.capacity = capacity
        self.memory_items: list[MemoryItem] = []
    
    def add(self, memory_item: MemoryItem) -> None:
        """添加一条记忆，超出容量时移除最旧的（FIFO）"""
        
        self.memory_items.append(memory_item)
        if len(self.memory_items) > self.capacity:
            self.memory_items.pop(0)
    
    def get(self, n: int = 2) -> list[MemoryItem]:
        """返回最近的 n 条记忆"""

        return self.memory_items[-n:]
    
    def clear(self) -> None:
        """清空记忆。"""

        self.memory_items.clear()


draft_system_prompt = """
你是一个起草者，负责根据用户问题生成简洁的初步回答。
"""


class Drafter:
    """起草者：根据用户问题生成初步回答"""
    def __init__(self) -> None:
        llm_client = LLMClient("dashscope")
        self.llm = llm_client.get_llm("qwen3.5-flash")
        self.agent = create_agent(
            model=self.llm,
            system_prompt=draft_system_prompt,
            tools=[
                get_weather,
                get_pois,
                get_location,
                get_distance,
                get_text_content,
                tavily_search
            ]
        )
    
    async def draft(self, user_query: str) -> str:
        """根据用户问题生成初步回答"""

        query = {"messages": [{"role": "user", "content": user_query}]}
        response = await self.agent.ainvoke(query)
        messages = response.get("messages", [])

        return messages[-1].content


review_system_prompt = """
你是一个严格的质量审查者，负责审查当前的回答并给出审查结果和改进建议。

请从以下维度审查回答：
1. **正确性**：回答中的事实信息是否准确。
2. **完整性**：是否完整地回应了用户问题的所有方面。
3. **清晰性**：回答是否结构清晰、易于理解。
4. **实用性**：回答是否提供了用户真正需要的信息。

审查要求：
1. 只有当回答在所有维度上都足够好时，才将is_satisfactory设为true。
2. 当is_satisfactory为false时，suggestions列表不能为空。

用户问题：
{user_query}

当前回答：
{current_response}
"""


class Reviewer:
    """评估者：根据当前回答生成审查评价"""
    def __init__(self) -> None:
        llm_client = LLMClient("zhipu")
        self.llm = llm_client.get_llm("glm-4.5-air").with_structured_output(
            Critique,
            method="function_calling"
        )
    
    async def review(self, user_query: str, current_response: str) -> Critique:
        """根据当前回答生成审查评价"""

        prompt = review_system_prompt.format(user_query=user_query, current_response=current_response)
        response = await self.llm.ainvoke(prompt)

        return response


revise_system_prompt = """
你是质量修订者，负责根据审查结果和改进建议修订当前回答。

你可以使用工具来补充信息，请遵守以下规则：
1. 仔细阅读审查结果和改进建议。
2. 针对性地修改回答，解决审查结果中指出的问题。
3. 如果改进建议指出信息不足，请使用工具补充。
4. 保留原回答中正确的部分，只修改需要改进的地方。
5. 输出修改后的完整回答。
"""

revise_query_template = """
用户问题：
{user_query}

当前回答：
{current_response}

审查结果：
{critique}

改进建议：
{suggestions}

历史回答记录以供参考：
{history_response}

请根据以上反馈修订回答。
"""


class Reviser:
    """修订者：根据审查结果与建议修订回答"""
    def __init__(self) -> None:
        llm_client = LLMClient("deepseek")
        self.llm = llm_client.get_llm("deepseek-chat")
        self.agent = create_agent(
            model=self.llm,
            system_prompt=revise_system_prompt,
            tools=[
                get_weather,
                get_pois,
                get_location,
                get_distance,
                get_text_content,
                tavily_search
            ]
        )
    
    async def revise(
            self, user_query: str, current_response: str, critique: Critique, 
            suggestions: list[str], history_response: str
        ) -> str:
        """根据审查结果与建议修订回答"""

        query = {
            "messages": [{
                "role": "user", 
                "content": revise_query_template.format(
                    user_query=user_query, 
                    current_response=current_response, 
                    critique=critique, 
                    suggestions=suggestions, 
                    history_response=history_response
                )
            }]
        }

        response = await self.agent.ainvoke(query)
        messages = response.get("messages", [])

        return messages[-1].content


class ReflectionAgent:
    """反思Agent：通过"草稿-审查-修订"循环提升回答质量"""
    def __init__(self, max_iterations: int = 3) -> None:
        self.drafter = Drafter()
        self.reviewer = Reviewer()
        self.reviser = Reviser()
        self.memory = ShortTermMemory()
        self.max_iterations = max_iterations
    
    async def run(self, user_query: str) -> str:
        """运行反思循环"""

        # 获取最近记忆内容
        recent_context = self.memory.get(self.max_iterations - 1)

        # 获取历史回答记录
        history_response = []
        for i, item in enumerate(recent_context):
            history_response.append(f"第{i}次回答: {item.response}")
        history_response = "\n\n".join(history_response)

        # 起草者进行初步回答
        print("正在生成初步回答...")
        current_response = await self.drafter.draft(user_query)
        print(f"初步回答：{current_response}")

        # 审查-修订循环
        for i in range(self.max_iterations):
            print(f"正在进行第 {i + 1} 轮审查...")
            # 审查者进行审查
            critique = await self.reviewer.review(user_query, current_response)
            print(f"当前回答是否满足要求？：{critique.is_satisfactory}")
            if critique.is_satisfactory:
                print("审查结果：回答已满足要求，退出循环。")
                break
            print(f"审查评价：{critique.critique}")
            print(f"改进建议：{critique.suggestions}")

            # 修订者进行改进
            current_response = await self.reviser.revise(
                user_query=user_query,
                current_response=current_response,
                critique=critique.critique,
                suggestions=critique.suggestions,
                history_response=history_response
            )
            print(f"改进后的回答：{current_response}")

            # 存储到短期记忆
            self.memory.add(MemoryItem(
                iteration=i,
                query=user_query,
                response=current_response,
                critique=critique,
            ))
        
        return current_response

reflection_agent = ReflectionAgent()
