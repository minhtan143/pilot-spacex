"""Configuration management for AuthCore.

Uses Pydantic Settings for environment variable loading and validation.
"""

from pydantic import AnyUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    Secret values are stored as SecretStr to prevent accidental logging.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: AnyUrl

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT (RS256 — PEM strings)
    jwt_private_key: SecretStr
    jwt_public_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_address: str = "noreply@authcore.local"
    smtp_use_tls: bool = True

    # App
    app_base_url: str = "http://localhost:8001"
    debug: bool = False
    environment: str = "development"

    # Rate limiting
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    resend_verification_max_per_hour: int = 3
    password_reset_token_expire_minutes: int = 60
    email_verification_token_expire_hours: int = 24


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance with values from environment.
    """
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
