"""RFC 7807 problem+json error handler for AuthCore domain exceptions."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from authcore.domain.exceptions import AuthCoreException


async def authcore_exception_handler(
    request: Request, exc: AuthCoreException
) -> JSONResponse:
    """Translate AuthCoreException subclasses to RFC 7807 problem+json responses.

    Args:
        request: Incoming FastAPI request (used for request_id state).
        exc: Domain exception to translate.

    Returns:
        JSONResponse with Content-Type application/problem+json.
    """
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, object] = {
        "type": f"https://authcore.local/errors/{exc.error_code.lower()}",
        "title": exc.title,
        "status": exc.status_code,
        "error_code": exc.error_code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    if request_id:
        body["request_id"] = request_id

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )
