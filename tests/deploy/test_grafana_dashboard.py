"""AF-510 Grafana provisioning contract tests."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
CHART = ROOT / "deploy" / "helm" / "aegisflow"
DASHBOARD = CHART / "dashboards" / "aegisflow-gate4.json"


def test_gate4_dashboard_contains_required_bounded_panels() -> None:
    payload = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    panels = {panel["title"]: panel for panel in payload["panels"]}

    assert payload["uid"] == "aegisflow-gate4"
    assert payload["editable"] is False
    assert set(panels) == {
        "Operation success rate",
        "Model cost",
        "Operation p95 latency",
        "Failed operations",
        "Model fallback",
        "Human intervention",
    }
    expressions = "\n".join(
        target["expr"] for panel in panels.values() for target in panel["targets"]
    )
    for metric in (
        "aegisflow_operations_total",
        "aegisflow_model_cost_total",
        "aegisflow_operation_duration_seconds_bucket",
        "aegisflow_human_interventions_total",
    ):
        assert metric in expressions
    assert "tenant" not in expressions
    assert "run_id" not in expressions


def test_chart_provisions_dashboard_and_read_only_grafana() -> None:
    config = (CHART / "templates" / "configmaps.yaml").read_text(encoding="utf-8")
    workloads = (CHART / "templates" / "workloads.yaml").read_text(encoding="utf-8")
    policy = (CHART / "templates" / "networkpolicies.yaml").read_text(encoding="utf-8")

    assert "aegisflow-gate4.json" in config
    assert "GF_AUTH_ANONYMOUS_ORG_ROLE" in workloads
    assert 'value: "Viewer"' in workloads
    assert "app.kubernetes.io/component: grafana" in policy
    assert "port: 3000" in policy
