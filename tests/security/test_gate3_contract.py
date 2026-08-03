from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

SECURITY_SUITES = (
    "tests/control_plane/test_oidc.py",
    "tests/control_plane/test_rbac.py",
    "tests/control_plane/test_audit_service.py",
    "tests/control_plane/test_registry_service.py",
    "tests/control_plane/test_tenant_scope.py",
    "tests/gateway/mcp/test_registry_gate.py",
    "tests/gateway/policy/test_contextual.py",
    "tests/gateway/policy/test_injection.py",
    "tests/gateway/sandbox/test_runner.py",
    "tests/security/test_cross_tenant_isolation.py",
)


def test_required_ci_preserves_gate3_evidence_contract() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    for suite in SECURITY_SUITES:
        assert suite in workflow

    assert "--junitxml=gate3-evidence/junit.xml" in workflow
    assert "gate3-evidence/security-gate.log" in workflow
    assert "gate3-evidence/secret-scan.log" in workflow
    assert "gate3-evidence/environment.txt" in workflow
    assert "gate3-security-evidence-${{ github.run_id }}" in workflow
    assert "retention-days: 30" in workflow
    assert "':!tests/control_plane/test_audit_service.py'" in workflow
    assert "':!tests/runtime/test_tracing.py'" in workflow
    assert "retry" not in workflow.lower()
