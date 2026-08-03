"""Static and CLI-backed contracts for the AF-102 container foundation."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).parents[1]
COMPOSE_FILE = ROOT / "compose.yaml"
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"

COMPOSE_ENV = {
    "APP_ENV": "test",
    "APP_BASE_URL": "http://127.0.0.1:8000",
    "CORE_HOST_PORT": "8000",
    "POSTGRES_USER": "aegisflow",
    "POSTGRES_PASSWORD": "local-placeholder-only",
    "POSTGRES_DB": "aegisflow_dev",
    "POSTGRES_HOST_PORT": "5432",
    "REDIS_HOST_PORT": "6379",
}


@pytest.fixture(scope="module")
def compose_config() -> dict[str, object]:
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is unavailable")

    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        env={**os.environ, **COMPOSE_ENV},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"docker compose config failed: {result.stderr}")
    return json.loads(result.stdout)


def test_compose_declares_only_approved_services(
    compose_config: dict[str, object],
) -> None:
    services = compose_config["services"]
    assert isinstance(services, dict)
    assert set(services) == {"core", "postgres", "redis", "sandbox-broker"}


def test_service_images_are_immutable(compose_config: dict[str, object]) -> None:
    services = compose_config["services"]
    assert isinstance(services, dict)
    for name in ("postgres", "redis"):
        image = services[name]["image"]
        assert "@sha256:" in image
        assert not image.endswith(":latest")


def test_ports_bind_only_to_loopback(compose_config: dict[str, object]) -> None:
    services = compose_config["services"]
    assert isinstance(services, dict)
    for name in ("core", "postgres", "redis"):
        ports = services[name]["ports"]
        assert ports
        assert all(port["host_ip"] == "127.0.0.1" for port in ports)


def test_core_environment_is_allowlisted(compose_config: dict[str, object]) -> None:
    services = compose_config["services"]
    assert isinstance(services, dict)
    assert set(services["core"]["environment"]) == {
        "APP_BASE_URL",
        "APP_ENV",
        "DATABASE_URL",
        "SANDBOX_BROKER_URL",
    }
    assert services["core"]["environment"]["DATABASE_URL"] == (
        "postgresql+asyncpg://aegisflow:local-placeholder-only@postgres:5432/"
        "aegisflow_dev"
    )
    assert set(services["postgres"]["environment"]) == {
        "POSTGRES_DB",
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
    }
    assert "environment" not in services["redis"]


def test_healthchecks_and_startup_dependencies_are_explicit(
    compose_config: dict[str, object],
) -> None:
    services = compose_config["services"]
    assert isinstance(services, dict)
    assert all("healthcheck" in services[name] for name in services)
    assert services["core"]["depends_on"] == {
        "postgres": {"condition": "service_healthy", "required": True},
        "redis": {"condition": "service_healthy", "required": True},
        "sandbox-broker": {"condition": "service_healthy", "required": True},
    }


def test_only_broker_has_docker_socket(compose_config: dict[str, object]) -> None:
    services = compose_config["services"]
    assert isinstance(services, dict)
    core_mounts = services["core"]["volumes"]
    assert all(mount["source"] != "/var/run/docker.sock" for mount in core_mounts)
    broker_mounts = services["sandbox-broker"]["volumes"]
    assert any(mount["source"] == "/var/run/docker.sock" for mount in broker_mounts)


def test_required_values_fail_during_compose_interpolation() -> None:
    compose_text = COMPOSE_FILE.read_text(encoding="utf-8")
    for variable in ("APP_ENV", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        assert f"${{{variable}:?" in compose_text


def test_dockerfile_uses_reproducible_non_root_runtime() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "ghcr.io/astral-sh/uv:0.11.31@sha256:" in dockerfile
    assert "python:3.12-slim@sha256:" in dockerfile
    assert "uv sync --locked --no-dev --no-editable" in dockerfile
    assert "USER appuser" in dockerfile
    assert 'CMD ["uvicorn"' in dockerfile
    assert 'CMD ["uv", "run"' not in dockerfile


def test_docker_build_context_excludes_sensitive_and_non_runtime_files() -> None:
    ignored = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert {".env", ".git", ".venv", "archive", "docs", "tests"} <= ignored


def test_example_environment_contains_only_placeholders_for_new_fields() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for variable in (
        "CORE_HOST_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_HOST_PORT",
        "REDIS_HOST_PORT",
    ):
        assert f"{variable}=<{variable}>" in example
