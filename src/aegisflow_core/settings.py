"""Minimal process-environment configuration for the application skeleton."""

from dataclasses import dataclass
import os

_ALLOWED_APP_ENVS = frozenset({"development", "test", "production"})


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is absent or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration intentionally limited to fields owned through AF-103."""

    app_env: str
    app_base_url: str | None
    database_url: str


def get_settings() -> Settings:
    """Load and validate the minimal application configuration."""
    app_env = os.environ.get("APP_ENV")
    if app_env not in _ALLOWED_APP_ENVS:
        raise ConfigurationError(
            "APP_ENV must be one of: development, test, production"
        )

    app_base_url = os.environ.get("APP_BASE_URL") or None
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ConfigurationError("DATABASE_URL is required")

    return Settings(
        app_env=app_env,
        app_base_url=app_base_url,
        database_url=database_url,
    )
