"""JWT Provider Abstraction — supports Supabase (default) and AuthCore.

Controlled by AUTH_PROVIDER env var (default: "supabase").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

import jwt
from jwt import PyJWTError

from pilot_space.infrastructure.auth import (
    SupabaseAuth,
    SupabaseAuthError,
    TokenExpiredError as SupabaseTokenExpiredError,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.config import Settings

logger = get_logger(__name__)


class JWTValidationError(Exception):
    """Token failed validation (expired, invalid signature, blacklisted JTI)."""


class JWTExpiredError(JWTValidationError):
    """Token is expired."""


@runtime_checkable
class JWTProvider(Protocol):
    """Protocol for JWT validation providers.

    Each implementation validates a raw Bearer token and returns the
    authenticated user's UUID or raises JWTValidationError / JWTExpiredError.
    """

    def validate_token(self, token: str) -> UUID:
        """Validate token and return user UUID.

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            User UUID extracted from the validated token.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token is invalid for any other reason.
        """
        ...


class SupabaseJWTProvider:
    """Validates Supabase Auth JWT tokens (HS256 / ES256).

    Delegates to the existing SupabaseAuth infrastructure. This provider
    is the default and maintains full backward compatibility.
    """

    def __init__(self, auth: SupabaseAuth | None = None) -> None:
        self._auth = auth or SupabaseAuth()

    def validate_token(self, token: str) -> UUID:
        """Validate Supabase JWT and return user UUID.

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            User UUID from the validated sub claim.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token is invalid.
        """
        try:
            payload = self._auth.validate_token(token)
            return payload.user_id
        except SupabaseTokenExpiredError as e:
            raise JWTExpiredError(str(e)) from e
        except SupabaseAuthError as e:
            raise JWTValidationError(str(e)) from e


class AuthCoreJWTProvider:
    """Validates AuthCore RS256 JWT tokens.

    Verifies the RS256 signature using the configured public key, checks
    the JTI against the Redis blacklist, and extracts the sub claim as
    the user UUID.
    """

    ALGORITHM = "RS256"

    def __init__(self, public_key_pem: str, redis_client: object | None = None) -> None:
        """Initialise AuthCore JWT provider.

        Args:
            public_key_pem: PEM-encoded RSA public key for RS256 verification.
            redis_client: Optional RedisClient instance for JTI blacklist checks.
                          If None, blacklist checking is skipped (not recommended
                          for production without a Redis connection).
        """
        self._public_key_pem = public_key_pem
        self._redis = redis_client

    def validate_token(self, token: str) -> UUID:
        """Validate AuthCore RS256 JWT and return user UUID.

        Performs three checks in order:
        1. RS256 signature verification with the configured public key.
        2. Standard claim validation (exp, iat, sub, jti are required).
        3. JTI blacklist check via Redis (if Redis client is configured).

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            User UUID from the validated sub claim.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token signature is invalid, claims are
                                missing, or the JTI has been revoked.
        """
        try:
            claims = jwt.decode(
                token,
                self._public_key_pem,
                algorithms=[self.ALGORITHM],
                options={"require": ["sub", "jti", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError as e:
            raise JWTExpiredError("AuthCore token has expired") from e
        except PyJWTError as e:
            raise JWTValidationError(f"AuthCore token is invalid: {e}") from e

        jti: str = claims["jti"]
        if self._is_jti_blacklisted(jti):
            raise JWTValidationError(f"Token JTI {jti!r} has been revoked")

        try:
            return UUID(claims["sub"])
        except (ValueError, AttributeError) as e:
            raise JWTValidationError(f"Invalid sub claim: {claims.get('sub')!r}") from e

    def _is_jti_blacklisted(self, jti: str) -> bool:
        """Check Redis blacklist for the given JTI.

        The blacklist key pattern is ``authcore:jti:revoked:<jti>``.
        Returns False (not blacklisted) when Redis is unavailable so that
        a Redis outage does not prevent valid logins.

        Args:
            jti: JWT ID claim from the token.

        Returns:
            True if the JTI is blacklisted, False otherwise.
        """
        if self._redis is None:
            return False

        import asyncio

        key = f"authcore:jti:revoked:{jti}"

        # Support both sync (Protocol .exists) and async RedisClient
        # The Pilot Space RedisClient is async; we run it in the current loop
        # if one is running, else use asyncio.run().
        exists_method = getattr(self._redis, "exists", None)
        if exists_method is None:
            logger.warning("Redis client has no 'exists' method; skipping JTI check")
            return False

        try:
            result = exists_method(key)
            # If the result is a coroutine, schedule it synchronously
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Running inside an event loop (FastAPI dependency context)
                        # Use run_coroutine_threadsafe or create a task — but since
                        # validate_token is sync by design (Protocol constraint),
                        # we run it via a new thread-safe future.
                        from concurrent.futures import Future as _Future

                        future: _Future[int] = asyncio.run_coroutine_threadsafe(result, loop)
                        count = future.result(timeout=1.0)
                    else:
                        count = loop.run_until_complete(result)
                except Exception as exc:
                    logger.warning("JTI blacklist check failed (async): %s", exc)
                    return False
            else:
                count = result
            return bool(count)
        except Exception as exc:
            logger.warning("JTI blacklist check failed: %s", exc)
            return False


def get_jwt_provider(settings: Settings) -> JWTProvider:
    """Factory: return the correct JWTProvider based on settings.auth_provider.

    Default is "supabase" for full backward compatibility.

    Args:
        settings: Application settings instance.

    Returns:
        A JWTProvider implementation for the configured auth provider.

    Raises:
        ValueError: If auth_provider has an unrecognised value.
    """
    provider = (settings.auth_provider or "supabase").lower().strip()

    if provider == "supabase":
        return SupabaseJWTProvider()

    if provider == "authcore":
        public_key = settings.authcore_public_key
        if not public_key:
            raise ValueError("AUTH_PROVIDER=authcore requires AUTHCORE_PUBLIC_KEY to be set")

        # Lazily import to avoid circular deps; RedisClient is optional
        try:
            from pilot_space.infrastructure.cache.redis import RedisClient

            redis_url = getattr(settings, "redis_url", None)
            redis_client: object | None = RedisClient(redis_url) if redis_url else None
        except Exception:
            redis_client = None
            logger.warning("Could not initialise Redis for JTI blacklist; skipping")

        return AuthCoreJWTProvider(
            public_key_pem=public_key,
            redis_client=redis_client,
        )

    raise ValueError(
        f"Unknown AUTH_PROVIDER {provider!r}. Supported values: 'supabase', 'authcore'."
    )
