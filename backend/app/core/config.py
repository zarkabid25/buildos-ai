from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BuildOS AI"
    environment: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql://buildos:buildos@localhost:5432/buildos"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]

    storage_dir: str = "./storage_data"
    max_upload_bytes: int = 10 * 1024 * 1024

    # Brute-force protection (BUILD-125). In-memory, so per process; see app/core/rate_limit.py.
    login_max_failures: int = 5
    login_failure_window_seconds: int = 15 * 60
    register_max_per_ip: int = 10
    register_window_seconds: int = 60 * 60

    llm_api_key: str = ""
    llm_model: str = "claude-opus-5"
    llm_use_fallbacks: bool = True
    llm_max_tokens: int = 16000
    llm_max_tool_iterations: int = 8


    @model_validator(mode="after")
    def _refuse_unsafe_production_config(self) -> "Settings":
        """BUILD-137: development defaults are fine on a laptop and dangerous on a
        server (anyone could mint a valid token with the published default secret).
        In production, fail at startup instead of running insecurely."""
        if self.environment != "production":
            return self
        problems = []
        if self.jwt_secret_key == DEFAULT_JWT_SECRET or len(self.jwt_secret_key) < 32:
            problems.append("JWT_SECRET_KEY must be a random value of at least 32 characters")
        if "buildos:buildos@" in self.database_url:
            problems.append("DATABASE_URL still uses the example password")
        if not self.cors_origins or any("localhost" in origin for origin in self.cors_origins):
            problems.append("CORS_ORIGINS must list the real frontend address, not localhost")
        if problems:
            raise ValueError("Refusing to start in production: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
