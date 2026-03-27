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


system_prompt = """
你是一个遵循 思考->行动->观察 模式的智能助手。

你在回答问题时需要遵循以下流程：
1. 分析当前问题。
2. 选择合适的工具并执行。
3. 观察工具执行结果。
4. 重复前3步直到你认为当前的信息足以给出最终回答。
5. 给出你的最终回答。
"""

llm_client = LLMClient("zhipu")
llm = llm_client.get_llm("glm-5-turbo")

react_agent = create_agent(
    model=llm,
    system_prompt=system_prompt,
    tools=[
        get_weather, 
        get_pois, 
        get_location,
        get_distance,
        get_text_content, 
        tavily_search,
    ],
)
