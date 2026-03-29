import sys
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from agents.plan_execute_agent import plan_execute_agent


async def main():
    user_query = "规划去武汉玩2天的行程"

    # result = await plan_execute_agent.run(user_query)
    # print(result)

    # langgraph调用时传入整个状态
    result = await plan_execute_agent.ainvoke({
        "user_query": user_query,
        "plan": None,  # 初始状态plan为None, 由planner节点生成
        "current_step_index": 0,  # 当前执行步骤索引，初始为0
        "completed_steps": [],  # 初始状态已完成步骤列表为空
        "final_result": None  # 最终结果，初始为None，由summarizer节点生成
    })
    print(result.get("final_result", "未生成最终结果"))

if __name__ == "__main__":
    asyncio.run(main())
