# Design Note — AF-301–AF-307 Durable Runtime Bundle

Status: Approved v1 — approved by the Project Owner for the AF-301–AF-307 batch.

## Problem

Gate 1B is reliable inside one process, but workflow lifetime, clarification and approval waits, graph checkpoints, and external-effect retries are not yet durable across worker loss. M3 must add durability without giving Temporal, LangGraph, and PostgreSQL overlapping authority.

## Objective

Implement one coherent runtime foundation for AF-301 through AF-307:

- AF-301: Temporal workflow, client, and worker bootstrap.
- AF-302: explicit state and retry ownership boundaries.
- AF-303: tenant/run-scoped LangGraph PostgreSQL checkpoints.
- AF-304: durable clarification Signal handling.
- AF-305: durable approval Signal handling.
- AF-306: typed Activity timeout/retry policies.
- AF-307: integrate the existing PostgreSQL idempotency ledger with retried Activities.

## Non-Goals

- Saga compensation and cleanup (AF-308).
- Kill-worker 20-run evidence (AF-309).
- LiteLLM, model fallback, or real provider calls (AF-310/AF-311).
- Gate 2 report/blog (AF-312), Redis, UI, OTel, deployment, or new product behavior.

## Relevant Documents / ADRs

- `docs/02_ARCHITECTURE.md`
- `docs/08_TEST_STRATEGY.md`
- `docs/18_RELIABILITY_PLAN.md`
- `docs/adr/0002-langgraph-temporal-state-ownership.md`
- `docs/adr/0008-observability-boundaries.md`
- Official Temporal Python SDK 1.31 documentation and replay/time-skipping APIs.
- Official `langgraph-checkpoint-postgres` 3.1 documentation, including mandatory setup and strict deserialization guidance.

## Dependency Decisions

- Add `temporalio>=1.31,<2`; lock the resolved version in `uv.lock`.
- Add `langgraph-checkpoint-postgres>=3.1,<4`; lock its Psycopg dependencies.
- Pin the Temporal Server development/CI image to the current approved version and immutable digest during implementation.
- Set `LANGGRAPH_STRICT_MSGPACK=true`; checkpoints may deserialize only known-safe application/Pydantic types.

## Affected Modules

- `runtime/temporal/`: contracts, workflow, activities, client, worker, policies.
- `runtime/checkpoint/`: configuration and `AsyncPostgresSaver` lifecycle.
- `runtime/gate1b.py`: injected checkpointer/config and durable resume adapter; no in-memory production default.
- `control_plane/idempotency_ledger.py`: reuse and narrowly extend the existing ledger only where Activity integration requires it.
- `settings.py`, `compose.yaml`, CI, tests, dependency lock, and minimal traceability/inventory entries.

## Proposed Flow

1. API/dispatcher starts `DeliveryWorkflow` with immutable identifiers and validated input; Temporal workflow ID is `aegisflow:{tenant_id}:{run_id}`.
2. Workflow executes a LangGraph Activity that advances Gate 1B until completion or a graph interrupt.
3. The Activity uses PostgreSQL checkpoints with a validated composite `thread_id=tenant:{tenant_id}:run:{run_id}:workflow:{workflow_version}` and the root graph's required empty `checkpoint_ns`.
4. Clarification or approval interrupts return a typed wait descriptor to Temporal. Temporal alone waits durably.
5. A typed Temporal Signal supplies the human decision. Identical duplicate Signal IDs are ignored; conflicting reuse is rejected and audited through an Activity.
6. Temporal calls an Activity that validates the persisted projection and resumes the exact LangGraph checkpoint.
7. Every external side effect runs only in an Activity and claims the existing PostgreSQL idempotency ledger before execution.
8. Completion/failure is projected to PostgreSQL by an Activity; Temporal Event History remains the lifecycle authority.

## State Ownership

| State | Authoritative owner | Projection/storage rule |
|---|---|---|
| Workflow lifecycle, wait, Signal receipt, Activity scheduling | Temporal | Event History |
| Agent node state and graph resume point | LangGraph | PostgresSaver |
| Tenant, Run, Step, Approval, Audit facts | Core Domain | PostgreSQL |
| External-effect claim/result | Gateway/Activity | Existing PostgreSQL idempotency ledger |
| Real-time notification | Presentation | Out of scope; Redis is never authoritative |

Workflow code stores only deterministic, serializable identifiers and decisions. It performs no network, filesystem, database, UUID, wall-clock, or random operation. All such work is delegated to Activities.

## Checkpoint Contract

- `thread_id` binds tenant, globally unique run, and immutable workflow version. This is required because LangGraph reserves `checkpoint_ns` for subgraph traversal and rewrites it to empty at the root graph.
- `checkpoint_ns` remains empty for the root graph; it is not used as an application tenancy boundary.
- A helper constructs and validates the complete config; callers cannot pass an arbitrary namespace.
- The checkpointer uses the application PostgreSQL service through a dedicated connection URL/search path.
- Library-owned checkpoint tables are initialized once by worker bootstrap using `AsyncPostgresSaver.setup()`; application business tables remain Alembic-owned.
- Resume rejects tenant, run, workflow-version, or pending-interrupt mismatches.

## Signal Contract

Clarification and approval Signals contain `signal_id`, `tenant_id`, `run_id`, target reference, decision/answer, actor reference, and received timestamp supplied at the boundary. Payloads reject extra fields.

- Same `signal_id` plus same canonical payload: no-op success.
- Same `signal_id` plus different payload: deterministic conflict; do not resume.
- Wrong tenant/run/target: reject and audit.
- Approval expiry uses Temporal time and is tested with time skipping.
- Approval remains a human decision; neither LLM output nor workflow code can manufacture it.

## Retry and Timeout Ownership

| Failure | Owner | Behavior |
|---|---|---|
| timeout, connection reset, GitHub/provider 5xx | Temporal Activity | bounded exponential retry |
| 429 | Temporal Activity | bounded retry using retry delay when available |
| authorization/policy denial | none | non-retryable final failure |
| invalid input/conflicting Signal | none | non-retryable final failure |
| deterministic agent quality/rework | LangGraph | graph route, not Temporal retry |
| model provider fallback | model gateway | AF-311, not this batch |
| test/sandbox semantic failure | LangGraph/reviewer | rework, not transport retry |

Activities declare start-to-close and schedule-to-close timeouts. Heartbeats are required only for operations long enough to benefit from cancellation/recovery. No nested unbounded retries are allowed.

## External Side Effects and Idempotency

Activity keys retain the frozen tuple: tenant, run, step, tool, canonical arguments hash. Temporal Activity attempt is metadata, never part of the key. On retry/replay:

- succeeded claim returns its stored result;
- active lease reports in-progress;
- expired/retryable claim obtains a new fencing token;
- stale writers cannot commit;
- argument mismatch fails final;
- remote reconciliation remains mandatory for GitHub writes.

AF-307 integrates this contract; it does not introduce a second ledger or another owner.

## Failure Modes

- Temporal unavailable: startup/readiness fails clearly; no silent in-process fallback.
- PostgreSQL/checkpointer unavailable: Activity fails retryably; workflow remains durable.
- missing checkpoint or identity mismatch: non-retryable safety failure.
- duplicate/conflicting Signal: ignore exact duplicate; reject conflict.
- worker termination: Temporal reschedules Activities; ledger fencing prevents stale completion.
- incompatible workflow change: replay test fails and blocks merge.

## Security Impact

- No Secret enters workflow input/history, checkpoint state, logs, or error text.
- Checkpoint deserialization uses strict msgpack allowlisting.
- Tenant identity is validated at Signal, checkpoint, projection, and ledger boundaries.
- Activities expose explicit ports; workflow code cannot call GitHub, PostgreSQL, sandbox, or model providers directly.
- Authorization and Policy Gate decisions remain deterministic and fail closed.

## Observability

Structured events include tenant_id, run_id, trace_id, workflow_id/version, Activity name/attempt, signal_id, and idempotency outcome. Secret payloads and human free text are not logged. OTel export remains AF-508/AF-509 scope.

## Rollback

- Stop worker/client entrypoints before removing the Temporal dependency.
- Revert code/config and restore the previous in-process Gate 1B entrypoint for development only.
- Do not delete Temporal histories or LangGraph checkpoints during rollback.
- No business-table downgrade is expected unless implementation proves a narrowly required migration; any migration must provide a tested downgrade.

## Resolved Decisions

1. One shared bundle/PR is allowed by the Project Owner's approved batch exception; each AF Issue retains explicit tests and traceability.
2. Temporal and checkpoint services run locally/in CI; Temporal Cloud is not required.
3. The existing idempotency ledger is extended/integrated, never duplicated.
4. AF-308/AF-309 are a separate failure-engineering batch after this foundation merges.
5. There are no open implementation questions. Human approval of this document is still mandatory.
