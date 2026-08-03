from contextlib import contextmanager

import pytest

from aegisflow_core.runtime.observability import Correlation, operation_span


def test_correlation_contains_only_explicit_bounded_fields() -> None:
    assert Correlation(tenant_id="tenant", run_id="run").attributes() == {
        "aegisflow.tenant.id": "tenant",
        "aegisflow.run.id": "run",
    }


def test_operation_span_records_error_type_without_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Span:
        def set_attribute(self, key: str, value: object) -> None:
            captured[key] = value

        def set_status(self, value: object) -> None:
            captured["status"] = value

    class Tracer:
        @contextmanager
        def start_as_current_span(self, name: str, attributes: dict[str, object]):
            captured["name"] = name
            captured["attributes"] = attributes
            yield Span()

    provider = type("Provider", (), {"get_tracer": lambda self, _name: Tracer()})()
    monkeypatch.setattr(
        "aegisflow_core.runtime.observability._active_provider", provider
    )
    with pytest.raises(RuntimeError, match="sensitive-value"):
        with operation_span("mcp.invoke", Correlation(trace_id="trace")):
            raise RuntimeError("sensitive-value")
    assert captured["error.type"] == "RuntimeError"
    assert "sensitive-value" not in repr(captured)
