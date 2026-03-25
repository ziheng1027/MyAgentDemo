from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager

from config.settings import get_settings


class MCPConfig(BaseModel):
    """MCP 服务配置"""

    command: str
    args: list[str]
    env: dict[str, str]


class MCPClient:
    """最小可用的 MCP 客户端"""

    def __init__(self, server_name: str = None) -> None:
        self.settings = get_settings()
        self.server_name = server_name
        
    
    def get_config(self) -> MCPConfig:
        """获取 MCP 服务配置"""

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
        """获取 MCP 服务标准输入输出服务器参数"""

        config = self.get_config()
        return StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )

    @asynccontextmanager
    async def session(self):
        """创建 MCP 会话上下文管理器"""

        async with stdio_client(self.get_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def list_tools(self):
        """获取 MCP 服务可用工具列表"""

        async with self.session() as session:
            result = await session.list_tools()
            return result.tools

    async def call_tool(self, tool_name: str, arguments: dict | None = None):
        """调用 MCP 服务指定工具"""

        async with self.session() as session:
            return await session.call_tool(tool_name, arguments=arguments or {})
