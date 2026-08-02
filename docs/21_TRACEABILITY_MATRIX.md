# 21 — Requirements Traceability Matrix

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
| Observability | Langfuse/OTel | ADR-0008 | AF-109, AF-508–510 | Dashboard |
| 100 Concurrency | Control Plane | — | AF-511 | Locust report |
| k3s + Helm | Deployment | ADR-0004 | AF-512, AF-513 | Install/rollback |
| Dogfooding | Personal | ADR-0012 | AF-515 | Usage log |
| OpsPilot | Roadmap | ADR-0012 | AF-R01 | Optional |
| Phase 0 GitHub Governance | Git/GitHub Workflow | — | AF-004 | 56 Labels, 7 Milestones, 75 Issues verified |
| Phase 0 Repository Scaffold | Documentation-only Repository | — | AF-008 | PR #76 merged; `25_PHASE0_EXIT_REVIEW.md`; AF-000–AF-008 verified and closed |
| Bootstrap Exception | Repository Governance | — | AF-004, AF-008 | `20_DECISION_LOG.md`; commits `817751a`, `82c91d7` |
| Application Skeleton | Modular Monolith | ADR-0001 | AF-101 | Approved Design Note/Test Plan; 21 tests; `/health` contract; implementation PR |
