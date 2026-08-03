import ast
from pathlib import Path


def test_control_plane_profile_is_bounded_and_credential_free() -> None:
    source = Path("tests/performance/locustfile.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == ["ControlPlaneUser"]
    assert any(
        isinstance(base, ast.Name) and base.id == "HttpUser"
        for base in classes[0].bases
    )
    assert '"/health"' in source
    assert '"/metrics"' in source
    assert "authorization" not in source.casefold()
