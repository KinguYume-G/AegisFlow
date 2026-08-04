"""Run sanitized Personal Workbench inputs through the existing Gate 1A graph."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field

from aegisflow_core.packs.delivery.clarifier.fakes import (
    DeterministicClarificationReasoner,
)
from aegisflow_core.packs.delivery.clarifier.hitl import (
    InMemoryClarificationGateway,
)
from aegisflow_core.packs.delivery.context.fakes import LocalFixtureContextRetriever
from aegisflow_core.packs.delivery.contracts.determinism import (
    FixedClock,
    SequentialIdGenerator,
)
from aegisflow_core.packs.delivery.contracts.normalized_request import SourceType
from aegisflow_core.packs.delivery.planner.fakes import DeterministicPlanReasoner
from aegisflow_core.runtime.graph import build_gate1a_graph
from aegisflow_core.runtime.tracing import InMemoryTraceRecorder


SCENARIOS = ("xuemai", "syntour", "omni-assistant", "internship-tracking")
_ID_NAMESPACE = UUID("7dfdc909-10e0-5daa-8de2-b13614508c2d")


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: Literal["xuemai", "syntour", "omni-assistant", "internship-tracking"]
    source_type: SourceType
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=100_000)
    received_at: datetime


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    scenario: str
    source_classification: Literal["sanitized_fixture", "private_repository"]
    run_id: UUID
    trace_id: UUID
    request_id: str
    status: Literal["planned"]
    risk_level: str
    task_count: int = Field(ge=1)
    citation_count: int = Field(ge=1)
    input_received_at: datetime


def _load_scenarios(path: Path) -> list[Scenario]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError("scenario input must be a regular file")
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    scenarios = [Scenario.model_validate(item) for item in raw]
    if tuple(item.scenario for item in scenarios) != SCENARIOS:
        raise ValueError("scenario input must contain the four canonical scenarios in order")
    return scenarios


def _parse_roots(values: list[str], fixture_root: Path) -> dict[str, tuple[Path, str]]:
    roots = {
        scenario: (fixture_root / scenario, "sanitized_fixture")
        for scenario in SCENARIOS
    }
    for value in values:
        scenario, separator, raw_path = value.partition("=")
        if not separator or scenario not in SCENARIOS or not raw_path:
            raise ValueError("repository roots must use canonical-scenario=/absolute/path")
        roots[scenario] = (Path(raw_path), "private_repository")
    resolved: dict[str, tuple[Path, str]] = {}
    for scenario, (path, classification) in roots.items():
        candidate = path.resolve(strict=True)
        if not candidate.is_dir() or candidate.is_symlink():
            raise ValueError(f"repository root is unsafe for scenario: {scenario}")
        resolved[scenario] = (candidate, classification)
    return resolved


def run_scenarios(
    scenario_file: Path,
    fixture_root: Path,
    repository_roots: list[str] | None = None,
) -> list[UsageRecord]:
    scenarios = _load_scenarios(scenario_file)
    roots = _parse_roots(repository_roots or [], fixture_root.resolve(strict=True))
    records: list[UsageRecord] = []

    for scenario in scenarios:
        run_id = uuid5(_ID_NAMESPACE, f"{scenario.scenario}:run")
        trace_id = uuid5(_ID_NAMESPACE, f"{scenario.scenario}:trace")
        root, classification = roots[scenario.scenario]
        graph = build_gate1a_graph(
            clock=FixedClock(scenario.received_at),
            id_generator=SequentialIdGenerator(f"{scenario.scenario}:steps"),
            clarification_reasoner=DeterministicClarificationReasoner(),
            context_retriever=LocalFixtureContextRetriever(root),
            plan_reasoner=DeterministicPlanReasoner(),
            hitl_gateway=InMemoryClarificationGateway(
                SequentialIdGenerator(f"{scenario.scenario}:hitl")
            ),
            trace_recorder=InMemoryTraceRecorder(),
        )
        result = graph.invoke(
            {
                "run_id": run_id,
                "trace_id": trace_id,
                "source_type": scenario.source_type,
                "source_ref": f"{classification}://{scenario.scenario}",
                "title": scenario.title,
                "body": scenario.body,
            },
            config={"configurable": {"thread_id": str(run_id)}},
        )
        if "__interrupt__" in result or result.get("plan") is None:
            raise RuntimeError(f"scenario did not reach a deterministic plan: {scenario.scenario}")
        request = result["request"]
        context = result["context"]
        plan = result["plan"]
        if not context.snippets:
            raise RuntimeError(f"scenario has no cited repository evidence: {scenario.scenario}")
        records.append(
            UsageRecord(
                scenario=scenario.scenario,
                source_classification=classification,
                run_id=run_id,
                trace_id=trace_id,
                request_id=request.idempotency_key,
                status="planned",
                risk_level=plan.risk_level,
                task_count=len(plan.tasks),
                citation_count=len(context.snippets),
                input_received_at=scenario.received_at,
            )
        )
    return records


def write_jsonl(records: list[UsageRecord], output: Path) -> None:
    parent = output.parent.resolve(strict=True)
    if output.exists() and output.is_symlink():
        raise ValueError("output must not be a symbolic link")
    payload = "".join(
        json.dumps(record.model_dump(mode="json"), sort_keys=True) + "\n"
        for record in records
    )
    output.write_text(payload, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("tests/fixtures/personal_workbench/scenarios.json"),
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=Path("tests/fixtures/personal_workbench/repositories"),
    )
    parser.add_argument("--repository", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    records = run_scenarios(
        arguments.scenarios,
        arguments.fixture_root,
        arguments.repository,
    )
    write_jsonl(records, arguments.output)
    print(json.dumps({"status": "ok", "cases": len(records), "output": str(arguments.output)}))


if __name__ == "__main__":
    main()
