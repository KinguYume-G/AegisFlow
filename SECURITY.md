# Security Policy

## Secret Policy

真实 Secret 只能通过本地未跟踪环境变量、GitHub Encrypted Secrets、OIDC/Workload Identity、Secret Manager 或 Kubernetes Secret 提供。

禁止把真实 Secret 写入代码、`.env.example`、Issue、PR、Chat、Prompt、Trace、日志、截图或测试 Fixture。

## 默认安全边界

- LLM 不直接批准权限；
- MCP Tool 必须做 Scope 和 Policy Check；
- 高风险动作必须 Human Approval；
- 沙箱默认无网络或白名单；
- 多租户访问绑定 `tenant_id`；
- Webhook 验证签名和防重放；
- 外部副作用幂等；
- 审计日志只追加。

## 私密报告

`SECURITY_CONTACT=<TO_BE_PROVIDED>`

在私密渠道未配置前，不在公开 Issue 披露可利用细节。
