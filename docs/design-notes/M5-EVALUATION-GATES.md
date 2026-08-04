# M5 Evaluation Gates — AF-504, AF-506, AF-507, AF-510

Status: Approved by Project Owner on 2026-08-04.

## Decisions

- AF-504 contains five real, sanitized fix cases from XueMai and `exilian-cyms`. Stored evidence is limited to a bounded problem statement, repository name, immutable commit SHA, sanitization note, and ground-truth commit reference.
- AF-506 aggregates immutable `EvaluationRun` evidence into deterministic JSON and Markdown. Ratio metrics always retain numerator and denominator; unavailable evidence is explicit. p95 uses the nearest-rank method.
- AF-507 compares a versioned candidate report with a versioned baseline. Correctness metrics permit zero regression; token cost and p95 latency permit at most 10% regression. Missing or incompatible evidence fails closed and the machine-readable decision report is always retained by CI.
- The checked-in CI pair is explicitly classified as `deterministic_gate_fixture`; it validates the gate and must never be presented as an achieved production measurement. Provider-backed reports use `measured_evaluation`.
- AF-510 provisions one Grafana dashboard over existing bounded Prometheus labels. It shows success rate, model cost, p95, failed operations, fallback, and human intervention. Human-intervention telemetry uses a new bounded counter; no user-controlled labels are accepted.

## Boundaries

- No provider calls, LLM-as-judge, private source bodies, credentials, raw patches, deployment changes, or new third-party dependencies.
- Evaluation does not own runtime or authorization state. Dataset text remains untrusted input.
- Baseline or threshold changes are reviewed files and can be rolled back with a normal Git revert.
