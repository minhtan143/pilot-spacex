"""Dependency injection container for AuthCore using dependency-injector."""

from __future__ import annotations

from dependency_injector import containers, providers

from authcore.config import Settings
from authcore.external.rate_limiter import LoginRateLimiter
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.engine import get_engine, get_session_factory
from authcore.infrastructure.email.smtp_email_service import SmtpEmailService
from authcore.infrastructure.tokens.jwt_service import JWTService
from authcore.infrastructure.tokens.key_manager import KeyManager


def _make_smtp_service(settings: Settings) -> SmtpEmailService:
    """Factory that constructs SmtpEmailService from Settings."""
    return SmtpEmailService(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value(),
        from_address=settings.smtp_from_address,
        use_tls=settings.smtp_use_tls,
    )


class InfraContainer(containers.DeclarativeContainer):
    """Infrastructure-level singletons: DB engine, Redis, JWT, email."""

    config = providers.Dependency(instance_of=Settings)

    # Async SQLAlchemy engine (singleton)
    db_engine = providers.Singleton(
        get_engine,
        settings=config,
    )

    # Session factory (singleton factory — creates sessions per request)
    session_factory = providers.Singleton(
        get_session_factory,
        engine=db_engine,
    )

    # Redis client
    redis_client = providers.Singleton(
        RedisClient,
        redis_url=config.provided.redis_url,
    )

    # JWT key manager + service
    key_manager = providers.Singleton(
        KeyManager,
        settings=config,
    )

    jwt_service = providers.Singleton(
        JWTService,
        key_manager=key_manager,
        settings=config,
    )

    # Email — use factory to avoid SecretStr .provided chain at class definition time
    email_service = providers.Singleton(_make_smtp_service, settings=config)


class Container(containers.DeclarativeContainer):
    """Top-level DI container: composes InfraContainer + application services."""

    wiring_modules = [
        "authcore.api.v1.routers.auth",
        "authcore.api.v1.routers.admin",
        "authcore.api.dependencies.auth",
    ]

    config = providers.Singleton(Settings)

    infra = providers.Container(
        InfraContainer,
        config=config,
    )

    # Rate limiter
    login_rate_limiter = providers.Factory(  # type: ignore[misc]
        LoginRateLimiter,
        redis_client=infra.redis_client,  # type: ignore[arg-type]
        max_attempts=config.provided.login_max_attempts,
    )
