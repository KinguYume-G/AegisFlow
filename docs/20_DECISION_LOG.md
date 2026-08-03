# 20 — Decision Log

## Accepted

| ADR | Decision |
|---|---|
| ADR-0001 | Modular Monolith |
| ADR-0002 | LangGraph / Temporal State Ownership |
| ADR-0003 | No Kafka |
| ADR-0004 | No Terraform |
| ADR-0005 | No SFT / LoRA |
| ADR-0006 | No CrewAI |
| ADR-0007 | RBAC + Contextual Policy |
| ADR-0008 | Langfuse / OTel Split |
| ADR-0009 | Phased Sandbox |
| ADR-0010 | Mixed Evaluation Dataset |
| ADR-0011 | No Workflow Builder |
| ADR-0012 | OpsPilot Roadmap Only |

## Repository Governance Decisions

### Phase 0 bootstrap exception

- 项目所有者确认提交 `817751a932f16c025bfd80be73d7a57c2783497b` 与 `82c91d73867bafb7873011275abe970fb2fcd908` 是 Phase 0 初始化期间直接推送 `main` 的一次性 bootstrap exception。
- 既有提交不回滚、不重写历史，也不补造历史 PR；该例外不构成任何未来工作的先例。
- 从 Phase 0 Exit 开始，所有改动必须执行 One Issue → One Branch → One PR → Human Review → Human Merge。
- AI 不得批准或 Merge 自己创建的 PR，也不得以该 bootstrap exception 为依据绕过未来治理流程。

### CI-001 inserted ahead of AF-103

- 项目所有者在 AF-102（PR #78）合并后、AF-103 开始前，经 Tech Lead（AI）分析后决定插入 `CI-001 — Add foundational CI`（GitHub Issue #79），不在原始 75 条 canonical Backlog 内。
- 原因：AF-101/AF-102 已产生真实可合并代码，但测试通过与否此前完全依赖贡献者自报证据，无独立验证；`docs/25_PHASE0_EXIT_REVIEW.md` 记录的 main 分支无 Branch Protection 风险持续未解决；AF-103 即将引入数据库迁移，是插入 CI 回归保护性价比最高的时间点。
- `CI-001` 使用独立的 `CI-` 前缀而非 `AF-` 编号，明确标记它不属于 canonical Backlog 的 75 条规划基线，避免与 `project/GITHUB_ISSUE_IMPORT.csv` 的事实源产生混淆。
- 该插入不改变已冻结的产品方向、架构或任何 Accepted ADR，不需要新 ADR；仅新增 GitHub Actions 工作流与 Branch Protection 配置。

### AF-103 ORM and migration stack

- Project Owner 于 2026-08-02 批准 AF-103 Design Note/Test Plan v3：采用 SQLAlchemy 2.0 async + asyncpg + Alembic，并由 `uv.lock` 锁定精确依赖版本。
- 持久化实现位于既有 `control_plane/domain/` 与 `control_plane/migrations/` 子目录，不新增第七个顶层模块，不改变 ADR-0001 或 ADR-0002 的状态所有权。
- 初始六表使用租户复合外键、数据库 `CHECK`、Workflow 不可变触发器与 append-only Audit 触发器；迁移 up/down 和负向约束测试进入 Required CI。
- 该技术选择由 canonical Issue AF-103 解决 `ORM/migration` 待决项，不需要新增 ADR；未来若改变持久化系统或状态所有权，仍必须走 ADR。

### Owner-approved dependency-closed batch delivery (2026-08-03)

- One Issue → One Branch → One PR remains the default unless the Project Owner explicitly approves a batch before implementation.
- An approved batch may contain at most 10 dependency-closed Issues on one branch and one PR. Every included Issue retains independent acceptance criteria, test evidence, traceability, and rollback boundaries.
- Batch approval changes delivery granularity only; architecture, security, CI, Human Review/Human Merge, and the prohibition on AI self-approval/self-merge remain mandatory.
- The first approved batch is AF-203 through AF-207. AF-208 through AF-210 stay outside this batch because GitHub writes, persistent idempotency, and real end-to-end effects require a separate review boundary.

## Open

Python/Node 精确版本、OIDC provider、Policy representation、Object storage、Langfuse hosting、k3s environment 和 Model providers 必须通过 Issue/ADR 决定。
