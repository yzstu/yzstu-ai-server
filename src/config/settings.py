import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constant import PROJECT_ROOT


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LLMSettings(BaseSettings):
    class ModelSettings(BaseSettings):
        intent: str
        tool_calling: str = "deepseek-ai/DeepSeek-V3.2-Exp"
    host: str
    key: str
    model: ModelSettings

    def get_key(self) -> str:
        return self.key


class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0

class Settings(BaseSettings):
    # 环境标识 (使用环境变量 ENVIRONMENT 指定)
    environment: str = os.getenv('ENVIRONMENT', Environment.DEVELOPMENT.value)
    app_name: str = "YZSTU AI Server"
    secret_key: str = Field(default="dev-secret-key-change-in-production")

    """服务器配置类"""
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    log_level: str = "INFO"

    # SSE配置
    sse_endpoint: str = "/sse"
    heartbeat_interval: int = 30

    # llm相关配置
    llm: LLMSettings

    model_config = SettingsConfigDict(
        # 按优先级加载环境文件
        env_file=(
            PROJECT_ROOT / f".env.{environment}.local",  # .env.development.local
            PROJECT_ROOT / ".env",  # 默认
            PROJECT_ROOT / ".env.local",  # 本地覆盖
            PROJECT_ROOT / f".env.{environment}",  # .env.development

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