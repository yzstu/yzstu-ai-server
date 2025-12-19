import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.constant import Environment, PROJECT_ROOT

class MCPSettings(BaseSettings):
    host: str = "http://localhost"
    port: int = 8000

    def get_sse_url(self) -> str:
        return f"{self.host}:{self.port}/sse"

class LLMSettings(BaseSettings):
    class ModelSettings(BaseSettings):
        intent: str
        tool_calling: str = "deepseek-ai/DeepSeek-V3.2-Exp"
    host: str
    key: str
    model: ModelSettings

    def get_key(self) -> str:
        return self.key

class LoggerSettings(BaseSettings):
    level: str = "INFO"
    dir: str = "./logs/"


class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0

class Settings(BaseSettings):
    # 环境标识 (使用环境变量 ENVIRONMENT 指定)
    environment: str = os.getenv('ENVIRONMENT', Environment.DEVELOPMENT.value)
    app_name: str = "yzstu-ai-server"
    secret_key: str = Field(default="dev-secret-key-change-in-production")

    """服务器配置类"""
    host: str = "0.0.0.0"
    port: int = 8001

    logger: LoggerSettings

    # SSE配置
    sse_endpoint: str = "/sse"
    heartbeat_interval: int = 30

    # llm相关配置
    llm: LLMSettings

    mcp_life: MCPSettings

    model_config = SettingsConfigDict(
        # 按优先级加载环境文件
        env_file=(
            PROJECT_ROOT / ".env",  # 默认
            PROJECT_ROOT / ".env.local",  # 本地覆盖
            PROJECT_ROOT / f".env.{environment}",  # .env.development
            PROJECT_ROOT / f".env.{environment}.local",  # .env.development.local
        ),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # 支持嵌套变量：DATABASE__HOST
        case_sensitive=False,
        extra="ignore",
    )


# 全局配置实例
@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（带缓存）"""
    return Settings()