# Gate 2 Reliability Report

**Milestone:** M3 Reliable Runtime

**Issue:** AF-312 / GitHub #42

**Evidence date:** 2026-08-03

**Review status:** Proposed — Gate 2 requires Human Review and merge of the AF-312 PR

## Executive Result

The M3 implementation satisfies the measured recovery targets in its hosted test environment:

- 20 of 20 worker-loss scenarios reached a terminal successful state;
- duplicate external effects: 0;
- lost durable Signals: 0;
- recovery p50: 2049.31 ms, below the 5-second target;
- recovery p95: 2973.56 ms, below the 15-second target;
- one protected real-provider request completed with measured token usage and provider-reported cost;
- deterministic tests cover bounded primary/fallback routing, circuit transitions, tenant isolation, Saga compensation, and PostgreSQL persistence.

This report does **not** claim that a live DeepSeek outage occurred or that the hosted smoke exercised Gemini fallback. Those paths are supported by deterministic failure-injection tests, while the real provider smoke exercised the primary route only.

## Immutable Evidence

| Evidence | Commit / Run | Result |
|---|---|---|
| AF-308–AF-311 implementation | [PR #100](https://github.com/KinguYume-G/AegisFlow/pull/100), merge `5a5b6a33e4cdf0750a5e3f2d86ddf0766c06d016` | Human merged; required CI passed |
| Required CI | [Actions run 30800569517](https://github.com/KinguYume-G/AegisFlow/actions/runs/30800569517) | Passed in 1m52s |
| Real worker-loss campaign | [Actions run 30801262477](https://github.com/KinguYume-G/AegisFlow/actions/runs/30801262477) | 20/20 accepted; evidence uploaded |
| Fault evidence artifact | `gate2-fault-evidence-30801262477`, artifact ID `8850930348` | 1097 bytes; not expired at report creation |
| Protected provider smoke | [Actions run 30804037539](https://github.com/KinguYume-G/AegisFlow/actions/runs/30804037539) | Passed in 21s on the same merge commit |

## Environment

### Worker-loss campaign

- GitHub-hosted `ubuntu-24.04` runner;
- Python 3.12 and uv 0.11.31 from pinned Actions;
- locked repository dependencies;
- pinned Temporal development service;
- one workflow worker process deliberately terminated and restarted per scenario;
- isolated task queue and work directory per execution;
- evidence emitted as JSONL and uploaded as an Actions artifact.

### Provider smoke

- protected GitHub Environment: `model-development`;
- protected-branch deployment policy;
- primary model identifier: `deepseek/deepseek-v4-flash`;
- fallback model identifier: `gemini/gemini-2.5-flash-lite`;
- API Keys supplied only through Environment Secrets;
- fixed non-sensitive prompt; response content intentionally omitted from logs.

## Fault Matrix Results

The hosted campaign executed four failure points five times each:

1. worker loss before activity execution;
2. worker loss during heartbeat-capable activity execution;
3. worker loss after durable Signal submission;
4. worker loss during workflow replay/recovery.

| Metric | Result | Gate target | Outcome |
|---|---:|---:|---|
| Terminal completions | 20/20 | 20/20 | Pass |
| Duplicate external effects | 0 | 0 | Pass |
| Lost Signals | 0 | 0 | Pass |
| Recovery p50 | 2049.31 ms | < 5000 ms | Pass |
| Recovery p95 | 2973.56 ms | < 15000 ms | Pass |

The artifact is the detailed machine-readable record. The repository report retains aggregates and immutable identifiers so the claim remains auditable after normal artifact retention expires.

## Model Gateway Evidence

The protected smoke produced this redacted evidence:

- status: `ok`;
- requested route: `primary`;
- configured model: `deepseek/deepseek-v4-flash`;
- resolved model: `deepseek-v4-flash`;
- route outcome: `succeeded`;
- token status: `measured`;
- cost source: `provider_reported`.

No credential, response body, or unrestricted prompt was logged. The fallback model was configured but not called because the primary request succeeded.

## Deterministic Reliability Evidence

PR #100 also verified:

- reverse-order Saga compensation with typed receipts, retry classification, manual escalation, and append-only audit projection;
- a separate idempotency-ledger compensation scope and original-effect `compensated` transition;
- Closed/Open/Half-Open circuit behavior with a single fenced probe;
- PostgreSQL-backed tenant-route circuit state across process boundaries;
- bounded fallback only for availability failures;
- fail-closed configuration, authentication, and budget errors;
- exact LiteLLM 1.94.0 lock with SDK retries disabled;
- migration downgrade-to-base and upgrade-to-head;
- 90% repository coverage gate and successful required CI.

## Security and Data Handling

- Real Keys exist only as GitHub Environment Secrets.
- Workflow logs expose only model identifiers and measurement classifications.
- The fixed smoke prompt contains no product, customer, repository, or personal data.
- Model response content is never printed or committed.
- Fault evidence contains synthetic identifiers and runtime measurements only.
- No production deployment or customer system was contacted.

## Limitations

1. The fault environment is single-region and ephemeral, not a production multi-node Temporal cluster.
2. The worker campaign covers a fixed 4×5 matrix, not long-duration chaos or infrastructure partition testing.
3. The provider smoke is one successful primary-route request; it does not prove a real DeepSeek outage or live Gemini failover.
4. Fallback and circuit failure paths are deterministic tests, not a claim about provider SLA.
5. Provider-reported cost is not reconciled with an invoice.
6. Node.js 20 deprecation was reported for the pinned artifact action and automatically executed on Node.js 24; this did not change the campaign result and should be addressed by a future dependency-maintenance update.
7. Tenant security, OIDC/RBAC, prompt injection, load testing, and deployment evidence belong to M4/M5.

## Gate 2 Recommendation

Accept Gate 2 after Human Review confirms that the evidence, limitations, and demo runbook are accurate. Acceptance authorizes M4 Governance & Security work; it does not assert production readiness.
