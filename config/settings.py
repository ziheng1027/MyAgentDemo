"""项目配置读取与归一化。"""

from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置对象。"""

    # pydantic v2固定使用model_config属性
    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8"
    )

    llm_provider: str = Field(default="deepseek", alias="LLM_PROVIDER")
    llm_name: str = Field(default="deepseek-chat", alias="LLM_NAME")

    zhipu_base_url: str | None = Field(default=None, alias="ZHIPU_BASE_URL")
    zhipu_api_key: str | None = Field(default=None, alias="ZHIPU_API_KEY")

    dashscope_base_url: str | None = Field(default=None, alias="DASHSCOPE_BASE_URL")
    dashscope_api_key: str | None = Field(default=None, alias="DASHSCOPE_API_KEY")

    deepseek_base_url: str | None = Field(default=None, alias="DEEPSEEK_BASE_URL")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")

    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    amap_api_key: str | None = Field(default=None, alias="AMAP_API_KEY")


@lru_cache
def get_settings() -> Settings:
    """缓存配置，避免重复读取环境变量。"""

    return Settings()
