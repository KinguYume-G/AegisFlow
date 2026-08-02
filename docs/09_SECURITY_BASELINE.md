# 09 — Security Baseline

## 安全假设

- LLM 是不可信决策组件
- RAG 文档是不可信输入
- MCP Tool 是高风险能力
- Sandbox 可能运行恶意代码
- 租户互不信任
- 外部 Webhook 可伪造

## 默认策略

Deny、Least Privilege、Human Approval、No Network by Default、Secret by Reference、Append-only Audit、Tenant Isolation、Structured Output、Deterministic Policy。

## Risk Levels

| Level | Example | Default |
|---|---|---|
| L0 | Read docs | Auto |
| L1 | Run tests | Auto |
| L2 | Temporary branch edit | Auto + Audit |
| L3 | Create Draft PR | Reviewer approval |
| L4 | Merge PR | Tech Lead approval |
| L5 | Production deploy / DB change | Two-person approval |

## Authentication

OIDC、短期 Token、Service Account 最小权限、issuer/audience/expiry 验证，不自建密码。

## Authorization

RBAC 处理身份，Contextual Policy Rules 处理 tenant、repo、environment、risk、approval。LLM 不可覆盖 Policy。

## Prompt Injection

采用来源标记、指令边界、结构化输出、Tool Schema、Policy Gate、Human Approval、Audit 和 Security Dataset。检测失败也不得导致权限绕过。

## Sandbox

M2 Docker：non-root、read-only FS、no Docker socket、resource limit、timeout、temporary workspace、network disabled/allowlist、cleanup。

M5 k3s：`runAsNonRoot`、`readOnlyRootFilesystem`、`seccompProfile`、no hostPath、NetworkPolicy、ResourceQuota、TTL cleanup。

## Secret

模型上下文、Trace、日志和审计只记录 Secret ID，不记录值。

## Supply Chain

锁依赖、依赖更新、Container scan、SBOM、固定 GitHub Action 版本、第三方 MCP 登记和 Review。

## Security Gate

High-risk Issue 必须有 Security Reviewer；没有 Reviewer 不得 Merge。
