"""Static dependency guard for AF-105 modules."""

import ast
from pathlib import Path


PACKAGE_ROOT = (
    Path(__file__).parents[4]
    / "src"
    / "aegisflow_core"
    / "packs"
    / "delivery"
)
PROHIBITED_IMPORT_ROOTS = {
    "alembic",
    "asyncpg",
    "fastapi",
    "langgraph",
    "litellm",
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


def test_clarifier_and_contract_are_framework_independent() -> None:
    source_files = [
        PACKAGE_ROOT / "contracts" / "clarification.py",
        *PACKAGE_ROOT.joinpath("clarifier").glob("*.py"),
    ]

    assert all(path.is_file() for path in source_files)
    for source_file in source_files:
        assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)


def test_af_108_hitl_module_is_not_created_early() -> None:
    assert not PACKAGE_ROOT.joinpath("clarifier", "hitl.py").exists()
