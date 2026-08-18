# AegisFlow 完整项目指南

**状态：** 独立说明草案，不是仓库权威事实源  
**用途：** 帮助项目负责人、开发者、AI Agent 和面试官快速理解 AegisFlow 的产品、架构、实现状态、差距与后续开发方向。  
**原则：** 所有能力必须区分 IMPLEMENTED、PARTIAL、TARGET、ROADMAP，不得把目标描述成已经实现。

---

## 1. 项目定义

AegisFlow 是一个面向企业软件研发场景的生产级 Agent Control Plane。  
它不是一个普通聊天机器人，也不是一个单纯生成代码的 Coding Agent。它要解决的是：

> 当企业让 AI Agent 读取代码、调用工具、修改仓库、运行测试和创建 Pull Request 时，如何保证整个过程可靠、可恢复、受权限控制、可人工审批、可评测、可追踪和可审计。

首个应用包是 DeliveryPack，负责证明这套控制平面能够支撑一条真实的软件交付闭环。

**一句话定义：**
> AegisFlow 将 GitHub 仓库和 PRD、Issue、Bug 或功能需求，通过受控的多 Agent 执行、版本化上下文、确定性 Policy、隔离 Sandbox、人工审批和耐久工作流，转化为带测试及审查证据的 GitHub Draft Pull Request。

---

## 2. 核心业务闭环

AegisFlow 的目标 Golden Path 是：

```text
GitHub Repository
+
PRD / Issue / Bug / Requirement
        ↓
Intake
        ↓
Clarifier
        ├── 信息不足 → 等待人工澄清
        └── 信息完整
                ↓
Context
        ↓
Planner
        ↓
Policy Gate
        ├── DENY → 结束并记录审计
        ├── REQUIRE_APPROVAL → 等待人工决策
        └── ALLOW
                ↓
Executor
        ↓
Docker Sandbox
        ↓
代码修改、构建、测试、Lint
        ↓
Reviewer
        ├── REWORK → 返回 Executor
        ├── REJECT → 结束
        └── PASS
                ↓
Human Approval
        ↓
GitHub Draft Pull Request
        ↓
Trace + Cost + Evaluation + Audit
```

核心结果不是一段 Agent 回复，而是：
- 一个可由工程师继续 Review 的 Draft Pull Request
- 完整的计划、Diff、测试、工具调用、风险、成本和审计证据

---

## 3. 产品范围

### 3.1 必须做深
- Agent Runtime
- Temporal Durable Workflow
- MCP Tool Gateway
- Policy Engine
- Human-in-the-loop
- Docker Sandbox
- PostgreSQL 业务持久化
- 多租户和 RBAC
- GitHub App 集成
- RAG 和版本化仓库上下文
- LiteLLM 模型路由与降级
- Evaluation
- Audit
- Trace、Metrics 和 Cost

### 3.2 做薄
Personal Workbench 只用于 Dogfooding，证明项目能够管理真实任务，而不是发展成独立产品。

### 3.3 Post-MVP
- OpsPilot 单场景模拟
- 默认关闭的本地 vLLM 路由
- GitHub Actions 只读 MCP

这些扩展必须复用现有控制平面端口，不能增加新的 DeliveryPack Agent 或绕过 Policy。

### 3.4 明确不做
- Kafka
- Terraform
- SFT / LoRA
- CrewAI
- 通用 ABAC 平台
- 微服务拆分
- 可视化 Workflow Builder
- 自动 Merge
- 自动生产部署
- mini-CodeRabbit 产品定位

---

## 4. 整体架构

```text
┌──────────────────────────────────────────────┐
│            Next.js Web Console               │
│ Dashboard / Runs / Approvals / Evals         │
│ Diff / Tests / Trace / Cost / Audit          │
└───────────────────────┬──────────────────────┘
                        │ OIDC / REST / Events
                        ▼
┌──────────────────────────────────────────────┐
│        AegisFlow Core — FastAPI 单体          │
│                                              │
│ control_plane  Tenant / RBAC / Approval      │
│ runtime        LangGraph / State / Context   │
│ gateway        GitHub / MCP / Policy/Sandbox │
│ models         LiteLLM / Routing / Cost      │
│ evaluation     Dataset / Regression / Report │
│ packs          DeliveryPack 六 Agent          │
└───────────────┬──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│              Temporal Worker                 │
│ Workflow / Retry / Timeout / Signal / Saga   │
└───────┬──────────────┬───────────────┬───────┘
        │              │               │
        ▼              ▼               ▼
 PostgreSQL       Redis Streams     MCP Gateway
 + pgvector       实时事件           Policy Gate
        │                              │
        │                       ┌──────┴──────┐
        │                       ▼             ▼
        │                    GitHub        Sandbox
        │
        ▼
 Langfuse + OpenTelemetry + Prometheus/Grafana
```

AegisFlow 必须保持模块化单体。不能为了看起来“企业级”而拆出大量微服务。

---

## 5. 状态所有权

同一种状态只能有一个权威所有者。

| 状态 | 权威所有者 | 持久位置 |
| :--- | :--- | :--- |
| Workflow 生命周期 | Temporal | Temporal Event History |
| 澄清、审批、CI 等耐久等待 | Temporal | Event History + PostgreSQL 投影 |
| Agent 图计算状态 | LangGraph | PostgresSaver |
| Tenant、RBAC、审批和版本事实 | Core Domain | PostgreSQL |
| 外部副作用幂等记录 | Gateway/Workflow | PostgreSQL |
| RAG 知识块 | Context Runtime | PostgreSQL + pgvector |
| 实时前端事件 | Presentation | Redis Streams |
| LLM Trace | Observability | Langfuse |
| 系统 Trace | Observability | OpenTelemetry Backend |
| 临时代码工作区 | Sandbox | 临时文件系统 |

**边界规则：**
- Temporal 不保存 Agent 推理细节。
- LangGraph 不拥有业务 Workflow 生命周期。
- PostgreSQL 不代替 Temporal 的执行历史。
- Redis 不作为业务事实源。
- Langfuse 不作为业务数据库。

---

## 6. 六个固定 Agent

### 6.1 Intake
负责：
- 解析 PRD、Issue、Bug 和 Requirement；
- 标准化任务；
- 提取目标、约束和验收条件；
- 生成稳定的幂等标识；
- 判断任务输入是否合法。

Intake 不修改代码，也不决定权限。

### 6.2 Clarifier
负责：
- 检测信息缺失；
- 发现模糊、矛盾或不可验证的要求；
- 生成最小必要澄清问题；
- 接收人工回复后更新结构化 Request。

需要跨进程、长时间等待时，由 Temporal 管理等待和 Signal；LangGraph 只处理恢复后的 Agent 状态。

### 6.3 Context
负责为后续 Agent 提供有依据的仓库上下文：
- 代码
- 测试
- 文档
- 配置
- ADR
- 依赖
- 符号
- Git 历史
- 历史 PR

所有证据应包含：
- `tenant_id`
- `repository_id`
- `branch`
- `commit_sha`
- `file_path`
- `line_number`
- `evidence`

### 6.4 Planner
负责：
- 生成实现计划；
- 识别受影响文件；
- 评估架构影响；
- 划分风险；
- 确定测试范围；
- 确定工具需求；
- 设置步骤、Token 和成本预算。

Planner 不修改代码，也不能批准自己的方案。

### 6.5 Executor
负责：
- Read → Search → Reason → Edit → Build → Test → Observe → Repair

Executor 采用：
- 外部确定性 Workflow + 内部有界 ReAct 循环

必须限制：
- 最大步骤数
- 最大工具调用数
- Token 预算
- 成本预算
- 超时
- 输出大小
- 工具 Allowlist
- 最大 Rework 次数
- 明确完成条件

Executor 的所有外部写操作都必须经过 Policy Gate。

### 6.6 Reviewer
根据以下证据进行审查：
- Requirement
- Plan
- Diff
- Test Results
- Tool Evidence
- Policy Decisions
- Execution Trace
- Risk

输出：
- PASS
- REWORK
- REJECT
- REQUIRE_HUMAN_APPROVAL

Reviewer 不能直接 Merge，也不能绕过人工审批。

---

## 7. Temporal、LangGraph、ReAct 和 MCP

### Temporal
**回答：** 任务如何在崩溃、超时、等待和重试之后继续可靠执行？  
**负责：** 长流程生命周期、Activity、Retry、Timeout、Signal、Human Wait、Worker Recovery、Saga/Compensation、外部副作用调度。

### LangGraph
**回答：** Agent 在局部任务内部如何改变结构化状态和选择下一节点？  
**负责：** Agent State、Agent Node、Conditional Edge、Checkpoint、Resume、Reviewer 路由、有界局部循环。

### ReAct
**回答：** Agent 在单次局部执行中如何循环进行 Reason、Act、Observe？  
ReAct 必须是有边界的，不能无限执行。

### MCP
**回答：** Agent 如何通过统一协议发现和调用工具？  
MCP 不是：
- Workflow Engine
- 权限系统
- Agent Framework

MCP 工具调用仍必须经过：
> Schema Validation → Parameter Normalization → Tenant/Repo Scope → Policy Gate → Approval Check → Idempotency Check → Execute → Result Validation → Audit

---

## 8. Policy 与权限

Policy Gate 必须在 Executor 之前执行，并包围每一次敏感工具调用。

```text
Planner
   ↓
Run-level Policy Gate
   ↓
Executor
   ↓
Tool Request
   ↓
Tool-level Policy Gate
   ↓
MCP / GitHub / Sandbox
```

**Policy 输入：**
- 用户角色
- tenant
- repository
- branch
- environment
- tool
- 参数
- 风险
- 审批状态
- 成本预算

**Policy 输出：**
- ALLOW
- DENY
- REQUIRE_APPROVAL

LLM 可以识别风险，但不能输出最终授权结论。

---

## 9. 多租户安全

所有租户所有的数据都必须具有 `tenant_id`。  
包括：
- Repository
- Run
- RunStep
- Approval
- AuditEvent
- ToolExecution
- Evaluation
- ModelUsage
- Credential Reference
- RAG Chunk

授权必须在服务端和数据库查询层完成，不能只在 Prompt 中要求 Agent“不读取其他租户”。

---

## 10. RAG 与仓库上下文

AegisFlow 的核心不是普通互联网 RAG，而是 **Versioned Repository RAG**。

索引维度至少包括：
- `tenant_id`
- `repository_id`
- `branch`
- `commit_sha`
- `file_path`
- `symbol`
- `language`
- `chunk_type`
- `content`
- `embedding`

正确检索流程：
```text
当前认证身份
        ↓
Tenant / Repository / Branch 权限条件
        ↓
Query Rewrite
        ↓
Vector + BM25 + Symbol Search
        ↓
Merge / Dedup
        ↓
Reranker
        ↓
防御性权限复核
        ↓
Context Compression
        ↓
Token Budget
        ↓
Agent
```

权限过滤必须进入每个检索查询，不能等召回完成后才过滤。

---

## 11. Memory

AegisFlow 的 Memory 可以分为：

| Memory | 实现 |
| :--- | :--- |
| Working Memory | LangGraph Structured State |
| Durable Workflow History | Temporal Event History |
| Semantic Memory | PostgreSQL + pgvector |
| Approved Experience | 经过评测和人工确认的经验 |

Temporal Event History 是耐久执行记录，不等于 Agent 长期语义记忆。  
未经评测、失败或可能包含污染数据的执行轨迹，不能自动进入长期经验库。

---

## 12. GitHub 集成

推荐边界：
```text
GitHub App
  ↓
Installation / Permission / Webhook
  ↓
AegisFlow GitHub Service
  ↓
Policy + Idempotency + Audit
  ↓
MCP Adapter / Workflow Activity
```

写操作必须具备：
- 最小权限
- Tenant/Repo/Branch Scope
- 幂等键
- 本地 Side Effect Ledger
- 远端资源核对
- AegisFlow Marker
- 审计记录
- 失败分类
- 重试策略

**AI 不得：**
- 自动 Merge PR
- 直接推送 main
- 删除仓库
- 修改 Secret
- 自动部署生产环境

---

## 13. Sandbox

Executor 不应在 Core 宿主环境直接运行任意代码。  
Sandbox 必须：
- 使用固定、可信镜像；
- non-root；
- read-only root filesystem；
- 禁止 Docker socket；
- 默认禁止网络；
- 限制 CPU、内存、磁盘、PID 和时间；
- 限制工作区；
- 限制 Secret；
- 支持超时和强制终止；
- 支持 TTL 清理；
- 保存必要的测试和 Diff 证据。

依赖安装应优先使用：
- 预构建镜像
- 离线缓存
- 锁文件
- 明确批准的临时网络策略

---

## 14. 数据层

### PostgreSQL
保存业务事实：
- Tenant
- User
- Repository
- RepositoryVersion
- Run
- RunStep
- Approval
- AuditEvent
- ToolExecution
- SideEffect
- PromptVersion
- WorkflowVersion
- Evaluation
- ModelUsage
- Cost

### pgvector
保存：
- 代码块
- 文档
- ADR
- 测试
- 语义索引
- 经批准的经验

### Redis Streams
只用于：
- 实时 UI 事件
- 轻量通知
- SSE/WebSocket 推送

Redis 故障不能造成业务事实丢失。

---

## 15. Model Gateway

所有 Agent 必须通过统一 ModelGateway 使用模型。

```text
Agent
  ↓
ModelGateway
  ↓
LiteLLM
  ├── Primary
  ├── Fallback
  └── Optional local vLLM
```

Model Gateway 负责：
- Provider 抽象
- 路由
- Fallback
- Retry
- Circuit Breaker
- Token 限制
- 成本统计
- 模型策略
- Prompt 版本关联
- 错误分类

本地 vLLM 只属于可选 Post-MVP 路由，默认关闭，不能成为生产启动依赖。

---

## 16. Observability

### Langfuse
负责：
- Prompt
- Completion
- Agent Trace
- Model
- Token
- Cost
- Latency
- Agent Evaluation

### OpenTelemetry
负责：
- HTTP
- Temporal Activity
- PostgreSQL
- MCP
- GitHub API
- Sandbox
- 工具执行

### Prometheus/Grafana
展示：
- 任务成功率
- Tool Call 成功率
- P50/P95/P99
- Token/Run
- Cost/Run
- Workflow Recovery
- Queue Depth
- Fallback Rate
- Failure Distribution

**关联字段应统一：**
- `tenant_id`
- `run_id`
- `trace_id`
- `workflow_version`
- `agent_name`
- `tool_name`
- `model`

---

## 17. Evaluation

评测数据集：
- SWE-bench 子集
- Delivery Golden Set
- Security Injection Set
- Historical Set
- Single-Agent Baseline

核心指标：
- **任务级：** Task Success Rate, Draft PR Success Rate, Patch Apply Rate, Human Acceptance Rate, First Pass Rate, Rework Rate
- **Agent 级：** Agent Success Rate, Average Steps, Loop Count, Token Usage, Context Hit Rate, Latency
- **Tool 级：** Tool Selection Accuracy, Parameter Accuracy, Tool Success Rate, Retry Rate, Duplicate Side Effects, Permission Denial Accuracy
- **RAG 级：** Recall@K, Precision@K, MRR, NDCG, Citation Accuracy, Groundedness
- **系统级：** P50/P95/P99, Worker Recovery Time, Signal Loss, Cost/Task, Fallback Success

指标状态必须区分：`TARGET`、`BASELINE`、`ACHIEVED`、`SLA`。  
只有固定环境和测试集上可复现的结果才能称为 `ACHIEVED`。

---

## 18. 目标前端

目标前端是 Next.js Console，但当前仓库没有产品 Web 前端实现。

目标页面：
- Dashboard
- Repositories
- Runs
- Run Detail
- Approvals
- Evaluations
- Audit Logs
- Settings

最重要的是 Run Detail：
- Run Metadata
- Repository / Branch / Commit
- Requirement
- Fixed DeliveryPack DAG
- Current Agent
- Agent Steps
- Tool Calls
- Context Citations
- Plan
- Diff
- Tests
- Risk
- Approval
- Token / Cost
- Trace
- Audit

状态图必须只读，不能发展成 Workflow Builder。

---

## 19. 当前真实实现状态

### 19.1 已有基础
当前代码库已经包含：
- FastAPI 模块化单体骨架
- SQLAlchemy 2.0 与 Alembic
- PostgreSQL 领域模型
- OIDC/JWKS 相关组件
- RBAC 与租户隔离组件
- 审批、审计和版本模型
- GitHub Webhook 验证
- Webhook 防重放和审计
- GitHub 读写适配组件
- LangGraph Gate 1A
- LangGraph Gate 1B
- 六个 DeliveryPack Agent 契约
- Policy Gate
- Prompt Injection 防护组件
- Docker Sandbox Broker
- Temporal Workflow 与 Activity 契约
- PostgreSQL LangGraph Checkpointer
- LiteLLM Model Gateway
- Circuit Breaker 和 Fallback
- Evaluation 数据结构与回归组件
- OpenTelemetry、Metrics 和 Langfuse 组件
- Helm/k3s 相关部署证据与测试
- 大量单元、组件、安全、故障注入和 E2E 测试

### 19.2 当前 FastAPI 边界
主要接口包括：
- `GET  /health`
- `POST /webhooks/github`
- `GET  /v1/tenants/{tenant_id}/runs/{run_id}/graph`
- `GET  /metrics`

独立 Sandbox Broker：
- `POST /v1/sandboxes/run`

### 19.3 当前 Docker Compose
当前 Compose 包含：
- PostgreSQL
- Redis
- Temporal PostgreSQL
- Temporal Server
- AegisFlow Core
- Temporal Worker
- Sandbox Broker

当前 Compose 不包含：
- Next.js Web
- 独立 LiteLLM Proxy
- Langfuse 服务
- Prometheus
- Grafana
- Temporal Web UI

### 19.4 尚未完全接通的生产链路
当前最大问题不是缺少组件，而是生产装配尚未形成完整闭环：

```text
GitHub Webhook
  ↓
NoOpWebhookDispatcher
  ✕
Temporal Workflow
```

Webhook 能够校验、审计并接受事件，但当前主应用使用 `NoOpWebhookDispatcher`，不会真正启动 Temporal Workflow。  
Temporal Worker 默认使用 `UnconfiguredGraphPort`，因此 Worker 虽然注册了 Workflow 和 Activity，但默认没有连接真实 LangGraph Gate 1B。  
`build_gate1b_graph()` 目前主要由 E2E 测试组装，未进入生产 Worker 装配。

其他主要缺口：
- 缺少完整 Run Create/List/Cancel/Retry API；
- 缺少 Clarification Signal API；
- 缺少 Approval Decision API；
- Redis Streams 实时事件链路未完整落地；
- 没有 Next.js Console；
- 没有产品级端到端浏览器操作闭环；
- 部分能力通过组件测试和受控证据验证，不等于完整生产部署。

因此准确描述是：
> AegisFlow 已经拥有较完整的控制平面后端组件、Agent 图、安全治理和测试证据，但真实入口、耐久工作流、生产 LangGraph 和前端之间尚未全部装配成可操作产品。

---

## 20. 历史验收证据

仓库验收资料记录过：
- 远程 CI：570 passed、1 skipped；
- Branch Coverage：90.99%；
- 83 项安全测试通过；
- 20/20 故障注入成功；
- 重复副作用为 0；
- Signal 丢失为 0；
- 100 用户压测共 1,906 请求、0 失败；
- 聚合 p95 约 140 ms。

这些数字只能在其记录的固定环境、提交和测试条件下称为 ACHIEVED，不能推广成生产 SLA。

---

## 21. 后续正确开发顺序

当前正式治理状态记录 M1–M5/Gate 4 已验收，并允许 AF-R01–AF-R03 可选 Post-MVP 工作。若要继续完善核心产品，需要先由 Project Owner 明确新的 Issue 范围。

### 第一阶段：接通生产执行链
```text
GitHub Webhook
→ Durable Dispatcher
→ Temporal Workflow
→ Activity
→ Production LangGraph Adapter
→ Gate 1B
```
**验收：**
- Webhook 能创建唯一 Run；
- 重复 Webhook 不重复启动；
- Worker 崩溃后恢复；
- 不重复创建 Branch 或 PR；
- Trace、审计和成本可关联。

### 第二阶段：补齐 Control Plane API
实现：
- `POST /v1/tenants/{tenant_id}/runs`
- `GET  /v1/tenants/{tenant_id}/runs`
- `GET  /v1/tenants/{tenant_id}/runs/{run_id}`
- `POST /v1/tenants/{tenant_id}/runs/{run_id}/cancel`
- `POST /v1/tenants/{tenant_id}/runs/{run_id}/retry`
- `POST /v1/tenants/{tenant_id}/runs/{run_id}/clarifications`
- `GET  /v1/tenants/{tenant_id}/approvals`
- `POST /v1/tenants/{tenant_id}/approvals/{id}/decision`

必须覆盖：OIDC、RBAC、Tenant Isolation、幂等、审计、负向安全测试。

### 第三阶段：实时事件
```text
Worker
→ Redis Streams
→ FastAPI SSE/WebSocket
→ Console
```
PostgreSQL 和 Temporal 仍然是事实源，Redis 仅提供实时投影。

### 第四阶段：Next.js Console
优先实现：
- Run List
- Run Detail
- Approval Inbox
- Diff/Test Evidence
- Trace/Cost
- Audit
- Evaluation

不要优先做动画和复杂 Dashboard。

### 第五阶段：真实 E2E
```text
Test Repository
+
Test Issue
→ Run
→ Clarification
→ Context
→ Plan
→ Policy
→ Sandbox Patch
→ Tests
→ Review
→ Approval
→ Draft PR
```
必须保存：
- GitHub 资源 ID
- Commit SHA
- Test Evidence
- Trace ID
- Cost
- Approval
- Audit
- Cleanup 结果

### 第六阶段：可选 Post-MVP
只有核心链路稳定后再考虑：
- OpsPilot 模拟诊断
- 默认关闭的本地 vLLM
- GitHub Actions 只读 MCP

---

## 22. 固定开发流程

每个实现任务必须遵循：
```text
读取权威文档
→ 选择 status:ready Issue
→ 确认依赖和验收条件
→ 编写或评审 Design Note
→ 编写 Test Plan / 失败测试
→ 最小实现
→ 执行测试
→ 安全与质量检查
→ 更新文档和 Traceability
→ One Issue / One Branch / One PR
→ Human Review
→ Human Merge
→ Handoff
```

**禁止：**
- 绕过 Issue；
- 顺手重构；
- 未批准新增依赖；
- 删除断言让测试通过；
- 使用真实 Secret；
- AI 自己审批或 Merge；
- 将目标能力写成已完成；
- 直接修改 main。

---

## 23. Definition of Done

一项功能只有在以下条件满足后才算完成：
1. 验收条件全部满足；
2. 正常和失败路径均验证；
3. 外部副作用经过幂等测试；
4. 安全改动具有负向测试；
5. 跨租户访问测试通过；
6. Temporal replay/retry/signal 被验证；
7. LangGraph checkpoint/resume 被验证；
8. 文档和 Traceability 同步；
9. 测试命令、环境、结果和限制完整记录；
10. 无 Secret 泄露；
11. CI 通过；
12. 人工 Review；
13. 人工 Merge。

---

## 24. 面试表达

**推荐表述：**
> AegisFlow 不是一个简单的 Coding Agent，而是一个面向软件研发 Agent 的控制平面。我用六个固定 Agent 实现需求到 Draft PR 的交付链路，Temporal 管理耐久工作流和外部副作用，LangGraph 管理 Agent 状态图，MCP 统一工具调用，Policy Gate 提供确定性权限治理，PostgreSQL 保存业务事实，Redis 负责实时事件。系统还覆盖多租户、RBAC、Sandbox、幂等、模型降级、Trace、成本、评测和审计。当前已经具备核心后端组件与测试证据，下一步重点是接通 Webhook、Temporal 和生产 LangGraph，并完成可操作的 Next.js Console。

**不要表达成：**
- 所有企业级能力已经完整上线生产。

**正确表达应当强调：**
- 已实现组件；
- 已获得的测试证据；
- 当前生产装配缺口；
- 对状态、权限、失败恢复和评测的工程理解；
- 不把目标指标包装成生产 SLA。

---

## 25. 最终原则

```text
Agent Control Plane First
+
Fixed DeliveryPack
+
Modular Monolith
+
One Source of Truth per State
+
Deterministic Policy
+
Bounded Agent Autonomy
+
Least Privilege Tools
+
Human Approval for Risk
+
Durable External Side Effects
+
Versioned Repository Context
+
Evaluation Before Release
+
Evidence Before Claims
```

AegisFlow 最终要证明的不是“Agent 能生成代码”，而是：
> **Agent 能在一个有状态、有权限、有失败、有成本、有审计要求的真实工程系统中可靠工作。**