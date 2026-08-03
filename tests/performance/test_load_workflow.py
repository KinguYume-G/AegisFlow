from pathlib import Path


def test_load_workflow_is_bounded_and_pinned() -> None:
    workflow = Path(".github/workflows/m5-load-test.yml").read_text(encoding="utf-8")
    assert "--users 100" in workflow
    assert "--run-time 20s" in workflow
    assert "--exit-code-on-error 1" in workflow
    assert "persist-credentials: false" in workflow
    for line in workflow.splitlines():
        if "uses:" in line:
            reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
            assert "@" in reference
            assert len(reference.rsplit("@", 1)[1]) == 40
