# M5 Final Acceptance Bundle Test Plan — AF-211, AF-516, AF-517

Status: Approved by Project Owner on 2026-08-04.

## Required verification / 必须验证

1. Confirm every referenced workflow ran on the recorded immutable `main` SHA and record success, failure, retry, and limitation truthfully.
2. Parse Gate 2 JSONL: 20 terminal completions, zero duplicate effects, zero lost signals; compute nearest-rank p50/p95.
3. Parse load CSV: 100-user profile evidence, request/failure totals, throughput, and p95; do not infer production capacity.
4. Parse Gate 3 JUnit and credential scan evidence; retain artifact identity and SHA-256.
5. Confirm the evaluation decision declares `deterministic_gate_fixture`; never report its values as production model quality.
6. Record the redacted Model Gateway route result and Langfuse trace ID without credentials or prompt content.
7. Verify Gate 1 evidence states that the real GitHub test covers Draft PR creation/deduplication/cleanup, not the complete six-Agent path.
8. Validate all relative Markdown links and the repository manifest; scan tracked changes for credential signatures.
9. Confirm no source, tests, workflow, dependency, Architecture, or Accepted ADR changed.
10. Leave final acceptance and Issue lifecycle changes to a Human Reviewer.

## Failure policy / 失败策略

Any missing artifact, unresolved external smoke failure, secret-shaped content, broken link, or unsupported claim blocks Gate 4. A transient failure may be retried once; both attempts must remain recorded.
