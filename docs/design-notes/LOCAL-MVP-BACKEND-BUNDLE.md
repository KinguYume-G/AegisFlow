# Local MVP Backend Bundle — AF-R04, AF-R05, AF-R06

Status: Approved by Project Owner on 2026-08-17.

## Problem

The repository contains tested components but not a runnable product path. Core
cannot create or control Runs, the Temporal Worker uses `UnconfiguredGraphPort`,
the six agent graph is not assembled with production adapters, human waits are not
fully reconstructable from PostgreSQL, and local Ollama cannot be the only model
route. Consequently `/health` can succeed while no PRD can traverse the product.

## Objective

Deliver one truthful local backend loop:

```text
PRD / Issue
  -> tenant-scoped FastAPI Run
  -> Temporal DeliveryWorkflow
  -> LangGraph Intake / Clarifier / Context / Planner
  -> Policy Gate
  -> Executor / Docker Sandbox
  -> Reviewer
  -> separate Human Approval
  -> governed dry-run Draft PR candidate
  -> Evaluation / Trace / Cost / Audit
```

The same contracts must be ready for the future Next.js console and for real OIDC,
hosted models, and GitHub App adapters without changing state ownership.

## Non-Goals

- Real GitHub mutation, merge, deployment, or production authorization bypass.
- General chat, Workflow Builder, arbitrary agent definitions, or autonomous policy.
- Kafka, Terraform, CrewAI, SFT/LoRA, general ABAC, or microservice extraction.
- Claiming local deterministic evidence is production model quality or capacity.

## Relevant Documents / ADRs

- `docs/DESIGN_BLUEPRINT.md`
- `docs/00_PROJECT_CHARTER.md`
- `docs/02_ARCHITECTURE.md`
- ADR-0002, ADR-0007, ADR-0009, ADR-0013, ADR-0014
- `docs/08_TEST_STRATEGY.md`
- `docs/19_SECURITY_STANDARD.md`
- GitHub Issues #113, #114, #115

## Affected Modules

- `settings`, `app`, and FastAPI routers/dependencies.
- Control-plane domain models, migration 0010, RBAC/bootstrap, Run services.
- Temporal client/worker and one `DurableGraphPort` implementation.
- DeliveryPack graph assembly, model reasoners, trace recorder, HITL gateways.
- ModelGateway/LiteLLM local-only composition.
- Policy, sandbox, approval, Draft PR candidate, evaluation and audit adapters.
- Docker Compose local-MVP configuration and developer runbook.

## Proposed Flow

### 1. Session and tenant bootstrap

With `LOCAL_MVP_PROFILE_ENABLED=true`, startup validates two distinct synthetic
tokens, creates a local tenant and immutable workflow, then creates separate
Developer and Reviewer memberships and roles. Authentication returns a `Principal`;
RBAC remains the only authority for every tenant operation.

### 2. Create Run

`POST /v1/tenants/{tenant_id}/runs` validates a bounded PRD/Issue schema and an
`Idempotency-Key`. In one transaction it stores `Run`, immutable `RunRequest`, and
an append-only creation event. After commit it starts the deterministic Temporal
workflow ID. Repeating the same key and payload returns the original Run; reusing
the key with different input returns conflict.

### 3. Durable agent computation

The Worker composes `PostgresDeliveryGraphAdapter`. Each Activity opens the
tenant/run/version-scoped PostgreSQL checkpointer, assembles the graph with
run-bound reasoners and adapters, and either invokes initial state or resumes from
the Human Signal. The Activity returns a terminal or waiting state immediately;
Temporal owns the durable wait.

### 4. Six agents and policy

- Intake normalizes the request.
- Clarifier uses bounded structured Ollama output and creates a durable
  clarification request when required.
- Context reads only the controlled per-run workspace and returns exact citations.
- Planner uses bounded structured Ollama output to produce the fixed Plan contract.
- Policy Gate makes the final deterministic permission/risk decision.
- Executor produces a bounded change set, sends the workspace through the Sandbox
  Broker, and records test evidence.
- Reviewer assesses the diff/test evidence and either requests rework or a separate
  human decision. The LLM never grants permission.

### 5. Human decisions and side effect

Clarification and approval endpoints verify tenant scope and capability, lock the
pending request, write an immutable receipt/event, and signal the existing Temporal
workflow. Approval exposes an exact action preview: target repository, base SHA,
changed paths, content digest, effect mode, and risk. The initial/safe UI action is
reject/cancel. An approved local run creates only a `dry_run` Draft PR candidate.

### 6. Read model

Run list/detail endpoints reconstruct product state from PostgreSQL:

- request and lifecycle status;
- ordered steps and pending Human request;
- exact approval preview and receipt;
- redacted trace/token/cost records;
- sandbox/test and Draft PR candidate evidence;
- append-only events/audit;
- terminal evaluation.

Polling uses a monotonic per-run event sequence and `after` cursor. Redis may later
project these events but is not required to recover facts.

## State Ownership

| State | Owner | PostgreSQL projection |
| --- | --- | --- |
| Workflow lifetime, Signal/retry/timeout | Temporal Event History | Run status/events |
| Agent values, interrupts, resume | LangGraph checkpointer | Steps/human requests/traces |
| Request, approval, result, audit, evaluation | PostgreSQL | Authoritative tables |
| Live UI transport/cache | Redis (optional) | Never authoritative |

Temporal does not store LangGraph business payload beyond stable references and
Signals. LangGraph does not own retry policy or week-long Human waits.

## External Side Effects

- Ollama HTTP completion through LiteLLM and ModelGateway.
- Temporal start and Signal operations.
- Docker Sandbox Broker execution.
- Local Draft PR candidate persistence only. Real GitHub writes remain disabled
  unless a separate authorized configuration and Issue enable them.

## Idempotency

- Run creation: `(tenant_id, idempotency_key, input_hash)`.
- Temporal start: derived workflow ID `aegisflow:{tenant_id}:{run_id}`.
- Step writes: `(run_id, sequence)` upsert.
- Clarification: `(tenant_id, run_id, step_key)`.
- Approval: `(tenant_id, run_id, step_id)` and one immutable decision.
- Events/traces: deterministic event IDs or monotonic unique sequence.
- Draft PR candidate: existing idempotency ledger plus exact argument/content hash.

## Failure Modes

- Configuration/identity invalid: startup or request fails closed.
- Database transaction fails: no partial fact is reported.
- Temporal unavailable: Run remains retryable with a sanitized failure event.
- Ollama unavailable/malformed: bounded retry then classified failure; no invented
  model output.
- LangGraph checkpoint missing/mismatched: no cross-run resume.
- Sandbox timeout/resource/error/test failure: evidence is stored; Reviewer rework
  is bounded; no Draft PR candidate is produced.
- Duplicate/conflicting Signal: rejected before state mutation.
- Approval timeout/rejection: terminal failed outcome with audit evidence.

## Security Impact

- Two-person local identity preserves self-approval prohibition.
- Tenant and repository scope is validated at API, retrieval, policy, tool, and
  persistence boundaries.
- All inputs and output collections have explicit bounds.
- Workspaces reject traversal, links, sensitive filenames, and credential patterns.
- No token, Secret, full prompt, raw exception, or model chain-of-thought is stored.

## Test Plan

See `docs/test-plans/LOCAL-MVP-BACKEND-BUNDLE.md`. Tests are written or updated
before each implementation slice.

## Observability

Every Run and Step carries tenant, run, trace, workflow version, agent/model,
latency, token availability, cost availability, and sanitized outcome. Business
facts are visible through the API even when Langfuse or OTLP is not configured.

## Documentation Updates

Update `docs/index.md`, decision log, traceability, repository layout, environment
template, Compose runbook, README/START_HERE, and `MANIFEST.md` after verification.

## Rollback

Disable local profile and local model configuration; stop Core/Worker; downgrade
migration 0010 if required. Existing M1–M5 routes and normal fail-closed production
configuration remain available.

## Open Questions

None blocking the local backend slice. Real GitHub Fixture writes and production
OIDC remain separate, explicitly authorized follow-up work.
