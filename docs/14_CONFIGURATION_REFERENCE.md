# 14 — Configuration Reference

## 原则

配置与代码分离；Secret 只用引用；不提供默认生产密码；环境分开；`.env.example` 只写占位符。

## 配置组

| Group | Examples | Secret |
|---|---|---|
| App | APP_ENV、URLs | No |
| PostgreSQL | DATABASE_URL | Yes |
| Redis | REDIS_URL | Usually |
| Temporal | Address、Namespace、Queue | Maybe |
| OIDC | `OIDC_ISSUER`、`OIDC_AUDIENCE`、`OIDC_JWKS_URL`、asymmetric `OIDC_ALGORITHM`、bounded cache/timeout | No（AF-402 仅验证外部 Token，不持有 Client Secret） |
| GitHub App | App ID、Private Key、Webhook Secret、Installation ID、API Timeout | Yes（凭据项） |
| Model | Names、API Key | Yes |
| Langfuse | Host、Keys | Yes |
| OTel | Export endpoint | Maybe |
| Sandbox | Runtime、allowlist | No |
| Encryption | Key reference | Yes |

## 需要项目所有者提供

- GitHub 测试组织或仓库
- GitHub App 配置
- OIDC Provider
- 至少一个 Model Provider
- Langfuse 实例
- 演示部署环境
- 可选域名

未提供时对应 Issue 保持 blocked，不得编造。

AF-402 的本地与 CI 验证使用运行时生成的测试密钥，不提交凭据。真实 Provider 参数只通过环境配置注入；Bearer Token 不得进入日志、Trace、异常或仓库文件。

## Redaction

日志只记录 `secret_name=<REFERENCE>` 和 `secret_present=true|false`。
