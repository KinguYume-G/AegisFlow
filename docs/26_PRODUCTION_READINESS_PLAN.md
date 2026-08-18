# 26 — Production Readiness Plan

> Status: Active planning baseline for AF-R04–AF-R08 and the production-readiness work that follows.
> Last verified: 2026-08-18.
> Authority: This document does not override `DESIGN_BLUEPRINT.md`, the Project Charter, Accepted ADRs, Architecture, or an active GitHub Issue.

## 1. Outcome

AegisFlow is an AI-driven software-delivery Agent Control Plane. Its primary business path is:

```text
PRD / GitHub Issue
  → FastAPI creates a tenant-scoped Run
  → Temporal owns the durable workflow lifecycle
  → LangGraph owns the six-Agent computational state
  → Intake → Clarifier → Context → Planner
  → Run-level Policy Gate
  → Executor → governed MCP / GitHub / Docker Sandbox tools
  → Build and test evidence
  → Reviewer → Human Approval
  → GitHub Draft PR candidate
  → Evaluation + Trace + Cost + Audit
```

The production target is not an unconstrained autonomous coding bot. It is a governed platform in which permissions are deterministic, external side effects are idempotent and auditable, humans approve high-impact actions, and every claim can be traced to evidence.

## 2. Truthful Current State

| Capability | Verified state | Production gap |
|---|---|---|
| FastAPI Run API | Implemented for the local MVP, tenant scoped | Production ingress, session integration, capacity validation |
| Temporal workflow | Durable lifecycle, signals, retry and recovery foundations exist | Production worker rollout/versioning and disaster-recovery exercise |
| LangGraph delivery graph | Six fixed Agents and checkpoint/resume foundations exist | Production checkpointer/store configuration and retention validation |
| Local model | Ollama path verified in the local MVP | Select and validate primary/fallback production providers |
| Policy and approval | Run-level and tool-level gates, human approval flow | Real identity claims and protected production approval roles |
| Sandbox | Docker sandbox build/test evidence verified locally | Production isolation profile, quotas, image provenance and host hardening |
| GitHub delivery | GitHub App adapters and dry-run Draft PR candidate path exist | Dedicated fixture installation and approved live side-effect canary |
| Data | PostgreSQL is business source of truth; Redis is projection/cache only | Managed backup, restore, retention and HA decisions |
| Console | Next.js developer and reviewer surfaces work locally | OIDC-backed session, production authorization, deployment packaging |
| Evaluation/observability | Evaluation, Langfuse, OpenTelemetry, Prometheus/Grafana foundations exist | Production sampling, alerting, retention, SLO and dashboard ownership |
| Automated quality | Backend 629 passed / 1 skipped; frontend unit/lint/type/build passed; browser smoke passed | Backend coverage is 88.71%, below the required 90% gate |
| Local business loop | A complete 10/10 Ollama + sandbox + approval + dry-run PR path was observed | This is local evidence, not production certification |

The project is therefore a working local full-stack MVP on top of substantial governance, reliability, evaluation and deployment foundations. It must not yet be described as fully production ready.

## 3. Repository Skeleton

The existing modular-monolith skeleton remains the target. Production work fills these boundaries; it does not split the system into microservices.

```text
AegisFlow/
├─ src/aegisflow_core/
│  ├─ control_plane/       # identity, tenant, RBAC, runs, approvals, audit
│  ├─ runtime/             # Temporal lifecycle and LangGraph computation
│  ├─ gateway/             # governed MCP, GitHub, sandbox and external adapters
│  ├─ models/              # LiteLLM gateway, routing, budgets and model contracts
│  ├─ evaluation/          # datasets, metrics, regression and reports
│  └─ packs/delivery/      # six-Agent delivery business pack
├─ web/console/            # Next.js management and reviewer console
├─ tests/                  # unit, integration, E2E, security, load and replay tests
├─ deploy/                 # Docker, Helm/k3d and observability deployment assets
├─ scripts/                # repeatable local, CI, demo and evidence commands
├─ docs/
│  ├─ adr/                 # accepted architecture decisions
│  ├─ design-notes/        # Issue-scoped designs
│  ├─ test-plans/          # Issue-scoped verification plans
│  ├─ reports/             # reproducible evidence and runbooks
│  ├─ handoffs/            # session and Issue handoffs
│  └─ templates/
├─ project/                # GitHub governance bootstrap material
├─ archive/                # non-authoritative historical material
└─ root configuration      # app, build, Compose and repository governance
```

### 3.1 Classification rules

- Business Python belongs under one of the six `src/aegisflow_core` module boundaries.
- The Next.js application remains under `web/console`; generated `.next`, Playwright, TypeScript and package-manager artifacts are ignored.
- Durable facts stay in PostgreSQL/Temporal/LangGraph stores according to ownership; Redis never becomes a business fact source.
- Deployment assets stay in `deploy`; root Compose files are allowed as repository entry points.
- Test evidence belongs in `docs/reports`, not in temporary folders or screenshots alone.
- Historical proposals and duplicates stay non-authoritative in `archive` until an explicit cleanup Issue approves deletion.

### 3.2 Deferred structure changes

The following are not performed inside AF-R08 because they are broader refactors or governance changes:

- moving root API composition modules solely for aesthetic reasons;
- deleting intentionally retained blueprint duplicates;
- introducing microservices, Kafka, Terraform, CrewAI, SFT/LoRA, general ABAC or a Workflow Builder;
- introducing a new object-storage or secret-management product without an ADR and Issue.

## 4. Safe Cleanup Plan

| Category | Action | Timing |
|---|---|---|
| `.pytest_cache`, `.uv-cache`, `.coverage`, `.next`, test/browser reports | Ignore and remove only as reproducible generated artifacts | AF-R08 |
| `.tmp/mvp.env`, `.tmp/test.env` | Keep local-only and ignored; never commit or print values | Ongoing |
| `.env` | Keep ignored; validate names only, never copy secrets into docs | Ongoing |
| User project guide and architecture image | Preserve; do not move or delete without owner confirmation | Ongoing |
| Stale README/index/layout/manifest/config docs | Update to the verified implementation state | AF-R08 |
| Duplicate blueprint/archive files | Retain for now; clean only through a separate Issue | Later |
| Old code paths | Delete only after reference search, replacement tests and an Issue-scoped rollback plan | Later |

## 5. Project Owner One-Time Preparation

The owner should prepare references and access, not paste secrets into chat or commit them to Git.

### 5.1 Decisions

- Select the production environment and region. Recommended first production shape: one Kubernetes cluster with the modular monolith, separate Core/Worker/Console/Sandbox workloads, and managed stateful dependencies where available.
- Reserve the product domain and decide TLS/ingress ownership.
- Select the OIDC provider and define developer, reviewer and administrator group mappings.
- Select primary and fallback model providers, approved models, token/cost budgets and data-processing constraints.
- Confirm whether Langfuse is hosted or self-managed and set trace-retention policy.
- Select PostgreSQL, Redis and artifact-storage services, backup retention and restore objectives.
- Define initial SLOs, alert recipients, monthly model budget and audit-log retention.

### 5.2 External accounts and fixtures

- A dedicated GitHub App installation on a non-production fixture repository.
- An OIDC application for Console and API callback/logout URLs.
- Protected GitHub environments for demo/staging/production with human reviewers.
- A deployment environment, DNS control and container registry.
- Production observability endpoints and ownership contacts.

### 5.3 Secret references

Store the actual values in the selected secret store or protected GitHub Environment. AegisFlow only receives references/configuration for:

- PostgreSQL and LangGraph database URLs;
- OIDC issuer, audience and JWKS configuration;
- GitHub App ID, installation ID, private-key reference and webhook secret reference;
- primary/fallback model credential references;
- Langfuse and OpenTelemetry credential/endpoint references;
- artifact-store credentials if an ADR approves that dependency.

## 6. Delivery Roadmap

### Phase A — Close the local full-stack MVP

- Complete AF-R04–AF-R08 without expanding scope.
- Raise backend coverage to at least 90% by testing behavior, not lowering thresholds.
- Re-run backend, frontend, browser, Compose, migration, secret and documentation checks.
- Update README, documentation index, architecture, repository layout, configuration reference, traceability and manifest.
- Produce a reproducible local-MVP runbook and Handoff.

Exit: a clean clone can reproduce the dry-run business loop with documented limitations and no real external write.

### Phase B — Production identity and Console security

- Replace the trusted-loopback Console persona with an OIDC-backed server session.
- Centralize authorization in a server-side data-access layer close to the data source.
- Use minimal DTOs; never trust UI hiding as authorization.
- Add CSRF/session, negative-role, expired-token and cross-tenant browser tests.

Exit: every Console and Route Handler request is authenticated, tenant bound and authorized server side.

### Phase C — Production deployment packaging

- Add Console and Sandbox workloads to Helm.
- Separate migrations into a controlled pre-deployment Job.
- Configure ingress/TLS, network policies, egress allowlists, pod security, resource requests/limits, probes, PDB and autoscaling boundaries.
- Support external PostgreSQL/Redis/Temporal/artifact stores without embedding secrets in values.
- Prove upgrade, rollback, backup and restore in staging.

Exit: an immutable release can be installed, upgraded and rolled back in a staging cluster.

### Phase D — Controlled real-provider canary

- Run the primary/fallback model path against approved providers.
- Install the GitHub App only on the fixture repository.
- Keep write tools behind policy and human approval; create a Draft PR only after explicit approval.
- Verify webhook idempotency, duplicate-delivery safety, compensation and audit evidence.

Exit: one approved fixture Run produces one Draft PR, with no duplicate side effects and complete evidence.

### Phase E — Operational hardening

- Define SLOs and alerts for success rate, queue depth, workflow age, tool failures, latency, tokens and cost.
- Exercise Temporal worker restart/replay and deployment-version transitions.
- Exercise database restore, credential rotation, incident response and audit export.
- Validate sandbox quotas, image signing/provenance and failure isolation.

Exit: staging fault drills meet the documented recovery and security objectives.

### Phase F — Evaluation and release governance

- Expand the Golden Dataset with real failure classes and permission cases.
- Add prompt/model/workflow version regression and shadow comparison.
- Gate releases on task success, tool-call correctness, security, latency and cost—not on subjective output alone.
- Require Human Review and Human Merge for every release.

Exit: a release candidate has reproducible functional, security, reliability, evaluation and operational evidence.

## 7. Production Definition of Done

AegisFlow may be called production ready only when all of the following are demonstrated in a staging environment representative of production:

- OIDC, RBAC and tenant isolation work end to end, including negative tests.
- Temporal and LangGraph state ownership, restart, retry, checkpoint and replay are verified.
- All external writes pass schema validation, scope checks, two policy gates, approval, idempotency and audit.
- GitHub fixture canary creates exactly one approved Draft PR and never auto-merges.
- Database backup/restore and deployment rollback are exercised.
- Secret scanning and log/trace redaction pass.
- Required test, coverage, security, evaluation and performance gates pass.
- Dashboards, alerts, runbooks, incident ownership and retention policies exist.
- The Project Owner or delegated humans approve the evidence and merge the release.

## 8. Immediate Next Issues After AF-R08

These are proposed work packages and must become ready GitHub Issues before implementation:

1. Production OIDC session and Console authorization.
2. Helm packaging for Console, Sandbox and controlled migrations.
3. External state services, backup/restore and secret references.
4. Staging ingress/TLS, network policy and workload hardening.
5. Real provider plus GitHub fixture canary.
6. Worker deployment/versioning, replay and disaster-recovery drills.
7. Production SLOs, alerts, evaluation gates and release evidence.
8. Optional repository refactor/duplicate cleanup after reference and governance review.

## 9. Primary Implementation References

- Next.js Backend for Frontend: <https://nextjs.org/docs/app/guides/backend-for-frontend>
- Next.js Authentication: <https://nextjs.org/docs/app/guides/authentication>
- Next.js Data Security: <https://nextjs.org/docs/app/guides/data-security>
- Next.js Production Checklist: <https://nextjs.org/docs/app/guides/production-checklist>
- FastAPI Bigger Applications: <https://fastapi.tiangolo.com/tutorial/bigger-applications/>
- FastAPI Deployment Concepts: <https://fastapi.tiangolo.com/deployment/concepts/>
- FastAPI in Containers: <https://fastapi.tiangolo.com/deployment/docker/>
- LangGraph Overview: <https://docs.langchain.com/oss/python/langgraph/overview>
- LangGraph Persistence: <https://docs.langchain.com/oss/python/langgraph/persistence>
- Temporal Documentation: <https://docs.temporal.io/>
- Temporal Python SDK API: <https://python.temporal.io/>
- Temporal Helm Charts: <https://github.com/temporalio/helm-charts>
