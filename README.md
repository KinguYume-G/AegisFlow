# AegisFlow — Production-Grade Agent Control Plane

> **Enterprise Software Delivery Agent Platform**

> **Mandatory onboarding / 强制入门：在阅读或修改仓库内容前，先阅读 [`START_HERE.md`](START_HERE.md)。**

AegisFlow 是一个生产级 Agent Control Plane。它负责企业 AI Agent 的可靠执行、工具权限、人工审批、评测、审计、可观测性与成本治理，并以 `DeliveryPack` 的“需求 → 交付”研发闭环验证平台能力。

## 当前阶段

**M1：AF-106 Context Agent Retrieval Contract Implementation**

Phase 0 已由 Project Owner / Human Reviewer 正式确认退出：PR #76 已人工审查并合并，AF-000–AF-008 已全部关闭并标记为 `status:verified`。56 个权威 Labels、7 个 Milestones 和 75 个 canonical Issues 保持为治理基线。

AF-101–AF-105 与插入的治理任务 CI-001 均已通过 Human Review/Merge 并标记为 `status:verified`；pytest/coverage、Core 镜像构建、PostgreSQL migration 验证与 main Branch Protection 门禁已经生效。AF-104–AF-110 Design Bundle v4 已通过 PR #84 Human Review/Merge；AF-106 已获批并进入实施，当前仅实现受限本地 Context 检索契约，不启动 AF-107。

## 不可改变的定位

> 我做的不是代码审查工具，是 Agent 控制平面。研发交付是压力最大的那个负载，所以我用它来证明底座。

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

## 当前状态

- [x] 产品方向冻结
- [x] 项目宪章、总任务书、架构、Roadmap、Milestones
- [x] GitHub Issue Backlog、Developer Guide、AI 协作规范
- [x] 测试、安全、可靠性、评测与威胁模型
- [x] ADR 集、Issue/PR 模板、配置占位符
- [x] GitHub 仓库与写权限确认，Phase 0 工程体系已推送
- [x] 56 个权威 Labels、7 个 Milestones、75 个 canonical Issues 导入
- [x] Phase 0 Exit PR 完成 Human Review 与 Human Merge
- [x] M0 人工确认完成，AF-000–AF-008 已关闭并验证
- [x] AF-101 实现 PR 完成 Human Review 与 Human Merge
- [x] AF-102 Design Note、Test Plan 与九项修正获人工批准
- [x] AF-102 实现 PR 完成 Human Review 与 Human Merge
- [x] CI-001 完成红灯/绿灯验证并启用 main Branch Protection
- [x] Project Owner 批准 AF-103 Design Note/Test Plan，并将 AF-103 调整为 `status:ready`
- [x] AF-103 实现及 migration compatibility 修复通过 CI、Human Review 与 Human Merge
- [x] AF-103 Issue #12 标记 `status:verified` 并关闭
- [x] AF-104–AF-110 Design Bundle v4 完成 Human Review/Merge
- [x] AF-104 获批并调整为 `status:ready`
- [x] AF-104 实现 PR 完成 CI、Human Review 与 Human Merge
- [x] AF-105 实现 PR 完成 CI、Human Review 与 Human Merge
- [ ] AF-106 实现 PR 完成 CI、Human Review 与 Human Merge

## 真实性规则

尚未实现或测量的能力不得写成已达成事实。`5 秒恢复`、`零重复副作用`、`100 并发`、`任务完成率`等在真实测试完成前只能标记为 TARGET。
