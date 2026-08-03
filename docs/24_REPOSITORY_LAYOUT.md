# 24 — Repository Layout & File Classification

本文件是仓库目录结构与每个文件分类的权威清单，随文档架构整理一并建立。新增、移动或归档文件时，需同步更新本表与 `docs/index.md`、根目录 `MANIFEST.md`。

## 设计原则

- 仓库根目录只保留 GitHub 生态强关联或约定俗成必须在根目录的文件：`README.md`（仓库首页渲染）、`.github/`（Issue/PR 模板、CODEOWNERS）、`.env.example`、`.gitignore`，以及本项目额外选择保留在根目录的强制入门文件 `START_HERE.md` 和核心治理文件 `AGENTS.md`、`CONTRIBUTING.md`、`SECURITY.md`、`MANIFEST.md`。
- 其余全部工程文档（宪章、架构、Roadmap、Milestones、Issue Backlog、测试/安全/可靠性/评测/可观测计划、ADR、模板）集中在 `docs/`，由 `docs/index.md` 作为二级入口统一导航。
- `project/` 只放 GitHub 导入用的机器可读数据（Labels/Milestones/Issues 定义）和导入步骤说明。
- `archive/` 存放历史副本、逐字节重复文件和未合并提案，明确标注"非当前事实源"，不得在未走 Issue/ADR 流程前依据其内容改变当前范围。

## 仓库根目录

| 文件 | 分类 | 用途 |
|---|---|---|
| START_HERE.md | 治理 | 所有人类贡献者与 AI Agent 的强制第一入口 |
| README.md | 治理 | 项目入口、六个 Agent 与 DeliveryPack 概览、当前阶段声明 |
| AGENTS.md | AI流程 | AI 协作总协议、固定开发循环、停止条件 |
| CONTRIBUTING.md | 治理 | 贡献流程、分支/PR/Commit 约束 |
| SECURITY.md | 安全 | 漏洞上报渠道、Secret 处理规则 |
| MANIFEST.md | 治理 | 仓库文件清单、Source-of-Truth 策略、应用源码与测试文件计数 |
| .env.example | 配置 | 环境变量占位符清单，禁止真实密钥 |
| .gitignore | 配置 | Git 忽略规则 |
| .dockerignore | 安全/配置 | 排除 Secret、Git 元数据、开发缓存、文档与测试源码，缩小镜像构建上下文 |
| .python-version | 配置 | AF-101 批准的 Python 3.12 工具链选择 |
| pyproject.toml | 配置 | Python 包、依赖、build backend、pytest 与 coverage 配置 |
| uv.lock | 配置 | uv 解析的可复现 Python 依赖锁文件 |
| Dockerfile | 配置/安全 | AF-102 多阶段 Core 镜像构建，锁定镜像摘要并以非 root 用户运行 |
| compose.yaml | 配置 | AF-102 本地 Core/PostgreSQL/Redis 编排、回环端口与健康检查 |
| alembic.ini | 配置 | AF-103 Alembic CLI 根入口，指向 `control_plane/migrations/` |

## .github/（GitHub 强制要求在仓库根目录才生效）

| 文件 | 分类 | 用途 |
|---|---|---|
| CODEOWNERS | 治理 | 代码所有者映射（当前为占位符，待填真实账号） |
| ISSUE_TEMPLATE/config.yml | 治理 | Issue 表单配置，禁用 blank issue |
| ISSUE_TEMPLATE/feature.yml | 治理 | Feature Issue 表单 |
| ISSUE_TEMPLATE/bug.yml | 治理 | Bug Issue 表单 |
| ISSUE_TEMPLATE/security.yml | 安全 | 安全 Issue 表单 |
| ISSUE_TEMPLATE/adr.yml | 架构 | ADR 提案 Issue 表单 |
| ISSUE_TEMPLATE/documentation.yml | 治理 | 文档 Issue 表单 |
| PULL_REQUEST_TEMPLATE.md | 治理 | PR 模板，强制安全/测试/回滚章节 |
| workflows/ci.yml | 质量/治理 | Required CI：锁定依赖、PostgreSQL 迁移 up/down/reapply、pytest 覆盖率门槛与 Core 镜像构建 |
| workflows/langfuse-smoke.yml | 质量/可观测/安全 | AF-109 Human Merge 后人工触发的 Langfuse auth/write/flush/bounded-query smoke；使用受保护 Environment |

## docs/（工程文档统一子目录）

| 文件 | 分类 | 用途 |
|---|---|---|
| index.md | 治理 | 文档总入口：权威顺序、工作启动检查、文档导航、维护规则 |
| AegisFlow_Final_Plan_v2.md | 架构 | 远端初始提交保留的产品方案，与 `DESIGN_BLUEPRINT.md` 逐字节一致，不构成独立事实源 |
| DESIGN_BLUEPRINT.md | 架构 | 冻结产品方案蓝图（冲突解决最高优先级） |
| 00_PROJECT_CHARTER.md | 治理 | 项目宪章：使命/范围/成功标准/角色 |
| 01_MASTER_TASK_BOOK.md | 治理 | 总任务书 |
| 02_ARCHITECTURE.md | 架构 | 模块化单体、容器划分、状态所有权铁律 |
| 03_ROADMAP.md | 治理 | 12 周 Gate 化路线图 |
| 04_MILESTONES.md | 治理 | M0–M5 + Post-MVP 里程碑定义 |
| 05_GITHUB_ISSUE_BACKLOG.md | 治理 | 75 个 Issue 正式规划基线（canonical） |
| 06_DEVELOPER_GUIDE.md | 治理 | 开发者指南 |
| 07_AI_COLLABORATION_PROTOCOL.md | AI流程 | AI 多月持续协作规范 |
| 08_TEST_STRATEGY.md | 质量 | 测试分层、Gate 套件、覆盖率与证据要求 |
| 09_SECURITY_BASELINE.md | 安全 | 安全基线、风险分级 L0–L5 |
| 10_GIT_GITHUB_WORKFLOW.md | 治理 | 分支/提交/PR/Release 规范 |
| 11_DOCUMENTATION_GOVERNANCE.md | 治理 | 文档治理与更新规则 |
| 12_DEFINITION_OF_READY_DONE.md | 治理 | Issue Ready/Done 定义 |
| 13_RISK_REGISTER.md | 可靠性 | 风险登记册 |
| 14_CONFIGURATION_REFERENCE.md | 配置 | 配置项分组与 Secret 分类参考 |
| 15_RELEASE_AND_VERSIONING.md | 治理 | 发布与版本/Tag 规则 |
| 16_OBSERVABILITY_PLAN.md | 可观测 | Langfuse/OTel/Prometheus 分工与关联键 |
| 17_EVALUATION_PLAN.md | 评测 | Golden Dataset、评测指标、CI 回归门禁 |
| 18_RELIABILITY_PLAN.md | 可靠性 | 幂等账本、重试分层、Saga、故障注入 |
| 19_THREAT_MODEL.md | 安全 | 威胁建模与缓解映射 |
| 20_DECISION_LOG.md | 架构 | 决策日志 |
| 21_TRACEABILITY_MATRIX.md | 治理 | 需求/架构/ADR/Issue/证据追溯矩阵 |
| 22_GLOSSARY.md | 治理 | 术语表 |
| 23_PHASE0_ACCEPTANCE.md | 治理 | Phase 0 验收清单与外部阻塞项 |
| 24_REPOSITORY_LAYOUT.md | 治理 | 本文件：仓库目录与文件分类清单 |
| 25_PHASE0_EXIT_REVIEW.md | 治理 | Phase 0 独立验收、bootstrap exception 风险与人工退出依据 |

## docs/design-notes/（Design Note，非文档 Issue 开工前必需）

| 文件 | 分类 | 用途 |
|---|---|---|
| AF-101.md | AI流程 | 已批准的 AF-101 应用骨架 Design Note 与技术决策 |
| AF-102.md | AI流程 | 已批准的 AF-102 Docker Compose 基础设施 Design Note 与九项决策 |
| CI-001.md | AI流程 | 已批准的 CI-001 基础 CI Design Note；不在 canonical 75 条 Backlog 内，插入依据见 `20_DECISION_LOG.md` |
| AF-103.md | AI流程 | 已批准的 AF-103 v3 初始领域模型与迁移 Design Note |
| M1-SHARED-CONTRACTS.md | AI流程 | AF-104–AF-110 完整跨 Issue 契约（**Approved v4**，PR #84）：Schema 所有权、确定性算法、安全边界、Langfuse 真实 smoke 与严格实施顺序 |
| AF-104.md | AI流程 | Intake Agent Contract Design Note（**Approved v4**，精确规范化/长度/幂等算法） |
| AF-105.md | AI流程 | Clarifier Agent Contract Design Note（**Approved v4**，固定五规则与结构化 resolve） |
| AF-106.md | AI流程 | Context Agent Retrieval Contract Design Note（**Approved v4**，受限 root 与确定性检索） |
| AF-107.md | AI流程 | Planner Agent Contract Design Note（**Approved v4**，稳定能力枚举与固定四任务算法） |
| AF-108.md | AI流程 | Clarification HITL Interface Design Note（**Approved v4**，`clarifier/hitl.py`、run 隔离、replay 幂等） |
| AF-109.md | AI流程 | Langfuse Tracing Design Note（**Approved v4**，诚实计量、确定性 trace correlation、真实 auth/flush/query smoke） |
| AF-110.md | AI流程 | Gate 1A E2E Design Note（**Approved v4**，真实 interrupt/resume、安全 resume helper、Fixture 迁移） |
| M2-SHARED-CONTRACTS.md | AI流程 | AF-201–AF-210 跨 Issue 契约（**Draft v2**）：设计决策已关闭，等待 Human Review |
| AF-201.md | AI流程 | GitHub App/Webhook 签名与有界防重放 Design Note（**Draft v2**） |
| AF-202.md | AI流程 | GitHub 只读工具 Design Note（**Draft v2**） |
| AF-203.md | AI流程 | pgvector 摄取与精确 Citation Design Note（**Draft v2**） |
| AF-204.md | AI流程 | Sandbox Broker 安全基线 Design Note（**Draft v2**） |
| AF-207.md | AI流程 | 可信 ExecutionScope Policy Gate Design Note（**Draft v2**） |
| AF-205.md | AI流程 | 受控 Executor Agent Contract Design Note（**Draft v2**） |
| AF-206.md | AI流程 | Reviewer/Approval 状态机 Design Note（**Draft v2**） |
| AF-208.md | AI流程 | 授权、原子幂等 GitHub Draft PR 工具 Design Note（**Draft v2**） |
| AF-209.md | AI流程 | 带 lease/fencing 的 Idempotency Ledger Design Note（**Draft v2**） |
| AF-210.md | AI流程 | 异步 Gate 1B E2E Design Note（**Draft v2**） |

## docs/test-plans/（配套 Design Note 的测试计划）

| 文件 | 分类 | 用途 |
|---|---|---|
| AF-101.md | 质量 | 已批准的 AF-101 Test Plan、测试先行顺序与失败判定 |
| AF-102.md | 质量 | 已批准的 AF-102 Test Plan 与真实 Docker 验证证据 |
| CI-001.md | 质量 | 已批准的 CI-001 Test Plan，以红灯/绿灯真实 Actions 运行证明 Gate 生效 |
| AF-103.md | 质量 | 已批准的 AF-103 v3 Test Plan，覆盖迁移、租户复合外键与触发器正负向验证 |
| AF-104.md | 质量 | Intake 配套 Test Plan（**Approved v4**） |
| AF-105.md | 质量 | Clarifier 配套 Test Plan（**Approved v4**） |
| AF-106.md | 质量 | Context 配套 Test Plan（**Approved v4**） |
| AF-107.md | 质量 | Planner 配套 Test Plan（**Approved v4**） |
| AF-108.md | 质量 | HITL Interface 配套 Test Plan（**Approved v4**） |
| AF-109.md | 质量 | Langfuse Tracing 配套 Test Plan（**Approved v4**，mock CI + 人工真实 smoke） |
| AF-110.md | 质量 | Gate 1A E2E 配套 Test Plan（**Approved v4**） |
| AF-201.md | 质量 | GitHub App/Webhook 配套 Test Plan（**Draft v2**） |
| AF-202.md | 质量 | GitHub 只读工具配套 Test Plan（**Draft v2**） |
| AF-203.md | 质量 | 仓库知识摄取配套 Test Plan（**Draft v2**） |
| AF-204.md | 质量 | Sandbox Broker 配套 Test Plan（**Draft v2**） |
| AF-207.md | 质量 | Policy Gate 配套 Test Plan（**Draft v2**） |
| AF-205.md | 质量 | Executor Agent 配套 Test Plan（**Draft v2**） |
| AF-206.md | 质量 | Reviewer/Approval 配套 Test Plan（**Draft v2**） |
| AF-208.md | 质量 | Draft PR 写工具配套 Test Plan（**Draft v2**） |
| AF-209.md | 质量 | Idempotency Ledger 配套 Test Plan（**Draft v2**） |
| AF-210.md | 质量 | Gate 1B E2E 配套 Test Plan（**Draft v2**，真实 E2E 需要外部资源） |

## src/aegisflow_core/（AF-101–AF-110 模块化单体与 DeliveryPack 契约；AF-201–AF-210 尚处 Draft 设计阶段，未写代码）

| 路径 | 分类 | 用途 |
|---|---|---|
| app.py | 代码 | FastAPI 应用工厂、路由挂载与安全异常信封 |
| main.py | 代码 | ASGI 入口 `aegisflow_core.main:app` |
| settings.py | 配置 | 应用/数据库及四项 Langfuse all-or-none 的 fail-fast 配置 |
| logging.py | 可观测 | 幂等 JSON stdout 日志基础 |
| __init__.py | 代码边界 | `aegisflow_core` 根包标记 |
| health/__init__.py | 代码边界 | Health 子包标记 |
| health/router.py | 代码 | 稳定的 `GET /health` 契约 |
| control_plane/__init__.py | 代码边界 | Control Plane 顶层包标记 |
| control_plane/domain/ | 代码/数据 | AF-103 六张 SQLAlchemy 模型、公共 metadata 与异步会话工厂 |
| control_plane/migrations/ | 数据/迁移 | AF-103 Alembic 环境、初始 schema、租户复合外键与不可变触发器 |
| runtime/__init__.py | 代码边界 | Runtime 顶层包标记 |
| runtime/state.py | 代码/状态 | AF-110 Gate 1A `AgentState`；强制 run/trace identity 并承载四 Agent 的版本化契约 |
| runtime/graph.py | 代码/编排/安全 | AF-110 LangGraph 进程内图、原生 interrupt/resume、安全 thread 校验、节点错误定位与 Trace 记录 |
| runtime/tracing.py | 可观测/安全 | AF-109 诚实 token/cost 契约、prompt 脱敏、确定性关联与 NoOp/InMemory/Langfuse Recorder |
| runtime/langfuse_smoke.py | 可观测/质量 | 严格的 Langfuse auth/write/flush/60 秒 bounded-query 人工 smoke 入口 |
| gateway/__init__.py | 代码边界 | Gateway 顶层包占位 |
| models/__init__.py | 代码边界 | Models 顶层包占位 |
| evaluation/__init__.py | 代码边界 | Evaluation 顶层包占位 |
| packs/__init__.py | 代码边界 | Application Packs 顶层包占位 |
| packs/delivery/__init__.py | 代码边界 | DeliveryPack 根边界与六个固定 Agent 的包入口 |
| packs/delivery/contracts/__init__.py | 代码边界 | DeliveryPack 版本化数据契约包标记，不做 re-export |
| packs/delivery/contracts/clarification.py | 代码/Schema | AF-105 ClarificationQuestion/Clarification v1 与状态不变量 |
| packs/delivery/contracts/context_package.py | 代码/Schema | AF-106 CitedSnippet/ContextPackage v1、POSIX 路径与扫描统计 |
| packs/delivery/contracts/determinism.py | 代码 | Clock/IdGenerator 端口与系统、固定、随机、顺序实现 |
| packs/delivery/contracts/measurement.py | 代码/Schema | AF-107 finite 非负 Measurement v1 与 not_available 不变量 |
| packs/delivery/contracts/normalized_request.py | 代码/Schema | AF-104 NormalizedRequest v1、长度与 UTC/幂等键验证 |
| packs/delivery/contracts/plan.py | 代码/Schema | AF-107 Plan/PlanTask/ToolRequirement v1 与稳定 capability allowlist |
| packs/delivery/clarifier/__init__.py | 代码边界 | Clarifier Agent 子包标记 |
| packs/delivery/clarifier/ports.py | 代码边界 | ClarificationReasoner 显式注入端口 |
| packs/delivery/clarifier/fakes.py | 代码 | 无外部调用的五规则确定性 Reasoner |
| packs/delivery/clarifier/agent.py | 代码 | Clarifier 委派、完整答案校验与结构化 resolve |
| packs/delivery/clarifier/hitl.py | 代码/可靠性/安全 | AF-108 进程内 HITL Gateway、run 隔离、replay 幂等与原子回答转换 |
| packs/delivery/context/__init__.py | 代码边界 | Context Agent 子包标记 |
| packs/delivery/context/ports.py | 代码边界 | ContextRetriever 显式注入端口 |
| packs/delivery/context/fakes.py | 代码/安全 | 受限 root、256 KiB/200 文件上限与确定性本地检索 |
| packs/delivery/context/agent.py | 代码 | Context 检索委派与异常传播 |
| packs/delivery/intake/__init__.py | 代码边界 | Intake Agent 子包标记 |
| packs/delivery/intake/agent.py | 代码 | NFKC/空白规范化、canonical SHA-256 与 IntakeAgent |
| packs/delivery/planner/__init__.py | 代码边界 | Planner Agent 子包标记 |
| packs/delivery/planner/ports.py | 代码边界 | PlanReasoner 显式注入端口 |
| packs/delivery/planner/fakes.py | 代码/安全 | 固定四任务、L1/L3 风险与诚实预算的确定性 Reasoner |
| packs/delivery/planner/agent.py | 代码 | Clarifier 充分性门禁、Planner 委派与异常传播 |

## tests/（AF-101–AF-110 测试）

| 文件 | 分类 | 用途 |
|---|---|---|
| __init__.py | 质量 | 测试包标记 |
| conftest.py | 质量 | 隔离环境变量与 ASGI async client fixtures |
| test_module_boundaries.py | 质量 | 包存在性、空边界与禁止依赖静态护栏 |
| test_settings.py | 质量 | 合法、缺失和非法配置测试 |
| test_app_startup.py | 质量/安全 | 应用构造、fail-fast 与安全异常信封测试 |
| test_health.py | 质量 | `/health` 精确响应契约测试 |
| test_logging.py | 质量/可观测 | 日志幂等与 JSON envelope 测试 |
| test_docker_compose_config.py | 质量/安全 | Compose 渲染、镜像 pin、环境 allowlist、回环端口与构建上下文静态护栏 |
| domain/conftest.py | 质量/数据 | 独立 PostgreSQL 测试事务与 rollback fixture |
| domain/test_models.py | 质量/数据 | 六表 metadata、命名约束、UUID/时间默认值与复合外键静态测试 |
| domain/test_migration_config.py | 质量/数据 | Alembic 根入口、完整 metadata 与默认 schema 测试 |
| domain/test_session.py | 质量/数据 | SQLAlchemy async engine/session factory 测试 |
| domain/test_database_constraints.py | 质量/安全 | 真实 PostgreSQL 的租户隔离、版本不可变、append-only Audit 与约束负向测试 |
| runtime/__init__.py | 质量 | Runtime 测试包标记 |
| runtime/test_tracing.py | 质量/安全/可观测 | AF-109 trace schema、redaction、配置矩阵、Recorder mock 与 smoke workflow 静态护栏 |
| e2e/__init__.py | 质量 | Gate 1A 端到端测试包标记 |
| e2e/test_gate1a.py | 质量/安全/可靠性 | AF-110 真实 interrupt/resume、错误 thread、幂等、可重复性、Trace 与节点失败定位门禁 |
| packs/__init__.py | 质量 | Application Pack 测试包标记，避免同名测试模块冲突 |
| packs/delivery/__init__.py | 质量 | DeliveryPack 测试包标记 |
| packs/delivery/clarifier/__init__.py | 质量 | Clarifier 测试包标记 |
| packs/delivery/clarifier/test_agent.py | 质量 | 显式 Reasoner 注入、异常传播、答案完成/缺失与不重入测试 |
| packs/delivery/clarifier/test_boundaries.py | 质量/架构 | Clarifier 禁止外部框架依赖且不提前创建 AF-108 HITL |
| packs/delivery/clarifier/test_contracts.py | 质量/Schema | Question/Clarification 长度、唯一性与状态不变量测试 |
| packs/delivery/clarifier/test_hitl.py | 质量/可靠性/安全 | AF-108 状态机、run 隔离、并发提交、幂等与输入边界测试 |
| packs/delivery/clarifier/test_reasoner.py | 质量/安全 | 中英文五规则、固定问题顺序与完整需求测试 |
| packs/delivery/context/__init__.py | 质量 | Context 测试包标记 |
| packs/delivery/context/test_agent.py | 质量 | ContextRetriever 显式注入与异常传播测试 |
| packs/delivery/context/test_boundaries.py | 质量/架构 | Context 禁止网络/框架依赖及 root 注入护栏 |
| packs/delivery/context/test_contracts.py | 质量/Schema | Citation 路径/行号、包分离与计数边界测试 |
| packs/delivery/context/test_retriever.py | 质量/安全 | 扩展名、symlink/越界、大小/数量、排序与原文行号测试 |
| packs/delivery/intake/__init__.py | 质量 | Intake 测试包标记 |
| fixtures/context/retrieval_contract.md | 质量/Fixture | Citation 与 unsupported-note 基础检索材料 |
| fixtures/context/tenant_guard.py | 质量/Fixture | 合成 tenant guard 检索材料，不作为应用代码导入 |
| fixtures/context/refund_tenant_isolation.py | 质量/Fixture | Gate 1A 租户隔离检索材料 |
| fixtures/context/refund_celery_export.py | 质量/Fixture | Gate 1A Celery 异步导出检索材料 |
| fixtures/context/refund_audit_security.md | 质量/Fixture | Gate 1A 审计与安全检索材料 |
| fixtures/gate1a/sample_request.json | 质量/Fixture | 脱敏退款审计 CSV 请求、验收标准与 sanitization 记录 |
| fixtures/gate1a/expected_clarification.json | 质量/Fixture | 五个确定性 Clarification 问题的外部契约 |
| fixtures/gate1a/fixed_clarification_response.json | 质量/Fixture | Gate 恢复使用的七项固定非空回答 |
| packs/delivery/intake/test_determinism.py | 质量 | Clock/IdGenerator UTC、UUID4 与可复现 UUID5 测试 |
| packs/delivery/intake/test_normalized_request.py | 质量/Schema | source type、长度、UTC、hash 格式与 canonical 向量测试 |
| packs/delivery/intake/test_agent.py | 质量/安全 | 规范化、幂等、注入边界与 prompt-like 数据测试 |
| packs/delivery/intake/test_boundaries.py | 质量/架构 | Intake/contracts 禁止框架、数据库、Runtime 与 Provider SDK 依赖 |
| packs/delivery/planner/__init__.py | 质量 | Planner 测试包标记 |
| packs/delivery/planner/test_agent.py | 质量 | Clarifier Gate、显式 Reasoner 注入与异常传播测试 |
| packs/delivery/planner/test_boundaries.py | 质量/架构 | Planner 禁止 Web/LangGraph/Policy/MCP/Provider 依赖且不提前实施后续 Issue |
| packs/delivery/planner/test_contracts.py | 质量/Schema | Measurement、Plan、结构化 ToolRequirement 与能力 allowlist 不变量测试 |
| packs/delivery/planner/test_reasoner.py | 质量/安全 | 固定任务、风险、诚实预算、证据缺失与 prompt-like context 测试 |

## docs/adr/（Accepted ADR）

| 文件 | 分类 | 用途 |
|---|---|---|
| 0001-modular-monolith.md | 架构 | 接受单体，否决 10 微服务拆分 |
| 0002-langgraph-temporal-state-ownership.md | 架构 | 状态所有权铁律 |
| 0003-no-kafka.md | 架构 | 否决 Kafka |
| 0004-no-terraform.md | 架构 | 否决 Terraform |
| 0005-no-sft-lora.md | 架构 | 否决 SFT/LoRA |
| 0006-no-crewai.md | 架构 | 否决 CrewAI |
| 0007-rbac-contextual-policy.md | 安全 | RBAC + 确定性 Contextual Policy，否决通用 ABAC |
| 0008-observability-boundaries.md | 可观测 | Langfuse 与 OTel 职责边界 |
| 0009-phased-sandbox.md | 安全 | 分阶段沙箱（M2 Docker → M5 k3s） |
| 0010-evaluation-datasets.md | 评测 | 混合评测数据集选型 |
| 0011-no-workflow-builder.md | 架构 | 否决可视化 Workflow Builder |
| 0012-opspilot-roadmap-only.md | 治理 | OpsPilot 仅 Post-MVP Roadmap |

## docs/templates/

| 文件 | 分类 | 用途 |
|---|---|---|
| ADR_TEMPLATE.md | 治理 | ADR 模板 |
| DESIGN_NOTE_TEMPLATE.md | AI流程 | Design Note 模板（非文档 Issue 开工前必填） |
| HANDOFF_TEMPLATE.md | AI流程 | AI 会话交接模板 |
| ISSUE_DESIGN_TEMPLATE.md | 治理 | Issue 设计评审模板 |
| TEST_PLAN_TEMPLATE.md | 质量 | 测试计划模板 |

## project/（GitHub 导入用机器可读数据）

| 文件 | 分类 | 用途 |
|---|---|---|
| GITHUB_SETUP.md | 治理 | GitHub 导入步骤说明（Labels→Milestones→Issues→保护分支→Tag） |
| LABELS.json | 治理 | 56 个唯一 Label 定义，完整覆盖 CSV、Backlog 与 Issue Templates 的引用 |
| MILESTONES.json | 治理 | Milestone 定义（M0–M5 + Post-MVP） |
| GITHUB_ISSUE_IMPORT.csv | 治理 | 75 个 canonical Issue 的机器可读导入数据 |

## archive/（非当前事实源，需人工经 Issue/ADR 流程后才可采纳）

| 文件 | 分类 | 用途 |
|---|---|---|
| originals/AegisFlow_Final_Plan_v2.md | 架构 | 冻结产品方案原始定稿的同内容存档副本 |
| duplicates/23_PHASE0_ACCEPTANCE.md | 治理 | 与 `docs/23_PHASE0_ACCEPTANCE.md` 逐字节重复的历史快照 |
| phase0-gap-patch/05_GITHUB_ISSUE_BACKLOG.md | 治理 | 未合并提案：把 Issue 从 75 条扩展到 80 条的补丁草稿 |
| phase0-gap-patch/GITHUB_ISSUE_IMPORT.csv | 治理 | 上述补丁已应用后的 80 行 CSV 草稿 |
| phase0-gap-patch/GITHUB_ISSUE_IMPORT.jsonl | 治理 | 同上补丁的 JSONL 导出格式 |
| phase0-gap-patch/GITHUB_ISSUE_IMPORT.md | 治理 | 同上补丁的 Markdown 导出格式 |
| phase0-gap-patch/GITHUB_ISSUE_IMPORT.xlsx | 治理 | 同上补丁的 Excel 导出格式 |

## 已知待办（不在本次分类范围内，供后续 Issue 参考）

- `archive/phase0-gap-patch/` 的合并需要先形成对应的 Design Note 和 ADR-0013/0014 的正式 Accepted 状态，再走一次独立的 PR，不与本次目录整理混在一起。
- AF-110 已将未追踪的根目录外部输入 `gemini-code-1785679381247.md` 映射为 `tests/fixtures/gate1a/` 下三个结构化 JSON，并在映射测试通过后删除本地源文件；该源文件从未成为仓库事实源。
- M2 Design Bundle 当前为 Draft v2，尚未写业务代码。设计决策已关闭；Human Review 后可按严格顺序实施。AF-210 真实 E2E 仍需独立私有 Fixture 仓库与开发 GitHub App。
