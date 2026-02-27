"""Unit tests for RequestIDMiddleware and authcore_exception_handler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from authcore.api.v1.middleware.error_handler import authcore_exception_handler
from authcore.api.v1.middleware.request_id import RequestIDMiddleware
from authcore.domain.exceptions import InvalidCredentialsError, UserNotFoundError


@pytest.fixture
def test_app() -> FastAPI:
    """Minimal FastAPI app with RequestIDMiddleware."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/echo")
    async def echo() -> dict[str, str]:
        return {"status": "ok"}

    return app


class TestRequestIDMiddleware:
    async def test_propagates_incoming_request_id(self, test_app: FastAPI) -> None:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
            resp = await client.get("/echo", headers={"X-Request-ID": "my-id-123"})
        assert resp.headers.get("x-request-id") == "my-id-123"

    async def test_generates_uuid_when_header_absent(self, test_app: FastAPI) -> None:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
            resp = await client.get("/echo")
        rid = resp.headers.get("x-request-id")
        assert rid is not None
        # Should be a valid UUID4
        import uuid
        uuid.UUID(rid)  # raises if not valid

    async def test_different_requests_get_different_ids(self, test_app: FastAPI) -> None:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
            r1 = await client.get("/echo")
            r2 = await client.get("/echo")
        assert r1.headers.get("x-request-id") != r2.headers.get("x-request-id")


class TestErrorHandler:
    async def test_returns_problem_json_for_authcore_exception(self) -> None:
        exc = InvalidCredentialsError("bad creds")
        request = MagicMock()
        request.state = MagicMock(spec=[])  # no request_id attribute

        response = await authcore_exception_handler(request, exc)
        assert response.status_code == exc.status_code
        assert response.media_type == "application/problem+json"

        import json
        body = json.loads(response.body)
        assert body["error_code"] == exc.error_code
        assert body["status"] == exc.status_code

    async def test_includes_detail_when_present(self) -> None:
        exc = UserNotFoundError("not found")
        request = MagicMock()
        request.state = MagicMock(spec=[])

        response = await authcore_exception_handler(request, exc)
        import json
        body = json.loads(response.body)
        assert "detail" in body

    async def test_includes_request_id_when_set(self) -> None:
        exc = InvalidCredentialsError()
        request = MagicMock()
        request.state.request_id = "req-abc-123"

        response = await authcore_exception_handler(request, exc)
        import json
        body = json.loads(response.body)
        assert body["request_id"] == "req-abc-123"
