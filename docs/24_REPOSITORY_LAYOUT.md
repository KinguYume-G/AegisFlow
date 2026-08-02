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
| workflows/ci.yml | 质量/治理 | CI-001 基础 CI：锁定依赖、pytest 覆盖率门槛与 Core 镜像构建 |

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

## docs/test-plans/（配套 Design Note 的测试计划）

| 文件 | 分类 | 用途 |
|---|---|---|
| AF-101.md | 质量 | 已批准的 AF-101 Test Plan、测试先行顺序与失败判定 |
| AF-102.md | 质量 | 已批准的 AF-102 Test Plan 与真实 Docker 验证证据 |
| CI-001.md | 质量 | 已批准的 CI-001 Test Plan，以红灯/绿灯真实 Actions 运行证明 Gate 生效 |

## src/aegisflow_core/（AF-101 模块化单体骨架）

| 路径 | 分类 | 用途 |
|---|---|---|
| app.py | 代码 | FastAPI 应用工厂、路由挂载与安全异常信封 |
| main.py | 代码 | ASGI 入口 `aegisflow_core.main:app` |
| settings.py | 配置 | `APP_ENV` 与 `APP_BASE_URL` 的最小 fail-fast 配置 |
| logging.py | 可观测 | 幂等 JSON stdout 日志基础 |
| __init__.py | 代码边界 | `aegisflow_core` 根包标记 |
| health/__init__.py | 代码边界 | Health 子包标记 |
| health/router.py | 代码 | 稳定的 `GET /health` 契约 |
| control_plane/__init__.py | 代码边界 | Control Plane 顶层包占位 |
| runtime/__init__.py | 代码边界 | Runtime 顶层包占位 |
| gateway/__init__.py | 代码边界 | Gateway 顶层包占位 |
| models/__init__.py | 代码边界 | Models 顶层包占位 |
| evaluation/__init__.py | 代码边界 | Evaluation 顶层包占位 |
| packs/__init__.py | 代码边界 | Application Packs 顶层包占位 |
| packs/delivery/__init__.py | 代码边界 | DeliveryPack 边界占位，不含 Agent 实现 |

## tests/（AF-101/AF-102 测试）

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
