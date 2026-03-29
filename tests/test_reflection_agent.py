import sys
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from agents.reflection_agent import reflection_agent


async def main():
    user_query = "我在武汉轻工大学金银湖校区，明天上午要去黄鹤楼，下午想去一个有特色的地方逛逛，帮我规划一下明天的行程安排，包括交通、时间和注意事项。"
    print(f"用户问题：{user_query}\n")

    # result = await reflection_agent.run(user_query)
    # print(f"\n最终回答：\n{result}")

    # langgraph版本传入的是状态字典
    result = await reflection_agent.ainvoke({
        "user_query": user_query,
        "current_response": "",
        "critique": None,
        "history_response": "",
        "iteration": 0,
        "max_iterations": 3
    })
    # 结果是一个状态字典，包含当前回答和迭代次数等信息
    print(f"\n最终回答：\n{result.get('current_response', '')}")

if __name__ == "__main__":
    asyncio.run(main())