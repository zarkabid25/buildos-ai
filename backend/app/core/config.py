from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BuildOS AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql://buildos:buildos@localhost:5432/buildos"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]

    storage_dir: str = "./storage_data"
    max_upload_bytes: int = 10 * 1024 * 1024

    llm_api_key: str = ""
    llm_model: str = "claude-opus-5"
    llm_use_fallbacks: bool = True
    llm_max_tokens: int = 16000
    llm_max_tool_iterations: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
