"""
Tests for RequestIDMiddleware, TimeoutMiddleware, and global_exception_handler.

A minimal FastAPI app is assembled here with only the middleware under test
and simple stub routes. This avoids triggering the full app lifespan (DB,
OpenAI, LangSmith) while exercising the real middleware classes.
"""

import asyncio
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import (
    RequestIDMiddleware,
    TimeoutMiddleware,
    global_exception_handler,
)
from app.core.validators import ResponseValidationError


# ---------------------------------------------------------------------------
# Minimal test app factory
# ---------------------------------------------------------------------------


def make_app(timeout: float = 30.0) -> FastAPI:
    """Return a bare FastAPI app with only the middleware under test."""
    app = FastAPI()

    # Mirror the registration order in main.py (LIFO: last registered = first executed)
    app.add_middleware(TimeoutMiddleware, timeout=timeout)
    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(10)
        return {"status": "ok"}

    @app.get("/raise-validation-error")
    async def raise_validation_error():
        raise ResponseValidationError("Draft too short")

    @app.get("/raise-unhandled")
    async def raise_unhandled():
        raise RuntimeError("something went very wrong")

    return app


# ---------------------------------------------------------------------------
# RequestIDMiddleware
# ---------------------------------------------------------------------------


class TestRequestIDMiddleware:
    def setup_method(self):
        self.client = TestClient(make_app(), raise_server_exceptions=False)

    def test_response_always_has_x_request_id_header(self):
        """Every response must carry an X-Request-ID header."""
        r = self.client.get("/ok")
        assert "x-request-id" in r.headers

    def test_generated_request_id_is_valid_uuid(self):
        """When the client sends no X-Request-ID, the middleware generates a UUID."""
        r = self.client.get("/ok")
        request_id = r.headers["x-request-id"]
        # Raises ValueError if not a valid UUID
        uuid.UUID(request_id)

    def test_provided_request_id_is_echoed_back(self):
        """When the client provides X-Request-ID, it must be returned unchanged."""
        custom_id = "my-trace-id-123"
        r = self.client.get("/ok", headers={"X-Request-ID": custom_id})
        assert r.headers["x-request-id"] == custom_id

    def test_different_requests_get_different_ids(self):
        """Without a client-supplied ID, each request should get a unique ID."""
        id_1 = self.client.get("/ok").headers["x-request-id"]
        id_2 = self.client.get("/ok").headers["x-request-id"]
        assert id_1 != id_2


# ---------------------------------------------------------------------------
# TimeoutMiddleware
# ---------------------------------------------------------------------------


class TestTimeoutMiddleware:
    def test_fast_request_passes_through(self):
        """A request that completes within the timeout must return normally."""
        client = TestClient(make_app(timeout=5.0), raise_server_exceptions=False)
        r = client.get("/ok")
        assert r.status_code == 200

    def test_slow_request_returns_504(self):
        """A request that exceeds the timeout must return 504 Gateway Timeout."""
        client = TestClient(make_app(timeout=0.01), raise_server_exceptions=False)
        r = client.get("/slow")
        assert r.status_code == 504

    def test_timeout_response_body_contains_detail(self):
        """The 504 body must include a 'detail' key describing the timeout."""
        client = TestClient(make_app(timeout=0.01), raise_server_exceptions=False)
        r = client.get("/slow")
        data = r.json()
        assert "detail" in data
        assert "timed out" in data["detail"].lower()

    def test_timeout_response_body_contains_request_id(self):
        """The 504 body must include a 'request_id' for traceability."""
        client = TestClient(make_app(timeout=0.01), raise_server_exceptions=False)
        r = client.get("/slow")
        data = r.json()
        assert "request_id" in data

    def test_timeout_response_has_x_request_id_header(self):
        """Even on timeout the X-Request-ID header must be present."""
        client = TestClient(make_app(timeout=0.01), raise_server_exceptions=False)
        r = client.get("/slow")
        assert "x-request-id" in r.headers


# ---------------------------------------------------------------------------
# global_exception_handler
# ---------------------------------------------------------------------------


class TestGlobalExceptionHandler:
    def setup_method(self):
        self.client = TestClient(make_app(), raise_server_exceptions=False)

    def test_response_validation_error_returns_422(self):
        """ResponseValidationError must map to HTTP 422 Unprocessable Entity."""
        r = self.client.get("/raise-validation-error")
        assert r.status_code == 422

    def test_response_validation_error_body_contains_detail(self):
        """422 body must include the original error message in 'detail'."""
        r = self.client.get("/raise-validation-error")
        data = r.json()
        assert "detail" in data
        assert "too short" in data["detail"].lower()

    def test_response_validation_error_body_contains_request_id(self):
        """422 body must include a 'request_id' for correlation."""
        r = self.client.get("/raise-validation-error")
        assert "request_id" in r.json()

    def test_unhandled_exception_returns_500(self):
        """Any unhandled exception must be caught and return HTTP 500."""
        r = self.client.get("/raise-unhandled")
        assert r.status_code == 500

    def test_unhandled_exception_body_contains_detail(self):
        """500 body must include a generic 'detail' message (not the raw traceback)."""
        r = self.client.get("/raise-unhandled")
        data = r.json()
        assert "detail" in data
        assert "internal server error" in data["detail"].lower()

    def test_unhandled_exception_body_contains_request_id(self):
        """500 body must include a 'request_id' for traceability."""
        r = self.client.get("/raise-unhandled")
        assert "request_id" in r.json()

    def test_error_response_carries_x_request_id_header(self):
        """Error responses must carry the X-Request-ID header."""
        r = self.client.get("/raise-validation-error")
        assert "x-request-id" in r.headers

    def test_provided_request_id_appears_in_error_body(self):
        """When client provides X-Request-ID, it must appear in the error body."""
        custom_id = "debug-session-42"
        r = self.client.get(
            "/raise-validation-error",
            headers={"X-Request-ID": custom_id},
        )
        assert r.json()["request_id"] == custom_id
