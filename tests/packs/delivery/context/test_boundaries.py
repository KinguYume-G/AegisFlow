"""Static dependency and root-injection guards for AF-106."""

import ast
import inspect
from pathlib import Path

from aegisflow_core.packs.delivery.context.fakes import LocalFixtureContextRetriever


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
    "github",
    "httpx",
    "langchain",
    "langgraph",
    "litellm",
    "openai",
    "requests",
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


def test_context_modules_are_framework_and_network_independent() -> None:
    source_files = [
        PACKAGE_ROOT / "contracts" / "context_package.py",
        *PACKAGE_ROOT.joinpath("context").glob("*.py"),
    ]

    assert all(path.is_file() for path in source_files)
    for source_file in source_files:
        assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)


def test_fixture_root_is_explicitly_injected() -> None:
    signature = inspect.signature(LocalFixtureContextRetriever)

    assert tuple(signature.parameters) == ("root",)
    source = inspect.getsource(LocalFixtureContextRetriever)
    assert "tests/" not in source
    assert "tests\\" not in source
