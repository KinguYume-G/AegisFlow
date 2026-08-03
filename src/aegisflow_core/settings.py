"""Minimal process-environment configuration for the application skeleton."""

from dataclasses import dataclass
import math
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
    github_app_id: str | None = None
    github_app_private_key: str | None = None
    github_webhook_secret: str | None = None
    github_installation_id: str | None = None
    github_api_timeout_seconds: float = 10.0
    aegisflow_bootstrap_tenant_slug: str = "gate1b-default"
    sandbox_broker_url: str | None = None
    sandbox_default_timeout_seconds: int = 120
    sandbox_default_memory_limit_mb: int = 512
    sandbox_default_cpu_limit: float = 1.0
    sandbox_default_pids_limit: int = 128

    @property
    def github_app_configured(self) -> bool:
        """Whether the complete GitHub App boundary is configured."""
        return all(
            (
                self.github_app_id,
                self.github_app_private_key,
                self.github_webhook_secret,
                self.github_installation_id,
            )
        )


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

    github_values = {
        "github_app_id": os.environ.get("GITHUB_APP_ID") or None,
        "github_app_private_key": os.environ.get("GITHUB_APP_PRIVATE_KEY") or None,
        "github_webhook_secret": os.environ.get("GITHUB_APP_WEBHOOK_SECRET") or None,
        "github_installation_id": os.environ.get("GITHUB_APP_INSTALLATION_ID") or None,
    }
    github_configured_count = sum(
        value is not None for value in github_values.values()
    )
    if github_configured_count not in (0, len(github_values)):
        raise ConfigurationError(
            "GitHub App configuration must provide all four required fields or none"
        )

    raw_github_timeout = os.environ.get("GITHUB_API_TIMEOUT_SECONDS") or "10"
    try:
        github_api_timeout_seconds = float(raw_github_timeout)
    except ValueError:
        raise ConfigurationError(
            "GITHUB_API_TIMEOUT_SECONDS must be a positive number"
        ) from None
    if github_api_timeout_seconds <= 0 or not math.isfinite(
        github_api_timeout_seconds
    ):
        raise ConfigurationError(
            "GITHUB_API_TIMEOUT_SECONDS must be a positive number"
        )

    return Settings(
        app_env=app_env,
        app_base_url=app_base_url,
        database_url=database_url,
        **langfuse_values,
        **github_values,
        github_api_timeout_seconds=github_api_timeout_seconds,
        aegisflow_bootstrap_tenant_slug=(
            os.environ.get("AEGISFLOW_BOOTSTRAP_TENANT_SLUG") or "gate1b-default"
        ),
        sandbox_broker_url=os.environ.get("SANDBOX_BROKER_URL") or None,
        sandbox_default_timeout_seconds=int(os.environ.get("SANDBOX_DEFAULT_TIMEOUT_SECONDS") or "120"),
        sandbox_default_memory_limit_mb=int(os.environ.get("SANDBOX_DEFAULT_MEMORY_LIMIT_MB") or "512"),
        sandbox_default_cpu_limit=float(os.environ.get("SANDBOX_DEFAULT_CPU_LIMIT") or "1"),
        sandbox_default_pids_limit=int(os.environ.get("SANDBOX_DEFAULT_PIDS_LIMIT") or "128"),
    )
