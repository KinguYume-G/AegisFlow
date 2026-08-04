"""Low-cardinality Prometheus metrics for control-plane operations."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

_COMPONENTS = frozenset({"api", "temporal", "database", "mcp", "sandbox", "model"})
_OUTCOMES = frozenset({"success", "failure", "denied", "timeout", "fallback"})
_OPERATIONS = frozenset(
    {"http.request", "temporal.advance_gate1b", "mcp.invoke", "sandbox.run", "model.complete"}
)
_INTERVENTION_KINDS = frozenset({"clarification", "approval"})
_INTERVENTION_OUTCOMES = frozenset({"submitted", "accepted", "rejected", "timed_out"})
_active_metrics: Metrics | None = None


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.operations = Counter(
            "aegisflow_operations_total",
            "Bounded operation outcomes.",
            ("component", "operation", "outcome"),
            registry=self.registry,
        )
        self.latency = Histogram(
            "aegisflow_operation_duration_seconds",
            "Bounded operation latency.",
            ("component", "operation"),
            registry=self.registry,
        )
        self.cost = Counter(
            "aegisflow_model_cost_total",
            "Model cost by bounded route and currency.",
            ("route", "currency"),
            registry=self.registry,
        )
        self.queue_depth = Gauge(
            "aegisflow_queue_depth",
            "Current bounded queue depth.",
            ("queue",),
            registry=self.registry,
        )
        self.resources = Gauge(
            "aegisflow_resource_usage_ratio",
            "Process resource usage ratio.",
            ("resource",),
            registry=self.registry,
        )
        self.human_interventions = Counter(
            "aegisflow_human_interventions_total",
            "Bounded human clarification and approval outcomes.",
            ("kind", "outcome"),
            registry=self.registry,
        )

    def observe_operation(
        self, component: str, operation: str, outcome: str, duration: float
    ) -> None:
        if component not in _COMPONENTS or outcome not in _OUTCOMES:
            raise ValueError("unbounded metric label")
        if operation not in _OPERATIONS or duration < 0:
            raise ValueError("invalid metric observation")
        self.operations.labels(component, operation, outcome).inc()
        self.latency.labels(component, operation).observe(duration)

    def observe_cost(self, route: str, currency: str, amount: float) -> None:
        if route not in {"primary", "fallback", "local_fallback"} or len(currency) != 3 or amount < 0:
            raise ValueError("invalid cost observation")
        self.cost.labels(route, currency).inc(amount)

    def observe_human_intervention(self, kind: str, outcome: str) -> None:
        if kind not in _INTERVENTION_KINDS or outcome not in _INTERVENTION_OUTCOMES:
            raise ValueError("unbounded human intervention label")
        self.human_interventions.labels(kind, outcome).inc()


def activate_metrics(metrics: Metrics) -> None:
    global _active_metrics
    _active_metrics = metrics


def observe_active_operation(
    component: str, operation: str, outcome: str, duration: float
) -> None:
    if _active_metrics is not None:
        _active_metrics.observe_operation(component, operation, outcome, duration)


def observe_model_cost(route: str, currency: str, amount: float) -> None:
    if _active_metrics is not None:
        _active_metrics.observe_cost(route, currency, amount)


def observe_human_intervention(kind: str, outcome: str) -> None:
    if _active_metrics is not None:
        _active_metrics.observe_human_intervention(kind, outcome)
