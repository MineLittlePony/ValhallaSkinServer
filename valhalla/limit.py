from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    storage_options={"ssl_cert_reqs": "none"},
)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Build a simple JSON response that includes the details of the rate limit
    that was hit. If no limit is hit, the countdown is added to headers.
    """
    response = JSONResponse(
        {
            "error": "RateLimitExceeded",
            "detail": f"Rate limit exceeded: {exc.detail}",
        },
        status_code=429,
    )
    return request.app.state.limiter._inject_headers(  # noqa: SLF001
        response, request.state.view_rate_limit
    )


def setup(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
