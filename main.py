import asyncio
import json

from client.mcp_client import MCPClient
from services.mcp_service import (
    get_weather, 
    get_pois, 
    get_distance,
    get_text_content, 
    tavily_search
)


async def main():
    result = await tavily_search(query="武汉旅行路线推荐", max_results=2)
    print(result)
    print(type(result))


if __name__ == "__main__":
    
    asyncio.run(main())
