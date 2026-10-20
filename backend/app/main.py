from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import RequestLogMiddleware, configure_logging
from app.core.redis_client import RedisUnavailableError, verify_redis_at_startup


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    # Phase 10 (Task 1): raises and prevents the process from ever serving
    # traffic if Redis is required (staging/production) and unreachable --
    # a no-op in development/test, where Redis has always been optional.
    verify_redis_at_startup(settings)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(RequestLogMiddleware)

    # Phase 9.1 (Task 2): only enforced once TRUSTED_HOSTS is actually set
    # (required by config.py's startup check once environment isn't
    # "development") -- an empty list here would make every Host header
    # valid, same as not having the middleware at all.
    if settings.trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.exception_handler(RedisUnavailableError)
    async def _redis_unavailable(_request: Request, exc: RedisUnavailableError) -> JSONResponse:
        # Phase 10: a mid-runtime Redis outage fails closed on the
        # security-critical token-store paths (see RedisUnavailableError's
        # docstring) rather than a generic 500 -- 503 tells the client this
        # is transient and worth retrying, not that their request was bad.
        return JSONResponse(status_code=503, content={"detail": f"Temporarily unavailable: {exc}"})

    return app


app = create_app()
