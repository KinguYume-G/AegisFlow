# M2 Design Bundle — Shared Cross-Issue Contracts (AF-201–AF-210)

> 状态：**Draft v2**，等待人工 Review。依赖 AF-104–AF-110（M1 已通过 PR #84/#85–#91 全部 Human Merge 并 `status:verified`）。Codex 在获得批准前不得实现，也不得创建 PR。
> 前提文档：`docs/02_ARCHITECTURE.md`、`docs/adr/0002/0007/0009`、`docs/09_SECURITY_BASELINE.md`、`docs/18_RELIABILITY_PLAN.md`、`docs/19_THREAT_MODEL.md`、`docs/08_TEST_STRATEGY.md`、`docs/16_OBSERVABILITY_PLAN.md`、`docs/14_CONFIGURATION_REFERENCE.md`、`docs/design-notes/M1-SHARED-CONTRACTS.md`。
> 本文件是 AF-201 至 AF-210 十份 Design Note 的共同前提，覆盖 Gate 1B（Plan → Policy Gate → Executor → Docker Sandbox → Reviewer → Approval → Draft PR）。第 0A 节是 v2 的规范性修订；若旧段落存在冲突，以第 0A 节为准。

## 0A. Draft v2 规范性修订（必须实施）

本节关闭 v1 的全部设计待定项，并修复跨 Issue 契约冲突。各 Issue 的 Design Note/Test Plan 必须按本节解释，不得恢复被本节否决的行为。

1. **GitHub 触发与客户端**：Gate 1B 只接受显式 `repository_dispatch`；M2 不订阅 `push`。GitHub App 客户端复用现有异步 `httpx`，App JWT 使用 `PyJWT[crypto]`/`cryptography`，不引入 PyGithub/githubkit。所有 GitHub、数据库与 Ledger 端口从首次实现起均为 async。
2. **AF-201 防重放**：GitHub Payload 没有可信事件时间，因此删除“由服务端接收时间判断首次请求过期”的伪时间窗口。AF-201 使用有界 TTL replay cache，以 `(installation_id, delivery_id)` 为键；默认 TTL 10 分钟，重复请求返回 `409 duplicate_delivery`、写拒绝审计且不 dispatch。AF-209 将其升级为持久 Ledger；签名和 Schema 校验仍先于 replay check。
3. **AF-202 返回契约**：`read_repository_tree()` 返回 `RepositoryTree(entries: list[TreeEntry], truncated: bool)`；写路径另提供 `find_pull_request_by_head_or_marker()`。所有分页返回对象显式携带 `truncated`。
4. **AF-203 引用完整性**：分块结果是 `TextChunk(content, start_line, end_line)`，数据库保存行范围。`PgVectorContextRetriever` 精确实现现有 `ContextRetriever.retrieve(request)`，并通过构造函数注入可信 `tenant_id`/`RepositoryTarget`。疑似 Secret 内容隔离或跳过并审计，不得修改内容后仍声明为精确 Citation。使用官方 `pgvector` Python 包。
5. **AF-204 沙箱边界**：通用 `docker-socket-proxy` 不能作为授权边界。实现窄接口 `SandboxBroker`，它独占 Docker socket，只接受结构化 `SandboxRequest`，强制镜像 digest、非 root、`privileged=false`、drop all capabilities、无 devices、无任意 bind mount、仅允许受验证的 workspace root、network none、只读根文件系统及资源限制；只操作自身创建且带正确 Marker 的容器。`InMemorySandboxRunner` 是确定性 fake，绝不在宿主机执行不可信命令。
6. **Workspace 所有权**：调用方创建并持有每次执行的 workspace；SandboxRunner 只清理容器，返回执行结果但不删除 workspace。调用方在生成并验证 diff 后于 `finally` 中清理 workspace。默认限制为 120 秒、512 MB、1 CPU、128 PIDs；硬上限 600 秒、2048 MB、2 CPU、256 PIDs。
7. **AF-205 受控执行**：Executor 只接受结构化、允许列表内的 `TestProfile`/工具能力，不接受任意 shell 字符串。所有相对路径必须 canonicalize 并限制在 workspace 内；限制文件数、单文件大小和总 patch 大小。测试计数来自结构化测试报告，无法获取时使用 `Measurement(status="not_available")`，不得推测。
8. **AF-206 审批状态**：`ReviewDecision` 使用 `approval_status: not_required|pending|approved|rejected`，并保留最终 `outcome`；禁止产生 pending 与终态 outcome 同时存在的对象。协议与实现均 async。纯协议/InMemory fake 留在 DeliveryPack，`PostgresApprovalGateway` 位于 `control_plane`。migration `0004` 增加 `(tenant_id, run_id, step_id)` 唯一约束和仅允许 `pending -> approved|rejected` 的数据库触发器。
9. **AF-207 可信仓库范围**：新增不可由需求文本构造的 `RepositoryTarget(owner, repo, base_ref, installation_id)`/`ExecutionScope`，由已验签 webhook 和 GitHub Installation 配置生成。Policy Gate 比较该可信对象；禁止解析 `NormalizedRequest.source_ref` 获取授权范围。
10. **AF-208 写授权**：Create Draft PR 始终是 L3。每次写入都需要 `WriteAuthorization`，由可信 `ApprovalAuthorizer` 从数据库校验 approved 记录，并绑定 tenant、run、step、RepositoryTarget、base SHA 和 patch/content digest；任意 UUID 不构成授权。写入使用 Git Data API 的 blob → tree → commit → conditional ref 流程，输入为结构化文件变更而不是无法验证的任意 patch。AF-208 必须从第一版接入原子幂等 claim，不允许 TOCTOU 重复 PR 窗口。
11. **AF-209 Ledger**：Guard 返回显式代数结果 `Execute(claim_token) | Reuse(result) | InProgress | FinalFailure`，不得用 `None` 表示多个状态。记录包含 tenant、scope、canonical key、arguments hash、attempt/fencing token 和 `lease_expires_at`；complete/fail 只允许当前 claim 条件更新。AF-209 migration 顺延为 `0005`，并必须把 AF-201 webhook dispatch 接入持久 Ledger。
12. **AF-210 运行时**：Gate 1B 节点、数据库和外部适配器全异步，使用 `ainvoke`/异步 resume。允许对 Gate 1A 做行为保持的共享 node-factory 重构，但必须通过全部 AF-110 回归。引入明确 Unit of Work 管理 Run/Step/Audit 事务边界；webhook accepted 后真实 dispatch Gate 1B。所有 Draft PR 路径都先 interrupt 等待人工审批。清理只关闭带匹配 Marker 的 PR 并删除匹配分支；GitHub PR 不可删除。
13. **真实验收**：使用独立私有 Fixture 仓库和仅安装到该仓库的开发 GitHub App。真实 GitHub E2E 放入独立、手动触发、受 protected environment 保护的 Workflow；不进入普通 PR CI。必须验证相同 webhook delivery 并发/重放最终只产生一个 Draft PR。

## 0. 与 M1 的边界

M1（AF-104–AF-110）证明的是**进程内、全 fake、无外部副作用**的 Gate 1A 链路：`tenant_id`/`workflow_id`/`workflow_version` 在 `StepTraceRecord` 中始终为 `None`，`AF-103` 建立的六张 Core Domain 表（`tenants`/`workflows`/`runs`/`steps`/`approvals`/`audit_events`）从未被写入过一行数据。

M2（Gate 1B）第一次引入真实外部副作用（GitHub Webhook、GitHub API 读写、Docker 容器执行）和真实人工审批等待，因此**第一次真正写入 Core Domain 表**——这是本 Bundle 相对 M1 最大的范围扩展，第 4 节详细定义。M2 仍然**不引入 Temporal、不引入真实模型 Provider（LiteLLM）、不做 RBAC/多租户 Onboarding**——这三项分别是 M3（Reliable Runtime）与 M4（Governance & Security）的范围，`03_ROADMAP.md`/`04_MILESTONES.md` 已经把它们排在 M2 之后。因此：

- Executor/Reviewer/Policy Gate 与 M1 的 Intake/Clarifier/Context/Planner 一样，使用**确定性 Reasoner/Fake 端口**，不调用真实 LLM。
- 审批等待仍然通过 LangGraph 原生 `interrupt()`/`Command(resume=...)`（进程内、`InMemorySaver`）实现，不是 Temporal Durable Signal；这是 M3 AF-304/AF-305 的替换目标，M2 明确不是最终形态。
- 租户模型使用**单一预置 Bootstrap Tenant**（见第 4.1 节），不做多租户 Onboarding、不做 RBAC 校验、不做跨租户隔离测试——那是 AF-401–AF-409（M4）范围。

## 1. 文件与模块所有权

新增顶层子包，均在既有 `02_ARCHITECTURE.md` 目标目录内，不新增顶层模块、不需要新 ADR：

| 路径 | 首次创建 Issue | 后续 Issue 可否修改 |
|---|---|---|
| `gateway/github/__init__.py`、`auth.py`、`webhook.py` | AF-201 | 只增不改；AF-208 新增 `gateway/github/pull_request.py`，不改 `auth.py`/`webhook.py` |
| `gateway/github/read_tools.py` | AF-202 | 之后不改 |
| `gateway/github/pull_request.py` | AF-208 | 之后不改 |
| `gateway/sandbox/__init__.py`、`runner.py`、`docker_runner.py` | AF-204 | 之后不改；AF-205 只导入使用 |
| `gateway/policy/__init__.py`、`gate.py`、`config.py` | AF-207 | 之后不改 |
| `runtime/context/__init__.py`、`chunking.py`、`embedder.py`、`store.py`、`ingestion.py`、`pgvector_retriever.py` | AF-203 | 之后不改 |
| `control_plane/domain/knowledge.py` | AF-203 | 之后不改（新表模型，复用 `domain/base.py` 的 `Base`/Mixin，不修改 `base.py`） |
| `control_plane/domain/idempotency.py` | AF-209 | 之后不改 |
| `control_plane/bootstrap.py`（`get_or_create_bootstrap_tenant`/`get_or_create_bootstrap_workflow`） | AF-201 | 只读复用；不得修改签名 |
| `control_plane/migrations/versions/0003_add_knowledge_chunks.py` | AF-203 | 之后不改 |
| `control_plane/migrations/versions/0004_add_approval_guards.py` | AF-206 | 之后不改 |
| `control_plane/migrations/versions/0005_add_idempotency_ledger.py` | AF-209 | 之后不改 |
| `packs/delivery/executor/{__init__,ports,fakes,agent}.py` | AF-205 | 之后不改 |
| `packs/delivery/reviewer/{__init__,ports,fakes,agent}.py` | AF-206 | 之后不改 |
| `packs/delivery/contracts/execution_result.py` | AF-205 | 之后不改 |
| `packs/delivery/contracts/review_decision.py` | AF-206 | 之后不改 |
| `packs/delivery/contracts/policy_decision.py` | AF-207 | 之后不改 |
| `packs/delivery/reviewer/approval_gateway.py`（`ApprovalGateway` 协议 + `InMemoryApprovalGateway` + `PostgresApprovalGateway`） | AF-206 | 之后不改；AF-210 只注入使用 |
| `runtime/tracing.py` 的 `StepTraceRecord.agent` Literal | **修改**：AF-205 追加 `"executor"`，AF-206 追加 `"reviewer"` | 两次都只追加一个字面量，其余内容不改 |
| `runtime/state.py` 的 `AgentState` | **修改**：AF-210 追加 `policy_decision`/`execution_result`/`review_decision`/`approval_reference` 字段 | 只有 AF-210 修改；不改已有字段 |
| `runtime/graph.py` | **修改**：AF-210 新增 `build_gate1b_graph()`/`resume_gate1b()` 函数；`build_gate1a_graph()`/`resume_gate1a()` 原样保留 | 只有 AF-210 修改，且是新增函数而非改写既有函数 |
| `compose.yaml` | **修改**：AF-204 新增 `sandbox-broker` 服务；不改 `postgres`/`redis` 既有定义 | 只有 AF-204 修改 |
| `tests/fixtures/gate1b/` | AF-210 创建；AF-203/205/206 各自的单元/组件测试使用自己的最小 fixture，不依赖 `gate1b/` | — |
| `docs/21_TRACEABILITY_MATRIX.md` | 每个 Issue 各自追加一行 | — |

**依赖顺序（严格顺序执行，理由见第 15 节）**：AF-201 → AF-202 → AF-203 → AF-204 → AF-207 → AF-205 → AF-206 → AF-208 → AF-209 → AF-210。此顺序满足全部十个 Issue 在 GitHub 上声明的 Dependencies 字段，未修改任何 Issue 的 Dependencies 数据。

## 2. GitHub App 身份与权限（AF-201 所有，AF-202/208 复用）

### 2.1 App 凭据

配置组沿用 `docs/14_CONFIGURATION_REFERENCE.md`：`GITHUB_APP_ID`、`GITHUB_APP_PRIVATE_KEY`（PEM，Secret Reference，不进入日志/Trace/Prompt）、`GITHUB_APP_WEBHOOK_SECRET`（HMAC 密钥）、`GITHUB_APP_INSTALLATION_ID`（M2 固定单一 Installation，对应第 3 节的单一测试仓库；不支持多 Installation 路由，那是更完整的多租户能力，M4 范围）。

### 2.2 最小权限集合（Repository Permissions）

| Permission | Level | 用途 | 使用 Issue |
|---|---|---|---|
| Contents | Read | 读取文件树/文件内容 | AF-202 |
| Contents | Write | 创建分支、提交 Commit | AF-208 |
| Issues | Read | 读取 Issue 详情（供 Intake/Context 未来接入真实来源，M2 只读不写） | AF-202 |
| Pull requests | Read | 读取 PR/Diff | AF-202 |
| Pull requests | Write | 创建 Draft PR | AF-208 |
| Metadata | Read | App 强制要求的最小权限 | AF-201 |

不申请 Merge、Admin、Actions、Deployments 等无关权限。Webhook 触发固定为 `repository_dispatch`；M2 不订阅 `push`。只有真实测试需要时才增加 pull_request 只读订阅，且不得成为 Gate 1B 触发入口。

### 2.3 `InstallationTokenProvider`（`gateway/github/auth.py`，AF-201 所有）

```text
class InstallationTokenProvider:
    def __init__(self, app_id: str, private_key_pem: str, installation_id: str, clock: Clock): ...
    def get_token(self) -> InstallationToken: ...  # 内部按 exp 缓存并在过期前刷新，短期 Token（GitHub 默认 1 小时）
```

`InstallationToken`（`expires_at`、`token` 值本身**不进入任何日志/Trace/AuditEvent**，只记录 `token_id`/`expires_at` 等元数据）。AF-202/AF-208 只依赖这个 Provider 获取 Token，不直接持有 App 私钥。

## 3. Webhook 签名、防重放与审计（AF-201）

### 3.1 校验顺序（固定，逐项短路，不可重排）

1. **签名校验**：`X-Hub-Signature-256` 头，HMAC-SHA256(`GITHUB_APP_WEBHOOK_SECRET`, raw_body)，使用常量时间比较（`hmac.compare_digest`）。失败 → 拒绝，HTTP 401，写 `AuditEvent(decision="deny", reason="invalid_signature")`。
2. **结构校验**：`X-GitHub-Event` 必须精确为 `repository_dispatch`，JSON Payload 必须能被目标 Pydantic Schema 解析。失败 → HTTP 400，写 `AuditEvent(reason="schema_rejected")`。
3. **有界防重放**：异步 ReplayGuard 以 `(installation_id, X-GitHub-Delivery)` 原子 claim，TTL 为 10 分钟且容量有界。重复 delivery → HTTP 409，写 `AuditEvent(reason="duplicate_delivery")`，不得 dispatch。GitHub Payload 不提供可信事件时间，因此不声称验证发送时间或事件年龄。
4. **持久化升级缝**：AF-201 的内存 Guard 提供单进程窗口保护；AF-209 用相同异步协议替换为 PostgreSQL Ledger，以实现跨进程和重启防重放。

### 3.2 失败审计

每次拒绝都写一行 `AuditEvent`：`actor="github_webhook"`、`action="verify"`、`resource_type="webhook_delivery"`、`resource_id=<X-GitHub-Delivery>`、`decision="deny"`、`reason=<上述四类之一>`。`tenant_id` 取第 4.1 节的 Bootstrap Tenant（M2 单租户，不做按 Installation 路由的多租户解析）。**通过校验时也写一行 `decision="allow"` 的 AuditEvent**，保证审计链路完整（不是只记录失败）。

### 3.3 端点契约

`POST /webhooks/github`（`health/router.py` 同级新增 `webhooks/` 子路由），响应体不回显任何 Payload 内容，只返回 `{"status": "accepted"}` 或结构化错误（不泄露校验失败的具体密钥比较结果，只暴露第 3.1 节四个分类原因之一）。

## 4. Core Domain 持久化范围（M2 起真正写入 AF-103 六张表）

### 4.1 Bootstrap Tenant / Workflow

`control_plane/bootstrap.py`（AF-201 所有）：

```text
async def get_or_create_bootstrap_tenant(session: AsyncSession, slug: str) -> Tenant: ...
async def get_or_create_bootstrap_workflow(
    session: AsyncSession, tenant_id: UUID, name: str, version: int, definition_hash: str
) -> Workflow: ...
```

两者都是**按唯一键幂等的 get-or-create**（`tenants.slug` 唯一、`workflows(tenant_id,name,version)` 唯一），并发调用不重复创建（`INSERT ... ON CONFLICT DO NOTHING` + 回查，或显式捕获唯一约束冲突后回查）。`slug`/`name`/`version`/`definition_hash` 的具体取值由 `.env` 配置（`AEGISFLOW_BOOTSTRAP_TENANT_SLUG`，默认 `"gate1b-default"`；`definition_hash` 用固定字符串 `"gate1b-v1"` 的 SHA-256，不代表真实图结构哈希——这是已知简化，留待真实 Workflow 版本化系统（`15_RELEASE_AND_VERSIONING.md` 范围）替换）。

M2 不做租户注册 API、不做多租户路由——**所有 M2 流量都归属这一个 Bootstrap Tenant**。多租户 Onboarding、RBAC、跨租户隔离测试是 AF-401–AF-409（M4）范围，本 Bundle 不触碰。

### 4.2 Run / Step 写入规则

Gate 1B 的每次执行对应一行 `runs`（`workflow_id`/`workflow_version` 指向 4.1 的 Bootstrap Workflow，`status` 使用既有 CHECK 约束里的 `pending`/`running`/`waiting_approval`/`completed`/`failed`；**不使用 `waiting_clarification`**，因为 Gate 1B 图默认信息已充分，不重新触发 Clarifier）。四个 Agent 节点（Policy Gate、Executor、Reviewer 各一次，加上 Draft PR 写操作）各自对应一行 `steps`（`sequence` 严格递增，`name` 取 `"policy_gate"`/`"executor"`/`"reviewer"`/`"draft_pr"`）。

**写入方 = `runtime/graph.py` 的 Gate 1B 图节点本身**（AF-210 所有），不是各 Agent 类内部——与 `StepTraceRecord` 的写入模式保持一致：Agent 类（`PolicyGate`/`ExecutorAgent`/`ReviewerAgent`）保持纯函数式、无数据库依赖，图节点负责编排 Agent 调用与 Run/Step/Trace/Audit 的持久化副作用。这保持了 M1 已建立的"Agent 契约与运行时编排分离"规则（`02_ARCHITECTURE.md` 六 Agent 契约表）。

### 4.3 Approval 写入规则（AF-206 所有，见第 8 节）

Reviewer 判定 `approval_status="pending"` 时，异步 `ApprovalGateway.request_approval(...)` 写入 `decision="pending"`；人工响应后 `submit_decision(...)` 更新为 approved/rejected。AF-206 的 migration `0004` 增加 `(tenant_id, run_id, step_id)` 唯一约束，并在数据库层只允许 `pending → approved|rejected`；终态不得被覆盖或恢复 pending。

## 5. GitHub MCP 只读工具（AF-202）

### 5.1 工具清单与 Schema

四个只读工具，均定义在 `gateway/github/read_tools.py`，共享一个 `GitHubReadClient`（内部持有 `InstallationTokenProvider`）：

| 工具 | 输入 | 输出（截断/分页后） |
|---|---|---|
| `read_repository_tree(owner, repo, ref, path=None)` | 仓库坐标 + 可选子路径 | `list[TreeEntry{path, type, size}]` |
| `read_file_content(owner, repo, ref, path)` | 文件坐标 | `FileContent{path, content, encoding, size, truncated}` |
| `read_issue(owner, repo, issue_number)` | Issue 坐标 | `IssueSnapshot{number, title, body, state, labels}` |
| `read_pull_request_diff(owner, repo, pr_number)` | PR 坐标 | `PullRequestDiff{number, files: list[DiffFile{path, patch, additions, deletions}]}` |

所有输出 Pydantic Schema `schema_version: Literal[1] = 1`、`extra="forbid"`，与 M1 契约风格一致。

### 5.2 分页

GitHub REST 原生分页（`Link` Header / `page`+`per_page`）在 `GitHubReadClient` 内部封装，对外**不暴露 GitHub 原生游标**——工具签名统一提供 `max_items: int = 200` 上限参数，内部循环翻页直到达到上限或无更多数据；超过上限时输出对象带 `truncated: bool = True`，不静默丢弃也不无界抓取。

### 5.3 Timeout 与错误映射

单次 HTTP 调用超时 `GITHUB_API_TIMEOUT_SECONDS`（默认 10 秒，可配置）。统一映射为工具层异常，不向调用方泄露原始 HTTP 异常类型：

| GitHub 响应 | 映射异常 | 说明 |
|---|---|---|
| 404 | `GitHubResourceNotFoundError` | |
| 401/403（含 rate limit 用 403 场景） | `GitHubPermissionDeniedError` | 不区分"无权限"与"App 未安装"的细节，避免信息泄露 |
| 429 或 403 + `X-RateLimit-Remaining: 0` | `GitHubRateLimitedError(retry_after: float)` | `retry_after` 取 `Retry-After` 或 `X-RateLimit-Reset` 头换算 |
| 5xx | `GitHubUpstreamError` | |
| 请求超时 | `GitHubTimeoutError` | |
| 响应体非预期 JSON 结构 | `GitHubMalformedResponseError` | |

只读工具**不写 Idempotency Ledger**（GET 无副作用，见第 9.4 节），**不需要 Policy Gate 前置校验**（`09_SECURITY_BASELINE.md` Risk Level L0 "Read docs" = Auto）。每次调用仍写 `StepTraceRecord`？——**不写**，只读工具不是 DeliveryPack Agent 节点，不产生 `agent` 字段意义下的步骤；调用量统计留给 OTel（M5 范围，M2 不引入 OTel，见第 13 节）。

## 6. pgvector 增量知识索引（AF-203）

### 6.1 表结构（`control_plane/domain/knowledge.py`，migration `0003_add_knowledge_chunks.py`）

```text
class RepositoryChunk(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "repository_chunks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "repository", "file_path", "chunk_index",
                          name="uq_repository_chunks_location"),
        ForeignKey("tenants.id", ondelete="RESTRICT"),  # tenant_id
    )
    tenant_id: UUID
    repository: str        # "owner/repo"
    file_path: str         # POSIX 相对路径，与 AF-106 ContextPackage 引用格式一致
    chunk_index: int
    content_hash: str      # sha256(chunk_text)，用于增量跳过
    content: str            # 有界长度（≤ 4000 字符）
    start_line: int         # 1-based inclusive
    end_line: int           # 1-based inclusive
    embedding: Vector(32)   # pgvector；32 维是确定性 fake embedder 的维度，见 6.3
    updated_at: datetime
```

迁移需要 `CREATE EXTENSION IF NOT EXISTS vector`（`compose.yaml` 的 Postgres 镜像已是 `pgvector/pgvector:pg16`，扩展已随镜像提供，只需在迁移里启用）。

### 6.2 增量索引算法

```text
def ingest_file(session, tenant_id, repository, file_path, raw_text, clock):
    chunks = chunk_text(raw_text)  # 见 6.4，确定性分块
    existing = load_existing_chunks(session, tenant_id, repository, file_path)  # by chunk_index
    for index, chunk_text_value in enumerate(chunks):
        content_hash = sha256(chunk_text_value)
        if index in existing and existing[index].content_hash == content_hash:
            continue  # 跳过未变化的 chunk，不重新计算 embedding
        embedding = embedder.embed(chunk_text_value)
        upsert_chunk(session, tenant_id, repository, file_path, index, content_hash, chunk_text_value, embedding)
    delete_chunks_beyond(session, tenant_id, repository, file_path, len(chunks))  # 文件变短时清理多余 chunk_index
```

整个 `ingest_file` 在一个数据库事务内完成（Upsert + 越界删除），保证同一文件的索引状态原子一致。

### 6.3 确定性 Embedder（`runtime/context/embedder.py`）

M2 没有真实 Model Provider（LiteLLM 是 M3 范围，`14_CONFIGURATION_REFERENCE.md` 明确把"至少一个 Model Provider"列为仍需项目所有者提供、未提供时对应能力 blocked 的外部输入）。因此 AF-203 定义 `Embedder` Protocol + 唯一具体实现 `DeterministicHashEmbedder`：

```text
class Embedder(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...

class DeterministicHashEmbedder:
    """32 维、词袋哈希、L2 归一化——无需外部模型，具备粗粒度语义局部性，可复现。"""
    def embed(self, text: str) -> tuple[float, ...]:
        # 归一化 + 分词 → 每个 token 哈希进 32 个桶之一并计数 → L2 归一化
        ...
```

真实模型驱动的 `Embedder` 实现是 M3+ 范围（一旦 Model Provider 确认，新增一个实现类即可，不改 `Embedder` 协议）。检索基准（AC "检索基准通过"）在 M2 的含义因此限定为**机制正确性**，不是语义排序质量：

- 相同文本两次 ingest → 相同 chunk_hash → 不重复写 embedding（幂等断言）。
- 已知 fixture 文本的精确/近似重复查询 → Top-K 命中期望 chunk（`DeterministicHashEmbedder` 的词袋哈希对完全重复或高重叠文本保证高 cosine 相似度，这是可测的确定性属性）。
- 跨租户/跨仓库查询 → 零命中（隔离测试，机制同 AF-106 的 root 注入隔离模式）。

真实语义相关性评测（Golden Set、SWE-bench 子集）是 `17_EVALUATION_PLAN.md` 与 M5 范围，本 Issue 不做。

### 6.4 分块（`runtime/context/chunking.py`）

固定规则：按行分块，每块 ≤ 200 行或 ≤ 4000 字符（先到者为界），不跨文件边界，不做语义感知分块（AST/语法树分块留待未来 Issue，如需要将是独立 Issue，不在本 Bundle 范围内）。

### 6.5 与 AF-106 的关系

`runtime/context/` 是新的运行时子包，**不修改** `packs/delivery/context/{agent,ports,fakes}.py`（AF-106 冻结）。AF-203 只新增一个新的 `ContextRetriever` 实现 `PgVectorContextRetriever`（实现 AF-106 已定义的 `ContextRetriever` 端口协议，放在 `runtime/context/pgvector_retriever.py`），供未来 Issue（M2 之外）替换 `LocalFixtureContextRetriever` 接入真实图。**Gate 1B（AF-210）本身仍然使用 AF-106 的 `LocalFixtureContextRetriever`，不在本 Bundle 内切换 Context 节点的检索实现**——这是刻意的范围收敛：把"pgvector 索引管道本身工作正确"与"Gate 1B 图切换到真实检索"分成两件事，避免 AF-210 的确定性 Fixture 断言被真实向量检索的浮点噪声破坏。

## 7. Docker Sandbox 基线（AF-204）

### 7.1 安全属性（`09_SECURITY_BASELINE.md`/ADR-0009 逐条落实）

| 属性 | 实现 |
|---|---|
| non-root | 容器 `USER` 非 0；`docker run --user` 显式指定，不依赖镜像内 USER 声明 |
| read-only FS | `--read-only`，仅 `/workspace`（bind mount）与 `/tmp`（`--tmpfs`，有大小上限）可写 |
| no Docker socket | 沙箱容器**不挂载** `/var/run/docker.sock`；见 7.2 的编排隔离设计 |
| resource limit | `--memory`、`--cpus`、`--pids-limit`，全部有默认值且可配置上限 |
| timeout | 默认 120 秒、硬上限 600 秒；超时由 Broker stop/remove 自己创建的容器 |
| network disabled/allowlist | 默认 `--network=none`；M2 不实现 allowlist 分支（沙箱内代码修改与测试执行不需要网络，见 7.3） |
| temporary workspace | 调用方创建并持有；runner 返回时必须仍存在，供 AF-205 diff |
| cleanup | Broker 清理容器；调用方在 diff 后于独立 `finally` 清理 workspace |

### 7.2 编排隔离："no Docker socket" 的准确范围

ADR-0009 的 "no Docker socket" 同时适用于 Core 与执行容器。只有既有 Sandbox 容器边界中的 `SandboxBroker` adapter 持有 socket；它不暴露 Docker API，而是接受结构化 `SandboxRequest` 并在服务端重建所有参数。Broker 对镜像 digest、用户、capabilities、devices、mount、network、资源上限和 Marker 做不可绕过校验，只允许管理自己创建的容器。这是既有 Sandbox 容器职责的落地，不新增业务微服务。

### 7.3 `SandboxRunner` 契约（`gateway/sandbox/runner.py`）

```text
class SandboxRequest(BaseModel):
    schema_version: Literal[1] = 1
    workspace_source: Path        # 宿主机临时目录，调用前已填充好待执行的文件树
    test_profile: TestProfile     # 结构化允许列表，不接受任意 shell
    timeout_seconds: PositiveInt = 120
    memory_limit_mb: PositiveInt = 512
    cpu_limit: PositiveFloat = 1.0
    pids_limit: PositiveInt = 256

class SandboxResult(BaseModel):
    schema_version: Literal[1] = 1
    status: Literal["completed", "timeout", "resource_exceeded", "internal_error"]
    exit_code: int | None
    stdout: str   # 有界截断，默认 64KB
    stderr: str   # 有界截断，默认 64KB
    duration_ms: NonNegativeFloat
    workspace_output: Path  # 执行后的宿主机临时目录（供调用方 diff）

class SandboxRunner(Protocol):
    def run(self, request: SandboxRequest) -> SandboxResult: ...
```

`DockerSandboxRunner`（真实实现，经 7.2 的 Broker 协议调用）与 `InMemorySandboxRunner`（确定性测试 fake，只返回注入结果，不启动容器且绝不执行宿主子进程）。**沙箱内永不注入任何 Secret、Token 或网络凭据**（`09_SECURITY_BASELINE.md` Secret 规则）。

## 8. Executor 与 Reviewer 契约

### 8.1 仓库内容获取与代码修改的职责边界（AF-205）

Executor 不直接持有 GitHub 凭据、不直接调用 GitHub 写 API：

1. **Fetch（可信编排层，AF-205 图节点内）**：调用 AF-202 的 `read_repository_tree`/`read_file_content`，把 Plan 涉及范围内的文件写入一个宿主机临时目录（`workspace_source`）。
2. **Apply（`ExecutorAgent`，确定性）**：`PatchReasoner` 端口 + `DeterministicPatchReasoner` fake 根据 `Plan`（M1 已定稿的 `PlanTask`/`ToolRequirement`）与 fetch 到的文件内容，生成要写入 `workspace_source` 的修改后文件内容（M2 没有真实 LLM，见 §0）。
3. **Execute（`SandboxRunner`，AF-204）**：把修改后的 `workspace_source` 与经 Policy Gate 允许的结构化 `TestProfile` 交给沙箱，网络关闭，非 root。
4. **Diff（可信编排层）**：对比 fetch 时的原始树与 `SandboxResult.workspace_output`，计算统一 diff（`difflib`/`git diff --no-index` 等价算法皆可，Codex 实现时选定并在 PR 中说明），得到 `patch: str` 与 `changed_files: list[str]`。

沙箱全程 `--network=none`，因此 Executor 绝不会在沙箱内触达真实 GitHub——这同时满足"只调用允许工具"（AC）与 Security Baseline 的默认无网络原则。

### 8.2 `ExecutionResult`（`packs/delivery/contracts/execution_result.py`，AF-205 所有）

```text
class TestOutcome(BaseModel):
    schema_version: Literal[1] = 1
    status: Literal["passed", "failed", "timeout", "error"]
    passed_count: NonNegativeInt
    failed_count: NonNegativeInt
    output_excerpt: str   # 有界截断

class ExecutionResult(BaseModel):
    schema_version: Literal[1] = 1
    status: Literal["completed", "failed"]
    patch: str                       # 统一 diff，空字符串表示无改动
    changed_files: list[str]
    test_outcome: TestOutcome
    reasoner_id: str
```

`ExecutorAgent.execute(plan: Plan, workspace_source: Path, sandbox_runner: SandboxRunner) -> ExecutionResult`——不接受隐式默认 `sandbox_runner`（沿用 M1 显式注入规则）。

### 8.3 失败契约

```text
class ExecutorNodeError(RuntimeError):
    def __init__(self, stage: Literal["fetch", "apply", "sandbox", "diff"], cause_type: str): ...
```

任一阶段失败都产出结构化 `ExecutorNodeError`，不吞异常、不用裸 `except: pass`；`ExecutionResult.status="failed"` 用于 Plan/沙箱**本身正常运行但测试失败**这一区分明确的业务结果，与"Executor 自身崩溃"的 `ExecutorNodeError` 是两个不同的失败通道（对齐 `18_RELIABILITY_PLAN.md` Failure Taxonomy 的 `Tool Failure` vs 其他类别）。

### 8.4 Reviewer 契约（AF-206）

```text
class ReviewFinding(BaseModel):
    schema_version: Literal[1] = 1
    severity: Literal["info", "warning", "blocking"]
    message: str

class ReviewDecision(BaseModel):
    schema_version: Literal[1] = 1
    findings: list[ReviewFinding]
    approval_status: Literal["not_required", "pending", "approved", "rejected"]
    outcome: Literal["draft_pr", "rework", "rejected"] | None = None
    reasoner_id: str

class ReviewerAgent:
    def __init__(self, reasoner: ReviewReasoner): ...
    def review(self, plan: Plan, execution_result: ExecutionResult) -> ReviewDecision: ...
    def resolve(self, decision: ReviewDecision, approval: ApprovalOutcome) -> ReviewDecision: ...
```

`review()` 的确定性规则（固定顺序，镜像 M1 Clarifier 五规则的写法）：

1. `execution_result.status == "failed"` → `outcome="rework"`，`approval_status="not_required"`，附带 blocking Finding，跳过审批。
2. 否则所有风险等级均 → `approval_status="pending"`、`outcome=None`，因为 Create Draft PR 固定为 L3。

`resolve()` 只在 `approval_status="pending"` 且 `outcome is None` 时调用；approved → `approval_status="approved"`、`outcome="draft_pr"`；rejected → `approval_status="rejected"`、`outcome="rejected"`。非法值抛 `InvalidApprovalDecisionError`。

### 8.5 `ApprovalGateway`（AF-206 所有，实现见 4.3）

```text
class ApprovalOutcome(BaseModel):
    schema_version: Literal[1] = 1
    approval_id: UUID
    decision: Literal["approved", "rejected"]
    decided_by: str
    reason: str | None

class ApprovalGateway(Protocol):
    async def request_approval(self, tenant_id: UUID, run_id: UUID, step_id: UUID, findings: list[ReviewFinding]) -> UUID: ...
    async def submit_decision(self, approval_id: UUID, run_id: UUID, decision: Literal["approved","rejected"], decided_by: str, reason: str | None) -> ApprovalOutcome: ...
    async def get_status(self, approval_id: UUID) -> Literal["pending","approved","rejected"]: ...
```

`InMemoryApprovalGateway`（单元/组件测试用，模式与 AF-108 `InMemoryClarificationGateway` 一致：`run_id` 校验、重复提交拒绝）；`PostgresApprovalGateway`（Gate 1B E2E 用，`request_approval` 写入 `approvals` 表一行 `decision="pending"`，`submit_decision` 原地 `UPDATE` 该行——这是 M2 相对 M1 的实质差异：`approvals` 表在 AF-103 就已存在，本 Issue 是第一次真正使用它，见 §4.3）。**两个实现共享同一协议，`request_approval` 按 `(run_id, step_id)` 幂等**（与 AF-108 的 `(run_id, step_key)` 幂等键同一设计动机：LangGraph 节点 replay 安全）。

## 9. Policy Gate v0（AF-207）

### 9.1 输入输出

```text
class PolicyDecision(BaseModel):
    schema_version: Literal[1] = 1
    decision: Literal["allow", "deny"]
    violated_rule: Literal["repository_scope", "tool_capability_scope", "risk_ceiling"] | None
    reasons: list[str]

class PolicyConfig(BaseModel):
    schema_version: Literal[1] = 1
    allowed_repository: str              # "owner/repo"，M2 固定单一仓库
    enabled_tool_capabilities: frozenset[str]   # ToolCapability 的子集
    max_allowed_risk_level: Literal["L1", "L2", "L3"]

class PolicyGate:
    def __init__(self, config: PolicyConfig): ...
    def evaluate(self, plan: Plan, scope: ExecutionScope) -> PolicyDecision: ...
```

### 9.2 确定性规则（固定顺序，第一条违反即 `deny` 并停止，不做规则累积）

1. `repository_scope`：可信 `scope.repository_target` 必须与配置允许的 owner/repo/base_ref/installation_id 完全一致；禁止读取 `request.source_ref` 做授权判断。
2. `tool_capability_scope`：`plan` 内出现的每个 `ToolRequirement.tool_name` 必须属于 `config.enabled_tool_capabilities`。
3. `risk_ceiling`：`plan.risk_level` 必须 ≤ `config.max_allowed_risk_level`（`L1 < L2 < L3` 的固定序）。

全部通过 → `decision="allow"`，`violated_rule=None`，`reasons=[]`。

### 9.3 审计（无 Langfuse Trace，只有 AuditEvent）

Policy Gate 不是 LLM 调用，不产生 `StepTraceRecord`（Langfuse 按 ADR-0008 只管 Prompt/LLM/Token/Cost/Agent Eval，确定性规则引擎不在其列）。**每次 `evaluate()` 调用后，图节点写一行 `AuditEvent`**：`actor="policy_gate"`、`action="evaluate"`、`resource_type="plan"`、`decision`、`reason`（取 `violated_rule` 或 `"allow"`）、`trace_id`（复用 Gate 1B 图的 `trace_id`，与 Langfuse Trace 关联，即使 Policy Gate 本身不写 Langfuse，也能通过 `trace_id` 在 `audit_events` 与 Langfuse Trace 之间做人工关联）。

### 9.4 `deny` 后的图行为

Policy Gate 拒绝 → Gate 1B 图不进入 Executor，直接产出 `run.status="failed"`（终态），不触发 Reviewer、不产生 `ExecutionResult`。这与 `18_RELIABILITY_PLAN.md` 的 `Authorization` 失败类别（`missing scope → deny`）一致。

## 10. GitHub Draft PR 写工具（AF-208）

### 10.0 原子幂等与授权端口

AF-208 从第一版就依赖异步 `IdempotencyGuard`；AF-209 提供 PostgreSQL 实现。测试使用明确的 InMemory 实现，不提供 NoOp 默认值。

```text
class ClaimResult: ...
class Execute(ClaimResult): claim_token: UUID
class Reuse(ClaimResult): result_reference: str
class InProgress(ClaimResult): retry_after_seconds: int
class FinalFailure(ClaimResult): reason: str

class IdempotencyGuard(Protocol):
    async def begin(self, command: IdempotentCommand) -> ClaimResult: ...
    async def complete(self, claim_token: UUID, result_reference: str) -> None: ...
    async def fail(self, claim_token: UUID, retryable: bool, reason: str) -> None: ...
```

### 10.1 授权前置检查（工具自身强制）

```text
class WriteAuthorization(BaseModel):
    approval_id: UUID
    tenant_id: UUID
    run_id: UUID
    step_id: UUID
    repository_target: RepositoryTarget
    base_sha: str
    content_digest: str

async def create_draft_pull_request(
    *, changes: tuple[FileChange, ...], authorization: WriteAuthorization,
    approval_authorizer: ApprovalAuthorizer, idempotency_guard: IdempotencyGuard, ...
) -> DraftPullRequestResult: ...
```

`ApprovalAuthorizer` 必须从数据库读取 approved 记录并校验所有绑定字段。调用方提供的 approval UUID、risk level 或布尔值都不能替代该校验。所有 Draft PR 写入固定为 L3。

### 10.2 Scope

分支命名固定模式 `aegisflow/run-{run_id}`；Commit 使用固定 Author（配置项，不是真人身份，例如 `AegisFlow Bot <bot@aegisflow.local>`）；PR 标题/正文包含结构化 **AegisFlow Marker**（HTML 注释，机器可解析且不影响人类阅读）：

```text
<!-- aegisflow:marker schema_version=1 run_id={run_id} idempotency_key={idempotency_key} -->
```

### 10.3 双重幂等检查（"本地 Ledger + 远端资源"，`02_ARCHITECTURE.md` Idempotency Contract 原文要求）

1. **本地**：在任何 GitHub 写调用前调用 `idempotency_guard.begin(command)`。`Execute` 才能继续；`Reuse` 直接返回；`InProgress`/`FinalFailure` 不执行。
2. **远端**：取得 claim 后按确定性分支名/Marker reconciliation。命中则用同一 claim 回填 `complete()` 并复用；未命中才执行 Git Data API 写入。

两层检查都未命中才真正创建分支、Commit、Draft PR。

## 11. Idempotency Ledger（AF-209）

### 11.1 表结构（`control_plane/domain/idempotency.py`，migration `0005_add_idempotency_ledger.py`）

```text
class IdempotencyRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "scope", "idempotency_key", name="uq_idempotency_records_scope_key"),
        CheckConstraint(
            "status IN ('pending','executing','succeeded','failed_retryable','failed_final','compensated')",
            name="status",
        ),
        CheckConstraint("scope IN ('webhook_delivery','tool_call')", name="scope"),
    )
    scope: str
    idempotency_key: str          # webhook_delivery: X-GitHub-Delivery；tool_call: sha256(tenant:run:step:tool:args_hash)
    tenant_id: UUID
    run_id: UUID | None
    step_id: UUID | None
    tool_name: str | None
    arguments_hash: str
    claim_token: UUID | None
    attempt: int
    lease_expires_at: datetime | None
    status: str
    result_reference: str | None  # 例如已创建 PR 的 URL，供幂等重放直接返回
    updated_at: datetime
```

状态机字面量与 `18_RELIABILITY_PLAN.md` 的 `PENDING/EXECUTING/SUCCEEDED/FAILED_RETRYABLE/FAILED_FINAL/COMPENSATED` 完全一致（小写存储，语义相同），刻意保持 Schema 兼容，使 M3 引入 Temporal 时可以直接复用同一张表而不需要破坏性迁移。

### 11.2 并发保证

`INSERT ... ON CONFLICT` 与行锁在单事务内返回显式 `ClaimResult`。活跃 lease 返回 `InProgress`；过期且可重试的 lease 生成新的 claim token/attempt。`complete`/`fail` 必须以 tenant/key/claim_token 条件更新，旧执行者无法覆盖新 attempt。

### 11.3 两种 Scope 的调用方

- `webhook_delivery`：AF-209 把 AF-201 的 ReplayGuard 实现替换为 Ledger adapter；取得 `Execute` 后才 dispatch Gate 1B，Reuse/InProgress/FinalFailure 均不重复 dispatch。
- `tool_call`：AF-208 在任何 GitHub 写入前取得 `Execute` claim，成功后用同一 token complete；AF-210 负责注入 PostgreSQL 实现。

### 11.4 只读工具不建 Ledger 记录

与第 5.3 节呼应：AF-202 的只读调用没有副作用，天然幂等，不写本表——避免 Ledger 表被读流量污染。

## 12. Trace / 审计边界总表

| 组件 | 产出 | 写入位置 |
|---|---|---|
| Webhook 校验（AF-201） | 通过/拒绝决定 | `audit_events` |
| Policy Gate（AF-207） | allow/deny 决定 | `audit_events`（不写 Langfuse） |
| Executor（AF-205） | 步骤完成 | `StepTraceRecord`（Langfuse/NoOp/InMemory，`agent="executor"`）+ `steps` 行 |
| Reviewer（AF-206） | 步骤完成 + 审批请求/决定 | `StepTraceRecord`（`agent="reviewer"`）+ `steps` 行 + `approvals` 行 |
| Draft PR 写操作（AF-208） | 幂等写结果 | `idempotency_records` + `audit_events`（`actor="draft_pr_tool"`） |

M2 不引入 OpenTelemetry（`16_OBSERVABILITY_PLAN.md` 把 MCP/Sandbox/External API 的系统级 Trace 划给 OTel，但 AF-508/509 才是引入 Issue，`21_TRACEABILITY_MATRIX.md` 已经把它们排在 M2 之后）——本 Bundle 的 MCP/Sandbox 调用暂时只有结构化日志（`logging.py` 既有的 JSON stdout 基础设施）与上表列出的 Postgres 审计/Langfuse Trace，没有分布式 Trace。这是已知、刻意的范围收敛，不是遗漏。

## 13. 依赖与配置新增

| 配置项 | 组 | Secret | 用途 |
|---|---|---|---|
| `GITHUB_APP_ID` | GitHub App | No | AF-201 |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App | Yes | AF-201 |
| `GITHUB_APP_WEBHOOK_SECRET` | GitHub App | Yes | AF-201 |
| `GITHUB_APP_INSTALLATION_ID` | GitHub App | No | AF-201 |
| `GITHUB_API_TIMEOUT_SECONDS` | GitHub App | No | AF-202 |
| `AEGISFLOW_BOOTSTRAP_TENANT_SLUG` | App | No | AF-201/§4.1 |
| `AEGISFLOW_TEST_REPOSITORY` | App | No | Policy Gate `allowed_repository`（AF-207），Gate 1B E2E（AF-210） |
| `SANDBOX_BROKER_URL` | Sandbox | No | AF-204 |
| `SANDBOX_DEFAULT_TIMEOUT_SECONDS` / `_MEMORY_LIMIT_MB` / `_CPU_LIMIT` / `_PIDS_LIMIT` | Sandbox | No | AF-204 |

新库依赖固定为：复用现有 `httpx`，新增 `PyJWT[crypto]`/`cryptography`（GitHub App JWT）与官方 `pgvector` 包。Docker SDK 只允许出现在 Sandbox Broker adapter 内，不进入 DeliveryPack。全部解析版本锁入 `uv.lock` 并在各实现 PR 记录。

## 14. Gate 1B 图与测试仓库（AF-210）

### 14.1 图结构

`build_gate1b_graph()` 复用 AF-110 的 `intake`→`clarifier`→`context`→`planner` 四节点（原样调用 `build_gate1a_graph` 内部逻辑或直接复制节点定义并追加——具体复用方式由 Codex 决定，只要求不修改 `build_gate1a_graph` 本身），追加：

```text
planner → policy_gate → (deny: END/failed) → (allow) executor → reviewer
reviewer → (execution failed) → rework | END
reviewer → (execution passed) → approval_wait → (Human resume) → draft_pr | rejected → END
rework → executor  (Reviewer 打回，Architecture stateDiagram 的 Rework→Executor 边)
```

`approval_wait` 节点的写法镜像 AF-110 `clarification_wait_node`：调用 `ApprovalGateway.request_approval`、`interrupt(...)` 携带 Findings、`Command(resume=...)` 携带人工决定、调用 `ReviewerAgent.resolve()`。

### 14.2 测试仓库（外部输入，阻塞）

Gate 1B 的真实验收路径需要 Project Owner 提供独立私有 GitHub Fixture 仓库和仅安装到该仓库的开发 GitHub App。它们阻塞 AF-210 的真实 E2E 完成，不阻塞 AF-201–AF-209 的组件实现。

### 14.3 清理保证

每次 E2E 运行结束自动关闭 Marker 匹配的测试 Draft PR，并删除同一 Marker 的测试分支。GitHub PR 记录不可删除；清理不得触碰非 AegisFlow 创建的资源。

## 15. Codex 实施顺序

严格顺序（同 §1 末尾），理由：虽然 GitHub 原生 Dependencies 字段允许 AF-204 与 AF-201/202/203 并行、AF-207 与 AF-205/206 并行，但本项目实际只有一位 Codex 执行者在同一时间推进一个 PR（不是多 Agent 并行开发），强制串行不产生吞吐损失，却能保持与 M1 相同的"文件所有权单向递增、永不冲突"纪律，代价为零、收益是可预测性。此顺序满足全部十个 Issue 的原始 Dependencies 声明，未修改 GitHub 上的 Dependencies 数据本身。

## 16. Resolved Decisions 与外部输入

设计决策已经关闭，不再保留实现期待定项：

1. Gate 1B 触发事件固定为 `repository_dispatch`；不使用 push 或 Issue 标签作为 M2 触发器。
2. GitHub 客户端固定为现有异步 `httpx` + `PyJWT[crypto]`/`cryptography`。
3. pgvector 集成固定使用官方 `pgvector` Python 包。
4. Docker 编排固定使用专用 `SandboxBroker` 窄协议；通用 socket proxy 与 Core 直持 socket 均被否决。
5. Policy Gate 固定使用可信 `RepositoryTarget/ExecutionScope`；不修改或解析冻结的 `NormalizedRequest.source_ref`。
6. AF-201 replay TTL 固定 10 分钟。Sandbox 默认 120 秒/512MB/1 CPU/128 pids，硬上限 600 秒/2048MB/2 CPU/256 pids。
7. Draft PR 固定为 L3，所有路径都需要绑定目标与内容摘要的数据库审批授权。
8. AF-206/AF-209 migration 依次为 `0004`/`0005`；所有 I/O 协议从首次实现起均 async。

仍需 Project Owner 在 AF-210 真实验收前提供的只是外部资源，不是设计决策：

- 一个独立私有 GitHub Fixture 仓库（建议 `KinguYume-G/AegisFlow-Gate1B-Fixture`）。
- 一个仅安装到该 Fixture 仓库的开发 GitHub App。
- 在 protected GitHub Environment 中配置 App ID、Installation ID、Private Key 与 Webhook Secret；Secret 不进入文档、Issue、PR 或聊天。

这些外部资源不阻塞 AF-201–AF-209 的组件实现，但缺失时 AF-210 不得宣称真实 E2E 完成。
