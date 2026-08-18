# Local MVP Backend Bundle Test Plan — AF-R04, AF-R05, AF-R06

Status: Approved by Project Owner on 2026-08-17.

## Scope

Verify the development-only identity/model profile, tenant-scoped Run API,
PostgreSQL read model, Temporal lifecycle, LangGraph checkpoint/resume, six agent
steps, policy, sandbox, separate Human approval, dry-run Draft PR candidate,
evaluation, trace, cost, and audit path.

## Unit Tests

1. Settings default all local capabilities off and reject partial, production,
   credential-bearing, unapproved-host, same-token, and malformed configurations.
2. Local token verification uses exact constant-time comparison and never returns or
   logs token material.
3. Structured Ollama reasoners accept only bounded schema-valid JSON, strip no
   policy constraints, and classify malformed output without exposing content.
4. Run request hashing and idempotency distinguish replay from conflicting payload.
5. Approval preview digest covers repository, base SHA, changed paths/bytes, effect
   mode, and risk; altered content cannot reuse an approval.
6. Dry-run candidate emits no GitHub client call and never manufactures a GitHub URL.
7. Event cursor, trace redaction, token/cost availability, and evaluation formulas
   are deterministic and bounded.

## Component Tests

1. FastAPI session and Run endpoints with synthetic Developer/Reviewer identities.
2. Run create/list/detail/graph/events plus not-found and validation responses.
3. Clarification submit and approval/rejection endpoints signal the exact workflow.
4. Postgres clarification and approval gateways survive adapter reconstruction.
5. Production Worker assembly contains a configured graph port when and only when
   approved configuration is complete.

## Integration Tests

1. Apply migration 0010 to a clean PostgreSQL database and validate constraints,
   tenant foreign keys, append-only facts, and downgrade/upgrade cycle.
2. Start one Temporal workflow, reach a real LangGraph interrupt, reconstruct the
   graph/checkpointer, signal it, and resume the same tenant/run/version.
3. Run a controlled workspace through the Docker Sandbox Broker with a digest-pinned
   image, no network, non-root user, resource limits, and bounded output.
4. Run a bounded real Ollama `qwen3:8b` structured completion through LiteLLM and
   ModelGateway. Record latency/tokens/cost truthfully; do not treat this as a
   performance or production-capacity claim.
5. Complete one local PRD through approval and assert a dry-run Draft PR candidate,
   evaluation, trace, cost, and audit evidence.

## Negative / Security Tests

1. Missing/incorrect developer or reviewer token; cross-tenant read/write; capability
   denial; Developer self-approval; Reviewer Run creation.
2. Oversized PRD/title/source fields, invalid repository/base SHA/path, unknown
   fields, and invalid event cursors.
3. Duplicate Run with changed payload, conflicting Human Signal, wrong target/run,
   double decision, and resume after completion.
4. Prompt injection in retrieved context is denied or escalated by deterministic
   policy; LLM output cannot authorize a tool.
5. Workspace traversal, symlink, credential filename/content, excessive file count,
   sandbox timeout/resource failure, and output archive escape.
6. Production configuration cannot enable synthetic identity, Ollama local-only, or
   dry-run tool substitution.

## Fault Injection

- Database unavailable before/after Run commit.
- Temporal unavailable or duplicate workflow start.
- Worker termination before and after LangGraph checkpoint.
- Ollama connection failure, timeout, malformed JSON, and schema mismatch.
- Sandbox broker unavailable, timeout, non-zero tests, and repeated Activity.
- Candidate persistence failure after idempotency claim.

## Fixtures

- Synthetic local Developer and Reviewer identities only.
- Sanitized PRD/Issue payloads with sufficient and insufficient variants.
- Controlled per-run Python workspace without `.env` or credentials.
- Fake model/provider and Temporal clients for unit/component tests.
- Real local PostgreSQL, Temporal, Ollama, and Docker only for marked integration
  tests.

## Expected Results

- Safe defaults and all negative tests fail closed.
- One Run is reconstructable after process/adapter restart.
- No external write occurs before exact Reviewer approval.
- Local completion records `effect_mode=dry_run`, a non-GitHub candidate reference,
  and immutable approval/audit receipts.
- Complete Python suite maintains branch coverage at or above 90%.

## Commands

```powershell
uv run pytest -q -p no:cacheprovider
uv run pytest -q -m "database or temporal or docker"
uv run python -m aegisflow_core.models.ollama_smoke
docker compose -f compose.yaml -f compose.local-mvp.yaml config
docker compose -f compose.yaml -f compose.local-mvp.yaml up --build
```

## Evidence

Capture exact pass/fail/skip counts, Alembic head, container health, one real Run ID,
Temporal workflow ID, LangGraph checkpoint identity, Ollama model/latency/tokens,
sandbox result, approval receipt, candidate reference, evaluation, and final audit
event. Never copy Secret values into the evidence.

### Verified 2026-08-18

- Complete Python suite: `633 passed, 1 skipped`; the skipped case is the protected real-GitHub write test.
- Repository coverage: required `fail_under = 90` gate passed.
- Focused PostgreSQL Run service: `5 passed`, including clarification, dual-role self-approval denial and duplicate Signal behavior.
- Browser-created Run `56e35374-fd5d-4229-b8fd-23e168ab4e4a` completed all 10 stages with Ollama, bounded Sandbox build/test evidence, separate Reviewer approval and an explicitly dry-run Draft PR candidate.
- No real GitHub write was requested or performed.

## Limitations

The local profile proves functional integration and governance, not production
capacity, production OIDC, real GitHub mutation, model-quality superiority, or
deployment readiness.
