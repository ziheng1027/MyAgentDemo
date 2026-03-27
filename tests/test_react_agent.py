import sys
import asyncio
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
from agents.react_agent import react_agent



async def main():
    user_query = "从武汉光谷广场到武汉轻工大学有多远？"
    messages = [{"role": "user", "content": user_query}]
    response = await react_agent.ainvoke({"messages": messages})
    messages = response.get("messages", [])
    
    print("user query:", user_query, "\n")
    for msg in messages[: -1]:
        if isinstance(msg, AIMessage):
            print("agent thought:", msg.content, "\n")
            print("agent action:", msg.tool_calls, "\n")
        elif isinstance(msg, ToolMessage):
            print("agent observation:", msg.content, "\n")
    print("agent answer:", messages[-1].content, "\n")

if __name__ == "__main__":
    asyncio.run(main())