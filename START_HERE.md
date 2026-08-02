# START HERE — AegisFlow Contributor & AI Onboarding / 从这里开始

> **Mandatory first read for every human contributor and AI agent. / 所有人类贡献者与 AI Agent 必须首先阅读本文。**

This is the onboarding entry point, not a replacement for the project’s authoritative product, architecture, or decision documents.
本文是入门入口，不替代项目的权威产品、架构或决策文档。

## Project Summary & Current Status / 项目概述与当前状态

- **AegisFlow** is a production-grade Agent Control Plane for reliable execution, tool governance, human approval, evaluation, audit, observability, and cost control. / AegisFlow 是面向可靠执行、工具治理、人工审批、评测、审计、可观测性与成本控制的生产级 Agent Control Plane。
- **DeliveryPack** is the only initial application pack. Its six fixed Agents are Intake, Clarifier, Context, Planner, Executor, and Reviewer. / DeliveryPack 是唯一首发应用包，固定包含 Intake、Clarifier、Context、Planner、Executor、Reviewer 六个 Agent。
- The repository is in **M1 / AF-103 Implementation**; AF-101, AF-102, and the CI-001 governance gate are verified. / 仓库处于 **M1 / AF-103 实施阶段**；AF-101、AF-102 与 CI-001 治理门均已验证。
- The canonical planning baseline contains 75 Issues in [`docs/05_GITHUB_ISSUE_BACKLOG.md`](docs/05_GITHUB_ISSUE_BACKLOG.md) and [`project/GITHUB_ISSUE_IMPORT.csv`](project/GITHUB_ISSUE_IMPORT.csv). `archive/` is not a current source of truth. / 正式规划基线为 75 条 Issue；`archive/` 不是当前事实源。
- GitHub import and M0 verification are complete. AF-101, AF-102, and CI-001 have been human-merged and verified; AF-103 Design Note/Test Plan v3 are approved and implementation is in progress. / GitHub 导入与 M0 验证已完成；AF-101、AF-102 与 CI-001 已人工合并并验证；AF-103 Design Note/Test Plan v3 已获批准并进入实施。

## Authoritative Reading Order / 权威阅读顺序

Read in this order before selecting work / 领取任务前按顺序阅读：

1. **This file / 本文件** — mandatory onboarding contract / 强制入门契约。
2. [`README.md`](README.md) — project positioning and current state / 项目定位与当前状态。
3. [`AGENTS.md`](AGENTS.md) — mandatory AI and contributor constraints / AI 与贡献者强制约束。
4. [`docs/index.md`](docs/index.md) — documentation map and task routing / 文档地图与任务导航。
5. The current Milestone, ready Issue, relevant ADRs, test strategy, and latest Handoff / 当前 Milestone、ready Issue、相关 ADR、测试策略与最近 Handoff。

When sources conflict, apply this unchanged precedence / 发生冲突时，按以下既定优先级裁决：

1. [`docs/DESIGN_BLUEPRINT.md`](docs/DESIGN_BLUEPRINT.md)
2. [`docs/00_PROJECT_CHARTER.md`](docs/00_PROJECT_CHARTER.md)
3. Accepted [`docs/adr/`](docs/adr/)
4. [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md)
5. Current Milestone and GitHub Issue / 当前 Milestone 与 GitHub Issue
6. Developer Guide, test strategies, and other active documents / Developer Guide、测试策略及其他活跃文档
7. Archived material, chat context, or AI memory / 归档资料、聊天上下文或 AI 记忆

Stop and request human direction if the conflict remains. / 冲突仍无法消除时，停止工作并请求人工决定。

## Mandatory Development Workflow / 强制开发流程

```text
Read required context / 读取必需上下文
→ Select one status:ready Issue / 选择一个 status:ready Issue
→ Verify dependencies and acceptance criteria / 确认依赖与验收标准
→ Review or create the Design Note / 评审或编写 Design Note
→ Define tests first / 先定义测试
→ Implement the smallest scoped change / 做范围内最小实现
→ Run tests and verify failure paths / 运行测试并验证失败路径
→ Perform security and quality checks / 执行安全与质量检查
→ Update documentation and Traceability / 更新文档与追踪矩阵
→ Open one linked PR / 提交一个关联 PR
→ Human review and human merge / 人工 Review 与 Merge
→ Record a structured Handoff / 记录结构化 Handoff
```

Do not write business code during Phase 0 or before all readiness gates pass. / Phase 0 期间或 Ready 条件未全部满足前，不得编写业务代码。

## Golden Rules / 黄金规则

- Do not change the frozen product direction or bypass an Accepted ADR. / 不改变冻结产品方向，不绕过 Accepted ADR。
- One Issue, one branch, one PR; keep changes minimal and scoped. / One Issue、One Branch、One PR；改动必须最小且不越界。
- Test first; provide commands, results, failures, and limitations as evidence. / 测试先行；以命令、结果、失败和限制作为证据。
- Never expose or invent secrets; use references and placeholders only. / 不暴露或编造 Secret，只使用引用与占位符。
- Never describe TARGET metrics or untested capabilities as achieved facts. / 不把 TARGET 指标或未测试能力写成已实现事实。
- Do not perform unrelated refactors, add unapproved dependencies, skip tests, or lower quality gates. / 不做无关重构、不加未批准依赖、不跳过测试、不降低质量门槛。
- LLM output cannot override deterministic Policy; external side effects must be authorized, auditable, and idempotent. / LLM 不得覆盖确定性 Policy；外部副作用必须经授权、可审计且幂等。
- AI must never approve, merge, or claim final review of its own work. / AI 不得批准、Merge 或充当自身工作的最终 Reviewer。

## Repository Map / 仓库地图

| Path | Purpose / 用途 |
|---|---|
| Root governance files / 根目录治理文件 | Mandatory entry points, contribution, security, configuration, and inventory / 强制入口、贡献、安全、配置与清单 |
| [`docs/`](docs/) | Active product, architecture, workflow, quality, security, and operations documentation / 活跃的产品、架构、流程、质量、安全与运维文档 |
| [`docs/adr/`](docs/adr/) | Accepted architecture decisions / 已接受的架构决策 |
| [`docs/templates/`](docs/templates/) | ADR, Design Note, Test Plan, Issue Review, and Handoff templates / ADR、设计、测试、Issue Review 与交接模板 |
| [`project/`](project/) | Canonical GitHub bootstrap data and import procedure / 正式 GitHub 初始化数据与导入流程 |
| [`.github/`](.github/) | Issue forms, PR template, and CODEOWNERS / Issue 表单、PR 模板与 CODEOWNERS |
| [`archive/`](archive/) | Historical duplicates and unmerged proposals; never an active fact source / 历史副本与未合并提案，不是活跃事实源 |

See [`docs/24_REPOSITORY_LAYOUT.md`](docs/24_REPOSITORY_LAYOUT.md) for the complete classification. / 完整分类见仓库布局文档。

## AI Working Agreement / AI 工作约定

At session start, state or verify / 会话开始时声明或确认：

```text
Current Milestone / 当前里程碑:
Selected Issue / 当前 Issue:
Dependencies / 依赖:
Relevant ADRs / 相关 ADR:
Security Risk / 安全风险:
Required External Inputs / 所需外部输入:
```

- Work only within the selected Issue; make assumptions explicit and prefer repository evidence over memory. / 只在所选 Issue 范围内工作；明确写出假设，以仓库证据优先于记忆。
- Report actual commands, outcomes, skipped checks, limitations, and remaining risks. / 如实报告命令、结果、未执行检查、限制与剩余风险。
- Stop for human input on architecture conflicts, missing acceptance criteria, unavailable authorization, real-secret requirements, unsafe tests, or high-risk external writes. / 遇到架构冲突、验收缺失、授权不可用、需要真实 Secret、无法安全测试或高风险外部写操作时停止并请求人工输入。
- End with a Handoff covering Issue, branch, PR, changed files, tests, decisions, risks, blockers, and the next smallest action. / 结束时记录 Issue、Branch、PR、变更文件、测试、决策、风险、阻塞与下一最小动作。

## Current Phase / 当前阶段

Phase 0, AF-101, AF-102, and CI-001 are complete. The project is now in **M1 / AF-103 Implementation**. / Phase 0、AF-101、AF-102 与 CI-001 均已完成；项目当前处于 **M1 / AF-103 实施阶段**。

Current work / 当前工作：

- Implement only the approved AF-103 v3 scope / 只实施已批准的 AF-103 v3 范围；
- Require CI-backed PostgreSQL migration, isolation, immutability, and rollback evidence / 必须提供 CI PostgreSQL 迁移、隔离、不可变性与回滚证据；
- Stop at the PR for Human Review and Human Merge / 创建 PR 后停止，等待 Human Review/Merge。

Only AF-103 implementation is currently authorized; all later Issues remain prohibited until explicitly approved. / 当前只授权 AF-103 实施；后续 Issue 在明确批准前仍禁止开始。

## Pull Request Exit Criteria / PR 退出标准

A PR is ready to leave review only when all applicable items are true / PR 只有在所有适用项满足后才能退出 Review：

- [ ] Linked to one Issue and limited to one-PR scope / 关联一个 Issue，范围可由一个 PR 完成
- [ ] Objective, non-goals, acceptance criteria, and approved design are clear / 目标、非目标、验收标准与获批设计明确
- [ ] Required tests pass; commands and results are recorded / 必需测试通过，命令与结果已记录
- [ ] Failure, security, tenant isolation, idempotency, retry, compensation, and rollback paths are covered where applicable / 适用时覆盖失败、安全、租户隔离、幂等、重试、补偿与回滚路径
- [ ] Documentation and [`docs/21_TRACEABILITY_MATRIX.md`](docs/21_TRACEABILITY_MATRIX.md) are synchronized / 文档与追踪矩阵已同步
- [ ] No real secrets, unsupported claims, unrelated refactors, skipped tests, or lowered gates / 无真实 Secret、无未经证实声明、无无关重构、无跳过测试或降低门槛
- [ ] Required checks pass and review conversations are resolved / 必需检查通过，Review 对话已解决
- [ ] A human reviewer approves and a human performs the merge / 人工 Reviewer 批准并由人工 Merge

If any item is false or unknown, keep the PR open and report the blocker. / 任一项不满足或未知时，保持 PR 未完成并报告阻塞。
