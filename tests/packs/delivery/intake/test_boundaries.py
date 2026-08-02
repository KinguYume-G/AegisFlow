"""Static dependency guard for AF-104 modules."""

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


def test_intake_and_contracts_are_framework_independent() -> None:
    source_files = [
        *PACKAGE_ROOT.joinpath("contracts").glob("*.py"),
        *PACKAGE_ROOT.joinpath("intake").glob("*.py"),
    ]

    assert source_files
    for source_file in source_files:
        assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)
