"""FastAPI adapter for the bounded Prometheus registry."""

from time import perf_counter

from fastapi import FastAPI, Request
from prometheus_client import make_asgi_app

from aegisflow_core.runtime.metrics import Metrics


def install_metrics(app: FastAPI, metrics: Metrics) -> None:
    @app.middleware("http")
    async def measure_http(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = perf_counter()
        outcome = "failure"
        try:
            response = await call_next(request)
            outcome = "success" if response.status_code < 400 else "failure"
            return response
        finally:
            if request.url.path != "/metrics":
                metrics.observe_operation(
                    "api", "http.request", outcome, perf_counter() - started
                )

    app.mount("/metrics", make_asgi_app(registry=metrics.registry))
