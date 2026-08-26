import os
from functools import lru_cache
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically locate and load .env if present
_env_path = find_dotenv(usecwd=True)
if _env_path:
    load_dotenv(_env_path, override=False)
else:
    # Check backend/.env
    _backend_env = Path(__file__).resolve().parent.parent / ".env"
    if _backend_env.exists():
        load_dotenv(_backend_env, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
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
    llm_model: str = "gemini-3.6-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024

    # LangSmith
    langchain_tracing_v2: bool = True
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
    s = Settings()
    # Propagate LangSmith & Gemini config to os.environ for LangGraph and LangChain auto-tracing
    if s.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if s.langchain_tracing_v2 else "false"
        os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langchain_project
    if s.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = s.gemini_api_key
    return s
