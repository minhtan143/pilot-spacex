"""X-Request-ID middleware: propagate or generate a request correlation ID."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID to every request and response.

    If the incoming request has an X-Request-ID header, it is forwarded.
    Otherwise, a new UUID4 is generated. The ID is available via
    ``request.state.request_id`` in route handlers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers[_HEADER] = request_id
        return response
