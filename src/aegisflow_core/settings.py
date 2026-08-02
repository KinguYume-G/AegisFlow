"""Minimal process-environment configuration for the application skeleton."""

from dataclasses import dataclass
import os

_ALLOWED_APP_ENVS = frozenset({"development", "test", "production"})


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is absent or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated process configuration owned through AF-109."""

    app_env: str
    app_base_url: str | None
    database_url: str
    langfuse_base_url: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_tracing_environment: str | None = None


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

    langfuse_values = {
        "langfuse_base_url": os.environ.get("LANGFUSE_BASE_URL") or None,
        "langfuse_public_key": os.environ.get("LANGFUSE_PUBLIC_KEY") or None,
        "langfuse_secret_key": os.environ.get("LANGFUSE_SECRET_KEY") or None,
        "langfuse_tracing_environment": os.environ.get(
            "LANGFUSE_TRACING_ENVIRONMENT"
        )
        or None,
    }
    configured_count = sum(value is not None for value in langfuse_values.values())
    if configured_count not in (0, len(langfuse_values)):
        raise ConfigurationError(
            "Langfuse configuration must provide all four required fields or none"
        )

    return Settings(
        app_env=app_env,
        app_base_url=app_base_url,
        database_url=database_url,
        **langfuse_values,
    )
