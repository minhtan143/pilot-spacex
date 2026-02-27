"""CQRS service: rotate refresh token with family theft detection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from authcore.config import Settings
from authcore.domain.exceptions import TokenFamilyRevokedError, TokenInvalidError
from authcore.domain.models.refresh_token import RefreshTokenEntity
from authcore.domain.services.token_family import TokenFamilyPolicy
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.tokens.jwt_service import JWTService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RefreshTokenPayload:
    """Input for token refresh."""

    raw_refresh_token: str
    ip_address: str = "unknown"


@dataclass(frozen=True)
class RefreshTokenResult:
    """Output of token rotation."""

    access_token: str
    refresh_token: str
    token_type: str
    user_id: uuid.UUID


class RefreshTokenService:
    """Rotate a refresh token: detect reuse attacks, revoke old, issue new pair."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        audit_repo: AuditLogRepository,
        jwt_service: JWTService,
        settings: Settings,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._audit_repo = audit_repo
        self._jwt = jwt_service
        self._settings = settings

    async def execute(self, payload: RefreshTokenPayload) -> RefreshTokenResult:
        """Rotate refresh token and issue new JWT pair.

        Args:
            payload: Raw refresh token string and client IP.

        Returns:
            RefreshTokenResult with fresh access and refresh tokens.

        Raises:
            TokenInvalidError: If the token is unknown or expired.
            TokenFamilyRevokedError: If a reuse attack is detected (family revoked).
        """
        # 1. Hash and look up stored token
        token_hash = JWTService.hash_token(payload.raw_refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)
        if stored is None or TokenFamilyPolicy.is_expired(stored):
            raise TokenInvalidError("Refresh token is invalid or expired")

        # 2. Detect reuse attack — token already revoked means family is compromised
        if TokenFamilyPolicy.is_reuse_attack(stored):
            await self._token_repo.revoke_family(stored.family_id)
            await self._audit_repo.append(
                stored.user_id,
                "TOKEN_REUSE_ATTACK",
                {"family_id": str(stored.family_id)},
                payload.ip_address,
            )
            logger.warning(
                "token_reuse_attack_detected",
                family_id=str(stored.family_id),
                user_id=str(stored.user_id),
            )
            raise TokenFamilyRevokedError("Session compromised — please log in again")

        # 3. Load user to get current role
        user = await self._user_repo.get_by_id(stored.user_id)
        if user is None:
            raise TokenInvalidError("User associated with this token no longer exists")

        # 4. Revoke used token (rotation)
        await self._token_repo.revoke_by_id(stored.id)

        # 5. Issue new token pair in the same family
        jti = uuid.uuid4()
        access_token, _ = self._jwt.create_access_token(user.id, user.role, jti)
        raw_refresh, refresh_hash = self._jwt.create_refresh_token_pair()

        expires_at = datetime.now(tz=UTC) + timedelta(
            days=self._settings.refresh_token_expire_days
        )
        new_token = RefreshTokenEntity(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=refresh_hash,
            family_id=stored.family_id,  # same family
            is_revoked=False,
            expires_at=expires_at,
            created_at=datetime.now(tz=UTC),
        )
        await self._token_repo.create_token(new_token)

        logger.info("token_rotated", user_id=str(user.id), ip=payload.ip_address)
        return RefreshTokenResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            user_id=user.id,
        )
