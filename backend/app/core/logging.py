"""Request logging (BUILD-142): one line per request, with an ID that's also
returned to the client as X-Request-ID, so an error a user reports can be matched
to the exact log line. Plain key=value text, which any log collector can parse."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("buildos.request")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept an ID from a proxy in front of us, but only a sane-looking one.
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "request_id=%s method=%s path=%s status=500 duration_ms=%.1f",
                request_id, request.method, request.url.path, duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        # Path only, never the query string: it can carry search terms and other user input.
        log = logger.warning if response.status_code >= 500 else logger.info
        log(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id, request.method, request.url.path, response.status_code, duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
