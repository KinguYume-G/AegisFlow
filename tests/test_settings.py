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
        "GITHUB_WEBHOOK_SECRET": "webhook-secret",
        "GITHUB_INSTALLATION_ID": "456",
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
            "GITHUB_WEBHOOK_SECRET",
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
