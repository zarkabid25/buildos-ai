import re
from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production"


class Environment(str, Enum):
    """Phase 9.1 (Task 2): a closed, typed set instead of a free-form string.

    The previous `environment: str` field only triggered its production
    safety checks on an exact match against the literal string
    "production" -- a deploy configured as "Production", "prod", or a
    differently-named staging/UAT environment silently skipped every check
    (default JWT secret, example DB password, weak bcrypt, permissive CORS).
    A closed enum can't be misspelled past validation: pydantic rejects any
    value that isn't one of these three at startup, instead of silently
    accepting a typo that would have disabled every safety check."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BuildOS AI"
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql://buildos:buildos@localhost:5432/buildos"
    redis_url: str = "redis://localhost:6379/0"

    # SecretStr so an accidental `logger.info(settings)`, a crash traceback,
    # or a pydantic model dump never prints the real secret -- only
    # "**********". Every call site uses `.get_secret_value()` explicitly,
    # which is the one place the real value is ever read.
    jwt_secret_key: SecretStr = SecretStr(DEFAULT_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    # bcrypt work factor. 12 is the production standard; the test suite lowers it to
    # the minimum (4) because it hashes hundreds of passwords and only checks behaviour.
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    cors_origins: list[str] = ["http://localhost:3000"]
    # Phase 9.1 (Task 2): Starlette's TrustedHostMiddleware allow-list. Empty
    # means "not enforced" (development default) -- staging/production
    # should set this to the real host(s) so a mismatched Host header is
    # rejected before it ever reaches routing.
    trusted_hosts: list[str] = []
    # Served over plain HTTP today (see deploy/OPERATIONS.md -- no reverse
    # proxy/TLS is set up yet). This flag exists so that the moment one is,
    # cookie-based flows (there are none today; auth is bearer-token-only)
    # would get Secure/SameSite=strict automatically rather than needing a
    # second round of hardening later.
    force_https_cookies: bool = False

    storage_dir: str = "./storage_data"
    max_upload_bytes: int = 10 * 1024 * 1024
    # Phase 10 (Task 3): "local" (default, the only backend ever actually
    # used in this project -- no S3 credentials have ever been provisioned)
    # or "s3". Deliberately NOT required to be "s3" in staging/production --
    # unlike Redis/email, nothing in this phase's instructions asked for
    # object storage to be mandatory, and doing so would make every
    # staging/production config refuse to start without real AWS
    # credentials this project has never been given.
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""  # set for a non-AWS S3-compatible provider (MinIO, R2, etc.)
    s3_access_key_id: SecretStr = SecretStr("")
    s3_secret_access_key: SecretStr = SecretStr("")
    s3_presigned_url_expiry_seconds: int = 300

    # Brute-force protection (BUILD-125). Shared across workers via Redis when
    # reachable (app/core/rate_limit.py); falls back to in-process memory otherwise.
    login_max_failures: int = 5
    login_failure_window_seconds: int = 15 * 60
    register_max_per_ip: int = 10
    register_window_seconds: int = 60 * 60
    # Phase 8 public forms -- same mechanism, new keys (app/core/rate_limit.py).
    public_form_max_per_ip: int = 10
    public_form_window_seconds: int = 60 * 60
    # Phase 9 security audit (PLAT-049): refresh was the one auth-adjacent
    # endpoint on all three token systems with no rate limiting at all.
    refresh_max_per_ip: int = 30
    refresh_window_seconds: int = 60 * 60
    # Phase 9 AI narration features (PLAT-048): a per-actor usage cap, separate
    # from the Phase 9.1 monthly plan quota (app/services/ai_quota_service.py).
    ai_narration_max_per_actor: int = 30
    ai_narration_window_seconds: int = 60 * 60

    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "claude-opus-5"
    llm_use_fallbacks: bool = True
    llm_max_tokens: int = 16000
    llm_max_tool_iterations: int = 8

    # Phase 9.1 (Task 3): "console" is the sandbox provider (logs the
    # message and records it as SIMULATED -- real enough to exercise
    # retry-safety and dedup in dev/tests, but not a real inbox; refused
    # outside development/test as of Phase 10). "smtp" needs real
    # credentials below; without them it's reported as NOT_CONFIGURED,
    # never a pretended delivery, same honesty rule as before this phase.
    email_provider: str = "console"
    email_from_address: str = "noreply@buildos.ai"
    # Used only to build links inside emails (invitation/reset URLs) --
    # never read by the API itself for anything security-sensitive.
    app_base_url: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Lets these be set as a plain comma-separated env var
        (CORS_ORIGINS=https://a.com,https://b.com) in addition to JSON,
        since that's how most deploy tooling injects env vars."""
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @model_validator(mode="after")
    def _refuse_unsafe_production_config(self) -> "Settings":
        """BUILD-137 / Phase 9.1 (Task 2): development defaults are fine on a
        laptop and dangerous on a server (anyone could mint a valid token
        with the published default secret). In production -- and now also
        staging, so a staging deploy can't accidentally run with the same
        unsafe defaults production refuses -- fail at startup instead of
        running insecurely."""
        if self.environment in (Environment.DEVELOPMENT, Environment.TEST):
            return self
        problems = []
        secret = self.jwt_secret_key.get_secret_value()
        if secret == DEFAULT_JWT_SECRET or len(secret) < 32:
            problems.append("JWT_SECRET_KEY must be a random value of at least 32 characters")
        if "buildos:buildos@" in self.database_url:
            problems.append("DATABASE_URL still uses the example password")
        if self.bcrypt_rounds < 12:
            problems.append("BCRYPT_ROUNDS must be at least 12")
        if not self.cors_origins or any("localhost" in origin for origin in self.cors_origins):
            problems.append("CORS_ORIGINS must list the real frontend address, not localhost")
        if not self.trusted_hosts:
            problems.append("TRUSTED_HOSTS must list the real host(s)")
        # Phase 10 (Task 2): the console provider is a real, inspectable
        # sandbox -- exactly why it must never be mistaken for production
        # delivery. Only a real provider is allowed once staging/production.
        if self.email_provider == "console":
            problems.append("EMAIL_PROVIDER must be 'smtp' (or another real provider), not the 'console' sandbox")
        if problems:
            raise ValueError(f"Refusing to start in {self.environment.value}: " + "; ".join(problems))
        return self

    def __repr__(self) -> str:
        """Redacts DATABASE_URL's password too, not just the SecretStr
        fields -- so an uncaught exception's traceback (which can print a
        local variable's repr) or a stray `logger.info(settings)` can never
        leak either secret, matching the "no secrets in logs" rule."""
        safe_db_url = re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", self.database_url)
        fields = ", ".join(
            f"{name}={value!r}" if name != "database_url" else f"database_url={safe_db_url!r}"
            for name, value in self.__dict__.items()
        )
        return f"Settings({fields})"

    __str__ = __repr__


@lru_cache
def get_settings() -> Settings:
    return Settings()
