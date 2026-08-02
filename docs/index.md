# AegisFlow 文档总入口

本页是 AegisFlow 的文档导航与当前状态入口。首次进入仓库时必须先阅读根目录的 [`START_HERE.md`](../START_HERE.md)，再依次阅读 `README.md`、`AGENTS.md` 和本页；开始具体任务前，再按本页加载当前 Issue、相关 ADR、测试策略与最近 Handoff。

## 当前状态

- **阶段**：M1 — AF-107 Planner Agent Contract Implementation
- **实现状态**：Phase 0、AF-101–AF-106、CI-001 已完成并验证；M1 Design Bundle v4 已通过 PR #84 Human Review/Merge，当前仅实施 AF-107
- **正式 Issue 基线**：75 条，来源为 `docs/05_GITHUB_ISSUE_BACKLOG.md` 与 `project/GITHUB_ISSUE_IMPORT.csv`
- **GitHub 初始化状态**：56 个权威 Labels、7 个 Milestones、75 个 canonical Issues 已导入并核验
- **最近完成 Issue**：AF-106（GitHub #15，canonical），通过 PR #87 Human Merge，当前为 `CLOSED / status:verified`
- **范围边界**：AF-107 已获批并进入实施；本轮只实现确定性 Planner 契约，AF-108 在 AF-107 Human Merge/验证前不得启动
- **真实性要求**：未实际测量的恢复时间、零重复副作用、并发量和完成率只能标记为 TARGET

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
- [`adr/`](adr/)：12 个 Accepted ADR
- [`20_DECISION_LOG.md`](20_DECISION_LOG.md)：已接受与待决事项
- [`21_TRACEABILITY_MATRIX.md`](21_TRACEABILITY_MATRIX.md)：需求、架构、ADR、Issue 与证据映射
- [`22_GLOSSARY.md`](22_GLOSSARY.md)：项目术语
- [`24_REPOSITORY_LAYOUT.md`](24_REPOSITORY_LAYOUT.md)：仓库目录结构与每个文件的分类清单
- [`25_PHASE0_EXIT_REVIEW.md`](25_PHASE0_EXIT_REVIEW.md)：Phase 0 独立验收审查，逐项核对 AF-000–AF-008 与退出条件
- [`design-notes/AF-101.md`](design-notes/AF-101.md)：AF-101 应用骨架 Design Note（Approved）
- [`design-notes/AF-102.md`](design-notes/AF-102.md)：AF-102 Docker Compose 基础设施 Design Note（Approved）
- [`design-notes/CI-001.md`](design-notes/CI-001.md)：CI-001 基础 CI Design Note（Approved；非 canonical 治理插入，见 `20_DECISION_LOG.md`）
- [`design-notes/AF-103.md`](design-notes/AF-103.md)：AF-103 初始领域模型与迁移 Design Note（Approved v3）
- [`design-notes/M1-SHARED-CONTRACTS.md`](design-notes/M1-SHARED-CONTRACTS.md)：M1 Design Bundle（AF-104–AF-110）完整跨 Issue 契约（**Approved v4**，PR #84）
- [`design-notes/AF-104.md`](design-notes/AF-104.md) … [`AF-107.md`](design-notes/AF-107.md)：已批准的自包含 Design Note；[`AF-108.md`](design-notes/AF-108.md) … [`AF-110.md`](design-notes/AF-110.md) 保持 Draft v4，严格顺序执行
- [`test-plans/AF-101.md`](test-plans/AF-101.md)：AF-101 配套 Test Plan（Approved）
- [`test-plans/AF-102.md`](test-plans/AF-102.md)：AF-102 配套 Test Plan（Approved，含真实执行证据）
- [`test-plans/CI-001.md`](test-plans/CI-001.md)：CI-001 配套 Test Plan（Approved；含真实 Actions 红灯/绿灯证据）
- [`test-plans/AF-103.md`](test-plans/AF-103.md)：AF-103 配套 Test Plan（Approved v3）
- [`test-plans/AF-104.md`](test-plans/AF-104.md) … [`AF-107.md`](test-plans/AF-107.md)：已批准的 Test Plan；[`AF-108.md`](test-plans/AF-108.md) … [`AF-110.md`](test-plans/AF-110.md) 保持 Draft v4

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
- `archive/phase0-gap-patch/` 保存把 Issue 从 75 条扩展到 80 条的未合并补丁及导出格式，其中拟议的 ADR-0013、ADR-0014 尚未成为 Accepted ADR。

除非 Project Owner 通过正式 Issue、ADR 和文档同步流程接受该补丁，不得依据归档内容改变当前范围、Issue 数量或状态所有权。

## 外部输入与停止条件

GitHub 仓库与治理写授权已经确认。测试仓库、OIDC Provider、Model Provider、Langfuse 配置和演示环境仍需项目所有者提供；缺少相应输入时，将对应 Issue 保持 blocked，不得编造配置或 Secret。

遇到架构冲突、未授权仓库、高风险外部写操作、缺失验收标准、真实 Secret 需求或无法安全测试时，立即停止并请求人工输入。

## 维护规则

- 产品方向变化、状态所有权、持久化系统、权限模型、Gate 或微服务策略变化必须新增 ADR；
- 架构、接口、配置、权限、测试门槛或部署变化必须在同一 PR 更新相关文档与 Traceability；
- GitHub 导入完成后，GitHub Issue 是实时执行状态源，仓库 Backlog 保留为规划基线；
- 活跃文档只陈述已验证事实，历史副本和未合并提案统一放入 `archive/`；
- 新增、移动或归档文档时，同步更新本页和根目录 `MANIFEST.md`，并执行链接检查。
