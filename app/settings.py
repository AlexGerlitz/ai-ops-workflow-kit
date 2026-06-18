from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    app_version: str = "0.2.0"
    git_sha: str = "local"
    deploy_environment: str = "local"
    embedding_dim: int = 64
    top_k: int = 5
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    public_base_url: str = "http://127.0.0.1:8080"
    telegram_bot_token: str | None = None
    telegram_approval_chat_id: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_dry_run: bool = True
    bitrix24_webhook_url: str | None = None
    bitrix24_dry_run: bool = True
    integration_max_attempts: int = 3
    integration_retry_delay_seconds: int = 300
    integration_worker_enabled: bool = False
    integration_worker_interval_seconds: float = 60.0
    integration_worker_batch_size: int = 10


settings = Settings()
