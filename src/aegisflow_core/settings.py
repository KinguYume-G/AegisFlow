"""Minimal process-environment configuration for the application skeleton."""

from dataclasses import dataclass
import math
import os

from aegisflow_core.control_plane.identity import OidcConfig

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
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "aegisflow-delivery"
    langgraph_database_url: str | None = None
    model_primary_name: str | None = None
    model_primary_api_key_env: str | None = None
    model_fallback_name: str | None = None
    model_fallback_api_key_env: str | None = None
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithm: str | None = None
    oidc_cache_ttl_seconds: int = 300
    oidc_max_cached_keys: int = 16
    oidc_http_timeout_seconds: float = 5.0
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "aegisflow-core"

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

    @property
    def model_gateway_configured(self) -> bool:
        """Whether both bounded model routes and Secret references exist."""
        return all(
            (
                self.model_primary_name,
                self.model_primary_api_key_env,
                self.model_fallback_name,
                self.model_fallback_api_key_env,
            )
        )

    @property
    def oidc_configured(self) -> bool:
        return all((self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url, self.oidc_algorithm))

    @property
    def oidc_config(self) -> OidcConfig | None:
        if not self.oidc_configured:
            return None
        return OidcConfig(
            issuer=self.oidc_issuer or "",
            audience=self.oidc_audience or "",
            jwks_url=self.oidc_jwks_url or "",
            algorithm=self.oidc_algorithm or "",
            cache_ttl_seconds=self.oidc_cache_ttl_seconds,
            max_cached_keys=self.oidc_max_cached_keys,
            http_timeout_seconds=self.oidc_http_timeout_seconds,
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

    model_values = {
        "model_primary_name": os.environ.get("MODEL_PRIMARY_NAME") or None,
        "model_primary_api_key_env": os.environ.get("MODEL_PRIMARY_API_KEY_ENV")
        or None,
        "model_fallback_name": os.environ.get("MODEL_FALLBACK_NAME") or None,
        "model_fallback_api_key_env": os.environ.get("MODEL_FALLBACK_API_KEY_ENV")
        or None,
    }
    model_configured_count = sum(value is not None for value in model_values.values())
    if model_configured_count not in (0, len(model_values)):
        raise ConfigurationError(
            "Model gateway configuration must provide both routes and Secret references or none"
        )
    if (
        model_configured_count
        and model_values["model_primary_name"] == model_values["model_fallback_name"]
    ):
        raise ConfigurationError("Primary and fallback model names must be distinct")

    oidc_values = {
        "oidc_issuer": os.environ.get("OIDC_ISSUER") or None,
        "oidc_audience": os.environ.get("OIDC_AUDIENCE") or None,
        "oidc_jwks_url": os.environ.get("OIDC_JWKS_URL") or None,
        "oidc_algorithm": os.environ.get("OIDC_ALGORITHM") or None,
    }
    oidc_configured_count = sum(value is not None for value in oidc_values.values())
    if oidc_configured_count not in (0, len(oidc_values)):
        raise ConfigurationError(
            "OIDC configuration must provide issuer, audience, JWKS URL, and algorithm or none"
        )
    try:
        oidc_cache_ttl_seconds = int(os.environ.get("OIDC_CACHE_TTL_SECONDS") or "300")
        oidc_max_cached_keys = int(os.environ.get("OIDC_MAX_CACHED_KEYS") or "16")
        oidc_http_timeout_seconds = float(os.environ.get("OIDC_HTTP_TIMEOUT_SECONDS") or "5")
        if oidc_configured_count:
            OidcConfig(
                issuer=oidc_values["oidc_issuer"] or "",
                audience=oidc_values["oidc_audience"] or "",
                jwks_url=oidc_values["oidc_jwks_url"] or "",
                algorithm=oidc_values["oidc_algorithm"] or "",
                cache_ttl_seconds=oidc_cache_ttl_seconds,
                max_cached_keys=oidc_max_cached_keys,
                http_timeout_seconds=oidc_http_timeout_seconds,
            )
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("OIDC configuration is invalid") from exc

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

    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None
    if otel_endpoint is not None and not otel_endpoint.startswith(("http://", "https://")):
        raise ConfigurationError("OTEL_EXPORTER_OTLP_ENDPOINT must be an HTTP URL")
    if app_env == "production" and otel_endpoint is not None and not otel_endpoint.startswith("https://"):
        raise ConfigurationError("production OTLP export must use HTTPS")
    otel_service_name = (os.environ.get("OTEL_SERVICE_NAME") or "aegisflow-core").strip()
    if not otel_service_name or len(otel_service_name) > 100:
        raise ConfigurationError("OTEL_SERVICE_NAME is invalid")

    return Settings(
        app_env=app_env,
        app_base_url=app_base_url,
        database_url=database_url,
        **langfuse_values,
        **github_values,
        **model_values,
        **oidc_values,
        oidc_cache_ttl_seconds=oidc_cache_ttl_seconds,
        oidc_max_cached_keys=oidc_max_cached_keys,
        oidc_http_timeout_seconds=oidc_http_timeout_seconds,
        github_api_timeout_seconds=github_api_timeout_seconds,
        aegisflow_bootstrap_tenant_slug=(
            os.environ.get("AEGISFLOW_BOOTSTRAP_TENANT_SLUG") or "gate1b-default"
        ),
        sandbox_broker_url=os.environ.get("SANDBOX_BROKER_URL") or None,
        sandbox_default_timeout_seconds=int(os.environ.get("SANDBOX_DEFAULT_TIMEOUT_SECONDS") or "120"),
        sandbox_default_memory_limit_mb=int(os.environ.get("SANDBOX_DEFAULT_MEMORY_LIMIT_MB") or "512"),
        sandbox_default_cpu_limit=float(os.environ.get("SANDBOX_DEFAULT_CPU_LIMIT") or "1"),
        sandbox_default_pids_limit=int(os.environ.get("SANDBOX_DEFAULT_PIDS_LIMIT") or "128"),
        temporal_address=os.environ.get("TEMPORAL_ADDRESS") or "localhost:7233",
        temporal_namespace=os.environ.get("TEMPORAL_NAMESPACE") or "default",
        temporal_task_queue=(
            os.environ.get("TEMPORAL_TASK_QUEUE") or "aegisflow-delivery"
        ),
        langgraph_database_url=(
            os.environ.get("LANGGRAPH_DATABASE_URL")
            or database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        ),
        otel_exporter_otlp_endpoint=otel_endpoint,
        otel_service_name=otel_service_name,
    )
