# 06 — Developer Guide

## 当前状态

Phase 0 已完成。AF-101 已批准并建立 Python 3.12、uv、src-layout 与最小 FastAPI 骨架；只有下方标记为“已落地”的命令可以作为当前事实，其余工具链仍须由对应 Issue 实现。

## AF-101 已落地命令

```bash
uv sync --locked
uv run --locked python -m pytest -v --cov=aegisflow_core --cov-report=term-missing
```

启动最小应用前必须设置 `APP_ENV=development|test|production`，再执行 `uv run --locked uvicorn aegisflow_core.main:app`。当前不提供 Makefile、ruff、mypy 或 CI 命令；这些能力需要独立 Issue 批准。

## 预期工具链

- Git
- Docker Engine / Docker Desktop
- Python（由锁文件固定）
- Node.js LTS（由锁文件固定）
- pnpm（由锁文件固定）
- PostgreSQL
- Redis
- Temporal
- GitHub CLI（可选）
- k3s 和 Helm（M5）

## 开发环境原则

- 依赖通过 Docker Compose；
- Secret 放未跟踪环境变量或 Secret Manager；
- `.env.example` 只含占位符；
- 测试数据库与开发数据库分离；
- GitHub App 只安装到测试仓库；
- Sandbox 不挂载 Docker Socket；
- 不在个人主仓库测试破坏性操作。

## 标准工作流

1. 领取 `status:ready` Issue。
2. 创建 `type/AF-xxx-short-name` 分支。
3. 使用 Design Note 模板完成设计。
4. 写失败测试、契约测试或明确测试计划。
5. 最小实现，不做无关重构。
6. 运行质量门。
7. 更新文档与 Traceability。
8. 使用 PR 模板提 PR。
9. 等待 Human Review 和 Merge。

## 预期统一命令

这些是命令契约，只有实现 Issue 完成后才算可用：

```text
make format
make lint
make typecheck
make test
make test-integration
make security
make docs-check
```

在命令落地前，PR 必须列出真实执行的等价命令。

## 模块依赖

```text
packs/delivery
    ↓
runtime / control_plane interfaces
    ↓
gateway / models / evaluation
    ↓
infrastructure adapters
```

Domain 不依赖 Web Framework、MCP SDK 或 Model Provider SDK。

## 数据库规则

- tenant-owned 表带 `tenant_id`
- 使用 migration
- 审计只追加
- 版本不可覆盖
- 幂等 Ledger 有唯一约束
- 跨租户查询必须有测试

## Temporal 规则

- Workflow 代码可重放
- 非确定性和 I/O 放 Activity
- Signal 处理幂等
- Retry 按错误类型
- 不在 Workflow 直接读取网络、随机数或系统时间

## LangGraph 规则

- State Schema 明确
- 节点 I/O 结构化
- Checkpoint 标识稳定
- 节点不绕过 MCP Gateway
- Reviewer 只基于证据
- Context 必须带引用

## MCP 规则

Tool 必须先注册，具备版本、Scope、Schema、Timeout、错误分类、Policy、Audit 和幂等。Secret 不传给模型。

## 文档同步

公共接口、状态所有权、数据模型、权限、Tool、版本、测试门槛、部署和风险变化时，在同一 PR 更新文档。
