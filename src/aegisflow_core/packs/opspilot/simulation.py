"""Pure deterministic diagnosis for the approved synthetic CI scenario."""

from aegisflow_core.packs.opspilot.contracts import OpsPilotAssessment, SimulatedCiIncident


def assess_simulated_incident(incident: SimulatedCiIncident) -> OpsPilotAssessment:
    """Return a proposal only; never execute remediation or contact an external system."""
    return OpsPilotAssessment(
        scenario_id=incident.scenario_id,
        category="dependency_integrity",
        severity="medium",
        diagnosis=(f"Workflow {incident.evidence.workflow!r} failed in job "
                   f"{incident.evidence.failed_job!r} because the locked dependency set "
                   "does not match the declared project dependencies."),
        remediation_steps=(
            "Reproduce the locked dependency sync in an isolated branch.",
            "Regenerate the lockfile with the repository-pinned package manager.",
            "Review the dependency diff and rerun the complete CI gate.",
        ),
    )
