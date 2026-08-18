"""Minimal process-environment configuration for the application skeleton."""

from dataclasses import dataclass, field
import math
import os
import re
from urllib.parse import urlsplit

from aegisflow_core.control_plane.identity import OidcConfig

_ALLOWED_APP_ENVS = frozenset({"development", "test", "production"})
_PINNED_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
_DEFAULT_SANDBOX_TEST_IMAGE = (
    "python:3.12-slim@sha256:"
    "57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
)


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
    sandbox_test_image: str = _DEFAULT_SANDBOX_TEST_IMAGE
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "aegisflow-delivery"
    langgraph_database_url: str | None = None
    model_primary_name: str | None = None
    model_primary_api_key_env: str | None = None
    model_fallback_name: str | None = None
    model_fallback_api_key_env: str | None = None
    model_local_fallback_enabled: bool = False
    model_local_fallback_name: str | None = None
    model_local_fallback_api_key_env: str | None = None
    model_local_fallback_base_url: str | None = None
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithm: str | None = None
    oidc_cache_ttl_seconds: int = 300
    oidc_max_cached_keys: int = 16
    oidc_http_timeout_seconds: float = 5.0
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "aegisflow-core"
    local_mvp_profile_enabled: bool = False
    local_mvp_developer_token: str | None = field(default=None, repr=False)
    local_mvp_reviewer_token: str | None = field(default=None, repr=False)
    local_mvp_tenant_slug: str = "local-mvp"
    local_mvp_workspace_root: str = "/workspaces"
    local_mvp_github_dry_run: bool = False
    model_ollama_enabled: bool = False
    model_ollama_name: str | None = None
    model_ollama_api_key_env: str | None = None
    model_ollama_base_url: str | None = None

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
    def model_local_fallback_configured(self) -> bool:
        return self.model_local_fallback_enabled and all(
            (self.model_local_fallback_name, self.model_local_fallback_api_key_env, self.model_local_fallback_base_url)
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

    @property
    def local_mvp_identity_configured(self) -> bool:
        return self.local_mvp_profile_enabled and all(
            (self.local_mvp_developer_token, self.local_mvp_reviewer_token)
        )

    @property
    def model_ollama_configured(self) -> bool:
        return self.model_ollama_enabled and all(
            (
                self.model_ollama_name,
                self.model_ollama_api_key_env,
                self.model_ollama_base_url,
            )
        )


def get_settings() -> Settings:
    """Load and validate the minimal application configuration."""
    app_env = os.environ.get("APP_ENV")
    if app_env not in _ALLOWED_APP_ENVS:
        raise ConfigurationError(
            "APP_ENV must be one of: development, test, production"
        )

    local_mvp_enabled = _boolean_env("LOCAL_MVP_PROFILE_ENABLED", False)
    local_developer_token = os.environ.get("LOCAL_MVP_DEVELOPER_TOKEN") or None
    local_reviewer_token = os.environ.get("LOCAL_MVP_REVIEWER_TOKEN") or None
    local_tenant_slug = os.environ.get("LOCAL_MVP_TENANT_SLUG") or "local-mvp"
    local_workspace_root = os.environ.get("LOCAL_MVP_WORKSPACE_ROOT") or "/workspaces"
    local_github_dry_run = _boolean_env(
        "LOCAL_MVP_GITHUB_DRY_RUN", local_mvp_enabled
    )
    local_explicit_values = (
        local_developer_token,
        local_reviewer_token,
        os.environ.get("LOCAL_MVP_TENANT_SLUG"),
        os.environ.get("LOCAL_MVP_WORKSPACE_ROOT"),
        os.environ.get("LOCAL_MVP_GITHUB_DRY_RUN"),
    )
    if not local_mvp_enabled and any(value is not None for value in local_explicit_values):
        raise ConfigurationError(
            "Local MVP configuration requires explicit profile enablement"
        )
    if local_mvp_enabled:
        if app_env == "production":
            raise ConfigurationError("Local MVP profile is forbidden in production")
        if not local_developer_token or not local_reviewer_token:
            raise ConfigurationError("Local MVP requires both local identity tokens")
        if not 16 <= len(local_developer_token) <= 256 or not 16 <= len(
            local_reviewer_token
        ) <= 256:
            raise ConfigurationError("Local MVP token length must be 16 through 256")
        if local_developer_token == local_reviewer_token:
            raise ConfigurationError("Local MVP identity tokens must be distinct")
        if not local_github_dry_run:
            raise ConfigurationError("Local MVP requires GitHub dry-run mode")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,62}", local_tenant_slug):
            raise ConfigurationError("Local MVP tenant slug is invalid")
        if not local_workspace_root.startswith(("/", "\\")) and not re.match(
            r"^[A-Za-z]:[\\/]", local_workspace_root
        ):
            raise ConfigurationError("Local MVP workspace root must be absolute")

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

    raw_local_enabled = (os.environ.get("MODEL_LOCAL_FALLBACK_ENABLED") or "false").lower()
    if raw_local_enabled not in {"true", "false"}:
        raise ConfigurationError("MODEL_LOCAL_FALLBACK_ENABLED must be true or false")
    local_enabled = raw_local_enabled == "true"
    local_values = {
        "model_local_fallback_name": os.environ.get("MODEL_LOCAL_FALLBACK_NAME") or None,
        "model_local_fallback_api_key_env": os.environ.get("MODEL_LOCAL_FALLBACK_API_KEY_ENV") or None,
        "model_local_fallback_base_url": os.environ.get("MODEL_LOCAL_FALLBACK_BASE_URL") or None,
    }
    local_count = sum(value is not None for value in local_values.values())
    if local_enabled and (
        app_env == "production"
        or local_count != len(local_values)
        or model_configured_count != len(model_values)
    ):
        raise ConfigurationError(
            "Local model fallback is non-production and requires both existing routes, model, Secret reference, and base URL"
        )
    if not local_enabled and local_count:
        raise ConfigurationError("Local model fallback configuration requires explicit enablement")
    if local_enabled:
        parsed = urlsplit(local_values["model_local_fallback_base_url"] or "")
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            raise ConfigurationError("Local model fallback base URL must be loopback HTTP without credentials")
        configured_names = [name for name in (
            model_values["model_primary_name"], model_values["model_fallback_name"],
            local_values["model_local_fallback_name"],
        ) if name is not None]
        if len(set(configured_names)) != len(configured_names):
            raise ConfigurationError("Model route names must be distinct")

    ollama_enabled = _boolean_env("MODEL_OLLAMA_ENABLED", False)
    ollama_values = {
        "model_ollama_name": os.environ.get("MODEL_OLLAMA_NAME") or None,
        "model_ollama_api_key_env": os.environ.get("MODEL_OLLAMA_API_KEY_ENV") or None,
        "model_ollama_base_url": os.environ.get("MODEL_OLLAMA_BASE_URL") or None,
    }
    ollama_count = sum(value is not None for value in ollama_values.values())
    if not ollama_enabled and ollama_count:
        raise ConfigurationError("Ollama configuration requires explicit enablement")
    if ollama_enabled:
        if not local_mvp_enabled:
            raise ConfigurationError(
                "Ollama local-only route requires the local MVP profile"
            )
        if app_env == "production" or ollama_count != len(ollama_values):
            raise ConfigurationError(
                "Ollama local-only route is non-production and requires complete configuration"
            )
        if local_enabled:
            raise ConfigurationError(
                "Ollama local-only route and local vLLM fallback cannot both be enabled"
            )
        parsed_ollama = urlsplit(ollama_values["model_ollama_base_url"] or "")
        if (
            parsed_ollama.scheme != "http"
            or parsed_ollama.hostname
            not in {"127.0.0.1", "localhost", "host.docker.internal"}
            or parsed_ollama.username is not None
            or parsed_ollama.password is not None
            or parsed_ollama.query
            or parsed_ollama.fragment
            or parsed_ollama.path not in {"", "/"}
        ):
            raise ConfigurationError(
                "Ollama base URL must be approved local HTTP without credentials"
            )
        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            ollama_values["model_ollama_api_key_env"] or "",
        ):
            raise ConfigurationError("Ollama API key environment reference is invalid")

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

    sandbox_test_image = (
        os.environ.get("SANDBOX_TEST_IMAGE") or _DEFAULT_SANDBOX_TEST_IMAGE
    )
    if not _PINNED_IMAGE.fullmatch(sandbox_test_image):
        raise ConfigurationError("SANDBOX_TEST_IMAGE must be digest pinned")

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
        model_local_fallback_enabled=local_enabled,
        **local_values,
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
        sandbox_test_image=sandbox_test_image,
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
        local_mvp_profile_enabled=local_mvp_enabled,
        local_mvp_developer_token=local_developer_token,
        local_mvp_reviewer_token=local_reviewer_token,
        local_mvp_tenant_slug=local_tenant_slug,
        local_mvp_workspace_root=local_workspace_root,
        local_mvp_github_dry_run=local_github_dry_run,
        model_ollama_enabled=ollama_enabled,
        **ollama_values,
    )


def _boolean_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.casefold()
    if normalized not in {"true", "false"}:
        raise ConfigurationError(f"{name} must be true or false")
    return normalized == "true"
