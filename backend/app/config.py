"""
Central configuration management.
All runtime settings are loaded from environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "changeme-supersecret-razorpay-recovery-key"

    # Database: defaults to async SQLite for out-of-the-box zero-setup execution
    database_url: str = "sqlite+aiosqlite:///./revenue_recovery.db"
    database_url_sync: str = "sqlite:///./revenue_recovery.db"

    # Redis (Optional)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # LLM (Gemini)
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "ai-revenue-recovery-agent"

    # Recovery Policies  (all configurable — never hard-coded in logic)
    max_retries: int = 3
    max_customer_messages: int = 3
    recovery_window_days: int = 7
    retry_cooldown_hours: int = 6

    # Batch Processing
    batch_concurrency: int = 25
    llm_concurrency: int = 5
    llm_rate_limit_per_sec: int = 5

    # Classification
    min_confidence_threshold: float = 0.70

    # Mock Gateway
    mock_gateway_seed: int = 42


@lru_cache
def get_settings() -> Settings:
    return Settings()
