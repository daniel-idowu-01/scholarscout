"""
Central application configuration.

All settings are read from environment variables.
Pydantic Settings validates types and provides defaults.
The singleton `settings` object is imported everywhere — never
read os.environ directly in application code.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Nested settings groups read os.environ directly (they have no env_file),
# so .env must be loaded before any of them is instantiated.
load_dotenv()


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str = "postgresql+asyncpg://scholarscout:scholarscout@localhost:5432/scholarscout"
    sync_url: str = "postgresql+psycopg2://scholarscout:scholarscout@localhost:5432/scholarscout"
    read_replica_url: str | None = None
    pool_size: int = 20
    max_overflow: int = 40
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    celery_url: str = "redis://localhost:6379/1"
    cache_url: str = "redis://localhost:6379/2"
    streams_url: str = "redis://localhost:6379/3"
    max_connections: int = 50
    socket_timeout: int = 5


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    backend: str = "minio"
    endpoint_url: str = "http://localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    region: str = "us-east-1"
    bucket_snapshots: str = "scholarscout-snapshots"
    bucket_assets: str = "scholarscout-assets"
    bucket_exports: str = "scholarscout-exports"
    use_ssl: bool = False


class OpenSearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENSEARCH_")

    url: str = "https://localhost:9200"
    username: str = "admin"
    password: str = "admin"
    verify_certs: bool = False
    index_opportunities: str = "scholarscout-opportunities"
    index_universities: str = "scholarscout-universities"
    shards: int = 3
    replicas: int = 1


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: str = "change-me-jwt-secret-min-64-chars-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30


class LLMSettings(BaseSettings):
    # Single assignment only — a second model_config would overwrite the prefix
    # and silently detach LLM_* env vars from these fields.
    model_config = SettingsConfigDict(env_prefix="LLM_", populate_by_name=True)

    default_provider: str = "anthropic"
    max_tokens_per_call: int = 4096
    monthly_budget_usd: float = 500.0

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_default_model: str = Field(default="gpt-4o-mini", alias="OPENAI_DEFAULT_MODEL")
    openai_extraction_model: str = Field(default="gpt-4o", alias="OPENAI_EXTRACTION_MODEL")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_default_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="ANTHROPIC_DEFAULT_MODEL"
    )
    anthropic_extraction_model: str = Field(
        default="claude-sonnet-4-6", alias="ANTHROPIC_EXTRACTION_MODEL"
    )

    huggingface_api_key: str = Field(default="", alias="HUGGINGFACE_API_KEY")
    huggingface_default_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct", alias="HUGGINGFACE_DEFAULT_MODEL"
    )


class CrawlerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CRAWLER_")

    default_concurrency: int = 5
    default_delay_seconds: float = 2.0
    request_timeout_seconds: int = 30
    max_retries: int = 3
    user_agent: str = "ScholarScoutBot/1.0 (+https://scholarscout.io/bot)"
    respect_robots_txt: bool = True
    max_page_size_mb: int = 10
    playwright_pool_size: int = 5

    priority_new_university: int = 100
    priority_high_ranked: int = 80
    priority_scheduled: int = 50
    priority_refresh: int = 30
    priority_discovery: int = 20


class EmailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMTP_")

    host: str = "localhost"
    port: int = 1025
    username: str = ""
    password: str = ""
    use_tls: bool = False
    from_email: str = Field(default="noreply@scholarscout.io", alias="SMTP_FROM_EMAIL")
    from_name: str = Field(default="ScholarScout", alias="SMTP_FROM_NAME")

    model_config = SettingsConfigDict(env_prefix="SMTP_", populate_by_name=True)


class ObservabilitySettings(BaseSettings):
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.1, alias="SENTRY_TRACES_SAMPLE_RATE")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")

    otel_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(default="scholarscout", alias="OTEL_SERVICE_NAME")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    model_config = SettingsConfigDict(populate_by_name=True)


class FeatureFlags(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FEATURE_")

    llm_extraction: bool = True
    semantic_search: bool = False
    notifications_email: bool = True
    notifications_telegram: bool = False
    recommendations: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-to-a-secure-random-string-min-64-chars"
    app_version: str = "0.1.0"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_prefix: str = "/api"
    api_v1_prefix: str = "/api/v1"

    app_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    app_allowed_hosts: list[str] = ["*"]

    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    storage: StorageSettings = StorageSettings()
    opensearch: OpenSearchSettings = OpenSearchSettings()
    auth: AuthSettings = AuthSettings()
    llm: LLMSettings = LLMSettings()
    crawler: CrawlerSettings = CrawlerSettings()
    email: EmailSettings = EmailSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    features: FeatureFlags = FeatureFlags()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def model_post_init(self, __context: Any) -> None:
        # Re-read sub-settings from the environment after parent init
        self.db = DatabaseSettings()
        self.redis = RedisSettings()
        self.storage = StorageSettings()
        self.opensearch = OpenSearchSettings()
        self.auth = AuthSettings()
        self.llm = LLMSettings()
        self.crawler = CrawlerSettings()
        self.email = EmailSettings()
        self.observability = ObservabilitySettings()
        self.features = FeatureFlags()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
