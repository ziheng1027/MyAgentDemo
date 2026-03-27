import sys
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from agents.plan_execute_agent import plan_execute_agent




async def main():
    user_query = "100块钱在武汉可以买多少碗热干面？"
    result = await plan_execute_agent.run(user_query)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
