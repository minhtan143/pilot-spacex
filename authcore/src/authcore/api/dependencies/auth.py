"""FastAPI dependencies for JWT authentication and session injection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from authcore.container.container import Container
from authcore.domain.exceptions import AuthUnauthorizedError, TokenExpiredError, TokenInvalidError
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.tokens.jwt_service import JWTService

_bearer = HTTPBearer(auto_error=True)

_JTI_PREFIX = "authcore:jti_blacklist:"


@dataclass(frozen=True)
class CurrentUser:
    """Resolved principal from JWT claims."""

    user_id: uuid.UUID
    role: str
    jti: str


@inject
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    jwt_service: JWTService = Depends(Provide[Container.infra.jwt_service]),  # type: ignore[misc]
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
) -> CurrentUser:
    """Extract and validate Bearer token, check JTI blacklist.

    Args:
        credentials: Bearer token from Authorization header.
        jwt_service: Injected JWT service.
        redis_client: Injected Redis client for JTI blacklist check.

    Returns:
        CurrentUser with resolved user_id, role, and jti.

    Raises:
        HTTPException 401: If token is invalid, expired, or revoked.
    """
    try:
        claims = jwt_service.verify_access_token(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (TokenInvalidError, AuthUnauthorizedError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = str(claims.get("jti", ""))
    if await redis_client.exists(f"{_JTI_PREFIX}{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=uuid.UUID(str(claims["sub"])),
        role=str(claims["role"]),
        jti=jti,
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency that enforces admin role.

    Raises:
        HTTPException 403: If user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
