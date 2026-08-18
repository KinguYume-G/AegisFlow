"""Static guards for the initial modular-monolith package boundaries."""

import ast
import importlib
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "aegisflow_core"
DOMAIN_PACKAGES = (
    "control_plane",
    "runtime",
    "gateway",
    "models",
    "evaluation",
    "packs",
    "packs.delivery",
)
PROHIBITED_IMPORT_ROOTS = {
    "anthropic",
    "fastapi",
    "litellm",
    "openai",
    "starlette",
    "uvicorn",
}


def _imports(path: Path) -> set[str]:
    imported: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def test_required_packages_are_importable() -> None:
    for package in DOMAIN_PACKAGES:
        imported = importlib.import_module(f"aegisflow_core.{package}")
        assert imported.__doc__


def test_domain_packages_do_not_import_frameworks_or_model_sdks() -> None:
    for package in DOMAIN_PACKAGES:
        package_path = PACKAGE_ROOT.joinpath(*package.split("."))
        for source_file in package_path.glob("*.py"):
            if source_file == PACKAGE_ROOT / "models" / "litellm_adapter.py":
                continue
            assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)

    control_plane = PACKAGE_ROOT / "control_plane"
    for source_file in (control_plane / "domain").glob("*.py"):
        assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)


def test_domain_packages_contain_only_approved_modules() -> None:
    expected_files = {
        PACKAGE_ROOT / "runtime" / "__init__.py",
        PACKAGE_ROOT / "runtime" / "langfuse_smoke.py",
            PACKAGE_ROOT / "runtime" / "fault_injection.py",
            PACKAGE_ROOT / "runtime" / "fault_injection_cli.py",
            PACKAGE_ROOT / "runtime" / "fault_probe.py",
            PACKAGE_ROOT / "runtime" / "fault_probe_worker.py",
            PACKAGE_ROOT / "runtime" / "graph.py",
            PACKAGE_ROOT / "runtime" / "gate1b.py",
        PACKAGE_ROOT / "runtime" / "state.py",
            PACKAGE_ROOT / "runtime" / "tracing.py",
            PACKAGE_ROOT / "runtime" / "observability.py",
            PACKAGE_ROOT / "runtime" / "metrics.py",
            PACKAGE_ROOT / "runtime" / "context" / "__init__.py",
            PACKAGE_ROOT / "runtime" / "context" / "chunking.py",
            PACKAGE_ROOT / "runtime" / "context" / "embedder.py",
            PACKAGE_ROOT / "runtime" / "context" / "store.py",
            PACKAGE_ROOT / "runtime" / "context" / "ingestion.py",
            PACKAGE_ROOT / "runtime" / "context" / "pgvector_retriever.py",
            PACKAGE_ROOT / "runtime" / "checkpoint" / "__init__.py",
            PACKAGE_ROOT / "runtime" / "checkpoint" / "postgres.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "__init__.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "activities.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "client.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "contracts.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "idempotent_activity.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "ownership.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "policies.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "saga.py",
            PACKAGE_ROOT / "runtime" / "temporal" / "saga_ledger.py",
                PACKAGE_ROOT / "runtime" / "temporal" / "worker.py",
                PACKAGE_ROOT / "runtime" / "temporal" / "workflow.py",
                PACKAGE_ROOT / "runtime" / "temporal" / "run_gateway.py",
                PACKAGE_ROOT / "runtime" / "temporal" / "graph_adapter.py",
        PACKAGE_ROOT / "gateway" / "__init__.py",
        PACKAGE_ROOT / "gateway" / "github" / "__init__.py",
        PACKAGE_ROOT / "gateway" / "github" / "auth.py",
            PACKAGE_ROOT / "gateway" / "github" / "read_tools.py",
            PACKAGE_ROOT / "gateway" / "github" / "pull_request.py",
            PACKAGE_ROOT / "gateway" / "github" / "idempotency_guard.py",
            PACKAGE_ROOT / "gateway" / "github" / "webhook.py",
            PACKAGE_ROOT / "gateway" / "sandbox" / "__init__.py",
            PACKAGE_ROOT / "gateway" / "sandbox" / "runner.py",
            PACKAGE_ROOT / "gateway" / "sandbox" / "docker_runner.py",
            PACKAGE_ROOT / "gateway" / "sandbox" / "broker.py",
            PACKAGE_ROOT / "gateway" / "policy" / "__init__.py",
            PACKAGE_ROOT / "gateway" / "policy" / "config.py",
            PACKAGE_ROOT / "gateway" / "policy" / "gate.py",
            PACKAGE_ROOT / "gateway" / "policy" / "contextual.py",
            PACKAGE_ROOT / "gateway" / "policy" / "injection.py",
            PACKAGE_ROOT / "gateway" / "mcp" / "__init__.py",
            PACKAGE_ROOT / "gateway" / "mcp" / "gate.py",
            PACKAGE_ROOT / "gateway" / "mcp" / "github_actions.py",
            PACKAGE_ROOT / "gateway" / "tenant.py",
        PACKAGE_ROOT / "models" / "__init__.py",
        PACKAGE_ROOT / "models" / "contracts.py",
        PACKAGE_ROOT / "models" / "circuit_breaker.py",
        PACKAGE_ROOT / "models" / "gateway.py",
        PACKAGE_ROOT / "models" / "litellm_adapter.py",
        PACKAGE_ROOT / "models" / "postgres_circuit.py",
        PACKAGE_ROOT / "models" / "smoke.py",
        PACKAGE_ROOT / "models" / "vllm_smoke.py",
        PACKAGE_ROOT / "evaluation" / "__init__.py",
        PACKAGE_ROOT / "evaluation" / "contracts.py",
        PACKAGE_ROOT / "evaluation" / "datasets.py",
        PACKAGE_ROOT / "evaluation" / "baseline.py",
        PACKAGE_ROOT / "evaluation" / "reporting.py",
        PACKAGE_ROOT / "evaluation" / "regression.py",
        PACKAGE_ROOT / "packs" / "__init__.py",
        PACKAGE_ROOT / "packs" / "opspilot" / "__init__.py",
        PACKAGE_ROOT / "packs" / "opspilot" / "contracts.py",
        PACKAGE_ROOT / "packs" / "opspilot" / "simulation.py",
        PACKAGE_ROOT / "packs" / "delivery" / "__init__.py",
            PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "__init__.py",
            PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "action_approval.py",
        PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "clarification.py",
        PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "context_package.py",
        PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "determinism.py",
        PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "measurement.py",
        PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "normalized_request.py",
            PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "plan.py",
                PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "idempotency.py",
                PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "unit_of_work.py",
            PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "execution_result.py",
            PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "review_decision.py",
            PACKAGE_ROOT / "packs" / "delivery" / "contracts" / "policy_decision.py",
            PACKAGE_ROOT / "packs" / "delivery" / "executor" / "__init__.py",
            PACKAGE_ROOT / "packs" / "delivery" / "executor" / "agent.py",
            PACKAGE_ROOT / "packs" / "delivery" / "executor" / "fakes.py",
            PACKAGE_ROOT / "packs" / "delivery" / "executor" / "ports.py",
            PACKAGE_ROOT / "packs" / "delivery" / "reviewer" / "__init__.py",
            PACKAGE_ROOT / "packs" / "delivery" / "reviewer" / "agent.py",
            PACKAGE_ROOT / "packs" / "delivery" / "reviewer" / "fakes.py",
            PACKAGE_ROOT / "packs" / "delivery" / "reviewer" / "ports.py",
        PACKAGE_ROOT / "packs" / "delivery" / "clarifier" / "__init__.py",
        PACKAGE_ROOT / "packs" / "delivery" / "clarifier" / "agent.py",
        PACKAGE_ROOT / "packs" / "delivery" / "clarifier" / "fakes.py",
        PACKAGE_ROOT / "packs" / "delivery" / "clarifier" / "hitl.py",
        PACKAGE_ROOT / "packs" / "delivery" / "clarifier" / "ports.py",
        PACKAGE_ROOT / "packs" / "delivery" / "context" / "__init__.py",
        PACKAGE_ROOT / "packs" / "delivery" / "context" / "agent.py",
        PACKAGE_ROOT / "packs" / "delivery" / "context" / "fakes.py",
        PACKAGE_ROOT / "packs" / "delivery" / "context" / "ports.py",
        PACKAGE_ROOT / "packs" / "delivery" / "intake" / "__init__.py",
        PACKAGE_ROOT / "packs" / "delivery" / "intake" / "agent.py",
        PACKAGE_ROOT / "packs" / "delivery" / "planner" / "__init__.py",
        PACKAGE_ROOT / "packs" / "delivery" / "planner" / "agent.py",
        PACKAGE_ROOT / "packs" / "delivery" / "planner" / "fakes.py",
            PACKAGE_ROOT / "packs" / "delivery" / "planner" / "ports.py",
            PACKAGE_ROOT / "packs" / "delivery" / "model_reasoners.py",
    }
    actual_files = {
        path
        for root in (
            PACKAGE_ROOT / "runtime",
            PACKAGE_ROOT / "gateway",
            PACKAGE_ROOT / "models",
            PACKAGE_ROOT / "evaluation",
            PACKAGE_ROOT / "packs",
        )
        for path in root.rglob("*.py")
    }
    assert actual_files == expected_files


def test_control_plane_contains_only_approved_modules() -> None:
    control_plane = PACKAGE_ROOT / "control_plane"
    expected_relative_files = {
        Path("__init__.py"),
        Path("bootstrap.py"),
        Path("run_graph.py"),
        Path("domain/__init__.py"),
        Path("domain/base.py"),
        Path("domain/tenant.py"),
        Path("domain/workflow.py"),
        Path("domain/execution.py"),
        Path("domain/approval.py"),
        Path("domain/audit.py"),
            Path("domain/session.py"),
                Path("domain/knowledge.py"),
                Path("domain/idempotency.py"),
                Path("domain/model_routing.py"),
                Path("domain/versioning.py"),
                Path("domain/access.py"),
                Path("approvals.py"),
                Path("rbac.py"),
                Path("audit.py"),
                Path("registries/__init__.py"),
                Path("registries/service.py"),
                Path("domain/registry.py"),
                Path("idempotency_ledger.py"),
                Path("runtime_uow.py"),
                Path("tenants/__init__.py"),
                Path("tenants/scope.py"),
                Path("versions/__init__.py"),
                Path("versions/service.py"),
                Path("identity/__init__.py"),
                    Path("identity/oidc.py"),
                    Path("identity/local.py"),
                    Path("clarifications.py"),
                    Path("run_projection.py"),
                    Path("run_service.py"),
                    Path("runs.py"),
                    Path("domain/run_lifecycle.py"),
        Path("migrations/env.py"),
        Path("migrations/versions/0001_initial_domain_model.py"),
            Path("migrations/versions/0002_normalize_check_names.py"),
            Path("migrations/versions/0003_add_knowledge_chunks.py"),
                Path("migrations/versions/0004_protect_approval_decisions.py"),
                Path("migrations/versions/0005_add_idempotency_ledger.py"),
                Path("migrations/versions/0006_add_model_circuit_state.py"),
                Path("migrations/versions/0007_add_tenant_version_foundations.py"),
                Path("migrations/versions/0008_add_identity_rbac.py"),
                    Path("migrations/versions/0009_add_tool_registry.py"),
                    Path("migrations/versions/0010_add_run_lifecycle_read_model.py"),
    }
    actual_relative_files = {
        path.relative_to(control_plane)
        for path in control_plane.rglob("*.py")
    }
    assert actual_relative_files == expected_relative_files


def test_delivery_and_domain_code_do_not_import_github_client_libraries() -> None:
    prohibited = {"cryptography", "httpx", "jwt"}
    guarded_roots = (
        PACKAGE_ROOT / "packs" / "delivery",
        PACKAGE_ROOT / "control_plane" / "domain",
    )
    for root in guarded_roots:
        for source_file in root.rglob("*.py"):
            assert _imports(source_file).isdisjoint(prohibited)


def test_application_layer_imports_are_explicit() -> None:
    assert "fastapi" in _imports(PACKAGE_ROOT / "app.py")
    assert "fastapi" in _imports(PACKAGE_ROOT / "health" / "router.py")
    assert "aegisflow_core" in _imports(PACKAGE_ROOT / "main.py")
