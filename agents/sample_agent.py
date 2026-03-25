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
你是一个智能助手，能够根据用户的问题调用不同的工具来获取信息。
"""

llm_client = LLMClient("deepseek")
llm = llm_client.get_llm("deepseek-chat")

sample_agent = create_agent(
    model=llm,
    system_prompt=system_prompt,
    tools=[
        get_weather, 
        get_location,
        get_distance,
    ]
)