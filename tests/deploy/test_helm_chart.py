from pathlib import Path
import re

ROOT = Path(__file__).parents[2]
CHART = ROOT / "deploy" / "helm" / "aegisflow"


def test_chart_uses_existing_secret_and_pinned_dependency_images() -> None:
    values = (CHART / "values.yaml").read_text(encoding="utf-8")
    templates = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((CHART / "templates").glob("*"))
        if path.is_file()
    )

    assert 'existingSecret: ""' in values
    image_block = values.split("images:\n", 1)[1].split("\ndependencyResources:", 1)[0]
    images = [line.split(": ", 1)[1] for line in image_block.splitlines() if ": " in line]
    assert len(images) == 5
    assert all(re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", image) for image in images)
    assert "kind: Secret" not in templates
    assert "existingSecret is required" in templates
    for key in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "DATABASE_URL",
        "LANGGRAPH_DATABASE_URL",
        "TEMPORAL_POSTGRES_USER",
        "TEMPORAL_POSTGRES_PASSWORD",
        "TEMPORAL_POSTGRES_DB",
    ):
        assert key in templates or key in (CHART / "README.md").read_text(encoding="utf-8")


def test_runtime_image_contains_alembic_assets_required_by_init_container() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY --chown=appuser:appgroup alembic.ini ./" in dockerfile
    assert "/app/src/aegisflow_core/control_plane/migrations" in dockerfile


def test_application_workloads_are_bounded_and_non_privileged() -> None:
    workloads = (CHART / "templates" / "workloads.yaml").read_text(encoding="utf-8")
    service_accounts = (CHART / "templates" / "serviceaccounts.yaml").read_text(
        encoding="utf-8"
    )

    assert workloads.count("runAsNonRoot: true") >= 3
    assert workloads.count("runAsUser: 10001") == 2
    assert workloads.count("runAsGroup: 10001") == 2
    assert workloads.count("readOnlyRootFilesystem: true") >= 3
    assert workloads.count('drop: ["ALL"]') >= 3
    assert workloads.count("allowPrivilegeEscalation: false") >= 3
    assert "securityContext: *appSecurity" in workloads
    assert "fieldPath: status.podIP" in workloads
    assert 'TEMPORAL_ADDRESS, value: "$(POD_IP):7233"' in workloads
    assert "resources:" in workloads
    assert "automountServiceAccountToken: false" in service_accounts
    assert "sandbox-broker" not in workloads


def test_network_policy_is_default_deny_with_explicit_flows() -> None:
    policy = (CHART / "templates" / "networkpolicies.yaml").read_text(
        encoding="utf-8"
    )

    assert "podSelector: {}" in policy
    assert "policyTypes: [Ingress, Egress]" in policy
    for port in (53, 5432, 6379, 7233, 8000, 9090):
        assert f"port: {port}" in policy
    for component in (
        "core",
        "worker",
        "prometheus",
        "temporal",
        "postgres",
        "redis",
        "temporal-postgres",
    ):
        assert f"app.kubernetes.io/component: {component}" in policy
    assert "to: [{podSelector: {}}]" not in policy


def test_k3d_workflow_is_pinned_and_always_tears_down() -> None:
    script = (ROOT / "scripts" / "k3d-demo.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "m5-k3s-demo-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "k3d cluster create --config" in script
    assert "k3d cluster list --no-headers" in script
    assert "--mode direct" in script
    assert "helm upgrade --install" in script
    assert "helm rollback" in script
    assert "k3d cluster delete" in script
    assert "rollout status statefulset" in script
    assert "kind: Secret" not in script
    assert "--from-literal" in script
    assert "sha256sum --check" in workflow
    assert "helm lint" in workflow
    assert "helm template" in workflow
    assert "if: always()" in workflow
    assert "kubectl describe pods" in workflow
    assert "bash scripts/k3d-demo.sh down" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in workflow
