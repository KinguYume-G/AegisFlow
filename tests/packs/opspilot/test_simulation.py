import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from aegisflow_core.packs.opspilot import SimulatedCiIncident, assess_simulated_incident


def _fixture() -> dict[str, object]:
    path = Path(__file__).parents[2] / "fixtures" / "opspilot" / "ci_lock_mismatch.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_simulated_incident_produces_deterministic_human_gated_plan() -> None:
    incident = SimulatedCiIncident.model_validate(_fixture())
    first = assess_simulated_incident(incident)
    assert first == assess_simulated_incident(incident)
    assert first.human_approval_required is True
    assert first.external_effects_performed is False
    assert first.category == "dependency_integrity"
    assert len(first.remediation_steps) == 3


def test_non_simulation_or_unknown_scenario_is_rejected() -> None:
    payload = _fixture(); payload["scenario_id"] = "production-incident"
    with pytest.raises(ValidationError): SimulatedCiIncident.model_validate(payload)
    payload = _fixture(); payload["evidence"]["source"] = "github"  # type: ignore[index]
    with pytest.raises(ValidationError): SimulatedCiIncident.model_validate(payload)
