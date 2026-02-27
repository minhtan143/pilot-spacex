"""Unit tests for JWT provider abstraction (AuthCore JWT bridge).

Covers:
- SupabaseJWTProvider extracts UUID from sub claim
- AuthCoreJWTProvider validates RS256 token
- AuthCoreJWTProvider rejects tokens with blacklisted JTI
- Factory returns correct provider based on config
- Backward compat: missing/empty AUTH_PROVIDER defaults to supabase
"""

from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from pilot_space.dependencies.jwt_providers import (
    AuthCoreJWTProvider,
    JWTExpiredError,
    JWTProvider,
    JWTValidationError,
    SupabaseJWTProvider,
    get_jwt_provider,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_rsa_keypair() -> tuple[str, str]:
    """Generate a fresh RSA-2048 key pair; return (private_pem, public_pem)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _sign_rs256(payload: dict[str, Any], private_pem: str) -> str:
    return jwt.encode(payload, private_pem, algorithm="RS256")


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[str, str]:
    return _make_rsa_keypair()


def _make_valid_authcore_claims(user_id: uuid.UUID | None = None) -> dict[str, Any]:
    uid = user_id or uuid.uuid4()
    now = int(time.time())
    return {
        "sub": str(uid),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + 3600,
        "role": "member",
    }


# ---------------------------------------------------------------------------
# SupabaseJWTProvider
# ---------------------------------------------------------------------------


class TestSupabaseJWTProvider:
    def test_extracts_uuid_from_valid_sub(self) -> None:
        user_id = uuid.uuid4()
        mock_payload = MagicMock()
        mock_payload.user_id = user_id

        mock_auth = MagicMock()
        mock_auth.validate_token.return_value = mock_payload

        provider = SupabaseJWTProvider(auth=mock_auth)
        result = provider.validate_token("dummy.token.here")

        assert result == user_id
        mock_auth.validate_token.assert_called_once_with("dummy.token.here")

    def test_raises_jwt_expired_error_on_expired_token(self) -> None:
        from pilot_space.infrastructure.auth import TokenExpiredError as SupabaseExpired

        mock_auth = MagicMock()
        mock_auth.validate_token.side_effect = SupabaseExpired("expired")

        provider = SupabaseJWTProvider(auth=mock_auth)
        with pytest.raises(JWTExpiredError):
            provider.validate_token("expired.token")

    def test_raises_jwt_validation_error_on_invalid_token(self) -> None:
        from pilot_space.infrastructure.auth import SupabaseAuthError

        mock_auth = MagicMock()
        mock_auth.validate_token.side_effect = SupabaseAuthError("bad token")

        provider = SupabaseJWTProvider(auth=mock_auth)
        with pytest.raises(JWTValidationError):
            provider.validate_token("bad.token")

    def test_satisfies_jwt_provider_protocol(self) -> None:
        provider = SupabaseJWTProvider(auth=MagicMock())
        assert isinstance(provider, JWTProvider)


# ---------------------------------------------------------------------------
# AuthCoreJWTProvider — happy path
# ---------------------------------------------------------------------------


class TestAuthCoreJWTProviderValid:
    def test_validates_rs256_token_and_returns_uuid(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, public_pem = rsa_keypair
        user_id = uuid.uuid4()
        claims = _make_valid_authcore_claims(user_id)
        token = _sign_rs256(claims, private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)
        result = provider.validate_token(token)

        assert result == user_id

    def test_satisfies_jwt_provider_protocol(self, rsa_keypair: tuple[str, str]) -> None:
        _, public_pem = rsa_keypair
        provider = AuthCoreJWTProvider(public_key_pem=public_pem)
        assert isinstance(provider, JWTProvider)


# ---------------------------------------------------------------------------
# AuthCoreJWTProvider — failure cases
# ---------------------------------------------------------------------------


class TestAuthCoreJWTProviderRejections:
    def test_raises_jwt_expired_error_for_expired_token(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, public_pem = rsa_keypair
        claims = _make_valid_authcore_claims()
        claims["exp"] = int(time.time()) - 60  # already expired
        token = _sign_rs256(claims, private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)
        with pytest.raises(JWTExpiredError):
            provider.validate_token(token)

    def test_raises_jwt_validation_error_for_wrong_key(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, _ = rsa_keypair
        _, wrong_public_pem = _make_rsa_keypair()  # different key pair
        claims = _make_valid_authcore_claims()
        token = _sign_rs256(claims, private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=wrong_public_pem)
        with pytest.raises(JWTValidationError):
            provider.validate_token(token)

    def test_raises_jwt_validation_error_for_missing_required_claims(
        self, rsa_keypair: tuple[str, str]
    ) -> None:
        private_pem, public_pem = rsa_keypair
        # Missing jti
        claims = {
            "sub": str(uuid.uuid4()),
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = _sign_rs256(claims, private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)
        with pytest.raises(JWTValidationError):
            provider.validate_token(token)

    def test_raises_jwt_validation_error_for_malformed_sub(
        self, rsa_keypair: tuple[str, str]
    ) -> None:
        private_pem, public_pem = rsa_keypair
        claims = _make_valid_authcore_claims()
        claims["sub"] = "not-a-uuid"
        token = _sign_rs256(claims, private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)
        with pytest.raises(JWTValidationError):
            provider.validate_token(token)

    def test_raises_jwt_validation_error_for_blacklisted_jti(
        self, rsa_keypair: tuple[str, str]
    ) -> None:
        private_pem, public_pem = rsa_keypair
        jti = str(uuid.uuid4())
        claims = _make_valid_authcore_claims()
        claims["jti"] = jti
        token = _sign_rs256(claims, private_pem)

        # Mock Redis returning 1 (key exists) for the blacklist key
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # sync int — not a coroutine

        provider = AuthCoreJWTProvider(public_key_pem=public_pem, redis_client=mock_redis)
        with pytest.raises(JWTValidationError, match="revoked"):
            provider.validate_token(token)

        mock_redis.exists.assert_called_once_with(f"authcore:jti:revoked:{jti}")

    def test_allows_token_when_jti_not_blacklisted(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, public_pem = rsa_keypair
        user_id = uuid.uuid4()
        jti = str(uuid.uuid4())
        claims = _make_valid_authcore_claims(user_id)
        claims["jti"] = jti
        token = _sign_rs256(claims, private_pem)

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0  # not in blacklist

        provider = AuthCoreJWTProvider(public_key_pem=public_pem, redis_client=mock_redis)
        result = provider.validate_token(token)
        assert result == user_id

    def test_skips_jti_check_when_no_redis(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, public_pem = rsa_keypair
        user_id = uuid.uuid4()
        claims = _make_valid_authcore_claims(user_id)
        token = _sign_rs256(claims, private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=public_pem, redis_client=None)
        result = provider.validate_token(token)
        assert result == user_id


# ---------------------------------------------------------------------------
# get_jwt_provider factory
# ---------------------------------------------------------------------------


def _make_settings(
    auth_provider: str = "supabase",
    authcore_public_key: str | None = None,
    authcore_url: str | None = None,
    redis_url: str = "redis://localhost:6379/0",
) -> MagicMock:
    settings = MagicMock()
    settings.auth_provider = auth_provider
    settings.authcore_public_key = authcore_public_key
    settings.authcore_url = authcore_url
    settings.redis_url = redis_url
    return settings


class TestGetJwtProviderFactory:
    def test_returns_supabase_provider_by_default(self) -> None:
        settings = _make_settings(auth_provider="supabase")
        provider = get_jwt_provider(settings)
        assert isinstance(provider, SupabaseJWTProvider)

    def test_returns_supabase_provider_when_empty_string(self) -> None:
        # Covers backward compat: AUTH_PROVIDER not set → empty string
        settings = _make_settings(auth_provider="")
        provider = get_jwt_provider(settings)
        assert isinstance(provider, SupabaseJWTProvider)

    def test_returns_supabase_provider_when_none(self) -> None:
        settings = _make_settings()
        settings.auth_provider = None  # type: ignore[assignment]
        provider = get_jwt_provider(settings)
        assert isinstance(provider, SupabaseJWTProvider)

    def test_returns_authcore_provider_when_configured(self, rsa_keypair: tuple[str, str]) -> None:
        _, public_pem = rsa_keypair
        settings = _make_settings(auth_provider="authcore", authcore_public_key=public_pem)

        # RedisClient is imported lazily inside get_jwt_provider; patch the source module
        with patch(
            "pilot_space.infrastructure.cache.redis.RedisClient",
            return_value=MagicMock(),
        ):
            provider = get_jwt_provider(settings)

        assert isinstance(provider, AuthCoreJWTProvider)

    def test_raises_value_error_when_authcore_missing_public_key(self) -> None:
        settings = _make_settings(auth_provider="authcore", authcore_public_key=None)
        with pytest.raises(ValueError, match="AUTHCORE_PUBLIC_KEY"):
            get_jwt_provider(settings)

    def test_raises_value_error_for_unknown_provider(self) -> None:
        settings = _make_settings(auth_provider="unknown_provider")
        with pytest.raises(ValueError, match="unknown_provider"):
            get_jwt_provider(settings)

    def test_case_insensitive_provider_name(self) -> None:
        settings = _make_settings(auth_provider="SUPABASE")
        provider = get_jwt_provider(settings)
        assert isinstance(provider, SupabaseJWTProvider)

    def test_authcore_provider_skips_redis_when_no_redis_url(
        self, rsa_keypair: tuple[str, str]
    ) -> None:
        _, public_pem = rsa_keypair
        settings = _make_settings(
            auth_provider="authcore",
            authcore_public_key=public_pem,
            redis_url="",
        )
        settings.redis_url = ""
        provider = get_jwt_provider(settings)
        assert isinstance(provider, AuthCoreJWTProvider)


# ---------------------------------------------------------------------------
# Backward compatibility: AUTH_PROVIDER not set defaults to supabase
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_default_provider_is_supabase(self) -> None:
        """Missing AUTH_PROVIDER env must default to Supabase provider."""
        settings = _make_settings()
        provider = get_jwt_provider(settings)
        assert isinstance(provider, SupabaseJWTProvider)

    def test_supabase_provider_validates_full_round_trip(self) -> None:
        """SupabaseJWTProvider returns UUID matching the sub claim."""
        user_id = uuid.uuid4()
        mock_payload = MagicMock()
        mock_payload.user_id = user_id
        mock_auth = MagicMock()
        mock_auth.validate_token.return_value = mock_payload

        provider = SupabaseJWTProvider(auth=mock_auth)
        assert provider.validate_token("any.token") == user_id
