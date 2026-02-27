"""Domain entity representing an authenticated user."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class UserEntity:
    """Rich domain entity for a user.

    Contains all business logic related to account state:
    lock/unlock, failed attempt tracking, lockout expiry.
    No I/O — pure in-memory logic only.
    """

    id: uuid.UUID
    email: str
    hashed_password: str
    role: str  # 'admin' | 'member' | 'guest'
    is_verified: bool
    is_locked: bool
    failed_attempts: int
    lockout_until: datetime | None
    created_at: datetime
    is_deleted: bool = False
    deleted_at: datetime | None = None

    def is_lockout_active(self) -> bool:
        """Return True if account is currently locked out (not yet expired)."""
        if not self.is_locked or self.lockout_until is None:
            return False
        return datetime.now(tz=UTC) < self.lockout_until

    def record_failed_attempt(self, max_attempts: int, lockout_minutes: int) -> None:
        """Increment failed attempt counter and lock account if threshold exceeded.

        Args:
            max_attempts: Number of failures before account is locked.
            lockout_minutes: Duration of lockout period in minutes.
        """
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.is_locked = True
            self.lockout_until = datetime.now(tz=UTC) + timedelta(minutes=lockout_minutes)

    def clear_failed_attempts(self) -> None:
        """Reset failed attempt counter and unlock account."""
        self.failed_attempts = 0
        self.is_locked = False
        self.lockout_until = None

    def auto_unlock_if_expired(self) -> bool:
        """Clear lockout if lockout period has expired.

        Returns:
            True if lockout was cleared (had expired), False otherwise.
        """
        if (
            self.is_locked
            and self.lockout_until is not None
            and datetime.now(tz=UTC) >= self.lockout_until
        ):
            self.clear_failed_attempts()
            return True
        return False
