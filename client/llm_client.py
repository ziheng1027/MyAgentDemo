from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from config.settings import get_settings


class LLMConfig(BaseModel):
    """统一的 LLM 连接配置"""

    provider: str
    base_url: str
    api_key: str


class LLMClient:
    """LLM 客户端类，负责根据配置创建模型实例"""

    def __init__(self, provider: str, temperature: float = 0.7, timeout: int = 30) -> None:
        self.settings = get_settings()
        self.provider = provider
        self.temperature = temperature
        self.timeout = timeout
    
    def get_config(self) -> LLMConfig:
        """返回当前启用的 LLM 配置。"""

        base_url_field = f"{self.provider.lower()}_base_url"
        api_key_field = f"{self.provider.lower()}_api_key"
        
        base_url = getattr(self.settings, base_url_field)
        api_key = getattr(self.settings, api_key_field)

        if not base_url or not api_key:
            raise ValueError(
                f"[{self.provider}] 配置缺失，请检查 {base_url_field} 和 {api_key_field}"
            )
        
        config = LLMConfig(
            provider=self.provider,
            base_url=base_url,
            api_key=api_key,
        )
        return config

    def get_llm(self, llm_name: str) -> ChatOpenAI:
        """返回统一配置的聊天模型实例"""

        config = self.get_config()
        self.llm_name = llm_name

        llm = ChatOpenAI(
            model=llm_name,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=self.temperature,
            timeout=self.timeout
        )
        return llm
