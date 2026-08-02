# 05 — GitHub Issue Backlog

本文件是 GitHub Issue 预拆分清单。导入后 GitHub 是实时状态源，本文件保留为规划基线。

## Backlog Summary

| ID | Title | Milestone | Labels | Dependencies |
|---|---|---|---|---|
| AF-000 | Establish Phase 0 documentation index | M0 Engineering System | type:docs,priority:P0,size:S,status:ready | None |
| AF-001 | Approve project charter | M0 Engineering System | type:docs,type:governance,priority:P0,size:S,status:ready | AF-000 |
| AF-002 | Approve architecture baseline | M0 Engineering System | type:architecture,priority:P0,risk:high,size:M,status:ready | AF-001 |
| AF-003 | Approve quality strategies | M0 Engineering System | type:test,type:security,priority:P0,risk:high,size:M,status:ready | AF-002 |
| AF-004 | Establish GitHub governance | M0 Engineering System | type:governance,priority:P0,size:M,status:ready | AF-001 |
| AF-005 | Establish AI collaboration protocol | M0 Engineering System | type:docs,type:ai-process,priority:P0,size:M,status:ready | AF-001 |
| AF-006 | Accept initial ADR set | M0 Engineering System | type:architecture,priority:P0,size:M,status:ready | AF-002 |
| AF-007 | Create configuration placeholder contract | M0 Engineering System | type:security,type:docs,priority:P0,size:S,status:ready | AF-003 |
| AF-008 | Prepare documentation-only repository scaffold | M0 Engineering System | type:docs,type:repo,priority:P0,size:S,status:ready | AF-000,AF-004,AF-007 |
| AF-101 | Create modular monolith application skeleton | M1 Demand to Plan | type:backend,priority:P0,size:M,status:blocked | AF-008 |
| AF-102 | Create Docker Compose foundation | M1 Demand to Plan | type:infra,priority:P0,size:M,status:blocked | AF-101 |
| AF-103 | Define initial domain model and migrations | M1 Demand to Plan | type:backend,type:architecture,priority:P0,size:M,status:blocked | AF-101,AF-102 |
| AF-104 | Implement Intake Agent contract | M1 Demand to Plan | type:agent-runtime,pack:delivery,priority:P0,size:M,status:blocked | AF-103 |
| AF-105 | Implement Clarifier Agent contract | M1 Demand to Plan | type:agent-runtime,pack:delivery,priority:P0,size:M,status:blocked | AF-104 |
| AF-106 | Implement Context Agent retrieval contract | M1 Demand to Plan | type:rag,pack:delivery,priority:P0,size:L,status:blocked | AF-103 |
| AF-107 | Implement Planner Agent contract | M1 Demand to Plan | type:agent-runtime,pack:delivery,priority:P0,size:L,status:blocked | AF-105,AF-106 |
| AF-108 | Implement clarification HITL interface | M1 Demand to Plan | type:workflow-runtime,priority:P0,size:M,status:blocked | AF-105 |
| AF-109 | Add initial Langfuse tracing and cost fields | M1 Demand to Plan | type:observability,priority:P1,size:M,status:blocked | AF-104,AF-105,AF-106,AF-107 |
| AF-110 | Build Gate 1A end-to-end test | M1 Demand to Plan | type:test,priority:P0,risk:high,size:L,status:blocked | AF-104,AF-105,AF-106,AF-107,AF-108,AF-109 |
| AF-201 | Register GitHub App and verify webhook signature | M2 Plan to Draft PR | type:integration,type:security,priority:P0,risk:high,size:M,status:blocked | AF-102 |
| AF-202 | Implement GitHub MCP read tools | M2 Plan to Draft PR | type:mcp,priority:P0,risk:medium,size:L,status:blocked | AF-201 |
| AF-203 | Implement repository knowledge ingestion | M2 Plan to Draft PR | type:rag,priority:P0,size:L,status:blocked | AF-202,AF-106 |
| AF-204 | Implement local Docker sandbox baseline | M2 Plan to Draft PR | type:sandbox,type:security,priority:P0,risk:high,size:L,status:blocked | AF-102 |
| AF-205 | Implement Executor Agent contract | M2 Plan to Draft PR | type:agent-runtime,pack:delivery,priority:P0,risk:high,size:L,status:blocked | AF-107,AF-204 |
| AF-206 | Implement Reviewer Agent contract | M2 Plan to Draft PR | type:agent-runtime,pack:delivery,priority:P0,size:L,status:blocked | AF-205 |
| AF-207 | Implement deterministic Policy Gate v0 | M2 Plan to Draft PR | type:security,type:policy,priority:P0,risk:high,size:L,status:blocked | AF-107 |
| AF-208 | Implement GitHub draft pull request tool | M2 Plan to Draft PR | type:mcp,type:integration,priority:P0,risk:high,size:L,status:blocked | AF-202,AF-205,AF-206,AF-207 |
| AF-209 | Implement webhook and tool-call idempotency | M2 Plan to Draft PR | type:reliability,priority:P0,risk:high,size:L,status:blocked | AF-201,AF-208 |
| AF-210 | Build Gate 1B end-to-end test | M2 Plan to Draft PR | type:test,priority:P0,risk:high,size:XL,status:blocked | AF-203,AF-204,AF-205,AF-206,AF-207,AF-208,AF-209 |
| AF-211 | Record Gate 1 demo and evidence report | M2 Plan to Draft PR | type:docs,type:demo,priority:P0,size:M,status:blocked | AF-110,AF-210 |
| AF-301 | Bootstrap Temporal workflow and worker | M3 Reliable Runtime | type:workflow-runtime,priority:P0,risk:high,size:L,status:blocked | AF-210 |
| AF-302 | Enforce runtime state ownership boundaries | M3 Reliable Runtime | type:architecture,type:reliability,priority:P0,risk:high,size:M,status:blocked | AF-301 |
| AF-303 | Add LangGraph PostgresSaver checkpoints | M3 Reliable Runtime | type:agent-runtime,type:reliability,priority:P0,size:L,status:blocked | AF-302 |
| AF-304 | Implement durable clarification signal | M3 Reliable Runtime | type:workflow-runtime,priority:P0,size:M,status:blocked | AF-301,AF-108 |
| AF-305 | Implement durable approval signal | M3 Reliable Runtime | type:workflow-runtime,type:security,priority:P0,risk:high,size:M,status:blocked | AF-301,AF-207 |
| AF-306 | Define activity retry and timeout policies | M3 Reliable Runtime | type:reliability,priority:P0,risk:high,size:M,status:blocked | AF-301 |
| AF-307 | Implement idempotency ledger | M3 Reliable Runtime | type:reliability,type:database,priority:P0,risk:high,size:L,status:blocked | AF-209,AF-301 |
| AF-308 | Implement Saga compensation | M3 Reliable Runtime | type:reliability,priority:P1,risk:high,size:L,status:blocked | AF-306,AF-307 |
| AF-309 | Create kill-worker fault injection harness | M3 Reliable Runtime | type:test,type:reliability,priority:P0,risk:high,size:L,status:blocked | AF-303,AF-304,AF-305,AF-307 |
| AF-310 | Implement LiteLLM model gateway | M3 Reliable Runtime | type:model-gateway,priority:P0,size:L,status:blocked | AF-109 |
| AF-311 | Implement circuit breaker and fallback | M3 Reliable Runtime | type:model-gateway,type:reliability,priority:P0,risk:high,size:L,status:blocked | AF-310 |
| AF-312 | Publish Gate 2 reliability report and blog | M3 Reliable Runtime | type:docs,type:demo,priority:P0,size:L,status:blocked | AF-309,AF-311 |
| AF-401 | Implement tenant domain and isolation filter | M4 Governance & Security | type:security,type:backend,priority:P0,risk:high,size:L,status:blocked | AF-103 |
| AF-402 | Integrate OIDC authentication | M4 Governance & Security | type:security,type:identity,priority:P0,risk:high,size:L,status:blocked | AF-401 |
| AF-403 | Implement RBAC | M4 Governance & Security | type:security,type:rbac,priority:P0,risk:high,size:L,status:blocked | AF-402 |
| AF-404 | Implement contextual policy rules | M4 Governance & Security | type:security,type:policy,priority:P0,risk:high,size:L,status:blocked | AF-403,AF-207 |
| AF-405 | Implement append-only audit log | M4 Governance & Security | type:security,type:audit,priority:P0,risk:high,size:L,status:blocked | AF-403,AF-404 |
| AF-406 | Implement MCP registry with scopes | M4 Governance & Security | type:mcp,type:security,priority:P0,risk:high,size:L,status:blocked | AF-202,AF-403,AF-404 |
| AF-407 | Harden Docker sandbox | M4 Governance & Security | type:sandbox,type:security,priority:P0,risk:high,size:L,status:blocked | AF-204 |
| AF-408 | Implement prompt injection detection | M4 Governance & Security | type:security,type:agent-safety,priority:P0,risk:high,size:L,status:blocked | AF-404,AF-405,AF-406 |
| AF-409 | Build cross-tenant isolation suite | M4 Governance & Security | type:test,type:security,priority:P0,risk:high,size:L,status:blocked | AF-401,AF-403,AF-405 |
| AF-410 | Implement immutable prompt versioning | M4 Governance & Security | type:control-plane,priority:P1,size:M,status:blocked | AF-103 |
| AF-411 | Implement immutable workflow versioning | M4 Governance & Security | type:control-plane,priority:P1,size:M,status:blocked | AF-103,AF-301 |
| AF-412 | Build governance security regression suite | M4 Governance & Security | type:test,type:security,priority:P0,risk:high,size:XL,status:blocked | AF-403,AF-404,AF-405,AF-406,AF-407,AF-408,AF-409 |
| AF-413 | Record Gate 3 governance demo | M4 Governance & Security | type:docs,type:demo,priority:P0,size:M,status:blocked | AF-412 |
| AF-501 | Create Golden Dataset framework | M5 Evaluation & Deployment | type:evaluation,priority:P0,size:L,status:blocked | AF-410,AF-411 |
| AF-502 | Select SWE-bench Verified Python subset | M5 Evaluation & Deployment | type:evaluation,priority:P1,size:M,status:blocked | AF-501 |
| AF-503 | Create security injection dataset | M5 Evaluation & Deployment | type:evaluation,type:security,priority:P0,risk:high,size:L,status:blocked | AF-408,AF-501 |
| AF-504 | Create historical bug dataset | M5 Evaluation & Deployment | type:evaluation,priority:P1,size:M,status:blocked | AF-501 |
| AF-505 | Implement single-agent baseline | M5 Evaluation & Deployment | type:evaluation,priority:P1,size:L,status:blocked | AF-501 |
| AF-506 | Implement evaluation metrics and report | M5 Evaluation & Deployment | type:evaluation,priority:P0,size:L,status:blocked | AF-502,AF-503,AF-504,AF-505 |
| AF-507 | Add prompt regression gate to CI | M5 Evaluation & Deployment | type:evaluation,type:ci,priority:P0,risk:high,size:L,status:blocked | AF-506 |
| AF-508 | Instrument system traces with OTel | M5 Evaluation & Deployment | type:observability,priority:P0,size:L,status:blocked | AF-301,AF-406 |
| AF-509 | Expose Prometheus metrics | M5 Evaluation & Deployment | type:observability,priority:P0,size:M,status:blocked | AF-508 |
| AF-510 | Build Grafana dashboards | M5 Evaluation & Deployment | type:observability,priority:P0,size:M,status:blocked | AF-509,AF-506 |
| AF-511 | Run 100-concurrent-user load test | M5 Evaluation & Deployment | type:performance,type:test,priority:P0,risk:medium,size:L,status:blocked | AF-509 |
| AF-512 | Create k3s demo environment | M5 Evaluation & Deployment | type:infra,priority:P1,risk:medium,size:L,status:blocked | AF-413 |
| AF-513 | Create Helm chart | M5 Evaluation & Deployment | type:infra,priority:P0,size:L,status:blocked | AF-512 |
| AF-514 | Implement read-only workflow run graph | M5 Evaluation & Deployment | type:frontend,priority:P1,size:L,status:blocked | AF-508 |
| AF-515 | Build thin Personal Workbench flows | M5 Evaluation & Deployment | pack:personal,priority:P2,size:L,status:blocked | AF-513,AF-514 |
| AF-516 | Complete README, reports and demo package | M5 Evaluation & Deployment | type:docs,type:demo,priority:P0,size:L,status:blocked | AF-506,AF-510,AF-511,AF-513 |
| AF-517 | Execute Gate 4 final acceptance | M5 Evaluation & Deployment | type:release,priority:P0,risk:high,size:L,status:blocked | AF-507,AF-510,AF-511,AF-513,AF-516 |
| AF-R01 | Build single-scenario OpsPilot simulation | Post-MVP Roadmap | type:roadmap,pack:opspilot,priority:P3,size:XL,status:blocked | AF-517 |
| AF-R02 | Add optional vLLM fallback | Post-MVP Roadmap | type:roadmap,type:model-gateway,priority:P3,size:L,status:blocked | AF-517 |
| AF-R03 | Add MCP integrations from dogfooding | Post-MVP Roadmap | type:roadmap,type:mcp,priority:P3,size:L,status:blocked | AF-515 |

## Detailed Issue Bodies

### AF-000 — Establish Phase 0 documentation index

**Milestone:** M0 Engineering System

**Labels:** `type:docs,priority:P0,size:S,status:ready`

## Objective

创建统一文档入口、阅读顺序和状态声明。

## Acceptance Criteria

- README 链接有效；明确当前无业务代码；禁止虚构已完成指标。

## Dependencies

`None`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-001 — Approve project charter

**Milestone:** M0 Engineering System

**Labels:** `type:docs,type:governance,priority:P0,size:S,status:ready`

## Objective

冻结使命、范围、成功标准和角色。

## Acceptance Criteria

- Charter 与 v2.0 一致；明确做/不做；具备变更控制。

## Dependencies

`AF-000`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-002 — Approve architecture baseline

**Milestone:** M0 Engineering System

**Labels:** `type:architecture,priority:P0,risk:high,size:M,status:ready`

## Objective

定义模块化单体、容器、状态所有权和信任边界。

## Acceptance Criteria

- LangGraph/Temporal 边界、State Ownership、Idempotency Contract 明确。

## Dependencies

`AF-001`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-003 — Approve quality strategies

**Milestone:** M0 Engineering System

**Labels:** `type:test,type:security,priority:P0,risk:high,size:M,status:ready`

## Objective

建立测试、安全、可靠性和评测基线。

## Acceptance Criteria

- 每类策略有测试层级、Gate、证据和停止条件。

## Dependencies

`AF-002`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-004 — Establish GitHub governance

**Milestone:** M0 Engineering System

**Labels:** `type:governance,priority:P0,size:M,status:ready`

## Objective

建立 Labels、Milestones、Issue/PR 模板和分支策略。

## Acceptance Criteria

- One Issue One PR；Human Merge；模板可用。

## Dependencies

`AF-001`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-005 — Establish AI collaboration protocol

**Milestone:** M0 Engineering System

**Labels:** `type:docs,type:ai-process,priority:P0,size:M,status:ready`

## Objective

约束 AI 多月持续开发。

## Acceptance Criteria

- 定义会话启动、设计、测试、实现、Handoff 和停止条件。

## Dependencies

`AF-001`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-006 — Accept initial ADR set

**Milestone:** M0 Engineering System

**Labels:** `type:architecture,priority:P0,size:M,status:ready`

## Objective

把冻结范围转化为 ADR。

## Acceptance Criteria

- 至少 12 个 ADR 标记 Accepted。

## Dependencies

`AF-002`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-007 — Create configuration placeholder contract

**Milestone:** M0 Engineering System

**Labels:** `type:security,type:docs,priority:P0,size:S,status:ready`

## Objective

定义配置项，不写真实密钥。

## Acceptance Criteria

- .env.example 全为占位符；配置所有权明确。

## Dependencies

`AF-003`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-008 — Prepare documentation-only repository scaffold

**Milestone:** M0 Engineering System

**Labels:** `type:docs,type:repo,priority:P0,size:S,status:ready`

## Objective

创建文档目录和 GitHub 模板，不写业务代码。

## Acceptance Criteria

- 仓库只含文档/config templates；manifest 验证无业务代码。

## Dependencies

`AF-000,AF-004,AF-007`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-101 — Create modular monolith application skeleton

**Milestone:** M1 Demand to Plan

**Labels:** `type:backend,priority:P0,size:M,status:blocked`

## Objective

建立 FastAPI 模块边界和最小 health contract。

## Acceptance Criteria

- 模块目录存在；只有骨架接口；测试先行。

## Dependencies

`AF-008`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-102 — Create Docker Compose foundation

**Milestone:** M1 Demand to Plan

**Labels:** `type:infra,priority:P0,size:M,status:blocked`

## Objective

建立 Core、PostgreSQL、Redis 本地依赖基础。

## Acceptance Criteria

- 一条命令启动；healthcheck 通过；配置来自占位符。

## Dependencies

`AF-101`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-103 — Define initial domain model and migrations

**Milestone:** M1 Demand to Plan

**Labels:** `type:backend,type:architecture,priority:P0,size:M,status:blocked`

## Objective

定义 Tenant、Workflow、Run、Step、Approval、Audit 基础模型。

## Acceptance Criteria

- 模型有 tenant_id；版本不可覆盖；迁移测试通过。

## Dependencies

`AF-101,AF-102`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-104 — Implement Intake Agent contract

**Milestone:** M1 Demand to Plan

**Labels:** `type:agent-runtime,pack:delivery,priority:P0,size:M,status:blocked`

## Objective

标准化 PRD/Bug/Issue 并生成幂等输入。

## Acceptance Criteria

- 结构化 Schema；重复输入识别；单元测试通过。

## Dependencies

`AF-103`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-105 — Implement Clarifier Agent contract

**Milestone:** M1 Demand to Plan

**Labels:** `type:agent-runtime,pack:delivery,priority:P0,size:M,status:blocked`

## Objective

识别缺失信息并形成澄清问题。

## Acceptance Criteria

- 缺失信息、问题和完成判定结构化；HITL 契约测试。

## Dependencies

`AF-104`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-106 — Implement Context Agent retrieval contract

**Milestone:** M1 Demand to Plan

**Labels:** `type:rag,pack:delivery,priority:P0,size:L,status:blocked`

## Objective

检索代码、文档、ADR 和历史 PR。

## Acceptance Criteria

- 输出 Context Package 和引用；无引用结论被标记。

## Dependencies

`AF-103`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-107 — Implement Planner Agent contract

**Milestone:** M1 Demand to Plan

**Labels:** `type:agent-runtime,pack:delivery,priority:P0,size:L,status:blocked`

## Objective

生成架构方案、任务拆分、风险和预算。

## Acceptance Criteria

- Plan Schema 稳定；风险和工具可验证；无副作用。

## Dependencies

`AF-105,AF-106`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-108 — Implement clarification HITL interface

**Milestone:** M1 Demand to Plan

**Labels:** `type:workflow-runtime,priority:P0,size:M,status:blocked`

## Objective

支持 Clarifier 发起和接收人工澄清。

## Acceptance Criteria

- 请求可暂停；回复关联 run；重复回复被拒。

## Dependencies

`AF-105`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-109 — Add initial Langfuse tracing and cost fields

**Milestone:** M1 Demand to Plan

**Labels:** `type:observability,priority:P1,size:M,status:blocked`

## Objective

记录 Agent 节点、Prompt、Token 和成本。

## Acceptance Criteria

- 每节点有 run/agent/prompt/model/token/latency；Secret 脱敏。

## Dependencies

`AF-104,AF-105,AF-106,AF-107`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-110 — Build Gate 1A end-to-end test

**Milestone:** M1 Demand to Plan

**Labels:** `type:test,priority:P0,risk:high,size:L,status:blocked`

## Objective

验证真实需求到带证据方案。

## Acceptance Criteria

- 固定 Fixture 可重复；失败点可定位；输出 Trace。

## Dependencies

`AF-104,AF-105,AF-106,AF-107,AF-108,AF-109`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-201 — Register GitHub App and verify webhook signature

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:integration,type:security,priority:P0,risk:high,size:M,status:blocked`

## Objective

建立 GitHub 事件入口。

## Acceptance Criteria

- 签名、时间窗口、防重放和失败审计测试通过。

## Dependencies

`AF-102`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-202 — Implement GitHub MCP read tools

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:mcp,priority:P0,risk:medium,size:L,status:blocked`

## Objective

提供仓库、Issue、PR、Diff 只读工具。

## Acceptance Criteria

- Tool Schema、Scope、Timeout、错误映射和审计完整。

## Dependencies

`AF-201`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-203 — Implement repository knowledge ingestion

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:rag,priority:P0,size:L,status:blocked`

## Objective

将仓库文档和代码索引到 pgvector。

## Acceptance Criteria

- 增量索引；tenant/repo 隔离；检索基准通过。

## Dependencies

`AF-202,AF-106`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-204 — Implement local Docker sandbox baseline

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:sandbox,type:security,priority:P0,risk:high,size:L,status:blocked`

## Objective

提供非 root、资源受限、临时工作区执行环境。

## Acceptance Criteria

- 禁止 Docker socket；网络可控；超时和清理测试通过。

## Dependencies

`AF-102`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-205 — Implement Executor Agent contract

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:agent-runtime,pack:delivery,priority:P0,risk:high,size:L,status:blocked`

## Objective

根据批准 Plan 在沙箱改码和测试。

## Acceptance Criteria

- 只调用允许工具；产生 Patch/Test/Evidence；失败结构化。

## Dependencies

`AF-107,AF-204`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-206 — Implement Reviewer Agent contract

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:agent-runtime,pack:delivery,priority:P0,size:L,status:blocked`

## Objective

汇总 Plan、Patch、测试和证据。

## Acceptance Criteria

- 输出 Decision、Findings、Approval Need；引用可追踪。

## Dependencies

`AF-205`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-207 — Implement deterministic Policy Gate v0

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:security,type:policy,priority:P0,risk:high,size:L,status:blocked`

## Objective

在 Executor 前做权限、成本和风险规则。

## Acceptance Criteria

- LLM 不可覆盖规则；拒绝有审计；规则有单测。

## Dependencies

`AF-107`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-208 — Implement GitHub draft pull request tool

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:mcp,type:integration,priority:P0,risk:high,size:L,status:blocked`

## Objective

创建 Branch、Commit 和 Draft PR。

## Acceptance Criteria

- 写操作有 Scope、审批、幂等和远端 Marker。

## Dependencies

`AF-202,AF-205,AF-206,AF-207`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-209 — Implement webhook and tool-call idempotency

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:reliability,priority:P0,risk:high,size:L,status:blocked`

## Objective

防止重复事件和外部副作用。

## Acceptance Criteria

- 唯一键含 tenant/run/step/tool/args hash；重复 PR 数 0。

## Dependencies

`AF-201,AF-208`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-210 — Build Gate 1B end-to-end test

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:test,priority:P0,risk:high,size:XL,status:blocked`

## Objective

验证方案到 Draft PR。

## Acceptance Criteria

- 测试仓库完成沙箱改码、Review、审批和 Draft PR。

## Dependencies

`AF-203,AF-204,AF-205,AF-206,AF-207,AF-208,AF-209`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-211 — Record Gate 1 demo and evidence report

**Milestone:** M2 Plan to Draft PR

**Labels:** `type:docs,type:demo,priority:P0,size:M,status:blocked`

## Objective

固化 Gate 1 证据。

## Acceptance Criteria

- 视频、Trace、成本和失败说明归档；不夸大。

## Dependencies

`AF-110,AF-210`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-301 — Bootstrap Temporal workflow and worker

**Milestone:** M3 Reliable Runtime

**Labels:** `type:workflow-runtime,priority:P0,risk:high,size:L,status:blocked`

## Objective

建立外层 durable workflow。

## Acceptance Criteria

- Workflow/Activity 分离；replay-safe；测试环境可启动。

## Dependencies

`AF-210`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-302 — Enforce runtime state ownership boundaries

**Milestone:** M3 Reliable Runtime

**Labels:** `type:architecture,type:reliability,priority:P0,risk:high,size:M,status:blocked`

## Objective

分离 Temporal、LangGraph、PostgreSQL、Redis 状态。

## Acceptance Criteria

- 无双重 retry；状态表与实现一致。

## Dependencies

`AF-301`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-303 — Add LangGraph PostgresSaver checkpoints

**Milestone:** M3 Reliable Runtime

**Labels:** `type:agent-runtime,type:reliability,priority:P0,size:L,status:blocked`

## Objective

持久化 Agent 图状态。

## Acceptance Criteria

- 节点后 checkpoint；resume 测试；tenant/run 唯一定位。

## Dependencies

`AF-302`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-304 — Implement durable clarification signal

**Milestone:** M3 Reliable Runtime

**Labels:** `type:workflow-runtime,priority:P0,size:M,status:blocked`

## Objective

澄清等待由 Temporal Signal 管理。

## Acceptance Criteria

- 跨 worker 重启等待和恢复；重复 signal 可处理。

## Dependencies

`AF-301,AF-108`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-305 — Implement durable approval signal

**Milestone:** M3 Reliable Runtime

**Labels:** `type:workflow-runtime,type:security,priority:P0,risk:high,size:M,status:blocked`

## Objective

高风险审批可长时间等待。

## Acceptance Criteria

- 批准/拒绝持久；过期和重复决策有测试。

## Dependencies

`AF-301,AF-207`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-306 — Define activity retry and timeout policies

**Milestone:** M3 Reliable Runtime

**Labels:** `type:reliability,priority:P0,risk:high,size:M,status:blocked`

## Objective

按错误类型设置 retry/timeout。

## Acceptance Criteria

- 429、5xx、权限、测试失败和不可逆错误策略不同。

## Dependencies

`AF-301`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-307 — Implement idempotency ledger

**Milestone:** M3 Reliable Runtime

**Labels:** `type:reliability,type:database,priority:P0,risk:high,size:L,status:blocked`

## Objective

持久记录外部副作用执行。

## Acceptance Criteria

- 唯一约束、状态机、结果重用和并发测试通过。

## Dependencies

`AF-209,AF-301`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-308 — Implement Saga compensation

**Milestone:** M3 Reliable Runtime

**Labels:** `type:reliability,priority:P1,risk:high,size:L,status:blocked`

## Objective

补偿 Branch、Draft PR 和临时资源。

## Acceptance Criteria

- 补偿可重复；失败升级人工；审计完整。

## Dependencies

`AF-306,AF-307`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-309 — Create kill-worker fault injection harness

**Milestone:** M3 Reliable Runtime

**Labels:** `type:test,type:reliability,priority:P0,risk:high,size:L,status:blocked`

## Objective

重复终止 worker 并测量恢复。

## Acceptance Criteria

- 20 次测试；记录恢复和重复副作用；可复现。

## Dependencies

`AF-303,AF-304,AF-305,AF-307`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-310 — Implement LiteLLM model gateway

**Milestone:** M3 Reliable Runtime

**Labels:** `type:model-gateway,priority:P0,size:L,status:blocked`

## Objective

统一模型接口、预算和成本。

## Acceptance Criteria

- 主/备配置为 Secret 引用；记录模型版本和成本。

## Dependencies

`AF-109`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-311 — Implement circuit breaker and fallback

**Milestone:** M3 Reliable Runtime

**Labels:** `type:model-gateway,type:reliability,priority:P0,risk:high,size:L,status:blocked`

## Objective

主模型故障时熔断降级。

## Acceptance Criteria

- Closed/Open/Half-Open 测试；Trace 显示路由链。

## Dependencies

`AF-310`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-312 — Publish Gate 2 reliability report and blog

**Milestone:** M3 Reliable Runtime

**Labels:** `type:docs,type:demo,priority:P0,size:L,status:blocked`

## Objective

形成可靠性证据和语义/源码研究记录。

## Acceptance Criteria

- 报告含环境、20 次结果、限制和真实证据。

## Dependencies

`AF-309,AF-311`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-401 — Implement tenant domain and isolation filter

**Milestone:** M4 Governance & Security

**Labels:** `type:security,type:backend,priority:P0,risk:high,size:L,status:blocked`

## Objective

所有业务访问绑定 tenant。

## Acceptance Criteria

- 缺失 tenant 被拒；查询自动过滤；隔离测试准备完成。

## Dependencies

`AF-103`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-402 — Integrate OIDC authentication

**Milestone:** M4 Governance & Security

**Labels:** `type:security,type:identity,priority:P0,risk:high,size:L,status:blocked`

## Objective

使用外部 OIDC，不自建密码。

## Acceptance Criteria

- Issuer/Client 为占位配置；Token 验证测试通过。

## Dependencies

`AF-401`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-403 — Implement RBAC

**Milestone:** M4 Governance & Security

**Labels:** `type:security,type:rbac,priority:P0,risk:high,size:L,status:blocked`

## Objective

建立 Admin/Developer/Reviewer/Security/DevOps/Viewer。

## Acceptance Criteria

- API 和 Tool 权限映射；拒绝测试完整。

## Dependencies

`AF-402`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-404 — Implement contextual policy rules

**Milestone:** M4 Governance & Security

**Labels:** `type:security,type:policy,priority:P0,risk:high,size:L,status:blocked`

## Objective

结合角色、tenant、repo、environment、risk、approval。

## Acceptance Criteria

- 不构建通用 ABAC；确定性规则可解释。

## Dependencies

`AF-403,AF-207`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-405 — Implement append-only audit log

**Milestone:** M4 Governance & Security

**Labels:** `type:security,type:audit,priority:P0,risk:high,size:L,status:blocked`

## Objective

记录权限、审批、工具和安全事件。

## Acceptance Criteria

- 普通用户不可删；actor/action/resource/decision/reason/trace 完整。

## Dependencies

`AF-403,AF-404`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-406 — Implement MCP registry with scopes

**Milestone:** M4 Governance & Security

**Labels:** `type:mcp,type:security,priority:P0,risk:high,size:L,status:blocked`

## Objective

统一注册工具、版本、Scope 和风险。

## Acceptance Criteria

- 未注册/未授权工具被拒；Token 不透传；审计完整。

## Dependencies

`AF-202,AF-403,AF-404`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-407 — Harden Docker sandbox

**Milestone:** M4 Governance & Security

**Labels:** `type:sandbox,type:security,priority:P0,risk:high,size:L,status:blocked`

## Objective

强化文件系统、网络和资源限制。

## Acceptance Criteria

- 负向测试通过；Secret 不进 workspace；自动清理。

## Dependencies

`AF-204`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-408 — Implement prompt injection detection

**Milestone:** M4 Governance & Security

**Labels:** `type:security,type:agent-safety,priority:P0,risk:high,size:L,status:blocked`

## Objective

识别 RAG 中诱导越权内容。

## Acceptance Criteria

- 注入被标记；Policy 拒绝高危工具；审计有证据。

## Dependencies

`AF-404,AF-405,AF-406`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-409 — Build cross-tenant isolation suite

**Milestone:** M4 Governance & Security

**Labels:** `type:test,type:security,priority:P0,risk:high,size:L,status:blocked`

## Objective

证明 Tenant A 无法访问 B。

## Acceptance Criteria

- API、DB、RAG、Trace、Tool 全覆盖。

## Dependencies

`AF-401,AF-403,AF-405`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-410 — Implement immutable prompt versioning

**Milestone:** M4 Governance & Security

**Labels:** `type:control-plane,priority:P1,size:M,status:blocked`

## Objective

Prompt 不可原地修改，Run 固定版本。

## Acceptance Criteria

- 新版本、回滚、审计和 run 关联测试通过。

## Dependencies

`AF-103`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-411 — Implement immutable workflow versioning

**Milestone:** M4 Governance & Security

**Labels:** `type:control-plane,priority:P1,size:M,status:blocked`

## Objective

Workflow 版本不可变。

## Acceptance Criteria

- 旧 Run 可重放；升级不影响在途流程。

## Dependencies

`AF-103,AF-301`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-412 — Build governance security regression suite

**Milestone:** M4 Governance & Security

**Labels:** `type:test,type:security,priority:P0,risk:high,size:XL,status:blocked`

## Objective

统一验证 RBAC、Policy、Audit、Injection、Sandbox。

## Acceptance Criteria

- 正向/负向/越权/重放测试可重复。

## Dependencies

`AF-403,AF-404,AF-405,AF-406,AF-407,AF-408,AF-409`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-413 — Record Gate 3 governance demo

**Milestone:** M4 Governance & Security

**Labels:** `type:docs,type:demo,priority:P0,size:M,status:blocked`

## Objective

固化注入拦截和跨租户证据。

## Acceptance Criteria

- 视频、测试日志、审计和限制完整。

## Dependencies

`AF-412`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-501 — Create Golden Dataset framework

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,priority:P0,size:L,status:blocked`

## Objective

定义 Dataset、Case、Expected、Run、Metric。

## Acceptance Criteria

- 可版本化、可重复、可比较；无真实 Secret。

## Dependencies

`AF-410,AF-411`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-502 — Select SWE-bench Verified Python subset

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,priority:P1,size:M,status:blocked`

## Objective

选择 10–15 个真实 Issue-Patch。

## Acceptance Criteria

- 选择标准、许可证、成本和限制有文档。

## Dependencies

`AF-501`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-503 — Create security injection dataset

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,type:security,priority:P0,risk:high,size:L,status:blocked`

## Objective

创建 15–20 个真值安全案例。

## Acceptance Criteria

- 覆盖 SQL 注入、Secret、Token、越权、Prompt Injection。

## Dependencies

`AF-408,AF-501`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-504 — Create historical bug dataset

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,priority:P1,size:M,status:blocked`

## Objective

整理 XueMai/SynTour 历史问题。

## Acceptance Criteria

- 5–10 个脱敏 Case；真值、修复和来源完整。

## Dependencies

`AF-501`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-505 — Implement single-agent baseline

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,priority:P1,size:L,status:blocked`

## Objective

建立 Full AegisFlow 对照。

## Acceptance Criteria

- 同任务、同模型、同预算；比较完成率/成本/越权/延迟。

## Dependencies

`AF-501`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-506 — Implement evaluation metrics and report

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,priority:P0,size:L,status:blocked`

## Objective

计算完成率、Tool Success、检出、误报、Patch、成本、p95。

## Acceptance Criteria

- 报告显示分子分母；小样本不只写百分比。

## Dependencies

`AF-502,AF-503,AF-504,AF-505`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-507 — Add prompt regression gate to CI

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:evaluation,type:ci,priority:P0,risk:high,size:L,status:blocked`

## Objective

Prompt 退化时阻止发布。

## Acceptance Criteria

- 阈值配置化；失败有报告；可回滚。

## Dependencies

`AF-506`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-508 — Instrument system traces with OTel

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:observability,priority:P0,size:L,status:blocked`

## Objective

追踪 API、Temporal、DB、MCP、Sandbox。

## Acceptance Criteria

- trace/run/tenant 贯通；敏感字段脱敏。

## Dependencies

`AF-301,AF-406`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-509 — Expose Prometheus metrics

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:observability,priority:P0,size:M,status:blocked`

## Objective

暴露成功、失败、成本、延迟、队列和资源。

## Acceptance Criteria

- 命名、Label Cardinality 和测试符合规范。

## Dependencies

`AF-508`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-510 — Build Grafana dashboards

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:observability,priority:P0,size:M,status:blocked`

## Objective

展示 Gate 数字。

## Acceptance Criteria

- 成功率、成本、p95、失败节点、Fallback、人工介入可见。

## Dependencies

`AF-509,AF-506`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-511 — Run 100-concurrent-user load test

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:performance,type:test,priority:P0,risk:medium,size:L,status:blocked`

## Objective

Locust 测试控制面。

## Acceptance Criteria

- 环境、场景、p50/p95/p99、错误率、资源和限制有报告。

## Dependencies

`AF-509`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-512 — Create k3s demo environment

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:infra,priority:P1,risk:medium,size:L,status:blocked`

## Objective

建立演示集群。

## Acceptance Criteria

- 配置无 Secret；Core/Worker/Observability 可运行。

## Dependencies

`AF-413`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-513 — Create Helm chart

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:infra,priority:P0,size:L,status:blocked`

## Objective

打包演示部署。

## Acceptance Criteria

- values 为占位符；upgrade/rollback 测试通过。

## Dependencies

`AF-512`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-514 — Implement read-only workflow run graph

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:frontend,priority:P1,size:L,status:blocked`

## Objective

只读展示节点状态。

## Acceptance Criteria

- 节点、状态、耗时、Trace 和失败原因可见。

## Dependencies

`AF-508`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-515 — Build thin Personal Workbench flows

**Milestone:** M5 Evaluation & Deployment

**Labels:** `pack:personal,priority:P2,size:L,status:blocked`

## Objective

接入 XueMai、SynTour、Omni-Assistant 和实习跟踪。

## Acceptance Criteria

- 只复用平台能力；不新增通用助手方向。

## Dependencies

`AF-513,AF-514`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-516 — Complete README, reports and demo package

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:docs,type:demo,priority:P0,size:L,status:blocked`

## Objective

生成面试证据包。

## Acceptance Criteria

- 中英 README、Architecture、ADR、Evaluation、Reliability、Load、Threat Model 齐全。

## Dependencies

`AF-506,AF-510,AF-511,AF-513`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-517 — Execute Gate 4 final acceptance

**Milestone:** M5 Evaluation & Deployment

**Labels:** `type:release,priority:P0,risk:high,size:L,status:blocked`

## Objective

完成四个必做演示和 Gate 验收。

## Acceptance Criteria

- 现场复现；结果记录；未达项不得伪装。

## Dependencies

`AF-507,AF-510,AF-511,AF-513,AF-516`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-R01 — Build single-scenario OpsPilot simulation

**Milestone:** Post-MVP Roadmap

**Labels:** `type:roadmap,pack:opspilot,priority:P3,size:XL,status:blocked`

## Objective

Gate 1–4 后增加一个模拟事故场景。

## Acceptance Criteria

- 只用模拟数据；不改主叙事；独立 ADR。

## Dependencies

`AF-517`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-R02 — Add optional vLLM fallback

**Milestone:** Post-MVP Roadmap

**Labels:** `type:roadmap,type:model-gateway,priority:P3,size:L,status:blocked`

## Objective

有 GPU 时加入本地模型。

## Acceptance Criteria

- 可选开关；不阻塞系统；成本和性能有测量。

## Dependencies

`AF-517`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---

### AF-R03 — Add MCP integrations from dogfooding

**Milestone:** Post-MVP Roadmap

**Labels:** `type:roadmap,type:mcp,priority:P3,size:L,status:blocked`

## Objective

只按真实需求增加工具。

## Acceptance Criteria

- 每个工具有场景、Scope、Policy、Audit 和测试。

## Dependencies

`AF-515`

## Required Process

- [ ] Read relevant architecture and ADR documents
- [ ] Create or update Design Note
- [ ] Define tests before implementation
- [ ] Confirm security impact
- [ ] Implement the smallest acceptable change
- [ ] Run tests and quality gates
- [ ] Update documentation and traceability matrix
- [ ] Open one PR linked to this Issue
- [ ] Wait for human review and merge

## Secret Handling

Use placeholders only. Do not request or expose real credentials in this Issue.

---
