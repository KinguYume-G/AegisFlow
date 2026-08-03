# 21 — Requirements Traceability Matrix

## AF-203–AF-207 implementation evidence (batch PR)

- AF-203: migration 0003, exact-line chunks, deterministic embeddings, isolation and secret-quarantine tests.
- AF-204: structured broker boundary, digest/resource validation, Core without Docker socket, adapter tests.
- AF-205: bounded paths/content/patches, structured TestProfile/evidence, deterministic Executor tests.
- AF-206: async memory/PostgreSQL approval gateways, migration 0004 terminal protection, Reviewer tests.
- AF-207: trusted ExecutionScope, fixed repository/capability/risk rule order, default-deny tests.

| Requirement | Architecture | ADR | Issues | Evidence |
|---|---|---|---|---|
| Demand-to-Delivery | DeliveryPack | — | AF-104–AF-211 | Gate 1 |
| Durable Execution | Temporal | ADR-0002 | AF-301–AF-309 | Worker Kill |
| Checkpoint | LangGraph | ADR-0002 | AF-303 | Resume |
| Idempotency | Ledger | ADR-0002 | AF-209, AF-307 | Duplicate tests |
| HITL | Signal | ADR-0002 | AF-304, AF-305 | Delayed response |
| MCP Governance | Gateway | ADR-0007 | AF-406 | Scope denial |
| Sandbox | Docker/k3s | ADR-0009 | AF-204, AF-407, AF-512 | Negative tests |
| RBAC/Tenant | Control Plane | ADR-0007 | AF-401–AF-409 | Isolation suite |
| Model Fallback | LiteLLM | — | AF-310, AF-311 | Outage test |
| Evaluation | Evaluation | ADR-0010 | AF-501–AF-507 | Reports |
| Observability | Langfuse/OTel | ADR-0008 | AF-109, AF-508–510 | AF-109 trace schema/redaction/Recorder tests and manual Langfuse smoke workflow; dashboard pending later Issues |
| 100 Concurrency | Control Plane | — | AF-511 | Locust report |
| k3s + Helm | Deployment | ADR-0004 | AF-512, AF-513 | Install/rollback |
| Dogfooding | Personal | ADR-0012 | AF-515 | Usage log |
| OpsPilot | Roadmap | ADR-0012 | AF-R01 | Optional |
| Phase 0 GitHub Governance | Git/GitHub Workflow | — | AF-004 | 56 Labels, 7 Milestones, 75 Issues verified |
| Phase 0 Repository Scaffold | Documentation-only Repository | — | AF-008 | PR #76 merged; `25_PHASE0_EXIT_REVIEW.md`; AF-000–AF-008 verified and closed |
| Bootstrap Exception | Repository Governance | — | AF-004, AF-008 | `20_DECISION_LOG.md`; commits `817751a`, `82c91d7` |
| Application Skeleton | Modular Monolith | ADR-0001 | AF-101 | PR #77 human-merged; 21 tests; `/health` contract; `status:verified` |
| Local Infrastructure Foundation | Modular Monolith / Deployment Evolution | ADR-0004 | AF-102 | Approved Design Note/Test Plan; 30 tests; real Compose build and three-service health verification |
| Continuous Integration | N/A (Repository Governance) | — | CI-001 | `CI / test`: red Run 30744284422; green Run 30744322133; protected-main readiness |
| Initial Domain Model | Core Domain / PostgreSQL | — | AF-103 | Local PostgreSQL: 49 tests, 100% coverage, migration up/idempotent/down/re-up, `alembic check`; CI Actions link recorded in PR |
| Intake Agent Contract | DeliveryPack / Intake | — | AF-104 | Canonical normalization and SHA-256 vectors; deterministic Clock/IdGenerator; `tests/packs/delivery/intake/` |
| Clarifier Agent Contract | DeliveryPack / Clarifier | — | AF-105 | Five deterministic gap rules; structured question/answer invariants; `tests/packs/delivery/clarifier/` |
| Context Retrieval Contract | DeliveryPack / Context | — | AF-106 | Bounded local retrieval; exact citations; path/symlink/size/count guards; `tests/packs/delivery/context/` |
| Planner Agent Contract | DeliveryPack / Planner | ADR-0007 | AF-107 | Measurement/Plan v1; stable capability allowlist; deterministic tasks/risk; Clarifier gate; `tests/packs/delivery/planner/` |
| Clarification HITL Interface | DeliveryPack / Clarifier | ADR-0002 | AF-108 | In-memory replay idempotency; run isolation; atomic answer transition; duplicate rejection; `test_hitl.py` |
| Gate 1A End-to-End | Runtime / DeliveryPack | ADR-0002, ADR-0008 | AF-110 | Native LangGraph interrupt/resume; validated run/thread identity; deterministic fixture-to-Plan path; four correlated node traces; `tests/e2e/test_gate1a.py` |
| GitHub App / Webhook Verification | Gateway (GitHub) / PostgreSQL Audit | — | AF-201 | Signed `repository_dispatch`; bounded atomic replay guard; safe installation-token cache; bootstrap and allow/deny audit; `tests/gateway/github/`, `tests/control_plane/test_bootstrap.py` |
| GitHub MCP Read Tools | Gateway (GitHub) | ADR-0007 | AF-202 | Five async GET-only tools; strict v1 schemas; bounded response/file/patch sizes; explicit pagination truncation; safe error mapping and PR reconciliation; `tests/gateway/github/test_read_tools.py` |
| Repository Knowledge Ingestion | Runtime (Context) / PostgreSQL+pgvector | — | AF-203 | PR #96 human-merged; line-accurate chunks, deterministic embeddings, isolation and secret quarantine |
| Docker Sandbox Baseline | Gateway (Sandbox) | ADR-0009 | AF-204 | PR #96 human-merged; narrow broker, digest/non-root/no-network/resource enforcement and live lifecycle smoke |
| Executor Agent Contract | DeliveryPack / Executor | — | AF-205 | PR #96 human-merged; bounded path/file/patch handling and structured sandbox evidence |
| Reviewer Agent Contract | DeliveryPack / Reviewer | ADR-0002 | AF-206 | PR #96 human-merged; async approval state machine and immutable PostgreSQL decisions |
| Deterministic Policy Gate v0 | Gateway (Policy) | ADR-0007 | AF-207 | PR #96 human-merged; trusted repository/capability/risk default-deny rules |
| GitHub Draft PR Write Tool | Gateway (GitHub) | ADR-0007 | AF-208 | Exact-scope approval, structured Git Data writes, atomic claim and remote Marker reconciliation; `test_pull_request.py` |
| Webhook/Tool-call Idempotency (M2 scope) | Ledger | ADR-0002 | AF-209 | Migration 0005; tenant/scope key, lease/fencing token, concurrent claim and stale-writer tests |
| Gate 1B End-to-End | Runtime / DeliveryPack | ADR-0002, ADR-0007, ADR-0009 | AF-210 | Async Policy→Executor→Reviewer→Human Approval→Draft PR graph; local/DB E2E passes; real GitHub evidence waits on protected Fixture/App environment |
| Durable Workflow Bootstrap and Ownership | Temporal / Runtime | ADR-0002 | AF-301, AF-302 | Pinned Temporal service; replay-safe Workflow/Activity boundary; executable ownership/import guards; `tests/runtime/temporal/` |
| Durable Graph Checkpoints | LangGraph / PostgreSQL | ADR-0002 | AF-303 | Official PostgresSaver setup; strict serializer; composite tenant/run/version identity; interrupt reconstruction and cross-tenant isolation tests |
| Durable Human Signals | Temporal / DeliveryPack | ADR-0002 | AF-304, AF-305 | Typed clarification/approval Signals; duplicate/conflict handling; timeout and worker reconstruction tests |
| Activity Reliability | Temporal / PostgreSQL Ledger | ADR-0002 | AF-306, AF-307 | Bounded retry classes/timeouts; fencing-ledger adapter; concurrent duplicate and stale-completion tests |
| Saga Compensation | Temporal / PostgreSQL Ledger | ADR-0002 | AF-308 | Reverse-order typed receipts; separate fenced compensation claim; original-effect `compensated` transition; explicit manual escalation and audit port tests |
| Worker-Loss Recovery | Temporal / Runtime | ADR-0002 | AF-309 | Hosted run 30801262477: real 4×5 abrupt worker-loss matrix, 20/20 terminal completions, duplicate effects 0, lost Signals 0, p50 2049.31 ms, p95 2973.56 ms; artifact 8850930348 |
| LiteLLM Model Gateway | Models / Langfuse projection | ADR-0008 | AF-310 | Exact locked LiteLLM 1.94.0; Secret-reference settings; SDK retries disabled; honest token/cost states; protected real-provider smoke workflow |
| Model Circuit and Fallback | Models / PostgreSQL | ADR-0002, ADR-0008 | AF-311 | Tenant-route Closed/Open/Half-Open state, fenced probe, bounded primary/fallback chain, migration 0006 and persistence/concurrency tests |
| Gate 2 Reliability Evidence | GitHub Actions / Documentation | ADR-0002, ADR-0008 | AF-312 | PR #100 merge 5a5b6a3; hosted fault run 30801262477; protected primary-provider smoke 30804037539; reviewed report, limitations, blog, and demo runbook |
| Tenant Persistence Scope | Control Plane / PostgreSQL | ADR-0007 | AF-401 | Explicit tenant session; automatic ORM criteria; cross-tenant write/root/raw SQL rejection; `tests/control_plane/test_tenant_scope.py` |
| Immutable Prompt Versions | Control Plane / PostgreSQL | ADR-0002, ADR-0007 | AF-410 | Concurrent ordered publication, immutable rows, rollback-as-new-version, exact Run binding and audit; `tests/control_plane/test_versioning.py` |
| Immutable Workflow Versions | Control Plane / PostgreSQL | ADR-0002, ADR-0007 | AF-411 | Canonical persisted definition/hash, one active version, rollback-as-new-version, legacy fail-closed resolution and immutable trigger tests |
