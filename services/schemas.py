from pydantic import BaseModel, Field


class WeatherItem(BaseModel):
    """天气信息项"""
    date: str = Field(description="日期，格式为 YYYY-MM-DD")
    dayweather: str = Field(description="白天天气")
    nightweather: str = Field(description="晚上天气")
    daytemp: str = Field(description="白天温度")
    nighttemp: str = Field(description="晚上温度")


class WeatherOutput(BaseModel):
    """get_weather工具输出"""
    city: str = Field(description="城市")
    weather: list[WeatherItem] = Field(description="天气信息列表")


class POIItem(BaseModel):
    """POI信息项"""
    name: str = Field(description="POI名称")
    address: str = Field(description="POI地址")
    photo_url: str = Field(description="POI图片链接")


class POISearchOutput(BaseModel):
    """get_pois工具输出"""
    pois: list[POIItem] = Field(description="POI信息列表")


class LocationOutput(BaseModel):
    """get_location工具输出"""
    country: str = Field(description="国家")
    province: str = Field(description="省份")
    city: str = Field(description="城市")
    district: str = Field(description="区县")
    location: str = Field(description="经纬度坐标")


class DistanceOutput(BaseModel):
    """get_distance工具输出"""
    distance: str = Field(description="距离，单位为米")
    duration: str = Field(description="耗时，单位为秒")


class TavilySearchOutput(BaseModel):
    """tavily_search工具输出"""
    results: list[dict] = Field(description="搜索结果列表")