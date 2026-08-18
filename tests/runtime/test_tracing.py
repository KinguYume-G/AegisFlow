"""Contract tests for AF-109 tracing and Langfuse integration."""

from __future__ import annotations

from decimal import Decimal
import itertools
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
import pytest

from aegisflow_core.runtime.tracing import (
    CostUsage,
    InMemoryTraceRecorder,
    LangfuseTraceRecorder,
    NoOpTraceRecorder,
    PostgresTraceRecorder,
    StepTraceRecord,
    TokenMeasurement,
    TokenUsage,
    build_step_trace_record,
    build_trace_recorder,
    make_event_id,
    redact,
    unavailable_cost_usage,
    unavailable_token_usage,
)
from aegisflow_core.settings import ConfigurationError, get_settings
import aegisflow_core.runtime.langfuse_smoke as smoke_module


class FakeObservation:
    def __init__(self) -> None:
        self.end_calls = 0

    def end(self) -> None:
        self.end_calls += 1


class FakeLangfuseClient:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.seeds: list[str] = []
        self.observation_calls: list[dict[str, Any]] = []
        self.observation = FakeObservation()

    def create_trace_id(self, *, seed: str) -> str:
        self.seeds.append(seed)
        return "0123456789abcdef0123456789abcdef"

    def start_observation(self, **kwargs: Any) -> FakeObservation:
        self.observation_calls.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return self.observation


def _record(**overrides: Any) -> StepTraceRecord:
    values: dict[str, Any] = {
        "tenant_id": uuid4(),
        "workflow_id": uuid4(),
        "workflow_version": 3,
        "run_id": uuid4(),
        "step_id": uuid4(),
        "trace_id": uuid4(),
        "agent": "planner",
        "raw_prompt": "Plan this safe request",
        "model": "deterministic-fake",
        "token_usage": unavailable_token_usage(),
        "cost": unavailable_cost_usage(),
        "latency_ms": 12.5,
    }
    values.update(overrides)
    return build_step_trace_record(**values)


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test",
    )
    for name in (
        "LANGFUSE_BASE_URL",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_TRACING_ENVIRONMENT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_trace_has_six_correlation_fields_and_event_id() -> None:
    record = _record()

    assert record.tenant_id is not None
    assert record.workflow_id is not None
    assert record.workflow_version == 3
    assert record.run_id
    assert record.step_id is not None
    assert record.trace_id
    assert isinstance(record.event_id, UUID)
    assert record.latency_ms == 12.5


def test_trace_rejects_negative_latency() -> None:
    with pytest.raises(ValidationError):
        _record(latency_ms=-0.1)


def test_event_id_is_deterministic_metadata() -> None:
    record = _record()

    assert record.event_id == make_event_id(
        run_id=record.run_id,
        step_id=record.step_id,
        agent=record.agent,
        trace_id=record.trace_id,
    )
    assert record.event_id == _record(
        tenant_id=record.tenant_id,
        workflow_id=record.workflow_id,
        workflow_version=record.workflow_version,
        run_id=record.run_id,
        step_id=record.step_id,
        trace_id=record.trace_id,
    ).event_id


@pytest.mark.parametrize("value", [-1, 1.5, None])
def test_token_measurement_rejects_invalid_measured_value(value: Any) -> None:
    with pytest.raises(ValidationError):
        TokenMeasurement(status="measured", value=value)


def test_token_measurement_invariants() -> None:
    assert TokenMeasurement(status="measured", value=0).value == 0
    assert TokenMeasurement(status="not_available").value is None
    with pytest.raises(ValidationError):
        TokenMeasurement(status="not_available", value=0)


def test_token_usage_rejects_invalid_total() -> None:
    with pytest.raises(ValidationError):
        TokenUsage(
            input_tokens=TokenMeasurement(status="measured", value=2),
            output_tokens=TokenMeasurement(status="measured", value=3),
            total_tokens=TokenMeasurement(status="measured", value=6),
        )


@pytest.mark.parametrize("amount", [Decimal("-0.01"), Decimal("NaN")])
def test_cost_usage_rejects_invalid_amount(amount: Decimal) -> None:
    with pytest.raises(ValidationError):
        CostUsage(amount=amount, currency="USD", source="estimated")


def test_cost_usage_invariants() -> None:
    measured = CostUsage(
        amount=Decimal("0.0012"),
        currency="USD",
        source="provider_reported",
    )
    assert measured.amount == Decimal("0.0012")
    with pytest.raises(ValidationError):
        CostUsage(amount=Decimal("1"), currency="usd", source="estimated")
    with pytest.raises(ValidationError):
        CostUsage(amount=Decimal("0"), currency="USD", source="not_available")
    with pytest.raises(ValidationError):
        CostUsage(source="estimated")


def test_fake_usage_is_not_available() -> None:
    tokens = unavailable_token_usage()
    cost = unavailable_cost_usage()

    assert {
        tokens.input_tokens.status,
        tokens.output_tokens.status,
        tokens.total_tokens.status,
    } == {"not_available"}
    assert cost.source == "not_available"
    assert cost.amount is None


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        ("Authorization: Bearer abc.def.ghi", "abc.def.ghi"),
        ("api_key=sk-live-super-secret", "sk-live-super-secret"),
        (
            "credential " + "sk-" + "lf-testplaceholder123",
            "sk-" + "lf-testplaceholder123",
        ),
        ("-----BEGIN PRIVATE KEY-----\nsecret-body\n-----END PRIVATE KEY-----", "secret-body"),
        ("contact jane.doe@example.com", "jane.doe@example.com"),
        ("postgresql://admin:p4ss@example.test/db", "admin:p4ss"),
        ("CLIENT_SECRET: ultra-secret-value", "ultra-secret-value"),
    ],
)
def test_redact_each_required_pattern(raw: str, secret: str) -> None:
    assert secret not in redact(raw)


def test_redact_preserves_safe_text_and_bounds_input() -> None:
    safe = "Explain why this plan is deterministic."
    assert redact(safe) == safe

    bounded = redact("x" * 200_000)
    assert len(bounded) < 200_000
    assert bounded.endswith("[TRUNCATED]")


def test_builder_redacts_before_constructing_record() -> None:
    record = _record(raw_prompt="Bearer do-not-store-this")
    assert "do-not-store-this" not in record.prompt


def test_settings_all_absent_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    recorder = build_trace_recorder(get_settings())
    assert isinstance(recorder, NoOpTraceRecorder)


def test_settings_all_present_is_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://jp.cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "placeholder-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "placeholder-secret")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "test")
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeLangfuseClient:
        captured.update(kwargs)
        return FakeLangfuseClient()

    recorder = build_trace_recorder(get_settings(), client_factory=factory)

    assert isinstance(recorder, LangfuseTraceRecorder)
    assert captured == {
        "base_url": "https://jp.cloud.langfuse.com",
        "public_key": "placeholder-public",
        "secret_key": "placeholder-secret",
        "environment": "test",
    }


@pytest.mark.parametrize("present_count", [1, 2, 3])
def test_settings_any_partial_combination_fails(
    monkeypatch: pytest.MonkeyPatch, present_count: int
) -> None:
    names = (
        "LANGFUSE_BASE_URL",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_TRACING_ENVIRONMENT",
    )
    for present in itertools.combinations(names, present_count):
        _base_env(monkeypatch)
        for name in present:
            monkeypatch.setenv(name, "placeholder")
        with pytest.raises(ConfigurationError):
            get_settings()


def test_noop_has_no_effect() -> None:
    recorder = NoOpTraceRecorder()
    assert recorder.record(_record()) is None


def test_inmemory_returns_defensive_copy() -> None:
    recorder = InMemoryTraceRecorder()
    original = _record()
    recorder.record(original)

    first_read = recorder.records
    second_read = recorder.records

    assert first_read == (original,)
    assert first_read is not second_read
    assert first_read[0] is not second_read[0]


@pytest.mark.database
@pytest.mark.asyncio
async def test_postgres_trace_records_digest_measurements_and_step_once() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url)
    tenant, workflow, run, step, trace = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO tenants (id,slug,name) VALUES (:id,:slug,'Trace Test')"),
            {"id": tenant, "slug": f"trace-{tenant.hex}"},
        )
        await connection.execute(
            text(
                "INSERT INTO workflows (id,tenant_id,name,version,definition_hash) "
                "VALUES (:id,:tenant,'delivery',1,'hash')"
            ),
            {"id": workflow, "tenant": tenant},
        )
        await connection.execute(
            text(
                "INSERT INTO runs (id,tenant_id,workflow_id,workflow_version,status) "
                "VALUES (:id,:tenant,:workflow,1,'running')"
            ),
            {"id": run, "tenant": tenant, "workflow": workflow},
        )
    record = _record(
        tenant_id=tenant,
        workflow_id=workflow,
        workflow_version=1,
        run_id=run,
        step_id=step,
        trace_id=trace,
        agent="planner",
        raw_prompt="Bearer must-never-be-stored",
        model="ollama_chat/qwen3:8b",
        token_usage=TokenUsage(
            input_tokens=TokenMeasurement(status="measured", value=10),
            output_tokens=TokenMeasurement(status="measured", value=4),
            total_tokens=TokenMeasurement(status="measured", value=14),
        ),
        cost=CostUsage(amount=Decimal("0"), currency="USD", source="estimated"),
    )
    recorder = PostgresTraceRecorder(database_url)
    recorder.record(record)
    recorder.record(record)

    async with engine.connect() as connection:
        row = (
            await connection.execute(
                text(
                    "SELECT t.prompt_digest, t.token_usage, t.cost_usage, s.sequence, "
                    "count(*) OVER () AS trace_count FROM run_traces t "
                    "JOIN steps s ON s.id=t.step_id WHERE t.run_id=:run"
                ),
                {"run": run},
            )
        ).mappings().one()
    assert row["prompt_digest"] != record.prompt
    assert "must-never" not in repr(row)
    assert row["token_usage"]["total_tokens"]["value"] == 14
    assert row["cost_usage"]["amount"] == "0"
    assert row["sequence"] == 4
    assert row["trace_count"] == 1
    await engine.dispose()


def test_langfuse_uses_deterministic_trace_id_and_event_metadata() -> None:
    client = FakeLangfuseClient()
    recorder = LangfuseTraceRecorder(client)
    record = _record()

    recorder.record(record)

    assert client.seeds == [str(record.trace_id)]
    assert len(client.observation_calls) == 1
    call = client.observation_calls[0]
    assert call["trace_context"] == {"trace_id": "0123456789abcdef0123456789abcdef"}
    assert call["metadata"]["event_id"] == str(record.event_id)
    assert "id" not in call
    assert "observation_id" not in call
    assert client.observation.end_calls == 1


def test_langfuse_makes_no_automatic_retry() -> None:
    client = FakeLangfuseClient(failure=RuntimeError("do-not-log-this-secret"))
    recorder = LangfuseTraceRecorder(client)

    recorder.record(_record())

    assert len(client.observation_calls) == 1


def test_local_error_log_contains_only_exception_type(caplog: pytest.LogCaptureFixture) -> None:
    client = FakeLangfuseClient(failure=RuntimeError("do-not-log-this-secret"))
    recorder = LangfuseTraceRecorder(client)

    with caplog.at_level(logging.WARNING, logger="aegisflow_core.runtime.tracing"):
        recorder.record(_record())

    assert "RuntimeError" in caplog.text
    assert "do-not-log-this-secret" not in caplog.text
    assert "Traceback" not in caplog.text


def test_smoke_workflow_is_manual_pinned_and_secret_scoped() -> None:
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "langfuse-smoke.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "environment: langfuse-development" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9" in workflow
    assert "LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}" in workflow
    assert "LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}" in workflow
    assert "LANGFUSE_BASE_URL: ${{ vars.LANGFUSE_BASE_URL }}" in workflow
    assert "LANGFUSE_TRACING_ENVIRONMENT: ${{ vars.LANGFUSE_TRACING_ENVIRONMENT }}" in workflow
    assert "uv run --locked python -m aegisflow_core.runtime.langfuse_smoke" in workflow


def test_smoke_executes_strict_auth_write_flush_and_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://jp.cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "placeholder-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "placeholder-secret")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "test")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    observation = FakeObservation()
    query_calls: list[dict[str, Any]] = []

    class Observations:
        def get_many(self, **kwargs: Any) -> SimpleNamespace:
            query_calls.append(kwargs)
            return SimpleNamespace(data=[SimpleNamespace(id="visible")])

    class StrictClient:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.api = SimpleNamespace(observations=Observations())
            self.flushed = False

        def auth_check(self) -> bool:
            return True

        def create_trace_id(self, *, seed: str) -> str:
            assert seed
            return "abcdef0123456789abcdef0123456789"

        def start_observation(self, **kwargs: Any) -> FakeObservation:
            assert kwargs["metadata"]["aegisflow_smoke"] is True
            assert "observation_id" not in kwargs
            return observation

        def flush(self) -> None:
            self.flushed = True

    monkeypatch.setattr(smoke_module, "Langfuse", StrictClient)

    trace_id = smoke_module.run_smoke()

    assert trace_id == "abcdef0123456789abcdef0123456789"
    assert observation.end_calls == 1
    assert query_calls == [
        {
            "trace_id": trace_id,
            "limit": 100,
            "fields": "core,io",
        }
    ]


def test_smoke_auth_failure_is_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://jp.cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "placeholder-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "placeholder-secret")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "test")

    class UnauthenticatedClient:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        def auth_check(self) -> bool:
            return False

    monkeypatch.setattr(smoke_module, "Langfuse", UnauthenticatedClient)

    with pytest.raises(RuntimeError, match="LangfuseAuthenticationFailed"):
        smoke_module.run_smoke()


def test_smoke_main_reports_only_exception_type(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail() -> str:
        raise RuntimeError("never-print-this-secret")

    monkeypatch.setattr(smoke_module, "run_smoke", fail)

    assert smoke_module.main() == 1
    output = capsys.readouterr()
    assert "RuntimeError" in output.err
    assert "never-print-this-secret" not in output.err
