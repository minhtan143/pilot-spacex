"""Domain entity representing a refresh token."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class RefreshTokenEntity:
    """Domain entity for a refresh token.

    Carries expiry and revocation state. No I/O — pure in-memory logic.
    Token rotation / theft detection uses family_id.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    family_id: uuid.UUID
    is_revoked: bool
    expires_at: datetime
    created_at: datetime

    def is_expired(self) -> bool:
        """Return True if the token's expiry time has passed.

        Returns:
            True if token is expired, False otherwise.
        """
        return datetime.now(tz=UTC) > self.expires_at
