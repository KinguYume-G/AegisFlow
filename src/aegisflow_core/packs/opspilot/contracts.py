"""Immutable contracts for the single approved OpsPilot simulation."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class IncidentEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: Literal["simulation"]
    workflow: str = Field(min_length=1, max_length=128)
    failed_job: str = Field(min_length=1, max_length=128)
    failure_signature: Literal["dependency_lock_mismatch"]


class SimulatedCiIncident(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    scenario_id: Literal["opspilot-ci-lock-mismatch-v1"]
    evidence: IncidentEvidence


class OpsPilotAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    scenario_id: str
    category: Literal["dependency_integrity"]
    severity: Literal["medium"]
    diagnosis: str
    remediation_steps: tuple[str, ...]
    human_approval_required: Literal[True] = True
    external_effects_performed: Literal[False] = False
