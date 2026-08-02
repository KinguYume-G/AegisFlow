# M1 Design Bundle — Shared Cross-Issue Contracts (AF-104–AF-110)

> 状态：**Draft v4**，等待 Project Owner / Human Reviewer 最终批准。本文是当前完整契约，不依赖任何未入库的历史草稿。批准前不得据此实现 AF-104–AF-110，也不得调整这些 Issue 的状态。

## 1. 范围与当前事实

- AF-101、AF-102、AF-103 与 CI-001 已完成 Human Merge 和验证。
- AF-103 GitHub Issue #12 已于 2026-08-02 关闭为 `COMPLETED`，生命周期标签为 `status:verified`。
- 本 Bundle 只覆盖 DeliveryPack 的 Intake、Clarifier、Context、Planner 契约、进程内 clarification HITL、初始 Langfuse tracing，以及 Gate 1A 进程内 E2E。
- 不包含真实 Model Provider、数据库写入、Temporal durable HITL、Policy Gate、Executor、Reviewer、MCP Registry 或部署能力。
- 实施顺序固定为：`AF-104 → AF-105 → AF-106 → AF-107 → AF-108 → AF-109 → AF-110`。只有当前 Issue 的 Design Note/Test Plan 获批、依赖已 Human Merge、Issue 为 `status:ready` 时才能开工。
- AF-106 的 canonical `Dependencies` 仍只记录 AF-103；本 Bundle 追加 AF-104/AF-105 为实施顺序门禁，不改写 75 条 canonical Backlog。

## 2. 文件与 Schema 所有权

| Issue | 所有内容 |
|---|---|
| AF-104 | `contracts/determinism.py`、`contracts/normalized_request.py`、`intake/` |
| AF-105 | `contracts/clarification.py`、`clarifier/{agent,ports,fakes}.py` |
| AF-106 | `contracts/context_package.py`、`context/`、基础 context fixtures |
| AF-107 | `contracts/measurement.py`、`contracts/plan.py`、`planner/` |
| AF-108 | `clarifier/hitl.py`；不得创建顶层 `packs/delivery/hitl.py` |
| AF-109 | `runtime/tracing.py`、`runtime/langfuse_smoke.py`、`langfuse-smoke.yml` |
| AF-110 | `runtime/state.py`、`runtime/graph.py`、Gate 1A fixtures 与 E2E tests |

`packs/delivery/contracts/__init__.py` 由 AF-104 创建，仅保留包说明，不作为跨文件 re-export 汇聚点。破坏性 Schema 变更必须提高 `schema_version` 并走新的 Design Note；不得静默改变 v1 字段语义。

## 3. 确定性端口

AF-104 定义：

```text
class Clock(Protocol):
    def now(self) -> datetime: ...

class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
```

- `SystemClock` 返回 timezone-aware UTC 时间；`FixedClock` 返回构造时传入的固定 UTC 时间。
- `RandomIdGenerator` 使用 `uuid4()`；`SequentialIdGenerator(seed)` 使用固定 namespace、seed 与递增计数派生 UUID5。
- 只有实际需要时间/ID 的组件才注入对应端口。`IntakeAgent` 只注入 `Clock`；AF-108 Gateway 与 AF-110 runner 注入 `IdGenerator`。
- 业务方法内部不得直接调用 `datetime.now()`/`uuid4()`。

## 4. NormalizedRequest 契约

```text
class NormalizedRequest(BaseModel):
    schema_version: Literal[1] = 1
    source_type: Literal["prd", "bug", "github_issue", "feature_request"]
    source_ref: str | None       # 最长 2,048 字符
    title: str                   # 最长 500 字符
    body: str                    # 最长 1,000,000 字符
    idempotency_key: str         # 64 位小写 SHA-256 hex
    received_at: datetime        # timezone-aware UTC
```

规范化算法固定如下：

1. 对 `title`/`body` 做 Unicode NFKC；把 CRLF/CR 转为 LF。
2. 每行去除首尾空白，把行内连续空格/Tab 折叠为一个空格；去除开头和结尾的空行。
3. `title` 与 `body` 不得同时为空；在规范化后执行长度限制。
4. `source_ref` 只做 NFKC + `strip()`，空字符串转为 `None`。
5. `idempotency_key = sha256(canonical_json({source_type,title,body}))`；canonical JSON 使用 UTF-8、排序键、无多余空白。`source_ref` 与 `received_at` 不进入哈希。

## 5. Clarification 契约与确定性规则

```text
class ClarificationQuestion(BaseModel):
    schema_version: Literal[1] = 1
    field: str       # snake_case，1..64
    question: str    # 1..1,000

class Clarification(BaseModel):
    schema_version: Literal[1] = 1
    questions: list[ClarificationQuestion]  # 最多 50 项，field 唯一
    is_sufficient: bool
    reasoner_id: str
    answers: dict[str, str] | None = None    # 最多 50 项；单值最长 8,192
```

Validator：有 questions 时必须 `is_sufficient=False, answers=None`；无 questions 时必须 `is_sufficient=True`；answers 非空时 questions 必须为空。

`DeterministicClarificationReasoner` 按固定顺序检查五项；相应证据不存在时生成固定问题：

| field | 充分证据 | 固定 question |
|---|---|---|
| `authorized_roles` | 出现明确排他授权语句，例如 `only/仅允许` 与角色名称 | 哪些角色被明确允许执行该操作？ |
| `time_range` | 出现带单位的默认范围和最大自定义范围 | 默认时间范围与最大可选时间跨度是多少？ |
| `record_limit` | 出现带数字的单次记录上限 | 单次处理的最大记录数是多少？ |
| `output_fields_and_redaction` | 同时列出输出字段并说明敏感字段处理 | 输出字段及敏感信息脱敏规则是什么？ |
| `delivery_mode` | 同时说明小/大数据量的同步或异步处理边界 | 何时同步返回，何时转为异步任务？ |

匹配不区分英文大小写；数字与单位必须同时存在，只有概念词而没有具体约束不算充分。问题顺序严格使用表格顺序，`reasoner_id="deterministic-clarifier-v1"`。

`ClarifierAgent.resolve()`：要求每个 question.field 在 answers 中存在且 `strip()` 后非空；缺失时抛 `IncompleteClarificationAnswersError(sorted_fields)`。成功时返回 `questions=[]`、`is_sufficient=True`、保留全部 answers、沿用 reasoner_id；不重新调用 Reasoner。额外 answers 可保留，但仍受数量和长度限制。

## 6. ContextPackage 与本地 Retriever

`CitedSnippet` 必须包含仓库相对路径、合法的 1-based 行范围、原文与 `source_trust="repository_content"`。`ContextPackage` 分离 `snippets` 与 `unsupported_notes`，不得把未引用推断伪装成证据。

`LocalFixtureContextRetriever(root)` 的行为固定如下：

- 构造时 `root.resolve()` 必须存在且为目录。
- 只读取 root 下的普通 `.md`/`.py`/`.txt` 文件；跳过 symlink、单文件超过 256 KiB 的文件，最多扫描 200 个文件。
- 每个候选路径 resolve 后必须仍位于 root 内，否则跳过并记录安全计数，不读取内容。
- 从规范化 request 的 title/body 提取 lowercase 字母数字 token（长度至少 3）；对每个文件按“不同 token 的命中数”评分。
- 只返回正分文件，按 `score desc, relative_path asc` 排序，最多 5 条；引用首个命中行，范围最多连续 5 行。
- 无命中时返回空 snippets 和明确的 unsupported note，不调用网络、GitHub API 或向量服务。

## 7. Plan、能力枚举与度量

`ToolRequirement.tool_name` 的 v1 稳定能力集合为：

```text
repository_read | repository_write | test_execute | sandbox_execute | pull_request_write
```

AF-406 将通过映射层或 `schema_version=2` 对接真实 Tool Registry，不修改 v1 含义。

```text
class Measurement(BaseModel):
    status: Literal["measured", "not_available"]
    value: Decimal | None
    unit: str | None
```

`not_available` 要求 value/unit 均为空；`measured` 要求 finite、非负 Decimal 和非空 unit。M1 的 `Plan.budget_estimate` 固定为 not_available。

`DeterministicPlanReasoner` 固定输出四个有序任务：读取引用、实施最小变更、执行测试、准备 Draft PR；能力分别为 `repository_read`、`repository_write`、`test_execute`、`pull_request_write`。输入涉及 tenant、权限、Secret、支付或审计时 risk=`L3`，否则 `L1`。Clarification 不充分时 `PlannerAgent` 必须拒绝；不得编造 Context 引用或成本。

## 8. Clarification HITL

AF-108 在 `packs/delivery/clarifier/hitl.py` 定义进程内 Gateway：

```text
request_clarification(run_id, step_key, questions) -> request_id
submit_response(request_id, run_id, answers) -> ClarificationOutcome
get_status(request_id) -> ClarificationStatus
```

- `(run_id, step_key)` 是请求幂等键；重复请求返回原 request_id，不重置状态或答案。
- submit 必须校验 request_id 存在、run_id 一致、状态为 PENDING；重复回答被拒绝。
- request_id 由注入的 IdGenerator 生成。
- 数据只在进程内，重启丢失；不代表 AF-304 durable HITL。

## 9. Trace 契约与 Langfuse 边界

```text
class TokenMeasurement(BaseModel):
    status: Literal["measured", "not_available"]
    value: NonNegativeInt | None

class TokenUsage(BaseModel):
    input_tokens: TokenMeasurement
    output_tokens: TokenMeasurement
    total_tokens: TokenMeasurement

class CostUsage(BaseModel):
    source: Literal["provider_reported", "estimated", "not_available"]
    amount: Decimal | None       # finite、非负
    currency: str | None         # ISO-4217 三个大写字母

class StepTraceRecord(BaseModel):
    tenant_id: UUID | None
    workflow_id: UUID | None
    workflow_version: int | None
    run_id: UUID
    step_id: UUID | None
    trace_id: UUID
    event_id: UUID               # AegisFlow correlation metadata，不是 Langfuse observation ID
    agent: Literal["intake", "clarifier", "context", "planner"]
    prompt: str                  # 构造前必须 redact
    model: str
    token_usage: TokenUsage
    cost: CostUsage
    latency_ms: NonNegativeFloat
```

fake 路径的全部 TokenMeasurement 和 CostUsage 固定为 `not_available`。`event_id` 由 `UUID5(namespace, f"{run_id}:{step_id or agent}:{trace_id}")` 派生，仅作为 metadata/correlation 字段。

Langfuse Python SDK v4 不允许自定义 observation ID，因此本 Issue **不宣称服务端强幂等或 upsert**。`LangfuseTraceRecorder.record()` 每次只发起一次记录，不做自动重试；使用 `Langfuse.create_trace_id(seed=str(trace_id))` 获得确定性 Langfuse trace ID，并把 AegisFlow event_id 放入 metadata。Trace 是非权威、best-effort telemetry；重复或缺失不得改变业务状态。

`NoOpTraceRecorder` 不记录；`InMemoryTraceRecorder` 保存副本供测试；`LangfuseTraceRecorder` 只捕获本地组装异常并记录异常类型，不记录 `str(exc)`、堆栈、请求、响应或凭证。SDK 自身日志保持 WARNING，禁止 debug 模式进入常规 CI。

Langfuse 配置四字段必须全有或全无：`LANGFUSE_BASE_URL`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`、`LANGFUSE_TRACING_ENVIRONMENT`。部分配置抛 `ConfigurationError`。

## 10. Langfuse 手工 smoke

AF-109 创建 `.github/workflows/langfuse-smoke.yml`，只允许 `workflow_dispatch`，引用已配置的 `langfuse-development` Environment：

- Secrets：`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`
- Variables：`LANGFUSE_BASE_URL`、`LANGFUSE_TRACING_ENVIRONMENT`
- Deployment branches：protected `main`

固定入口为 `python -m aegisflow_core.runtime.langfuse_smoke`。它必须：

1. `auth_check()` 成功，否则退出 1；
2. 用 `GITHUB_RUN_ID:GITHUB_RUN_ATTEMPT` 生成本次 smoke 的确定性 trace seed；
3. 创建、结束一条带 `aegisflow_smoke=true` 与 event_id metadata 的 observation；
4. 调用 `flush()`；
5. 最多轮询 observation API 60 秒（固定 2 秒间隔），按 trace ID 确认哨兵 observation 可见；
6. 认证失败、flush/查询失败或超时均退出 1；不得打印任何 Secret。

这条 workflow 不在 PR/push CI 中运行，普通 CI 不读取真实 Secret。

## 11. Gate 1A 图与恢复安全

AF-110 使用 `langgraph>=1.2,<2`、`StateGraph`、`InMemorySaver`、`interrupt()` 与 `Command(resume=...)`。具体导入路径按 `uv.lock` 的实际版本核实，但以下行为不可改变：

- `AgentState` 至少含 `run_id`、`trace_id`、request、clarification、context、plan；`thread_id=str(run_id)`，不再生成第二套身份。
- 组装函数的 Reasoner/Retriever/Gateway/Recorder/Clock/IdGenerator 全部显式注入，不允许隐式 fake。
- Clarifier 信息不足时先以 `(run_id,"clarifier")` 创建幂等请求，再 interrupt；恢复后 submit 并调用 `ClarifierAgent.resolve()`。
- `resume_gate1a()` 在调用 `Command(resume=...)` 前读取 checkpoint，确认该 thread 存在且当前有待恢复 interrupt；否则抛 `InvalidResumeThreadError`。错误 thread 不得恢复原运行、不得产生原运行 Plan，原 checkpoint 保持不变。
- Clarifier 的完成 Trace 在成功 resolve 后记录，避免 replay 在 interrupt 前产生重复的逻辑完成记录。
- `InMemorySaver`/Gateway 只提供进程内演示，不代表 Temporal/PostgresSaver 能力。

## 12. Gate 1A Fixture

根目录 `gemini-code-1785679381247.md` 是未跟踪的脱敏输入，不是事实源。AF-110 将其迁移为：

- `tests/fixtures/gate1a/sample_request.json`：fixture metadata、Raw Request、Existing Context 摘要、Acceptance Criteria、Sanitization Record；
- `expected_clarification.json`：五个固定 field/question；
- `fixed_clarification_response.json`：七项固定人工答案；
- `tests/fixtures/context/`：FastAPI/SQLAlchemy tenant isolation、Celery async export、audit/security 三类脱敏仓库片段。

迁移验证逐项覆盖原文件五个正文部分，提交结构化文件后删除本地未跟踪源文件。证据是“根目录文件不存在 + 三个 JSON 已被 Git 跟踪 + 内容映射检查通过”；不得声称未跟踪文件的删除会出现在 PR diff。

## 13. 依赖与配置

| Issue | 新依赖/配置 |
|---|---|
| AF-104 | `pydantic>=2.13,<3`，由 `uv.lock` 锁定 |
| AF-109 | `langfuse>=4.14,<5`；四个 Langfuse 配置字段 |
| AF-110 | `langgraph>=1.2,<2`，由 `uv.lock` 锁定 |

所有 Issue 均无数据库迁移。每个实现 PR 必须更新 `docs/21_TRACEABILITY_MATRIX.md`；只有 AF-110 因真实新增 runtime graph/state 才同步更新 `docs/02_ARCHITECTURE.md`。

## 14. 统一停止条件

出现架构/Accepted ADR 冲突、依赖未完成、Issue 非 ready、需要真实 Secret 进入 PR、测试无法安全执行、官方 SDK 不支持设计所需行为或验收标准不明确时立即停止。AI 只能创建实现 PR并等待 Human Review/Merge，不得自行批准、合并或关闭 AF-104–AF-110。
