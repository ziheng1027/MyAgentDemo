import asyncio
from agents.sample_agent import sample_agent


async def main():
    response = await sample_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user", 
                    "content": "湖北省武汉市武汉轻工大学到湖北省武汉市汉口站的距离有多远？"
                }
            ]
        }
    )
    print(response)

if __name__ == "__main__":
    asyncio.run(main())