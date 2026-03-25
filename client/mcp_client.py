from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager

from config.settings import get_settings


class MCPConfig(BaseModel):
    command: str
    args: list[str]
    env: dict[str, str]


class MCPClient:
    """最小可用的 MCP 客户端。"""

    def __init__(self, server_name: str = None) -> None:
        self.settings = get_settings()
        self.server_name = server_name
        
    
    def get_config(self) -> MCPConfig:
        if self.server_name == "amap":
            return MCPConfig(
                command="npx.cmd",
                args=["-y", "@amap/amap-maps-mcp-server"],
                env={"AMAP_MAPS_API_KEY": self.settings.amap_api_key or ""}
            )
        
        if self.server_name == "tavily":
            return MCPConfig(
                command="npx.cmd",
                args=[
                    "-y", "mcp-remote",
                    f"https://mcp.tavily.com/mcp/?tavilyApiKey={self.settings.tavily_api_key}",
                ],
                env={}
            )
        
        raise ValueError("不支持的 MCP 服务")
    
    def get_server_params(self) -> StdioServerParameters:
        config = self.get_config()
        return StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )

    @asynccontextmanager
    async def session(self):
        async with stdio_client(self.get_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def list_tools(self):
        async with self.session() as session:
            result = await session.list_tools()
            return result.tools

    async def call_tool(self, tool_name: str, arguments: dict | None = None):
        async with self.session() as session:
            return await session.call_tool(tool_name, arguments=arguments or {})
