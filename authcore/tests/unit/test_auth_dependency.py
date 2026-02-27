"""Unit tests for get_current_user and require_admin dependencies."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from authcore.api.dependencies.auth import CurrentUser, get_current_user, require_admin
from authcore.domain.exceptions import TokenExpiredError, TokenInvalidError
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.tokens.jwt_service import JWTService


def _make_claims(user_id: uuid.UUID, role: str, jti: str) -> dict[str, object]:
    return {"sub": str(user_id), "role": role, "jti": jti}


class TestGetCurrentUser:
    async def test_valid_token_returns_current_user(
        self, jwt_service: JWTService, redis_client: RedisClient
    ) -> None:
        user_id = uuid.uuid4()
        jti = uuid.uuid4()
        access_token, _ = jwt_service.create_access_token(user_id, "member", jti)

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)
        result = await get_current_user(
            credentials=creds,
            jwt_service=jwt_service,
            redis_client=redis_client,
        )
        assert result.user_id == user_id
        assert result.role == "member"

    async def test_expired_token_raises_401(
        self, jwt_service: JWTService, redis_client: RedisClient
    ) -> None:
        mock_jwt = MagicMock(spec=JWTService)
        mock_jwt.verify_access_token.side_effect = TokenExpiredError("expired")

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired-token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=creds,
                jwt_service=mock_jwt,
                redis_client=redis_client,
            )
        assert exc_info.value.status_code == 401

    async def test_invalid_token_raises_401(
        self, jwt_service: JWTService, redis_client: RedisClient
    ) -> None:
        mock_jwt = MagicMock(spec=JWTService)
        mock_jwt.verify_access_token.side_effect = TokenInvalidError("invalid")

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=creds,
                jwt_service=mock_jwt,
                redis_client=redis_client,
            )
        assert exc_info.value.status_code == 401

    async def test_revoked_jti_raises_401(
        self, jwt_service: JWTService, redis_client: RedisClient
    ) -> None:
        user_id = uuid.uuid4()
        jti = uuid.uuid4()
        access_token, _ = jwt_service.create_access_token(user_id, "member", jti)

        # Blacklist the JTI
        await redis_client.set(f"authcore:jti_blacklist:{jti}", "1")

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=creds,
                jwt_service=jwt_service,
                redis_client=redis_client,
            )
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()


class TestRequireAdmin:
    async def test_admin_user_passes(self) -> None:
        user = CurrentUser(user_id=uuid.uuid4(), role="admin", jti="jti-1")
        result = await require_admin(current_user=user)
        assert result == user

    async def test_member_raises_403(self) -> None:
        user = CurrentUser(user_id=uuid.uuid4(), role="member", jti="jti-2")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=user)
        assert exc_info.value.status_code == 403

    async def test_guest_raises_403(self) -> None:
        user = CurrentUser(user_id=uuid.uuid4(), role="guest", jti="jti-3")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=user)
        assert exc_info.value.status_code == 403
