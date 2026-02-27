"""Unit tests for UserEntity domain model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from authcore.domain.models.user import UserEntity


def _make_user(
    *,
    is_locked: bool = False,
    failed_attempts: int = 0,
    lockout_until: datetime | None = None,
) -> UserEntity:
    return UserEntity(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="member",
        is_verified=True,
        is_locked=is_locked,
        failed_attempts=failed_attempts,
        lockout_until=lockout_until,
        created_at=datetime.now(tz=UTC),
    )


class TestIsLockoutActive:
    def test_not_locked_returns_false(self) -> None:
        user = _make_user(is_locked=False)
        assert user.is_lockout_active() is False

    def test_locked_with_no_lockout_until_returns_false(self) -> None:
        user = _make_user(is_locked=True, lockout_until=None)
        assert user.is_lockout_active() is False

    def test_locked_with_future_lockout_until_returns_true(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(minutes=10)
        user = _make_user(is_locked=True, lockout_until=future)
        assert user.is_lockout_active() is True

    def test_locked_with_past_lockout_until_returns_false(self) -> None:
        past = datetime.now(tz=UTC) - timedelta(seconds=1)
        user = _make_user(is_locked=True, lockout_until=past)
        assert user.is_lockout_active() is False


class TestRecordFailedAttempt:
    def test_increments_failed_attempts(self) -> None:
        user = _make_user(failed_attempts=2)
        user.record_failed_attempt(max_attempts=5, lockout_minutes=15)
        assert user.failed_attempts == 3

    def test_does_not_lock_before_threshold(self) -> None:
        user = _make_user(failed_attempts=3)
        user.record_failed_attempt(max_attempts=5, lockout_minutes=15)
        assert user.is_locked is False

    def test_locks_at_max_attempts(self) -> None:
        user = _make_user(failed_attempts=4)
        user.record_failed_attempt(max_attempts=5, lockout_minutes=15)
        assert user.is_locked is True
        assert user.lockout_until is not None

    def test_lockout_until_is_in_future(self) -> None:
        user = _make_user(failed_attempts=4)
        before = datetime.now(tz=UTC)
        user.record_failed_attempt(max_attempts=5, lockout_minutes=15)
        assert user.lockout_until is not None
        assert user.lockout_until > before

    def test_lockout_until_approximates_lockout_duration(self) -> None:
        user = _make_user(failed_attempts=4)
        user.record_failed_attempt(max_attempts=5, lockout_minutes=15)
        expected = datetime.now(tz=UTC) + timedelta(minutes=15)
        delta = abs((user.lockout_until - expected).total_seconds())  # type: ignore[operator]
        assert delta < 2  # within 2 seconds


class TestClearFailedAttempts:
    def test_resets_failed_attempts_to_zero(self) -> None:
        user = _make_user(failed_attempts=3, is_locked=True)
        user.clear_failed_attempts()
        assert user.failed_attempts == 0

    def test_clears_is_locked(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(minutes=10)
        user = _make_user(is_locked=True, lockout_until=future)
        user.clear_failed_attempts()
        assert user.is_locked is False

    def test_clears_lockout_until(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(minutes=10)
        user = _make_user(is_locked=True, lockout_until=future)
        user.clear_failed_attempts()
        assert user.lockout_until is None


class TestAutoUnlockIfExpired:
    def test_returns_true_and_clears_when_lockout_expired(self) -> None:
        past = datetime.now(tz=UTC) - timedelta(seconds=1)
        user = _make_user(is_locked=True, lockout_until=past, failed_attempts=5)
        result = user.auto_unlock_if_expired()
        assert result is True
        assert user.is_locked is False
        assert user.failed_attempts == 0
        assert user.lockout_until is None

    def test_returns_false_when_lockout_still_active(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(minutes=10)
        user = _make_user(is_locked=True, lockout_until=future, failed_attempts=5)
        result = user.auto_unlock_if_expired()
        assert result is False
        assert user.is_locked is True

    def test_returns_false_when_not_locked(self) -> None:
        user = _make_user(is_locked=False)
        result = user.auto_unlock_if_expired()
        assert result is False

    def test_returns_false_when_locked_but_no_lockout_until(self) -> None:
        user = _make_user(is_locked=True, lockout_until=None)
        result = user.auto_unlock_if_expired()
        assert result is False
