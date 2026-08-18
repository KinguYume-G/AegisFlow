# AegisFlow — Production-Oriented Agent Control Plane

> **Enterprise Software Delivery Agent Platform**

> **Mandatory onboarding / 强制入门：在阅读或修改仓库内容前，先阅读 [`START_HERE.md`](START_HERE.md)。**

AegisFlow is a production-oriented Agent Control Plane for reliable execution, tool authorization, human approval, evaluation, audit, observability, and cost governance. `DeliveryPack` validates the platform through a requirement-to-delivery workflow. The repository contains a verified local full-stack MVP and substantial production foundations; it is not yet production certified. / AegisFlow 是一个面向生产的 Agent Control Plane，负责企业 AI Agent 的可靠执行、工具权限、人工审批、评测、审计、可观测性与成本治理，并以 `DeliveryPack` 的“需求 → 交付”研发闭环验证平台能力。仓库已有经过验证的本地全栈 MVP 和较完整的生产化底座，但尚未完成生产认证。

## Current Phase / 当前阶段

**Post-MVP：AF-R04–AF-R08 Local Full-Stack MVP / 本地全栈 MVP 收口**

Phase 0 已由 Project Owner / Human Reviewer 正式确认退出：PR #76 已人工审查并合并，AF-000–AF-008 已全部关闭并标记为 `status:verified`。56 个权威 Labels、7 个 Milestones 和 75 个 canonical Issues 保持为治理基线。

M1–M5 and Gate 4 have been accepted by the Project Owner. AF-R01–AF-R03 are completed Post-MVP extensions. The active approved batch is AF-R04–AF-R08: a loopback-only Ollama profile, tenant-scoped Run API, production Delivery graph wiring, Temporal workflow, and Next.js developer/reviewer Console. GitHub writes remain dry-run by default and this batch does not constitute production certification. / M1–M5 与 Gate 4 已由 Project Owner 验收；AF-R01–AF-R03 已完成。当前获批批次为 AF-R04–AF-R08：回环限定的 Ollama 配置、租户级 Run API、生产 Delivery Graph 接线、Temporal 工作流以及 Next.js 开发者/审查者控制台。GitHub 写入默认保持 dry-run，本批次不代表生产认证。

## Frozen Positioning / 不可改变的定位

> This is not a code-review product; it is an Agent Control Plane. Software delivery is the stress workload used to prove the platform. / 我做的不是代码审查工具，是 Agent 控制平面。研发交付是压力最大的那个负载，所以我用它来证明底座。

唯一首发应用包是 `DeliveryPack`：

```text
需求 / PRD / Bug / GitHub Issue
  → Intake
  → Clarifier
  → Context
  → Planner
  → Policy Gate
  → Executor
  → Reviewer
  → Human Approval
  → Draft PR / 部署
  → Trace / Cost / Evaluation / Learning
```

六个命名 Agent 固定为：Intake、Clarifier、Context、Planner、Executor、Reviewer。不得新增平级 Agent，也不得把项目改造成 mini-CodeRabbit、通用聊天助手或 OpsPilot 主项目。

## 首次进入项目

任何开发者或 AI 第一次进入仓库时，先按顺序阅读：

1. [`START_HERE.md`](START_HERE.md)：所有人类贡献者与 AI Agent 的强制第一入口；
2. [`README.md`](README.md)：项目定位与当前阶段；
3. [`AGENTS.md`](AGENTS.md)：不可违反的协作与开发约束；
4. [`docs/index.md`](docs/index.md)：文档总入口、事实源、当前工作与任务导航。

完成这些入口文档后，再按照 `docs/index.md` 为当前任务加载相关 Issue、ADR、测试策略与最近 Handoff。

## 深入阅读顺序

1. [`docs/DESIGN_BLUEPRINT.md`](docs/DESIGN_BLUEPRINT.md)
2. [`docs/00_PROJECT_CHARTER.md`](docs/00_PROJECT_CHARTER.md)
3. [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md)
4. [`docs/adr/`](docs/adr/)
5. [`docs/03_ROADMAP.md`](docs/03_ROADMAP.md)
6. [`docs/04_MILESTONES.md`](docs/04_MILESTONES.md)
7. [`docs/05_GITHUB_ISSUE_BACKLOG.md`](docs/05_GITHUB_ISSUE_BACKLOG.md)
8. [`docs/06_DEVELOPER_GUIDE.md`](docs/06_DEVELOPER_GUIDE.md)
9. [`docs/index.md`](docs/index.md)

## 工程原则

- Documentation First
- Architecture First
- Test First
- Security by Default
- Small Iterations
- GitHub Driven
- One Issue, One Pull Request
- Human Review Required
- No Secrets in Git, Chat, Logs, Prompts, Issues or PRs

## Verified Snapshot / 已验证快照

- Gate 1B real GitHub Draft PR boundary: passed on `main`.
- Gate 2: 20/20 fault runs completed, duplicate effects 0, lost signals 0, p95 2972.42 ms.
- Gate 3: 83 security tests passed; tracked credential signatures 0.
- M5 load profile: 100 users, 1906 requests, 0 failures, aggregate p95 140 ms on an ephemeral GitHub runner.
- k3s/Helm, primary Model Gateway, Langfuse trace write/read, and protected Personal Workbench smokes passed with the limitations recorded in the final report.
- Full evidence, artifact identities, SHA-256 values, and limitations: [`docs/reports/GATE4_FINAL_ACCEPTANCE.md`](docs/reports/GATE4_FINAL_ACCEPTANCE.md).
- Local MVP observed one complete 10/10 Ollama + Docker Sandbox + separate Human Approval + dry-run Draft PR candidate path on 2026-08-18.
- Current backend regression: 633 passed, 1 protected real-GitHub test skipped; repository coverage gate passes at 90%.
- Current Console checks: 17 unit tests, lint, TypeScript and production build pass; local browser smoke passed, with two project-specific browser cases intentionally skipped per run.
- Final acceptance remains a Human decision / 最终验收仍由人工决定。

## Local Full-Stack MVP / 本地全栈 MVP

Prerequisites: Docker Desktop with Compose, Ollama listening on `127.0.0.1:11434`, and the selected local model already pulled. No real GitHub or model-provider Secret is required for this dry-run profile.

```powershell
Copy-Item .env.local-mvp.example .env.local-mvp
# Change the local-only database password and the two persona tokens.
docker compose --env-file .env.local-mvp -f compose.yaml -f compose.local-mvp.yaml up -d --build
```

After the health checks pass:

- Developer Console: <http://127.0.0.1:3000>
- Reviewer Console: <http://127.0.0.1:3001>
- Core API: <http://127.0.0.1:8000>

The demonstrated path is:

```text
PRD / Issue → Run → Temporal → LangGraph
→ Intake → Clarifier → Context → Planner → Policy
→ Executor → Sandbox Build/Test → Reviewer
→ separate Human Approval → dry-run Draft PR candidate
→ Evaluation + Trace + Cost + Audit
```

Stop the local stack without deleting its volumes:

```powershell
docker compose --env-file .env.local-mvp -f compose.yaml -f compose.local-mvp.yaml down
```

See [`docs/26_PRODUCTION_READINESS_PLAN.md`](docs/26_PRODUCTION_READINESS_PLAN.md) for the truthful current-state matrix, owner preparation checklist, repository cleanup boundaries and production roadmap.

## Truthfulness Rule / 真实性规则

尚未实现或测量的能力不得写成已达成事实。CI fixture、短时临时环境压测与单路 provider smoke 不得表述为生产质量、容量承诺或完整在线降级证明。
