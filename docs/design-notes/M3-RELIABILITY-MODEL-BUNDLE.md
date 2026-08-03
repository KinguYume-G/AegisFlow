# Design Note — AF-308–AF-311 Reliability and Model Runtime Bundle

Status: Approved v1 — approved by the Project Owner for the AF-308–AF-311 batch.

## Objective

Complete the two remaining executable Gate 2 tracks in one dependency-safe batch:

- AF-308: repeatable Saga compensation with explicit human escalation.
- AF-309: reproducible kill-worker fault injection and machine-readable recovery evidence.
- AF-310: a provider-neutral LiteLLM model gateway with Secret references, usage, cost, and model-version records.
- AF-311: deterministic circuit breaker and primary-to-fallback routing.

AF-308/AF-309 and AF-310/AF-311 may be developed in parallel inside this approved batch. AF-312 remains separate because its report must summarize real evidence produced after both tracks work.

## Non-Goals

- Publishing the Gate 2 report/blog or claiming Gate 2 has passed (AF-312).
- Wiring DeliveryPack agents to a nondeterministic production model by default.
- A model-provider registry, tenant onboarding, UI, OTel, multi-region routing, or deployment automation.
- Deleting unknown remote resources, retrying non-idempotent effects blindly, or storing provider Secrets in PostgreSQL, traces, fixtures, or Git.

## Authority and Boundaries

- Temporal owns compensation scheduling, durable workflow state, timers, and Activity retries.
- LangGraph owns agent graph state only; it does not perform compensation or provider retry.
- PostgreSQL owns business audit facts, the existing idempotency ledger, and shared circuit state.
- The model gateway owns one bounded route attempt chain and records every attempted route.
- Langfuse receives redacted trace projections through the existing AF-109 boundary; it is not a business fact source.

The frozen boundaries in `docs/02_ARCHITECTURE.md`, ADR-0002, ADR-0008, and ADR-0009 remain unchanged.

## AF-308 — Saga Compensation

Add a typed compensation plan to `runtime/temporal/` and narrow extensions to the existing idempotency ledger.

1. Every compensable Activity returns a typed receipt containing the exact owned resource identity, effect key, and compensation kind.
2. Temporal records successful receipts and compensates them in reverse completion order after a terminal downstream failure.
3. A compensation Activity claims a stable idempotency key derived from the original effect; replay or retry reuses the same claim.
4. Successful compensation moves the existing ledger record to `compensated` and emits an append-only audit event.
5. Permanent or ambiguous compensation failure stops automatic cleanup and returns a typed `manual_intervention_required` outcome with the remaining receipts.
6. Remote GitHub cleanup first reconciles an AegisFlow ownership marker. Unknown branches, commits, PRs, or files are never deleted.

Compensation handlers cover only effects actually implemented by the repository: owned temporary workspaces and marked GitHub draft-delivery resources. PostgreSQL facts and audit events are not erased as compensation.

## AF-309 — Kill-Worker Fault Injection

Add a deterministic harness under `tests/fault_injection/` plus a manually dispatched GitHub Actions workflow.

- The harness starts isolated runs with unique tenant/run/workflow identifiers and kills only the Compose worker container it created.
- Twenty iterations exercise four fixed fault points five times each: Activity execution, clarification wait, approval wait, and post-effect/pre-completion recovery.
- It restarts the worker, waits with bounded deadlines, and records recovery duration, terminal status, duplicate-effect count, lost-Signal count, and compensation outcome.
- Each iteration writes one canonical JSONL record; a summary command validates exactly 20 unique completed iterations and computes p50/p95 without editing the evidence.
- Failed or timed-out iterations remain evidence and make the workflow fail; they are never silently retried into a green result.
- Cleanup is marker- and Compose-project-scoped. The harness refuses production-like endpoints and never accepts arbitrary container names.

Raw evidence is an Actions artifact, not a committed success claim. AF-312 will publish the reviewed report and limitations.

## AF-310 — LiteLLM Model Gateway

Implement provider-neutral contracts in `models/` and isolate the LiteLLM Python SDK behind one adapter.

- Use official stable LiteLLM `1.94.0`, aligned with the signed GitHub Release published 2026-07-28, and lock the complete dependency graph in `uv.lock`.
- Explicitly exclude compromised versions `1.82.7` and `1.82.8`; CI installs only with `uv sync --locked`.
- Call the SDK with provider retry/fallback disabled. AegisFlow owns bounded routing, circuit state, and audit evidence.
- Production configuration names a primary and fallback model plus the environment-variable names that contain their credentials. Configuration stores references, never Secret values.
- CI uses an injected deterministic adapter and requires no provider Secret or network call.
- Every result records requested route, resolved provider/model version, token usage, provider-reported cost when available, deterministic cost status when unavailable, latency, and a redacted error category.
- Prompt, completion, headers, API keys, and raw provider exceptions do not enter application logs or audit events.
- Budget denial happens before the provider call and fails closed.

The gateway is implemented and tested in this batch, but DeliveryPack's deterministic test reasoners remain the default until a later Issue explicitly authorizes live-model behavior.

## AF-311 — Circuit Breaker and Fallback

Implement a state machine with injected clock and a PostgreSQL-backed production store.

- Key state by tenant plus logical route, preventing cross-tenant influence.
- `Closed`: send to primary; counted transient failures advance the threshold.
- `Open`: skip primary until `open_until` and route to fallback.
- `HalfOpen`: a fenced lease permits exactly one primary probe across workers.
- Probe success closes and resets the circuit; probe failure reopens it.
- Authentication, authorization, invalid-request, policy, and budget failures are final and do not trip the availability circuit.
- If both routes fail, return one explicit typed failure; never enter an unbounded route loop.
- The trace records the ordered route chain and outcome without prompt or credential content.

Add one Alembic migration for shared circuit state. Upgrade, downgrade, and re-upgrade must preserve a single migration head.

## Configuration and External Input

Repository configuration will use non-secret variables for model identifiers and Secret references for credentials. Exact names will be finalized in implementation and documented in `.env.example`; no value is committed.

Before the protected real-provider smoke test, the Project Owner must provide outside chat:

1. one primary model identifier;
2. one fallback model identifier (a second model on the same provider is acceptable for this milestone);
3. the corresponding credential(s) as GitHub Environment Secrets and local environment variables.

The Project Owner must send only the model identifiers and Secret variable names to Codex, never their values. Missing provider configuration blocks only the protected real-provider smoke and AF-312 evidence; unit, integration, migration, compensation, and fault-harness implementation remain executable.

## Failure and Security Rules

- Missing or partial model configuration fails startup of the model gateway; the core health endpoint remains truthful about its own contract.
- Provider timeouts, 429, and 5xx are availability failures eligible for the bounded route policy.
- Secret/configuration/authentication errors fail fast without fallback that could hide misconfiguration.
- Compensation never guesses resource identity and never erases audit history.
- Circuit state changes and compensation results are tenant-scoped and append auditable facts.
- No real GitHub or provider write runs in ordinary PR CI.

## Rollback

- Disable model-gateway construction and the manual fault workflow; deterministic DeliveryPack behavior remains available.
- Stop scheduling new compensation plans while retaining existing histories and receipts for safe replay/manual handling.
- Revert code/config and downgrade only the circuit-state migration using its tested downgrade.
- Never delete Temporal histories, ledger rows, audit events, or fault evidence as part of rollback.

## Definition of Done

- AF-308 compensation is reverse-ordered, repeatable, fenced, audited, and escalates ambiguity.
- AF-309 produces a reproducible 20-iteration artifact with duplicate effects and lost Signals explicitly measured.
- AF-310 stores no Secret value, records model/version/token/cost evidence, and uses an exact locked LiteLLM dependency.
- AF-311 proves Closed/Open/Half-Open behavior, one fenced probe, and an ordered primary/fallback trace.
- Migrations, full CI, Compose/build checks, secret scan, and documentation link/inventory checks pass.
- One batch PR is created for Human Review; AI does not merge or mark the Issues verified.

## Resolved Decisions

1. AF-308–AF-311 use one batch branch and PR under the Project Owner's efficiency exception.
2. AF-312 is deliberately excluded until real 20-run and provider-fallback evidence exists.
3. LiteLLM is an isolated Python SDK adapter, not another AegisFlow control plane or source of truth.
4. Shared circuit state is PostgreSQL-backed; a process-local breaker is insufficient for multiple workers and restart recovery.
5. The ordinary CI path is deterministic and Secret-free; real provider validation is protected and manually dispatched.
6. There are no open implementation questions after the Project Owner supplies model identifiers and Secret reference names.
