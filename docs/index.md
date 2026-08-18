# AegisFlow 文档总入口

> **Current execution state / 当前执行状态（2026-08-18）**: M5 Gate 4 has been accepted by the Project Owner. AF-R01–AF-R03 are completed extensions. The active approved batch is AF-R04–AF-R08, which closes a loopback-only Ollama, FastAPI, Temporal, LangGraph and Next.js local MVP without changing DeliveryPack or the six fixed Agents. / M5 Gate 4 已由 Project Owner 验收；AF-R01–AF-R03 已完成。当前获批批次为 AF-R04–AF-R08，用于收口回环限定的 Ollama、FastAPI、Temporal、LangGraph 与 Next.js 本地 MVP，不改变 DeliveryPack 与六个固定 Agent。

> 当前批次：GitHub Issues #113–#117（AF-R04–AF-R08）；Project Owner 已批准作为依赖闭合批次开发，但最终结论仍必须由 Human Review/Merge 与 Project Owner 确认。

本页是 AegisFlow 的文档导航与当前状态入口。首次进入仓库时必须先阅读根目录的 [`START_HERE.md`](../START_HERE.md)，再依次阅读 `README.md`、`AGENTS.md` 和本页；开始具体任务前，再按本页加载当前 Issue、相关 ADR、测试策略与最近 Handoff。

## 当前状态

- **阶段**：Post-MVP Local Full-Stack MVP；M1–M5 与 Gate 4 已由 Project Owner 验收
- **实现状态**：AF-R04–AF-R08 已完成本地闭环实现，正在补齐文档、覆盖率和最终可复现证据；生产身份、真实 GitHub canary 与生产部署仍是后续工作
- **正式 Issue 基线**：75 条，来源为 `docs/05_GITHUB_ISSUE_BACKLOG.md` 与 `project/GITHUB_ISSUE_IMPORT.csv`
- **GitHub 初始化状态**：56 个权威 Labels、7 个 Milestones、75 个 canonical Issues 已导入并核验
- **最近本地证据**：2026-08-18 完成一条 10/10 Ollama + Sandbox + 独立审批 + dry-run Draft PR candidate 闭环；后端 633 passed / 1 protected test skipped，覆盖率门槛通过 90%
- **范围边界**：当前批次使用 ADR-0014 的可信回环身份与 GitHub dry-run 配置；不得把本地配置表述为生产认证，不得绕过真实 OIDC、Policy Gate 或 Human Review
- **真实性要求**：CI fixture、组件组合证据、短时压测与单路 Provider smoke 必须保留限制，不得包装成生产结论

## 权威顺序

文档或上下文冲突时，按以下顺序裁决；仍不能消除冲突时停止工作并要求人工决定：

1. [`DESIGN_BLUEPRINT.md`](DESIGN_BLUEPRINT.md)
2. [`00_PROJECT_CHARTER.md`](00_PROJECT_CHARTER.md)
3. [`adr/`](adr/) 中状态为 Accepted 的 ADR
4. [`02_ARCHITECTURE.md`](02_ARCHITECTURE.md)
5. 当前 Milestone 与 GitHub Issue
6. Developer Guide、测试策略及其他活跃文档
7. 归档资料、聊天上下文或 AI 记忆

## 工作启动检查

开始任何实现前必须确认：

- 当前 Milestone、Issue、依赖和验收标准明确；
- Issue 为 `status:ready`，且范围能在一个 PR 内完成；
- 已读取相关 Architecture、ADR、测试策略和最近 Handoff；
- 非文档 Issue 已有通过 Review 的 Design Note 与 Test Plan；
- 不需要真实 Secret、未授权外部写操作或冻结范围外技术。

任一项不满足时，不得编写业务代码。

## 文档导航

### 产品、范围与计划

- [`DESIGN_BLUEPRINT.md`](DESIGN_BLUEPRINT.md)：冻结的产品方向与整体方案
- [`00_PROJECT_CHARTER.md`](00_PROJECT_CHARTER.md)：使命、边界、Gate 与治理角色
- [`01_MASTER_TASK_BOOK.md`](01_MASTER_TASK_BOOK.md)：Workstream 与依赖主线
- [`03_ROADMAP.md`](03_ROADMAP.md)：12 周阶段计划与止损规则
- [`04_MILESTONES.md`](04_MILESTONES.md)：M0–M5 退出条件
- [`05_GITHUB_ISSUE_BACKLOG.md`](05_GITHUB_ISSUE_BACKLOG.md)：75 条正式规划基线
- [`23_PHASE0_ACCEPTANCE.md`](23_PHASE0_ACCEPTANCE.md)：Phase 0 验收和外部阻塞

### 架构与决策

- [`02_ARCHITECTURE.md`](02_ARCHITECTURE.md)：容器、模块、状态所有权与信任边界
- [`adr/`](adr/)：13 个 Accepted ADR
- [`20_DECISION_LOG.md`](20_DECISION_LOG.md)：已接受与待决事项
- [`21_TRACEABILITY_MATRIX.md`](21_TRACEABILITY_MATRIX.md)：需求、架构、ADR、Issue 与证据映射
- [`22_GLOSSARY.md`](22_GLOSSARY.md)：项目术语
- [`24_REPOSITORY_LAYOUT.md`](24_REPOSITORY_LAYOUT.md)：仓库目录结构与每个文件的分类清单
- [`25_PHASE0_EXIT_REVIEW.md`](25_PHASE0_EXIT_REVIEW.md)：Phase 0 独立验收审查，逐项核对 AF-000–AF-008 与退出条件
- [`26_PRODUCTION_READINESS_PLAN.md`](26_PRODUCTION_READINESS_PLAN.md)：当前真实状态、目录与清理边界、项目负责人准备清单和生产化路线图
- [`adr/0014-local-mvp-execution-profile.md`](adr/0014-local-mvp-execution-profile.md)：可信回环身份、Ollama 与 GitHub dry-run 本地执行边界
- [`design-notes/LOCAL-MVP-BACKEND-BUNDLE.md`](design-notes/LOCAL-MVP-BACKEND-BUNDLE.md)：AF-R04–AF-R06 后端本地闭环设计
- [`test-plans/LOCAL-MVP-BACKEND-BUNDLE.md`](test-plans/LOCAL-MVP-BACKEND-BUNDLE.md)：AF-R04–AF-R06 后端验证计划
- [`design-notes/AF-R07-NEXTJS-CONSOLE.md`](design-notes/AF-R07-NEXTJS-CONSOLE.md)：Next.js Developer/Reviewer Console 设计
- [`test-plans/AF-R07-NEXTJS-CONSOLE.md`](test-plans/AF-R07-NEXTJS-CONSOLE.md)：Console 单元、契约与浏览器验证计划
- [`design-notes/AF-101.md`](design-notes/AF-101.md)：AF-101 应用骨架 Design Note（Approved）
- [`design-notes/AF-102.md`](design-notes/AF-102.md)：AF-102 Docker Compose 基础设施 Design Note（Approved）
- [`design-notes/CI-001.md`](design-notes/CI-001.md)：CI-001 基础 CI Design Note（Approved；非 canonical 治理插入，见 `20_DECISION_LOG.md`）
- [`design-notes/AF-103.md`](design-notes/AF-103.md)：AF-103 初始领域模型与迁移 Design Note（Approved v3）
- [`design-notes/M1-SHARED-CONTRACTS.md`](design-notes/M1-SHARED-CONTRACTS.md)：M1 Design Bundle（AF-104–AF-110）完整跨 Issue 契约（**Approved v4**，PR #84）
- [`design-notes/AF-104.md`](design-notes/AF-104.md) … [`AF-110.md`](design-notes/AF-110.md)：已批准的自包含 Design Note，严格顺序执行
- [`design-notes/M2-SHARED-CONTRACTS.md`](design-notes/M2-SHARED-CONTRACTS.md)：M2 Gate 1B 跨 Issue 契约（**Draft v2**，设计决策已关闭，等待 Human Review）
- [`design-notes/AF-201.md`](design-notes/AF-201.md) … [`AF-210.md`](design-notes/AF-210.md)：AF-201–AF-210 Design Notes（**Draft v2**，严格顺序：201→202→203→204→207→205→206→208→209→210）
- [`test-plans/AF-101.md`](test-plans/AF-101.md)：AF-101 配套 Test Plan（Approved）
- [`test-plans/AF-102.md`](test-plans/AF-102.md)：AF-102 配套 Test Plan（Approved，含真实执行证据）
- [`test-plans/CI-001.md`](test-plans/CI-001.md)：CI-001 配套 Test Plan（Approved；含真实 Actions 红灯/绿灯证据）
- [`test-plans/AF-103.md`](test-plans/AF-103.md)：AF-103 配套 Test Plan（Approved v3）
- [`test-plans/AF-104.md`](test-plans/AF-104.md) … [`AF-110.md`](test-plans/AF-110.md)：已批准的 Test Plan
- [`test-plans/AF-201.md`](test-plans/AF-201.md) … [`AF-210.md`](test-plans/AF-210.md)：AF-201–AF-210 配套 Test Plans（**Draft v2**）

### 开发与协作

- [`06_DEVELOPER_GUIDE.md`](06_DEVELOPER_GUIDE.md)：开发环境和模块规则
- [`07_AI_COLLABORATION_PROTOCOL.md`](07_AI_COLLABORATION_PROTOCOL.md)：AI 会话、Context Packet 与 Handoff
- [`10_GIT_GITHUB_WORKFLOW.md`](10_GIT_GITHUB_WORKFLOW.md)：Issue、Branch、PR 与 Release 流程
- [`11_DOCUMENTATION_GOVERNANCE.md`](11_DOCUMENTATION_GOVERNANCE.md)：文档状态、审查与同步要求
- [`12_DEFINITION_OF_READY_DONE.md`](12_DEFINITION_OF_READY_DONE.md)：Ready、Done 与 Gate Done
- [`14_CONFIGURATION_REFERENCE.md`](14_CONFIGURATION_REFERENCE.md)：配置组、Secret 引用与外部输入
- [`15_RELEASE_AND_VERSIONING.md`](15_RELEASE_AND_VERSIONING.md)：软件、Prompt、Workflow 与 Tool 版本规则
- [`templates/`](templates/)：ADR、Design Note、Test Plan、Issue Review 与 Handoff 模板

### 质量、安全与运行

- [`08_TEST_STRATEGY.md`](08_TEST_STRATEGY.md)：测试层级、Gate Suite 与证据要求
- [`09_SECURITY_BASELINE.md`](09_SECURITY_BASELINE.md)：默认拒绝、权限、沙箱和 Secret 基线
- [`13_RISK_REGISTER.md`](13_RISK_REGISTER.md)：当前风险登记
- [`16_OBSERVABILITY_PLAN.md`](16_OBSERVABILITY_PLAN.md)：Langfuse、OTel 和指标边界
- [`17_EVALUATION_PLAN.md`](17_EVALUATION_PLAN.md)：数据集、Baseline、指标和回归门禁
- [`18_RELIABILITY_PLAN.md`](18_RELIABILITY_PLAN.md)：恢复、幂等、重试、补偿与故障注入
- [`19_THREAT_MODEL.md`](19_THREAT_MODEL.md)：资产、攻击者、威胁与缓解措施
- [`SECURITY.md`](../SECURITY.md)：仓库级安全与漏洞报告规则

### GitHub 初始化资料

- [`project/GITHUB_SETUP.md`](../project/GITHUB_SETUP.md)：导入顺序与所需授权
- [`project/GITHUB_ISSUE_IMPORT.csv`](../project/GITHUB_ISSUE_IMPORT.csv)：75 条正式 Issue 导入数据
- [`project/LABELS.json`](../project/LABELS.json)：Label 定义
- [`project/MILESTONES.json`](../project/MILESTONES.json)：Milestone 定义

## 归档与待评审补丁

`archive/` 不属于当前事实源：

- [`AegisFlow_Final_Plan_v2.md`](AegisFlow_Final_Plan_v2.md) 保留自远端初始提交，与当前权威蓝图 `DESIGN_BLUEPRINT.md` 逐字节一致，不构成独立事实源；
- `archive/originals/` 保存正式蓝图的原始同内容副本；
- `archive/duplicates/` 保存未删除的逐字节重复快照；
- `archive/phase0-gap-patch/` 保存把 Issue 从 75 条扩展到 80 条的未合并补丁及导出格式；其中同名编号的历史提案仍非事实源。当前 Accepted ADR-0013 是独立的 Post-MVP 边界决策，ADR-0014 仍未接受。

除非 Project Owner 通过正式 Issue、ADR 和文档同步流程接受该补丁，不得依据归档内容改变当前范围、Issue 数量或状态所有权。

## 外部输入与停止条件

GitHub 仓库、治理写授权和当前验收所需的受保护 Environments 已确认；真实 Secret 只保存在 GitHub Environment 或本地环境中，不进入文档、日志、Issue 或 PR。最终批次不得新增外部权限或编造输入。

遇到架构冲突、未授权仓库、高风险外部写操作、缺失验收标准、真实 Secret 需求或无法安全测试时，立即停止并请求人工输入。

### M3 Durable Runtime 批次

- [`design-notes/M3-DURABLE-RUNTIME-BUNDLE.md`](design-notes/M3-DURABLE-RUNTIME-BUNDLE.md)：AF-301–AF-307 durable runtime 批次契约，**Approved v1**。
- [`test-plans/M3-DURABLE-RUNTIME-BUNDLE.md`](test-plans/M3-DURABLE-RUNTIME-BUNDLE.md)：AF-301–AF-307 配套 Test Plan，**Approved v1**。
- [`design-notes/M3-RELIABILITY-MODEL-BUNDLE.md`](design-notes/M3-RELIABILITY-MODEL-BUNDLE.md)：AF-308–AF-311 可靠性与模型运行时批次契约，**Approved v1**。
- [`test-plans/M3-RELIABILITY-MODEL-BUNDLE.md`](test-plans/M3-RELIABILITY-MODEL-BUNDLE.md)：AF-308–AF-311 配套 Test Plan，**Approved v1**。
- [`design-notes/AF-312.md`](design-notes/AF-312.md)：Gate 2 可靠性证据发布方案，**Approved v1**。
- [`test-plans/AF-312.md`](test-plans/AF-312.md)：Gate 2 报告、Blog 与 Demo Runbook 验证计划，**Approved v1**。
- [`reports/GATE2_RELIABILITY_REPORT.md`](reports/GATE2_RELIABILITY_REPORT.md)：Gate 2 工程证据、指标、限制与验收建议。
- [`reports/GATE2_RELIABILITY_BLOG.md`](reports/GATE2_RELIABILITY_BLOG.md)：面向读者的可靠性技术总结。
- [`reports/GATE2_DEMO_RUNBOOK.md`](reports/GATE2_DEMO_RUNBOOK.md)：受保护工作流的可重复演示步骤与停止条件。
- [`design-notes/M4-GOVERNANCE-SECURITY-BUNDLE.md`](design-notes/M4-GOVERNANCE-SECURITY-BUNDLE.md)：AF-401–AF-413 租户、身份、RBAC、Policy、Audit、MCP、Sandbox 与 Gate 3 共享契约，**Approved v1**。
- [`test-plans/M4-GOVERNANCE-SECURITY-BUNDLE.md`](test-plans/M4-GOVERNANCE-SECURITY-BUNDLE.md)：M4 五个依赖波次的安全与隔离总 Test Plan，**Approved v1**。
- [`reports/GATE3_GOVERNANCE_SECURITY_REPORT.md`](reports/GATE3_GOVERNANCE_SECURITY_REPORT.md)：Gate 3 自动化安全回归、证据要求与限制。
- [`reports/GATE3_DEMO_RUNBOOK.md`](reports/GATE3_DEMO_RUNBOOK.md)：无需真实 Secret 或强制录屏的可重复 Gate 3 验收步骤。
- [`design-notes/M5-EVALUATION-FOUNDATION.md`](design-notes/M5-EVALUATION-FOUNDATION.md)：AF-501–AF-505 评测数据与 Baseline 契约。
- [`test-plans/M5-EVALUATION-FOUNDATION.md`](test-plans/M5-EVALUATION-FOUNDATION.md)：AF-501–AF-505 配套验证计划。
- [`design-notes/M5-EVALUATION-GATES.md`](design-notes/M5-EVALUATION-GATES.md)：AF-504、AF-506、AF-507、AF-510 历史真值、报告、CI 回归与 Grafana 契约。
- [`test-plans/M5-EVALUATION-GATES.md`](test-plans/M5-EVALUATION-GATES.md)：AF-504、AF-506、AF-507、AF-510 配套验证计划。
- [`design-notes/M5-OBSERVABILITY-BUNDLE.md`](design-notes/M5-OBSERVABILITY-BUNDLE.md)：AF-508、AF-509、AF-511、AF-514 可观测性批次契约。
- [`test-plans/M5-OBSERVABILITY-BUNDLE.md`](test-plans/M5-OBSERVABILITY-BUNDLE.md)：Tracing、Metrics、Load 与只读 Run Graph 验证计划。
- [`design-notes/M5-DEPLOYMENT-WORKBENCH-BUNDLE.md`](design-notes/M5-DEPLOYMENT-WORKBENCH-BUNDLE.md)：AF-512、AF-513、AF-515 k3d/Helm 部署与 Personal Workbench 批次契约（**Approved v2**）。
- [`test-plans/M5-DEPLOYMENT-WORKBENCH-BUNDLE.md`](test-plans/M5-DEPLOYMENT-WORKBENCH-BUNDLE.md)：k3d 集群、Helm upgrade/rollback 与 Personal Workbench 隔离验证计划（**Approved v2**）。
- [`design-notes/M5-FINAL-ACCEPTANCE-BUNDLE.md`](design-notes/M5-FINAL-ACCEPTANCE-BUNDLE.md)：AF-211/AF-516/AF-517 最终验收证据契约。
- [`test-plans/M5-FINAL-ACCEPTANCE-BUNDLE.md`](test-plans/M5-FINAL-ACCEPTANCE-BUNDLE.md)：最终证据真实性、完整性、安全与停止条件。
- [`design-notes/POST-MVP-ROADMAP-BUNDLE.md`](design-notes/POST-MVP-ROADMAP-BUNDLE.md)：AF-R01–AF-R03 已批准的最小扩展契约。
- [`test-plans/POST-MVP-ROADMAP-BUNDLE.md`](test-plans/POST-MVP-ROADMAP-BUNDLE.md)：OpsPilot、可选 vLLM 与 Actions Read-only MCP 的验证计划。
- [`adr/0013-post-mvp-extension-boundaries.md`](adr/0013-post-mvp-extension-boundaries.md)：Post-MVP 扩展必须复用现有 Control Plane 边界的 Accepted 决策。
- [`reports/GATE1_EVIDENCE_REPORT.md`](reports/GATE1_EVIDENCE_REPORT.md)：Gate 1B、Trace、成本来源与限制证据。
- [`reports/GATE4_FINAL_ACCEPTANCE.md`](reports/GATE4_FINAL_ACCEPTANCE.md)：Gate 1–4、评测、负载、k3s、Provider 与 Artifact 完整性台账（Candidate）。
- [`reports/GATE4_DEMO_RUNBOOK.md`](reports/GATE4_DEMO_RUNBOOK.md)：无需强制录屏的可重复最终验收流程。
- [`reports/LOCAL_MVP_RUNBOOK.md`](reports/LOCAL_MVP_RUNBOOK.md)：AF-R04–AF-R08 本地 Ollama、Temporal、LangGraph、Sandbox 与双 Console 完整闭环运行手册。
- [`handoffs/2026-08-18-AF-R04-R08.md`](handoffs/2026-08-18-AF-R04-R08.md)：当前批次完成内容、测试证据、风险、Owner 输入和下一最小动作。

## 维护规则

- 产品方向变化、状态所有权、持久化系统、权限模型、Gate 或微服务策略变化必须新增 ADR；
- 架构、接口、配置、权限、测试门槛或部署变化必须在同一 PR 更新相关文档与 Traceability；
- GitHub 导入完成后，GitHub Issue 是实时执行状态源，仓库 Backlog 保留为规划基线；
- 活跃文档只陈述已验证事实，历史副本和未合并提案统一放入 `archive/`；
- 新增、移动或归档文档时，同步更新本页和根目录 `MANIFEST.md`，并执行链接检查。
