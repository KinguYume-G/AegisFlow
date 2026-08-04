# M5 Final Acceptance Bundle — AF-211, AF-516, AF-517

Status: Approved by Project Owner on 2026-08-04 for design and evidence collection. Human acceptance remains required.

## Objective / 目标

Close the documentation and evidence gap for Gate 1 and Gate 4 without adding product behavior. / 在不新增产品能力的前提下，补齐 Gate 1 与 Gate 4 的文档和可复核证据。

## Scope / 范围

- AF-211: archive Gate 1B GitHub evidence, trace/cost visibility evidence, and limitations. Video is optional by Project Owner decision.
- AF-516: provide a concise bilingual entry point and link the existing Architecture, ADR, Evaluation, Reliability, Load, and Threat Model evidence.
- AF-517: execute the protected workflows on one immutable `main` SHA and publish a repeatable runbook plus a candidate acceptance record.

## Evidence contract / 证据契约

- Every external claim includes a GitHub Actions run URL, commit SHA, artifact identity, or redacted trace identifier.
- CI fixtures are identified as deterministic fixtures, never as production measurements.
- A green provider smoke proves the exercised route only; it does not prove a forced fallback.
- Automated component evidence is not presented as a single live end-to-end demonstration.
- Secrets, raw private-repository content, and provider payloads are excluded.
- Gate 4 remains `Candidate` until Human Review and Human Merge.

## Non-goals / 非目标

No business code, new workflow, dependency, architecture or ADR change; no Issue closure; no production deployment; no fabricated metric; no mandatory recording.

## Outputs / 产出

- [`../reports/GATE1_EVIDENCE_REPORT.md`](../reports/GATE1_EVIDENCE_REPORT.md)
- [`../reports/GATE4_FINAL_ACCEPTANCE.md`](../reports/GATE4_FINAL_ACCEPTANCE.md)
- [`../reports/GATE4_DEMO_RUNBOOK.md`](../reports/GATE4_DEMO_RUNBOOK.md)

## Rollback / 回滚

Revert this documentation-only change. External workflow runs and immutable GitHub evidence remain available under repository retention policy.
