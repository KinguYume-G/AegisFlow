"""Static contracts for the AF-R07 local console containers."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
OVERRIDE = ROOT / "compose.local-mvp.yaml"
CONSOLE_DOCKERFILE = ROOT / "web" / "console" / "Dockerfile"


def test_local_profile_declares_isolated_developer_and_reviewer_consoles() -> None:
    compose = OVERRIDE.read_text(encoding="utf-8")

    assert "  console:" in compose
    assert "  reviewer-console:" in compose
    assert 'AEGISFLOW_CONSOLE_PERSONA: "developer"' in compose
    assert 'AEGISFLOW_CONSOLE_PERSONA: "reviewer"' in compose
    assert compose.count("AEGISFLOW_LOCAL_TOKEN:") == 2


def test_console_ports_are_loopback_only_and_roles_use_distinct_ports() -> None:
    compose = OVERRIDE.read_text(encoding="utf-8")

    assert '"127.0.0.1:${CONSOLE_HOST_PORT:-3000}:3000"' in compose
    assert '"127.0.0.1:${REVIEWER_CONSOLE_HOST_PORT:-3001}:3000"' in compose


def test_console_image_is_reproducible_and_non_root() -> None:
    dockerfile = CONSOLE_DOCKERFILE.read_text(encoding="utf-8")

    assert "node:24" in dockerfile and "@sha256:" in dockerfile
    assert "npm ci" in dockerfile
    assert "USER nextjs" in dockerfile
    assert 'CMD ["node", "server.js"]' in dockerfile
