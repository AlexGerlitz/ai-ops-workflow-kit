from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    app_version: str = "0.2.0"
    git_sha: str = "local"
    deploy_environment: str = "local"
    embedding_dim: int = 64
    top_k: int = 5
    llm_provider: str = "auto"
    llm_timeout_seconds: float = 30.0
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    transcription_provider: str = "local_stub"
    transcription_dry_run: bool = True
    whisper_model: str = "whisper-1"
    deepgram_api_key: str | None = None
    deepgram_model: str = "nova-3"
    public_base_url: str = "http://127.0.0.1:8080"
    telegram_bot_token: str | None = None
    telegram_approval_chat_id: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_dry_run: bool = True
    google_drive_credentials_json: str | None = None
    google_drive_dry_run: bool = True
    bitrix24_webhook_url: str | None = None
    bitrix24_dry_run: bool = True
    integration_max_attempts: int = 3
    integration_retry_delay_seconds: int = 300
    integration_worker_enabled: bool = False
    integration_worker_interval_seconds: float = 60.0
    integration_worker_batch_size: int = 10


settings = Settings()
