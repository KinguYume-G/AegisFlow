"""Unit tests for minimal process-environment configuration."""

import pytest

from aegisflow_core.settings import ConfigurationError, get_settings


@pytest.mark.parametrize("app_env", ["development", "test", "production"])
def test_valid_app_env_accepted(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test",
    )
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    settings = get_settings()

    assert settings.app_env == app_env
    assert settings.app_base_url is None


def test_missing_app_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test",
    )

    with pytest.raises(ConfigurationError):
        get_settings()


def test_invalid_app_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test",
    )

    with pytest.raises(ConfigurationError):
        get_settings()


def test_app_base_url_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test",
    )
    monkeypatch.setenv("APP_BASE_URL", "https://aegisflow.example.test")

    settings = get_settings()

    assert settings.app_base_url == "https://aegisflow.example.test"


@pytest.mark.parametrize("database_url", [None, ""])
def test_database_url_required(
    monkeypatch: pytest.MonkeyPatch, database_url: str | None
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(ConfigurationError):
        get_settings()


def test_database_url_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = (
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test"
    )
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = get_settings()

    assert settings.database_url == database_url


def test_github_app_configuration_is_optional(valid_env: None) -> None:
    settings = get_settings()

    assert settings.github_app_configured is False


def test_complete_github_app_configuration_is_accepted(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_PRIVATE_KEY": "private-key",
        "GITHUB_APP_WEBHOOK_SECRET": "webhook-secret",
        "GITHUB_APP_INSTALLATION_ID": "456",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = get_settings()

    assert settings.github_app_configured is True
    assert settings.github_installation_id == "456"


@pytest.mark.parametrize(
    "configured_names",
    [
        ("GITHUB_APP_ID",),
        ("GITHUB_APP_ID", "GITHUB_APP_PRIVATE_KEY"),
        (
            "GITHUB_APP_ID",
            "GITHUB_APP_PRIVATE_KEY",
            "GITHUB_APP_WEBHOOK_SECRET",
        ),
    ],
)
def test_partial_github_app_configuration_is_rejected(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    configured_names: tuple[str, ...],
) -> None:
    for name in configured_names:
        monkeypatch.setenv(name, "configured")

    with pytest.raises(ConfigurationError):
        get_settings()


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "not-a-number"])
def test_github_api_timeout_must_be_positive(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("GITHUB_API_TIMEOUT_SECONDS", value)

    with pytest.raises(ConfigurationError):
        get_settings()


def test_github_api_timeout_is_configurable(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_API_TIMEOUT_SECONDS", "2.5")

    assert get_settings().github_api_timeout_seconds == 2.5


def test_complete_model_gateway_references_are_accepted(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODEL_PRIMARY_NAME", "provider/model-a")
    monkeypatch.setenv("MODEL_PRIMARY_API_KEY_ENV", "PRIMARY_PROVIDER_KEY")
    monkeypatch.setenv("MODEL_FALLBACK_NAME", "provider/model-b")
    monkeypatch.setenv("MODEL_FALLBACK_API_KEY_ENV", "FALLBACK_PROVIDER_KEY")
    settings = get_settings()
    assert settings.model_gateway_configured
    assert settings.model_primary_api_key_env == "PRIMARY_PROVIDER_KEY"


def test_partial_model_gateway_references_fail_closed(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODEL_PRIMARY_NAME", "provider/model-a")
    with pytest.raises(ConfigurationError, match="Model gateway"):
        get_settings()


def test_primary_and_fallback_model_must_be_distinct(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in {
        "MODEL_PRIMARY_NAME": "provider/same",
        "MODEL_PRIMARY_API_KEY_ENV": "PRIMARY_KEY",
        "MODEL_FALLBACK_NAME": "provider/same",
        "MODEL_FALLBACK_API_KEY_ENV": "FALLBACK_KEY",
    }.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match="distinct"):
        get_settings()


def test_complete_oidc_configuration_is_accepted(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = {
        "OIDC_ISSUER": "https://issuer.example.test",
        "OIDC_AUDIENCE": "aegisflow-dev",
        "OIDC_JWKS_URL": "https://issuer.example.test/.well-known/jwks.json",
        "OIDC_ALGORITHM": "RS256",
        "OIDC_CACHE_TTL_SECONDS": "120",
        "OIDC_MAX_CACHED_KEYS": "8",
        "OIDC_HTTP_TIMEOUT_SECONDS": "2.5",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = get_settings()
    assert settings.oidc_configured
    assert settings.oidc_config is not None
    assert settings.oidc_config.max_cached_keys == 8


def test_partial_or_unsafe_oidc_configuration_fails_closed(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.test")
    with pytest.raises(ConfigurationError, match="OIDC"):
        get_settings()


def test_otel_configuration_is_optional_and_bounded(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    assert settings.otel_exporter_otlp_endpoint is None
    assert settings.otel_service_name == "aegisflow-core"
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel.example.test/v1/traces")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "aegisflow-test")
    settings = get_settings()
    assert settings.otel_exporter_otlp_endpoint == "https://otel.example.test/v1/traces"
    assert settings.otel_service_name == "aegisflow-test"


def test_otel_configuration_rejects_unsafe_production_export(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel.example.test")
    with pytest.raises(ConfigurationError, match="HTTPS"):
        get_settings()
    for name, value in {
        "OIDC_AUDIENCE": "aegisflow-dev",
        "OIDC_JWKS_URL": "https://issuer.example.test/jwks",
        "OIDC_ALGORITHM": "HS256",
    }.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match="OIDC"):
        get_settings()
