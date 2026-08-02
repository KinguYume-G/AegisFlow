# 00 — Project Charter

## 项目身份

- **项目名**：AegisFlow
- **定位**：Production-Grade Agent Control Plane
- **副标题**：Enterprise Software Delivery Agent Platform
- **首发应用包**：DeliveryPack
- **主叙事**：不是代码审查工具，而是用研发交付负载证明 Agent 控制平面能跑生产。

## 项目使命

建立一套跨模型、跨工具、可自托管的 Agent Control Plane，使企业能够安全、可靠、可审计、可评测地把 AI Agent 接入研发流程。

## 核心问题

AegisFlow 必须解决：

- 长流程执行中断与状态恢复；
- 外部副作用重复执行；
- 工具越权与高风险操作审批；
- Prompt / Workflow 无版本；
- 模型故障导致流程崩溃；
- 无法跟踪节点、成本和质量；
- 多租户数据隔离；
- Prompt Injection 诱导高危工具调用；
- 缺乏可复现评测与 CI 回归门禁。

## 产品边界

### 做深

- Control Plane
- Agent Runtime
- Temporal Workflow Runtime
- MCP Gateway
- Policy Engine
- Sandbox
- Evaluation
- Model Gateway
- Observability

### 做薄

Personal Workbench，仅用于 Dogfooding。

### Roadmap

OpsPilot 单场景模拟版，只有 Gate 1–4 全部通过后才允许启动。

### 明确不做

- Kafka
- Terraform
- SFT / LoRA
- CrewAI Adapter
- 通用 ABAC 平台
- 微服务拆分
- 可视化 Workflow Builder
- mini-CodeRabbit 产品定位

## 不可变产品契约

DeliveryPack 六个命名 Agent：

1. Intake
2. Clarifier
3. Context
4. Planner
5. Executor
6. Reviewer

产品文档、UI、Trace 和面试叙事必须统一命名。

## 成功定义

### Gate 1

真实需求能够产生澄清记录、带引用上下文、方案和任务拆分、沙箱修改、Review 证据、Draft PR、完整 Trace 与成本记录。

### Gate 2

- Worker 终止后可恢复；
- 外部副作用重复次数为 0；
- 主模型故障后可降级；
- 恢复和幂等有可重复测试证据。

### Gate 3

- 跨租户访问被拒；
- RBAC 和 MCP Scope 生效；
- Prompt Injection 不可绕过确定性 Policy；
- 审计记录完整。

### Gate 4

- Golden Dataset 可重复运行；
- Prompt 回归进入 CI；
- k3s + Helm 可部署；
- Grafana 展示核心指标；
- 100 并发控制面压测完成；
- 四个必做演示现场可复现。

## 指标声明

- `TARGET`：目标，尚未测量；
- `BASELINE`：第一次测量；
- `ACHIEVED`：固定环境和测试集上复现；
- `SLA`：只有生产运营后才能声明。

简历和 README 只能使用 `ACHIEVED`。

## 治理角色

| 角色 | 责任 |
|---|---|
| Project Owner | 最终方向、Secret、审批与 Merge |
| Chief Architect / Tech Lead | 架构、ADR、Issue 设计、质量门 |
| AI Developer | Issue 范围内设计、测试和实现 |
| Human Reviewer | Review、风险判断、Merge |
| Security Reviewer | 高风险变更与权限审查 |
| Release Owner | Gate 验收与发布 |

AI 不得同时担任开发者、最终 Reviewer 和 Merger。

## 工程原则

- Documentation First
- Architecture First
- Test First
- Security by Default
- Small Iterations
- GitHub Driven
- Evidence over Claims
- Deterministic Guardrails over LLM Decisions
- Modular Monolith before Microservices
- One Source of Truth per State

## 变更控制

改变定位、首发应用包、LangGraph/Temporal 边界、消息基础设施、持久化系统、权限模型、安全边界、Gate 或微服务策略时，必须新建 ADR 并由 Project Owner 接受。
