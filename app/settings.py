from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    embedding_dim: int = 64
    top_k: int = 5
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"


settings = Settings()
