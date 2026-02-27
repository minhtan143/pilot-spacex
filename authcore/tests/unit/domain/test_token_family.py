"""Unit tests for TokenFamilyPolicy domain service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from authcore.domain.models.refresh_token import RefreshTokenEntity
from authcore.domain.services.token_family import TokenFamilyPolicy


def _make_token(
    *,
    is_revoked: bool = False,
    expires_at: datetime | None = None,
) -> RefreshTokenEntity:
    if expires_at is None:
        expires_at = datetime.now(tz=UTC) + timedelta(days=7)
    return RefreshTokenEntity(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token_hash="abc123",
        family_id=uuid.uuid4(),
        is_revoked=is_revoked,
        expires_at=expires_at,
        created_at=datetime.now(tz=UTC),
    )


class TestIsReuseAttack:
    def test_revoked_token_is_reuse_attack(self) -> None:
        token = _make_token(is_revoked=True)
        assert TokenFamilyPolicy.is_reuse_attack(token) is True

    def test_valid_token_is_not_reuse_attack(self) -> None:
        token = _make_token(is_revoked=False)
        assert TokenFamilyPolicy.is_reuse_attack(token) is False

    def test_fresh_token_is_not_reuse_attack(self) -> None:
        token = _make_token(is_revoked=False)
        assert TokenFamilyPolicy.is_reuse_attack(token) is False


class TestIsExpired:
    def test_past_expires_at_is_expired(self) -> None:
        past = datetime.now(tz=UTC) - timedelta(seconds=1)
        token = _make_token(expires_at=past)
        assert TokenFamilyPolicy.is_expired(token) is True

    def test_future_expires_at_is_not_expired(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(days=7)
        token = _make_token(expires_at=future)
        assert TokenFamilyPolicy.is_expired(token) is False

    def test_revoked_but_not_expired_is_not_expired(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(days=7)
        token = _make_token(is_revoked=True, expires_at=future)
        assert TokenFamilyPolicy.is_expired(token) is False

    def test_expired_and_revoked_is_expired(self) -> None:
        past = datetime.now(tz=UTC) - timedelta(seconds=1)
        token = _make_token(is_revoked=True, expires_at=past)
        assert TokenFamilyPolicy.is_expired(token) is True
