import asyncio
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.validators import ResponseValidationError

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: float = 30.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "Request timed out",
                extra={"request_id": request_id, "path": request.url.path, "timeout": self.timeout},
            )
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )


async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    if isinstance(exc, ResponseValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )
    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )
