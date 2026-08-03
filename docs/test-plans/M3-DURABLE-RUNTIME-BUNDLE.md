# Test Plan — AF-301–AF-307 Durable Runtime Bundle

Status: Approved v1 — approved by the Project Owner for the AF-301–AF-307 batch.

## Scope

Verify Temporal bootstrap and replay safety, single-owner runtime boundaries, PostgreSQL graph checkpoints, durable clarification/approval Signals, classified retries/timeouts, and Activity integration with the existing idempotency ledger.

## AF-301 — Temporal Bootstrap

- Start a test Temporal environment and worker with the registered workflow/Activities.
- Execute one workflow to a typed result.
- Assert deterministic workflow sandbox execution and replay a captured history with `Replayer`.
- Invalid/missing address, namespace, and task queue fail startup without in-memory fallback.

## AF-302 — Ownership Boundaries

- Static AST/import test forbids workflow modules from importing SQLAlchemy, asyncpg, httpx, Docker, GitHub adapters, filesystem APIs, or non-deterministic clock/UUID/random APIs.
- Contract test maps each state to exactly one owner.
- Assert LangGraph nodes have no transport retry while Temporal Activities own external retry.
- PostgreSQL projections cannot drive Temporal lifecycle decisions.

## AF-303 — PostgreSQL Checkpoints

- Initialize official checkpointer tables against real PostgreSQL and verify setup idempotency.
- Persist after a graph node, dispose the first checkpointer/graph instance, reconstruct it, and resume.
- Assert exact tenant/run/workflow-version config is required.
- Cross-tenant, wrong-run, wrong-version, missing checkpoint, and no-pending-interrupt resumes fail closed.
- Strict msgpack setting/allowlist is enforced.

## AF-304 — Clarification Signal

- Workflow waits without polling and resumes after the correct Signal.
- Exact duplicate signal is idempotent.
- Conflicting duplicate, wrong tenant/run/reference, malformed payload, and late signal are rejected.
- Restart/recreated worker observes the durable wait and can resume.

## AF-305 — Approval Signal

- Approved and rejected decisions persist and follow distinct routes.
- Exact duplicate decision is idempotent; conflicting duplicate fails.
- Expiry is tested with a one-second bounded timeout on the pinned local/CI Temporal Server; no external test-server binary download is required.
- No approval can be synthesized by graph/LLM output; actor/reference are required.

## AF-306 — Retry and Timeout Policies

Parameterized tests cover timeout, connection reset, 429/retry delay, 5xx, authorization, policy denial, invalid input, sandbox/test failure, and non-retryable side effects.

- Retryable failures use bounded attempts/backoff.
- Permission/policy/input failures are explicitly non-retryable.
- Agent rework does not consume Temporal retry attempts.
- Activity timeout values are positive, finite, and operation-specific.

## AF-307 — Idempotent Activities

- Concurrent duplicate Activity calls produce one executor and one stored result.
- Temporal retry reuses the same canonical key.
- Successful result is reused after worker/client reconstruction.
- Expired lease fences the stale worker; stale completion raises `ClaimLostError`.
- Argument mismatch and final failure cannot be retried into a different effect.
- GitHub Activity reconciliation verifies local ledger plus remote marker.

## Integration / Recovery Scenarios

1. Start workflow; reach clarification wait; recreate worker; Signal; reach approval wait; recreate worker; approve; complete.
2. Fail a retryable Activity once; confirm Temporal retry and exactly one persisted effect.
3. Deliver the same clarification/approval Signal twice; confirm one transition.
4. Persist a LangGraph interrupt; reconstruct graph/checkpointer; resume the same tenant/run/version.
5. Replay the resulting Temporal history with current workflow code.

AF-309 owns the 20-iteration kill-worker harness and quantitative Gate 2 report. This batch proves the primitives with deterministic component/integration tests and at least one process-reconstruction path.

## Fixtures

- Pinned local/CI Temporal Server for workflow semantics, replay, worker/client integration, and bounded expiry.
- Existing pgvector PostgreSQL service for business facts, ledger, and checkpoint tables.
- Fake Activities and existing deterministic reasoners for unit tests.
- No real GitHub or model-provider write is required in this batch.

## Commands

```text
uv sync --locked
uv run --locked alembic upgrade head
uv run --locked python -m pytest --cov=aegisflow_core --cov-report=term-missing
uv run --locked alembic downgrade base
uv run --locked alembic upgrade head
docker compose config
docker compose build core temporal-worker sandbox-broker
```

Additional focused commands will run Temporal integration/replay tests and checkpoint tests explicitly in CI; their marker names must be registered in `pyproject.toml`.

## Expected Results

- All tests pass; no flaky retries or skipped mandatory integration tests in CI.
- Coverage remains at or above 90% overall and changed-line target.
- Replay detects zero nondeterminism.
- Duplicate external effects: zero.
- Cross-tenant checkpoint/signal access: zero accepted.
- Migration/checkpointer setup is repeatable; rollback/reapply remains green.
- Container images and Compose configuration validate.

## Evidence

PR records dependency versions, commands, test counts, coverage, replay result, checkpoint reconstruction, concurrency outcome, skipped tests, CI URL, security scan, and rollback result.

## Limitations

- The 20-run kill-worker measurement, Saga compensation, real model fallback, Gate 2 report, and production Temporal deployment are deliberately deferred to AF-308–AF-312.
