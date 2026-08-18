# Local Full-Stack MVP Runbook

> Scope: AF-R04–AF-R08, development/test only.
> Last verified: 2026-08-18 on Windows with Docker Desktop and host Ollama.
> External effect mode: GitHub dry-run; no real repository write.

## 1. What this proves

This runbook proves one local business loop through the production-shaped boundaries:

```text
Next.js Console → FastAPI Run API → PostgreSQL → Temporal
→ LangGraph six-Agent graph → Policy → Docker Sandbox
→ Reviewer → separate Human Approval → dry-run Draft PR candidate
→ Evaluation + Trace + Cost + Audit
```

It does not prove production identity, production capacity, hosted-provider failover, or a real GitHub Draft PR.

## 2. Prerequisites

- Docker Desktop with Compose is running.
- Ollama is listening on `127.0.0.1:11434`.
- The model named by `OLLAMA_MODEL` is already pulled; the verified default is `qwen3:8b`.
- Ports 3000, 3001, 8000, 55432, 56379 and 57233 are available, or are changed in the local env file.
- Commands are run from the repository root.

Do not paste or commit real credentials. This profile needs no real GitHub App, OIDC or hosted-model Secret.

## 3. Configure

```powershell
Copy-Item .env.local-mvp.example .env.local-mvp
```

Change at least `POSTGRES_PASSWORD`, `LOCAL_MVP_DEVELOPER_TOKEN` and `LOCAL_MVP_REVIEWER_TOKEN` in the ignored copy. Tokens must be distinct and at least 16 characters. Keep `LOCAL_MVP_GITHUB_DRY_RUN=true`.

Confirm the local model exists:

```powershell
ollama list
```

## 4. Start

```powershell
docker compose --env-file .env.local-mvp -f compose.yaml -f compose.local-mvp.yaml up -d --build
```

Inspect bounded service state:

```powershell
docker compose --env-file .env.local-mvp -f compose.yaml -f compose.local-mvp.yaml ps
```

Expected endpoints:

- Developer Console: <http://127.0.0.1:3000>
- Reviewer Console: <http://127.0.0.1:3001>
- Core health: <http://127.0.0.1:8000/health>

The migration container should exit successfully. Core, Temporal Worker, PostgreSQL, Redis, Temporal, Sandbox Broker, Console and Reviewer Console should be healthy/running.

## 5. Complete a Run

1. Open the Developer Console.
2. Create a Run from a bounded PRD. Use a real repository-shaped owner/name and a 40-character base SHA, but remember that GitHub stays dry-run.
3. If the Clarifier pauses, answer every displayed question in the Developer Console.
4. Wait for the graph to reach Human Approval.
5. Open the same Run in the Reviewer Console.
6. Inspect the action preview, digest, build/test evidence and review result.
7. Approve or reject as the separate Reviewer. The Developer persona cannot approve its own Run.
8. Verify terminal state and evidence.

Expected successful timeline:

```text
1 Intake
2 Clarifier
3 Context
4 Planner
5 Policy Gate
6 Executor
7 Reviewer
8 Human Approval
9 Draft PR candidate
10 Evaluation / Trace / Cost / Audit projection
```

Expected GitHub result is explicitly a dry-run candidate reference, never a real PR URL.

## 6. Automated Verification

### Backend

Set `DATABASE_URL` to the migrated local PostgreSQL test database without printing it, then run:

```powershell
.\.venv\Scripts\python.exe -m coverage run -m pytest
.\.venv\Scripts\python.exe -m coverage report -m
```

Verified 2026-08-18 result: 633 passed, 1 protected real-GitHub test skipped, and the repository 90% coverage gate passed.

### Console

```powershell
npm --prefix web/console run test:run
npm --prefix web/console run lint
npm --prefix web/console run typecheck
npm --prefix web/console run build
npm --prefix web/console run test:e2e
```

Verified result: 17 unit tests passed; lint, TypeScript and production build passed. A fresh browser Run completed the governed business path, and a final resume-based Playwright verification passed 2 tests with 2 project-specific skips. Set `AEGISFLOW_E2E_RUN_ID` to re-check an existing Run without paying the model execution cost again.

## 7. Failure interpretation

- `identity_not_configured`: neither production OIDC nor the local profile was configured.
- `authentication_required` / `local_identity_denied`: Persona/token is missing, mismatched or local mode is disabled.
- `tenant_access_denied`: the authenticated actor is not authorized for that tenant/capability.
- `rbac_self_approval_forbidden`: a requester attempted to approve its own external side effect.
- `core_unavailable`: Console could not reach Core within the bounded timeout.
- Ollama connection/model error: verify host Ollama, `OLLAMA_MODEL`, and `host.docker.internal` access from the Worker container.
- Sandbox error: inspect only the bounded Sandbox Broker/Worker logs; never print environment variables.

## 8. Stop and reset

Stop without deleting state:

```powershell
docker compose --env-file .env.local-mvp -f compose.yaml -f compose.local-mvp.yaml down
```

Deleting named volumes removes local PostgreSQL, Redis, Temporal and sandbox state. Treat that as destructive and perform it only after explicitly confirming the exact Compose project and accepting that local Runs will be lost.

## 9. Production boundary

Before production, replace local Persona tokens with OIDC-backed server sessions, deploy the Console/Sandbox through the production chart, use external secret references, exercise backup/restore and rollback, and run an explicitly approved GitHub fixture canary. The full gap list is in [`../26_PRODUCTION_READINESS_PLAN.md`](../26_PRODUCTION_READINESS_PLAN.md).
