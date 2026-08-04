import httpx
import pytest
from fastapi import FastAPI
from prometheus_client import generate_latest

from aegisflow_core.metrics_endpoint import install_metrics
from aegisflow_core.runtime.metrics import Metrics


def test_metrics_reject_unbounded_labels() -> None:
    metrics = Metrics()
    with pytest.raises(ValueError, match="unbounded"):
        metrics.observe_operation("tenant-123", "request", "success", 0.1)
    with pytest.raises(ValueError, match="unbounded"):
        metrics.observe_operation("api", "request", "user-value", 0.1)


@pytest.mark.anyio
async def test_metrics_endpoint_exposes_success_and_latency() -> None:
    app = FastAPI()
    metrics = Metrics()
    install_metrics(app, metrics)

    @app.get("/probe")
    async def probe() -> dict[str, str]:
        return {"status": "ok"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/probe")).status_code == 200
        response = await client.get("/metrics/")
    assert response.status_code == 200
    body = response.text
    assert 'aegisflow_operations_total{component="api",operation="http.request",outcome="success"} 1.0' in body
    assert "aegisflow_operation_duration_seconds_count" in body


def test_cost_queue_and_resource_metrics_are_exported() -> None:
    metrics = Metrics()
    metrics.cost.labels("primary", "USD").inc(1.25)
    metrics.observe_cost("local_fallback", "USD", 0.0)
    metrics.queue_depth.labels("temporal").set(4)
    metrics.resources.labels("cpu").set(0.5)
    output = generate_latest(metrics.registry).decode()
    assert "aegisflow_model_cost_total" in output
    assert "aegisflow_queue_depth" in output
    assert "aegisflow_resource_usage_ratio" in output
    with pytest.raises(ValueError, match="invalid cost"):
        metrics.observe_cost("tenant-value", "USD", 1.0)


def test_human_interventions_are_bounded_and_exported() -> None:
    metrics = Metrics()
    metrics.observe_human_intervention("clarification", "submitted")
    metrics.observe_human_intervention("approval", "accepted")
    output = generate_latest(metrics.registry).decode()
    assert (
        'aegisflow_human_interventions_total{kind="clarification",outcome="submitted"} 1.0'
        in output
    )
    assert 'aegisflow_human_interventions_total{kind="approval",outcome="accepted"} 1.0' in output
    with pytest.raises(ValueError, match="unbounded"):
        metrics.observe_human_intervention("tenant-value", "submitted")
