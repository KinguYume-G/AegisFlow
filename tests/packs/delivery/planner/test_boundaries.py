"""Static dependency guards for AF-107 Planner modules."""

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[4] / "src" / "aegisflow_core" / "packs" / "delivery"
PROHIBITED_IMPORT_ROOTS = {
    "alembic",
    "asyncpg",
    "fastapi",
    "langchain",
    "langgraph",
    "litellm",
    "mcp",
    "openai",
    "sqlalchemy",
    "starlette",
    "temporalio",
    "uvicorn",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def test_planner_and_contracts_are_framework_independent() -> None:
    source_files = [
        PACKAGE_ROOT / "contracts" / "measurement.py",
        PACKAGE_ROOT / "contracts" / "plan.py",
        *PACKAGE_ROOT.joinpath("planner").glob("*.py"),
    ]

    assert len(source_files) == 6
    assert all(path.is_file() for path in source_files)
    for source_file in source_files:
        assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)


def test_af_107_does_not_create_later_issue_modules() -> None:
    assert not PACKAGE_ROOT.joinpath("clarifier", "hitl.py").exists()
    assert not PACKAGE_ROOT.parents[1].joinpath("runtime", "state.py").exists()
