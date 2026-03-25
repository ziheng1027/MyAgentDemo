import asyncio
from langchain_core.messages import AIMessage

from agents.sample_agent import sample_agent


async def main():
    response = await sample_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user", 
                    "content": "武汉今天的天气怎么样？"
                }
            ]
        }
    )
    messages = response.get("messages", [])
    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
    print(ai_messages[-1].content)

if __name__ == "__main__":
    asyncio.run(main())