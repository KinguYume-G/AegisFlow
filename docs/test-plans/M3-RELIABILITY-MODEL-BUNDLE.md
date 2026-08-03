# Test Plan — AF-308–AF-311 Reliability and Model Runtime Bundle

Status: Approved v1 — approved by the Project Owner for the AF-308–AF-311 batch.

## Scope

Verify Saga compensation, worker-loss recovery evidence, a Secret-safe LiteLLM boundary, and a shared deterministic circuit breaker. AF-312 publication and Gate 2 acceptance remain out of scope.

## AF-308 — Compensation

- Reverse-order compensation for two or more completed effects.
- Exact replay and concurrent duplicate compensation execute each handler once.
- An expired lease fences a stale compensator; stale completion cannot overwrite the winner.
- Successful compensation records `compensated` plus an append-only audit event.
- Retryable handler failure follows the bounded Temporal Activity policy.
- Permanent, exhausted, missing-receipt, or ambiguous-remote-state failure returns `manual_intervention_required` and preserves remaining receipts.
- Ownership-marker mismatch proves that no unrelated workspace, branch, or PR is deleted.
- PostgreSQL business and audit rows remain present after compensation.

## AF-309 — Fault Injection

Unit tests validate command construction, environment refusal, deadlines, evidence schema, percentile calculation, duplicate iteration rejection, and scoped cleanup without invoking Docker.

The real manual workflow runs this fixed matrix five times per scenario:

| Scenario | Fault point | Required recovery evidence |
|---|---|---|
| activity | worker exits during an Activity | workflow completes or compensates; effect count is one |
| clarification | worker exits while waiting for a Signal | Signal is retained and consumed once after restart |
| approval | worker exits while waiting for a decision | decision is retained and consumed once after restart |
| completion gap | worker exits after effect commit and before workflow completion | ledger result is reused; no duplicate effect |

Acceptance requires exactly 20 unique iteration records, zero duplicate external effects, zero lost Signals, a terminal result for every iteration, recorded compensation outcomes, and computed p50/p95 recovery time. Any failed iteration fails the job and remains in the uploaded artifact.

## AF-310 — Model Gateway

- Complete and partial configuration: all-or-none model and Secret-reference validation.
- Credential lookup occurs at the adapter boundary; Secret values never appear in settings representation, logs, traces, errors, snapshots, or serialized requests.
- Injected fake adapter proves the exact LiteLLM call contract with SDK retry/fallback disabled.
- Success records requested and resolved route/model, token counts, latency, and cost status.
- Missing provider cost produces an explicit `not_available` state, never an invented number.
- Budget denial makes zero adapter calls.
- Timeout, 429, 5xx, authentication, authorization, invalid request, malformed usage, and provider cancellation map to typed categories.
- Dependency test asserts the locked LiteLLM version is `1.94.0` and rejects known compromised versions.

The protected manual provider smoke sends a fixed non-sensitive prompt, verifies authentication and one bounded primary/fallback scenario when the provider permits it, flushes trace data, and uploads redacted evidence. It never prints a credential or raw provider response.

## AF-311 — Circuit Breaker and Fallback

- Injected-clock state-machine tests cover every legal Closed/Open/Half-Open transition.
- Transient-failure threshold opens the circuit; final input/auth/policy/budget errors do not.
- Open state skips primary and records the fallback route.
- At expiry, concurrent workers obtain exactly one fenced Half-Open probe.
- Probe success closes/reset; probe failure reopens with a new bounded interval.
- Primary success makes no fallback call.
- Primary availability failure routes once to fallback.
- Both routes failing returns one typed terminal failure without recursion or hidden retry.
- Tenant A's circuit cannot change tenant B's state.
- Ordered trace data contains route/model/outcome but no prompt or Secret.
- PostgreSQL store tests cover transaction contention, stale fencing, restart persistence, and time comparisons in UTC.

## Migration and Integration

- Upgrade from current head, downgrade one revision, and re-upgrade.
- Assert one Alembic head and the expected circuit-state constraints/indexes.
- Run compensation through the real PostgreSQL ledger and Temporal worker.
- Reconstruct worker/client/store instances and verify persisted compensation and circuit state.
- Build Core and worker images; validate Compose configuration.
- Ordinary PR CI uses no GitHub App, Langfuse, or provider Secret.

## Commands

```text
uv sync --locked
uv run --locked alembic upgrade head
uv run --locked python -m pytest --cov=aegisflow_core --cov-report=term-missing
uv run --locked alembic downgrade -1
uv run --locked alembic upgrade head
docker compose config
docker compose build core temporal-worker sandbox-broker
```

Focused fault-injection and provider-smoke commands will be exposed through named manual GitHub Actions workflows. Their exact commands must also run locally with documented non-secret inputs.

## Evidence Required in the PR

- Full test count, coverage, migration round trip, single-head result, container build, and secret-scan results.
- Compensation ordering/idempotency/escalation test evidence.
- Fault harness schema/unit results; real 20-run artifact URL when executed.
- Locked LiteLLM version and official Release alignment.
- Circuit transition/concurrency/tenant-isolation results.
- Any unavailable real-provider smoke is declared honestly and blocks AF-312 evidence, not disguised as passing.

## Stop Conditions

Stop without a risky workaround if a test requires a real Secret in source/PR logs, a production endpoint, an unscoped container kill, deletion of an unverified remote resource, a floating LiteLLM dependency, or a nondeterministic retry loop.

## Expected Result

All deterministic tests and CI checks pass, migration rollback/reapply is green, ordinary CI contains no external write, and the batch PR stops for Human Review. AF-312 remains blocked until the real fault and provider evidence is reviewed.
