"""应用配置。

全部走环境变量，启动时强类型校验，失败即崩溃（fail fast）。不允许带着错误
配置半可用地跑起来——那种状态下的报错会出现在离根因很远的地方。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IRP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = "local"
    debug: bool = False

    # 基础设施
    # 应用连接用的角色必须是非超级用户，否则 RLS 会被无声绕过
    database_url: str = "postgresql+asyncpg://irp_app:irp_app@127.0.0.1:5433/irp"
    # 迁移需要 DDL 权限，用属主角色；留空则回退到 database_url
    database_migration_url: str = ""
    database_pool_size: int = 10
    database_echo: bool = False
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "irp-documents"
    s3_access_key: SecretStr = SecretStr("minioadmin")
    s3_secret_key: SecretStr = SecretStr("minioadmin")
    s3_presign_ttl_seconds: int = 900

    # 认证
    # HS256 要求密钥不短于 32 字节，否则 PyJWT 会告警且强度不足
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-0123456789abcdef")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7

    # 模型接入（M0 阶段用 fake，不产生外部调用）
    llm_provider: Literal["fake", "openai_compatible"] = "fake"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o-mini"
    embedding_provider: Literal["fake", "openai_compatible"] = "fake"
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024
    llm_timeout_seconds: int = 60

    # 可观测性
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("jwt_secret")
    @classmethod
    def _reject_default_secret_outside_local(cls, v: SecretStr, info: ValidationInfo) -> SecretStr:
        env = info.data.get("environment", "local")
        if env != "local" and v.get_secret_value().startswith("dev-only-change-me"):
            raise ValueError("生产/预发环境必须显式设置 IRP_JWT_SECRET")
        return v

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """进程内单例。测试中可通过 get_settings.cache_clear() 重置。"""
    return Settings()
