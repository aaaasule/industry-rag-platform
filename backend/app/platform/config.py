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
    # PDF OCR 文档内并行度（Celery chord 页级任务后置）
    parse_ocr_workers: int = 4

    # 认证
    # HS256 要求密钥不短于 32 字节，否则 PyJWT 会告警且强度不足
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-0123456789abcdef")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7
    # 接入点凭证 Fernet 密钥；local 可空并回退 jwt_secret
    credential_secret: SecretStr = SecretStr("")

    # 模型接入（默认 fake，不产生外部调用）
    llm_provider: Literal["fake", "openai_compatible"] = "fake"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o-mini"
    embedding_provider: Literal["fake", "openai_compatible"] = "fake"
    # 空则回退 llm_base_url / llm_api_key（单厂商场景）
    embedding_base_url: str = ""
    embedding_api_key: SecretStr = SecretStr("")
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 10
    # None = 跟随 embedding_provider
    rerank_provider: Literal["fake", "openai_compatible"] | None = None
    rerank_base_url: str = ""
    rerank_api_key: SecretStr = SecretStr("")
    rerank_model: str = "qwen3-rerank"
    rerank_path: str = "/reranks"
    # None = 真实 Embedding+Rerank 时默认开，否则关
    retrieval_rerank_default: bool | None = None
    llm_timeout_seconds: int = 60

    # 限流（≤0 关闭对应规则）
    rate_limit_user_per_minute: int = 20
    rate_limit_tenant_chat_concurrency: int = 10

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

    @property
    def resolved_embedding_base_url(self) -> str:
        return self.embedding_base_url or self.llm_base_url

    @property
    def resolved_embedding_api_key(self) -> str:
        key = self.embedding_api_key.get_secret_value()
        return key or self.llm_api_key.get_secret_value()

    @property
    def resolved_rerank_provider(self) -> Literal["fake", "openai_compatible"]:
        if self.rerank_provider is not None:
            return self.rerank_provider
        return self.embedding_provider

    @property
    def resolved_rerank_base_url(self) -> str:
        return self.rerank_base_url or self.resolved_embedding_base_url

    @property
    def resolved_rerank_api_key(self) -> str:
        key = self.rerank_api_key.get_secret_value()
        return key or self.resolved_embedding_api_key

    @property
    def effective_rerank_default(self) -> bool:
        if self.retrieval_rerank_default is not None:
            return self.retrieval_rerank_default
        return self.embedding_provider != "fake" and self.resolved_rerank_provider != "fake"

    @property
    def resolved_credential_secret(self) -> str:
        explicit = self.credential_secret.get_secret_value()
        if explicit:
            return explicit
        if self.is_local:
            return self.jwt_secret.get_secret_value()
        raise ValueError("非 local 环境必须设置 IRP_CREDENTIAL_SECRET")


@lru_cache
def get_settings() -> Settings:
    """进程内单例。测试中可通过 get_settings.cache_clear() 重置。"""
    return Settings()
