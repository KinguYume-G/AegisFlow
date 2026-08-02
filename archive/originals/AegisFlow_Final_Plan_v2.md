# AegisFlow 最终方案 v2.0（定稿·不再更改方向）

> **Agent Control Plane，以"需求到交付"研发闭环为首个应用包**
> 本文档取代此前所有选型讨论与 v1.0 执行方案。开工依据只看这一份。

---

## 一、最终定位

**项目名**：AegisFlow — Production-Grade Agent Control Plane
**副标题**：Enterprise Software Delivery Agent Platform

**一句话**：企业把 AI agent 接进研发流程时，AegisFlow 负责它们的可靠执行、工具权限、人工审批、评测与成本——并用一条"需求 → 交付"的完整研发闭环证明这套底座真的能跑生产。

### 叙事主轴（README、简历、面试口径必须统一）

> 我做的不是代码审查工具，是 Agent 控制平面。研发交付是压力最大的那个负载，所以我用它来证明底座。

**为什么不是代码审查产品**：AI 代码审查是 2026 红海（CodeRabbit 约 14 万付费用户、Copilot Reviews 已捆绑分发、Anthropic 已入场）。但红海市场 ≠ 红海岗位——恰恰因为巨头在这个赛道砸钱，Kimi、通义、字节的 coding agent 团队才在大量招人。正确做法是**进这个域，但站在治理层**，而不是造 mini-CodeRabbit。

**市场对"哪一层最值钱"的官方认证**：GitHub Agent HQ 把 control plane 明确称为"你的 agent 治理层"，提供安全策略、审计日志、agent 白名单、沙箱执行、模型访问控制。而这一层远未闭合——2026 年初的行业判断是"主流平台都支持 MCP，但策略、审计、跨平台管控仍然落后，没有任何厂商闭合完整回路"。GitHub 只治理自己生态。**跨生态、可自托管、带 Policy Engine 与评测的控制平面，就是空位。**

---

## 二、核心闭环（应用包：DeliveryPack）

```
需求 / PRD / Bug / GitHub Issue
        ↓  Intake        解析来源、幂等去重
        ↓  Clarifier     找出缺失信息，生成澄清问题（HITL 第一次介入）
        ↓  Context       RAG 检索代码、文档、ADR、历史 PR
        ↓  Planner       架构方案 + 任务拆分 + 风险分级
        ↓  [Policy Gate] 权限、成本预算、高危操作确定性检查
        ↓  Executor      沙箱内改码 + 跑测试
        ↓  Reviewer      汇总证据，形成结论
        ↓  [人工审批]     高风险必须过人（HITL 第二次介入）
        ↓  Draft PR / 部署
        ↓  Trace + 成本 + 评测 + 失败复盘写回知识库
```

**六个 Agent，不多不少**：Intake / Clarifier / Context / Planner / Executor / Reviewer。
（原蓝图的 Quality、Test、Architecture、Release、Security 全部合并进 Planner 的风险分级与 Reviewer 的证据汇总——它们证明的是同一批平台能力，重复投入零收益。）

---

## 三、范围裁决（最终，不再讨论）

| 内容 | 裁决 |
|---|---|
| Control Plane（租户/RBAC/注册表/Policy/审批/审计） | **做深** |
| Agent Runtime（LangGraph 图/Memory/Context 压缩/Checkpoint） | **做深** |
| Workflow Runtime（Temporal/幂等/Retry/Timeout/Saga/失败重放） | **做深，第一攻坚点** |
| MCP Tool Gateway + Policy Engine + 沙箱 | **做深，差异化护城河** |
| 评测（Golden Dataset + 回归 + CI 门禁） | **做深** |
| 模型网关（LiteLLM 路由 + 熔断降级） | **做** |
| 可观测（Langfuse + OTel + Prometheus/Grafana） | **做** |
| Personal Workbench | **做到最薄**：用平台管自己的 XueMai / SynTour / Omni-Assistant，外加一条实习跟踪流。目的只有一个——面试能说"这系统我每天在用" |
| OpsPilot | **ROADMAP**。仅当 Gate 1-4 全过且有余力，做单场景模拟数据版 |
| ForgeFDE 交付管理 | **否决**。其"需求澄清→价值评估→任务拆分"已被吸收为上面的 Clarifier + Planner |
| Kafka | **砍**（Redis Streams / Temporal signal 替代；面试讲清"为什么我这规模不需要 Kafka"反而加分） |
| Terraform | **砍**（Helm + GitHub Actions 足够） |
| SFT / LoRA | **砍**（对 Agent 编排岗不加分，与算法博士正面竞争是劣势） |
| CrewAI Adapter / A-B | **砍**（讲清 LangGraph 取舍即可） |
| ABAC | **砍**，RBAC 做扎实 |
| 10 个微服务 | **砍**，改模块化单体 AegisFlow Core |
| 可视化 Workflow Builder | **砍**，只做只读运行状态图 |
| vLLM | **降级为可选**，只在有 GPU 时作为降级链最后一环 |

---

## 四、架构（模块化单体）

```
┌──────────────────────────────────────────────┐
│            Next.js Web Console               │
│  Runs · Traces · Evals · Approvals · Cost    │
└───────────────────────┬──────────────────────┘
                        │ OIDC / Rate Limit
┌───────────────────────▼──────────────────────┐
│      AegisFlow Core（单一 FastAPI 服务）       │
│  control_plane/  租户·RBAC·注册表·审批·审计    │
│  runtime/        LangGraph 图·Memory·压缩     │
│  gateway/        MCP 网关·Policy Engine·沙箱   │
│  models/         LiteLLM 路由·熔断·降级        │
│  evaluation/     Golden·回归·成本统计          │
│  packs/delivery/ 六 Agent 定义与 Prompt        │
└────────┬──────────────────────────┬──────────┘
         │                          │
   Temporal Worker              GitHub App
 （durable·幂等·HITL signal）   （Issue/PR Webhook）
         │
┌────────▼─────────────────────────────────────┐
│  PostgreSQL(+pgvector) / Redis(Streams)      │
└──────────────────────────────────────────────┘
   OpenTelemetry → Prometheus/Grafana + Langfuse
   Docker Compose（开发）→ k3s + Helm（演示）
```

**分层铁律（面试高频考点，背下来）**：
- **LangGraph** 管 agent 内部状态图：条件路由、并行、Reviewer 汇总、节点重放
- **Temporal** 管跨服务长流程：等待澄清回复、等待人工审批、等待 CI、worker 崩溃恢复、Saga 补偿
- 判断阈值：有外部副作用 + 等待时长超过分钟级 + 失败成本高 → 上 Temporal；否则 LangGraph 单层够用

---

## 五、12 周执行计划（带验收门与止损）

**全局止损**：Gate 不过，下一阶段新功能冻结。写文档/画图时间不得超过写代码时间的 20%。

### 第 1-3 周｜闭环跑通（面试可用最低线）
- FastAPI 单体骨架 + PostgreSQL + Redis + Docker Compose 一键起
- 六 Agent LangGraph 图跑通：Issue/PRD → 澄清 → RAG → 规划 → 沙箱改码 → 审查 → Draft PR
- GitHub App + GitHub MCP；Langfuse 接入（步骤级 Trace + Token 成本）
- **Gate 1**：投一个真实需求，产出带证据的方案 + Draft PR + 完整 Trace。跑不通 → 砍 Executor，先保"需求到方案"链路

### 第 4-6 周｜可靠运行时（技术制高点）
- Temporal 外层包裹 LangGraph；审批 = durable signal
- 幂等键 `(workflow_id, step_id)`；PostgresSaver checkpoint
- **重点攻坚**：kill worker → 5 秒内从 checkpoint 恢复 → 零重复副作用（不重复建 Branch/PR）
- 模型网关：LiteLLM 路由 + 主模型故障熔断降级链
- **产出一篇技术博客**：《kill -9 之后：Temporal + LangGraph 双层架构的崩溃恢复与幂等实战》（含源码级分析，这篇博客的面试价值 ≥ 一个功能模块）
- **Gate 2**：恢复演示视频录完 + 博客发布

### 第 7-9 周｜治理层（护城河）
- 多租户 + RBAC + OIDC + 审计日志
- MCP Gateway 权限治理 + Policy Engine（确定性规则，**LLM 不直接决定权限**）+ 沙箱执行
- Prompt Injection 拦截：在 RAG 文档埋注入指令 → 标记安全事件 → Policy 拒绝 → 审计留痕
- Prompt / Workflow 版本管理
- **Gate 3**：注入拦截可复现 + 跨租户访问被拒测试通过

### 第 10-12 周｜评测、部署、包装
- Golden Dataset + 回归测试进 GitHub Actions：新 Prompt 导致指标下降 → CI 拦截发布
- k3s + Helm；Grafana 看板（成功率/成本/延迟/失败节点）
- 100 并发控制面压测（locust）+ 一页报告
- Personal Workbench 薄版接自己的三个项目
- README / 文档 / 演示视频 / 简历打磨
- **条件延伸**：OpsPilot 单场景模拟版（仅 Gate 1-3 全过且有余力）
- **Gate 4**：四个必做演示全部现场可复现

---

## 六、评测体系

不从零造数据，也不盲抄公开集（Devign / Big-Vul 是 C/C++ 函数级，与需求-交付场景不匹配）。最终配方：

1. **SWE-bench 子集**（10-15 个 Python instance）——真实 Issue-修复对，与本场景最匹配
2. **自造注入集**（15-20 个）——在自己仓库人工注入典型缺陷（SQL 注入、Secret 硬编码、未轮换 token、越权接口），真值已知，检出率/误报率可精确算
3. **真实历史集**（5-10 个）——XueMai / SynTour 的历史真实 bug

**指标**：任务完成率、Tool Call 成功率、缺陷检出率、误报率、Patch 可应用率、单需求 Token 成本、p95 延迟、人工干预率。每个数字都要出现在 Grafana 和简历上。

---

## 七、面试演示（4 必做 + 1 条件）

1. **正常闭环**：需求投入 → 澄清 → 规划 → 沙箱改码 → 审批 → Draft PR，全程 Trace + 成本可见
2. **Worker 崩溃恢复**（核心杀手锏）：现场 kill → 5 秒恢复 → 零重复副作用
3. **模型降级**：关主模型 → 熔断打开 → 切备用 → Trace 显示完整链路
4. **Prompt Injection 拦截**：RAG 文档藏注入 → Policy 拒绝 → 审计留痕
5. （条件）**Prompt 回归被 CI 拦截**——第四阶段完成则升为必做，对口字节评测岗与上海 AI 实验室评测体系要求

---

## 八、目标公司对标（写进 README 的 "Why this project"）

| 公司 | 对标方向 | AegisFlow 的对应 |
|---|---|---|
| 上海 AI 实验室 | 智能体系统研发（工具调用/记忆/任务编排/执行链路/评测体系） | Control Plane + Runtime + 评测中心，逐条对应 JD |
| 月之暗面 | Kimi Coding Agent / Sandbox infra | 六 Agent 交付链 + 沙箱 + 工具治理 |
| 蚂蚁 | Agentar 金融级高可信 | RBAC + 审计 + MCP 权限 + Policy Engine |
| 阿里通义 | AI 全栈（MCP/Eval/Tracing/Guardrail/Harness/智能路由） | 模型网关路由降级 + Guardrails + Langfuse |
| 字节 | Agent 评测 / 扣子 | Golden Dataset + CI 回归门禁 + Tool Call 成功率 |
| MiniMax / 阶跃 | 多 Agent 编排 / 云原生 | LangGraph×Temporal 双层 + K8s/Helm |

---

## 九、包装

- **GitHub**：仓库只放 AegisFlow Core。README 第一屏 = 一句话价值 + 架构图 + kill-worker 恢复 GIF + 评测数字表 + 一键启动
- **原 2069 行蓝图** → 改名 `docs/DESIGN_BLUEPRINT.md`，定位为"系统设计文档"。它从执行计划降级为视野证明，这个降级反而让它变成资产
- **必备文档**：README（中/英）、ARCHITECTURE、**ADR**（重点写"为什么砍掉 Kafka / 微服务 / OpsPilot"——工程取舍本身就是面试素材）、EVALUATION、RELIABILITY、LOAD_TEST、THREAT_MODEL、ROADMAP
- **简历一句话**：
  > 设计并实现生产级 Agent Control Plane（LangGraph + Temporal + MCP + FastAPI + PostgreSQL + Redis + K8s），支持多租户 RBAC、持久执行与崩溃恢复（worker 被杀后 5 秒内从 checkpoint 续跑、零重复副作用）、MCP 工具权限治理与 Prompt 注入拦截、Prompt 回归 CI 门禁；以"需求到交付"研发闭环应用包验证平台，Golden Dataset 上任务完成率 X%、缺陷检出率 Y%、单需求成本 $Z。

---

## 十、面试标准话术（背下来）

> 这份完整蓝图是我对企业级 Agent 平台的整体理解。考虑到个人开发的时间成本，我优先落地了最核心的可靠运行时、工具治理与一条真实研发交付闭环。在这个范围里我深度解决了状态恢复、幂等、权限和评测问题——为此我读了 Temporal 和 LangGraph 的源码。如果给我更多时间，我会基于这个稳固底座按蓝图方向扩展 OpsPilot。

**为什么"砍需求"反而显得强**：面试官要招的是能做出正确工程取舍的人。说"我做了 20 个微服务"的实习生，他知道是浅尝辄止；说"我理解全貌，但选择先把状态管理这块硬骨头啃透"的实习生，他会眼前一亮——因为这就是技术 Leader 每天在做的事。

---

## 今天就做的三件事

1. 仓库结构从 10 个 services 改成单体模块目录（control_plane / runtime / gateway / models / evaluation / packs）
2. 把 OpsPilot、Personal Workbench 完整章节剪切进 `ROADMAP.md`，原蓝图改名 `docs/DESIGN_BLUEPRINT.md`
3. 起 Docker Compose 骨架：FastAPI + PostgreSQL + Redis，跑通 healthcheck

**选型结束。从这一刻起，剩下的全是执行。**
