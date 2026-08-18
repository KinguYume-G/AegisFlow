"""Static contracts for the AF-R09 authenticated local profile."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
OVERRIDE = ROOT / "compose.oidc-dev.yaml"


def test_oidc_worker_has_complete_local_delivery_runtime() -> None:
    compose = OVERRIDE.read_text(encoding="utf-8")
    worker = compose.split("  temporal-worker:\n", 1)[1].split("\n  console:\n", 1)[0]

    for setting in (
        'LOCAL_MVP_PROFILE_ENABLED: "true"',
        'LOCAL_MVP_GITHUB_DRY_RUN: "true"',
        'MODEL_OLLAMA_ENABLED: "true"',
        "MODEL_OLLAMA_BASE_URL: http://host.docker.internal:11434",
        "SANDBOX_BROKER_URL: http://sandbox-broker:8081",
        "LOCAL_MVP_WORKSPACE_ROOT: /workspaces",
    ):
        assert setting in worker
    assert '"host.docker.internal:host-gateway"' in worker
    assert "sandbox_workspaces:/workspaces" in worker
    assert "sandbox-broker:" in worker
    assert "condition: service_healthy" in worker
