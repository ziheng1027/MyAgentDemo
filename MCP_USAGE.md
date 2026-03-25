# 在当前项目中连接并使用 MCP 工具

这个项目现在已经补上了一个最小可运行的 MCP 客户端链路：

1. 在 [`config/settings.py`](D:\YZH\Item\Agent\MyDemo\config\settings.py) 里维护 `mcp_servers`
2. 在 [`client/mcp_client.py`](D:\YZH\Item\Agent\MyDemo\client\mcp_client.py) 里建立 MCP 连接
3. 在 [`main.py`](D:\YZH\Item\Agent\MyDemo\main.py) 里演示列工具和调工具

## 1. 你贴的配置是什么意思

你给出的配置本质上是在描述一个 **stdio 型 MCP 服务**：

```json
{
  "mcpServers": {
    "amap-mcp-server": {
      "command": "npx",
      "args": ["amap-mcp-server"],
      "env": {
        "AMAP_MAPS_API_KEY": "your valid amap maps api key"
      }
    }
  }
}
```

含义如下：

- `command`: 启动 MCP server 的命令
- `args`: 命令参数
- `env`: 启动这个 server 时注入的环境变量

在 Python 里，我们要做的事情就是：

1. 用 `StdioServerParameters` 把这组配置描述出来
2. 用 `stdio_client(...)` 启动这个进程
3. 用 `ClientSession(...)` 建立 MCP 会话
4. `initialize()`
5. `list_tools()` / `call_tool()`

## 2. 为什么这里用了 `npx.cmd`

你的环境是 Windows + PowerShell，并且当前机器禁用了 `npx.ps1` 脚本执行。

所以这里不能直接依赖：

```json
"command": "npx"
```

更稳的写法是：

```json
"command": "npx.cmd"
```

这样可以绕开 PowerShell 的脚本执行限制。

## 3. 项目里现在怎么写的

默认在配置中注册了一个名为 `amap` 的 MCP 服务：

```python
"amap": {
    "command": "npx.cmd",
    "args": ["-y", "@amap/amap-maps-mcp-server"],
    "env": {
        "AMAP_MAPS_API_KEY": amap_api_key,
    },
}
```

你后面如果要接别的 MCP 服务，只需要继续往 `mcp_servers` 里加。

## 4. 怎么运行

只列出工具：

```powershell
python main.py --server amap
```

列出工具并调用某个工具：

```powershell
python main.py --server amap --tool tool_name --arguments "{\"keyword\":\"咖啡\"}"
```

## 5. 关键代码在哪

MCP 连接核心在 [`client/mcp_client.py`](D:\YZH\Item\Agent\MyDemo\client\mcp_client.py)：

```python
server_params = StdioServerParameters(
    command=self.server_config.command,
    args=self.server_config.args,
    env=env,
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
```

工具列表：

```python
result = await session.list_tools()
```

工具调用：

```python
result = await session.call_tool(tool_name, arguments=arguments or {})
```

## 6. 当前要注意的一点

我在本机实际验证时，发现你原文里的：

```text
amap-mcp-server
```

这个 npm 包名目前会返回 404，不能直接运行。

这意味着：

- 你的配置结构是对的
- 但 `args` 里的包名需要替换成一个真实存在的 MCP server

如果你已经有自己本地的高德 MCP server，也可以改成：

```json
{
  "command": "node",
  "args": ["./servers/amap/index.js"]
}
```

或者：

```json
{
  "command": "python",
  "args": ["./servers/amap_server.py"]
}
```

也就是说，MCP 客户端并不关心 server 是 npm、python 还是 node，只要它能通过 stdio 说 MCP 协议就行。
