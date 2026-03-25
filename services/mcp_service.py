import json
from langchain.tools import tool

from client.mcp_client import MCPClient


def get_text_content(result) -> str:
    """从 MCP 调用结果中提取第一段文本内容。

    Args:
        result: MCP 工具调用的返回结果对象。

    Returns:
        str: 提取的文本内容，如果不存在则返回空字符串。
    """

    if not getattr(result, "content", None):
        return ""

    first_item = result.content[0]
    text = getattr(first_item, "text", "").strip()

    return text


async def call_mcp_tool(server_name: str, tool_name: str, arguments: dict | None = None):
    """统一调用指定 MCP 服务的指定工具。

    Args:
        server_name (str): MCP 服务器名称。
        tool_name (str): 要调用的工具名称。
        arguments (dict | None): 工具参数，默认为 None。

    Returns:
        MCP 工具调用的原始返回结果。
    """

    client = MCPClient(server_name=server_name)

    return await client.call_tool(tool_name, arguments or {})


@tool
async def get_weather(city: str) -> dict:
    """查询指定城市未来几天的天气并返回精简后的天气信息。

    Args:
        city (str): 城市名称、行政区名称或 adcode，例如 `武汉`、`上海`、`310000`。

    Returns:
        dict: 包含城市名称和预报列表的字典，格式为：
            {
                "city": str,     # 城市名称
                "forecasts": [   # 天气预报列表
                    {
                        "date": str,         # 日期
                        "week": str,         # 星期数字
                        "dayweather": str,   # 白天天气
                        "nightweather": str, # 夜间天气
                        "daytemp": str,      # 白天温度
                        "nighttemp": str     # 夜间温度
                    },
                    ...
                ]
            }
    """

    result = await call_mcp_tool("amap", "maps_weather", {"city": city})
    text = get_text_content(result)
    data = json.loads(text)

    return {
        "city": data.get("city", ""),
        "forecasts": [
            {
                "date": forecast.get("date", ""),
                "week": forecast.get("week", ""),
                "dayweather": forecast.get("dayweather", ""),
                "nightweather": forecast.get("nightweather", ""),
                "daytemp": forecast.get("daytemp", ""),
                "nighttemp": forecast.get("nighttemp", ""),
            }
            for forecast in data.get("forecasts", [])
        ],
    }


@tool
async def get_pois(keywords: str, city: str) -> list[dict]:
    """根据关键词和城市搜索 POI 并返回精简后的地点信息列表。

    Args:
        keywords (str): 地点搜索关键词，例如 `景点`、`咖啡店`、`黄鹤楼`。
        city (str): 搜索所在城市，例如 `武汉`、`上海`。

    Returns:
        list[dict]: 精简后的 POI 列表，格式为：
            [
                {
                    "id": str,         # POI 唯一标识
                    "name": str,       # POI 名称
                    "address": str,    # POI 地址
                    "photo_url": str   # POI 的图片链接；如果没有图片则为空字符串
                },
                ...
            ]
    """

    result = await call_mcp_tool(
        "amap",
        "maps_text_search",
        {"keywords": keywords, "city": city},
    )
    text = get_text_content(result)
    data = json.loads(text)

    return [
        {
            "id": poi.get("id", ""),
            "name": poi.get("name", ""),
            "address": poi.get("address", ""),
            "photo_url": (poi.get("photos") or {}).get("url", ""),
        }
        for poi in data.get("pois", [])
    ]


async def get_location(address: str) -> dict:
    """根据地点名称或结构化地址获取经纬度坐标

    适用场景：
        - 用户提供地点名称，希望获取该地点的经纬度坐标。
        - 在计算距离之前，先把自然语言地址转换为经纬度坐标。

    Args:
        address (str): 待解析的地点名称或结构化地址，例如 `湖北省武汉市黄鹤楼`、`北京市朝阳区望京SOHO`。

    Returns:
        dict: 精简后的坐标结果，格式为：
        {
            "country": "中国",
            "province": "湖北省",
            "city": "武汉市",
            "district": "武昌区",
            "location": "114.3063,30.5478"
        }
    """

    result = await call_mcp_tool("amap", "maps_geo", {"address": address})
    text = get_text_content(result)
    data = json.loads(text)["return"][0]
    
    return {
        "country": data.get("country", ""),
        "province": data.get("province", ""),
        "city": data.get("city", ""),
        "district": data.get("district", ""),
        "location": data.get("location", ""),
    }

@tool
async def get_distance(origins: str, destination: str) -> dict:
    """测量两个经纬度坐标之间的距离并返回结果。

    Args:
        origins (str): 起点坐标，格式必须为 `经度,纬度`，例如 `114.3055,30.5928`。
        destination (str): 终点坐标，格式必须为 `经度,纬度`，例如 `114.3162,30.5810`。

    Returns:
        dict: 距离结果，格式为：
            {
                "origin_id": str,  # 起点编号
                "dest_id": str,    # 终点编号
                "distance": int,   # 距离，单位通常为米
                "duration": int    # 预计耗时，单位通常为秒
            }
    """

    result = await call_mcp_tool(
        "amap",
        "maps_distance",
        {"origins": origins, "destination": destination},
    )
    text = get_text_content(result)
    data = json.loads(text)

    return data.get("results", [{}])[0]


@tool
async def tavily_search(query: str, max_results: int = 5) -> dict:
    """使用 Tavily 进行联网搜索并返回格式化的结果。

    Args:
        query (str): 搜索问题或关键词。
        max_results (int): 期望返回的结果上限，默认 5。

    Returns:
        dict: 包含搜索查询和结果列表的字典，格式为：
            {
                "query": str,   # 搜索的查询内容
                "results": [    # 搜索结果列表
                    {
                        "title": str,   # 结果标题
                        "content": str  # 结果内容摘要
                    },
                    ...
                ]
            }
    """

    result = await call_mcp_tool(
        "tavily",
        "tavily_search",
        {"query": query, "max_results": max_results},
    )
    text = get_text_content(result)
    data = json.loads(text)

    return {
        "query": data.get("query", ""),
        "results": [
            {
                "title": result.get("title", ""),
                "content": result.get("content", ""),
            } 
            for result in data.get("results", [])
        ]
    }
