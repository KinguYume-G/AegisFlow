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
            assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)

    control_plane = PACKAGE_ROOT / "control_plane"
    for source_file in (control_plane / "domain").glob("*.py"):
        assert _imports(source_file).isdisjoint(PROHIBITED_IMPORT_ROOTS)


def test_unimplemented_domain_packages_contain_only_boundary_markers() -> None:
    expected_files = {
        PACKAGE_ROOT / "runtime" / "__init__.py",
        PACKAGE_ROOT / "gateway" / "__init__.py",
        PACKAGE_ROOT / "models" / "__init__.py",
        PACKAGE_ROOT / "evaluation" / "__init__.py",
        PACKAGE_ROOT / "packs" / "__init__.py",
        PACKAGE_ROOT / "packs" / "delivery" / "__init__.py",
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


def test_control_plane_contains_only_approved_af_103_modules() -> None:
    control_plane = PACKAGE_ROOT / "control_plane"
    expected_relative_files = {
        Path("__init__.py"),
        Path("domain/__init__.py"),
        Path("domain/base.py"),
        Path("domain/tenant.py"),
        Path("domain/workflow.py"),
        Path("domain/execution.py"),
        Path("domain/approval.py"),
        Path("domain/audit.py"),
        Path("domain/session.py"),
        Path("migrations/env.py"),
        Path("migrations/versions/0001_initial_domain_model.py"),
        Path("migrations/versions/0002_normalize_check_names.py"),
    }
    actual_relative_files = {
        path.relative_to(control_plane)
        for path in control_plane.rglob("*.py")
    }
    assert actual_relative_files == expected_relative_files


def test_application_layer_imports_are_explicit() -> None:
    assert "fastapi" in _imports(PACKAGE_ROOT / "app.py")
    assert "fastapi" in _imports(PACKAGE_ROOT / "health" / "router.py")
    assert "aegisflow_core" in _imports(PACKAGE_ROOT / "main.py")
