import ast
from pathlib import Path

import pytest

from aegisflow_core.runtime.temporal.ownership import RuntimeOwner, STATE_OWNERS, owner_of


def test_every_runtime_state_has_exactly_one_owner() -> None:
    assert len(STATE_OWNERS) == len(set(STATE_OWNERS))
    assert owner_of("workflow_lifecycle") is RuntimeOwner.TEMPORAL
    assert owner_of("agent_graph_state") is RuntimeOwner.LANGGRAPH
    assert owner_of("tenant_run_step_approval_audit") is RuntimeOwner.POSTGRESQL
    with pytest.raises(ValueError):
        owner_of("unknown")


def test_workflow_module_has_no_side_effect_or_nondeterministic_imports() -> None:
    path = Path(__file__).parents[3] / "src" / "aegisflow_core" / "runtime" / "temporal" / "workflow.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "asyncpg", "docker", "httpx", "os", "pathlib", "psycopg", "random",
        "secrets", "sqlalchemy", "subprocess", "time", "uuid",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(forbidden)
