from pathlib import Path
import re

import pytest

from scripts.personal_workbench.seed_requests import (
    SCENARIOS,
    run_scenarios,
    write_jsonl,
)


ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "personal_workbench"
SCENARIO_FILE = FIXTURES / "scenarios.json"
REPOSITORIES = FIXTURES / "repositories"


def test_four_fixture_scenarios_are_deterministic_and_plan_only(tmp_path: Path) -> None:
    first = run_scenarios(SCENARIO_FILE, REPOSITORIES)
    second = run_scenarios(SCENARIO_FILE, REPOSITORIES)
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    write_jsonl(first, first_path)
    write_jsonl(second, second_path)

    assert first_path.read_bytes() == second_path.read_bytes()
    assert tuple(record.scenario for record in first) == SCENARIOS
    assert len({record.run_id for record in first}) == 4
    assert len({record.trace_id for record in first}) == 4
    assert len({record.request_id for record in first}) == 4
    assert all(record.source_classification == "sanitized_fixture" for record in first)
    assert all(record.status == "planned" for record in first)
    assert all(record.task_count == 4 for record in first)
    assert all(record.citation_count >= 1 for record in first)


def test_usage_log_contains_only_bounded_schema_fields(tmp_path: Path) -> None:
    output = tmp_path / "usage.jsonl"
    write_jsonl(run_scenarios(SCENARIO_FILE, REPOSITORIES), output)
    payload = output.read_text(encoding="utf-8")

    assert "body" not in payload
    assert "content" not in payload
    assert "@" not in payload
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}", payload)


def test_repository_override_is_classified_without_disclosing_path() -> None:
    override = f"xuemai={REPOSITORIES / 'xuemai'}"
    records = run_scenarios(SCENARIO_FILE, REPOSITORIES, [override])

    assert records[0].source_classification == "private_repository"
    assert all(str(REPOSITORIES) not in record.model_dump_json() for record in records)


def test_invalid_repository_override_fails_closed() -> None:
    with pytest.raises(ValueError, match="canonical-scenario"):
        run_scenarios(SCENARIO_FILE, REPOSITORIES, ["unknown=/tmp"])


def test_cli_uses_existing_gate1a_graph_without_agent_or_write_expansion() -> None:
    source = (ROOT / "scripts" / "personal_workbench" / "seed_requests.py").read_text(
        encoding="utf-8"
    )

    assert "build_gate1a_graph" in source
    assert "ExecutorAgent" not in source
    assert "ReviewerAgent" not in source
    assert "DraftPullRequest" not in source
    assert "httpx" not in source


def test_real_repository_smoke_is_manual_scoped_and_pinned() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "personal-workbench-smoke.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "environment: personal-workbench-development" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1" in workflow
    assert "permission-contents: read" in workflow
    assert workflow.count("persist-credentials: false") == 4
    assert "PERSONAL_WORKBENCH_APP_PRIVATE_KEY" in workflow
    assert "personal-workbench-evidence-${{ github.run_id }}" in workflow
