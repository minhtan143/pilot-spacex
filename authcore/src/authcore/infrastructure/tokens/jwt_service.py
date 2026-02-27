"""RS256 JWT access token creation and verification."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from authcore.config import Settings
from authcore.domain.exceptions import TokenExpiredError, TokenInvalidError
from authcore.infrastructure.tokens.key_manager import KeyManager


class JWTService:
    """RS256 JWT sign/verify. Stateless — no I/O."""

    ALGORITHM = "RS256"

    def __init__(self, key_manager: KeyManager, settings: Settings) -> None:
        self._key_manager = key_manager
        self._settings = settings

    def create_access_token(
        self, user_id: uuid.UUID, role: str, jti: uuid.UUID
    ) -> tuple[str, datetime]:
        """Create a signed RS256 access token.

        Args:
            user_id: The subject user's UUID.
            role: The user's role ('admin', 'member', 'guest').
            jti: Unique JWT ID for revocation tracking.

        Returns:
            Tuple of (encoded_token, expires_at).
        """
        expires_at = datetime.now(tz=UTC) + timedelta(
            minutes=self._settings.access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "role": role,
            "jti": str(jti),
            "iat": datetime.now(tz=UTC),
            "exp": expires_at,
        }
        token = jwt.encode(
            payload, self._key_manager.get_private_key(), algorithm=self.ALGORITHM
        )
        return token, expires_at

    def create_refresh_token_pair(self) -> tuple[str, str]:
        """Generate a refresh token raw value and its hash.

        Returns:
            Tuple of (raw_token, token_hash). Raw is sent to client; hash stored in DB.
        """
        raw = secrets.token_urlsafe(64)
        token_hash = self.hash_token(raw)
        return raw, token_hash

    def verify_access_token(self, token: str) -> dict[str, object]:
        """Verify and decode an RS256 access token.

        Args:
            token: Encoded JWT string.

        Returns:
            Decoded claims dict with sub, role, jti, exp, iat.

        Raises:
            TokenExpiredError: If the token's expiry has passed.
            TokenInvalidError: If the token is malformed or signature invalid.
        """
        try:
            return jwt.decode(
                token,
                self._key_manager.get_public_key(),
                algorithms=[self.ALGORITHM],
                options={"require": ["sub", "role", "jti", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Access token has expired")
        except jwt.PyJWTError:
            raise TokenInvalidError("Access token is invalid")

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Compute SHA-256 hex digest of a raw token string.

        Args:
            raw_token: The raw token string from the client.

        Returns:
            Hex-encoded SHA-256 hash for DB storage.
        """
        return hashlib.sha256(raw_token.encode()).hexdigest()
