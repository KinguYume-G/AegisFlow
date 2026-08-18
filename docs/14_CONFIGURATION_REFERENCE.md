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
| Local MVP | `LOCAL_MVP_*`, loopback ports, dry-run flag | Local-only token values; forbidden in production |
| Ollama | `MODEL_OLLAMA_*`, `OLLAMA_MODEL` | No hosted Secret; placeholder key is local adapter compatibility only |
| Console BFF | `AEGISFLOW_CORE_URL`, Persona, local token, Console URLs | Local token is server-only and development-only |

## Local MVP profile

`LOCAL_MVP_PROFILE_ENABLED` is default-off and accepted only in `development` or `test`. The profile uses two distinct local Persona tokens, loopback-bound ports, Ollama, and `LOCAL_MVP_GITHUB_DRY_RUN=true`. It must never be used as a production authentication mechanism or as evidence of a real GitHub write.

Use [`.env.local-mvp.example`](../.env.local-mvp.example) as the copyable local template. The copied `.env.local-mvp` file is ignored. `MODEL_OLLAMA_*` is a separate route from the optional vLLM fallback and is rejected by production configuration.

The Next.js Console reads `AEGISFLOW_LOCAL_TOKEN` only in server code and proxies through Route Handlers. No local token is serialized into browser props or client-side JavaScript. Production must replace this profile with an OIDC-backed server session and keep authorization in Core.

## 需要项目所有者提供

- GitHub 测试组织或仓库
- GitHub App 配置
- OIDC Provider
- 至少一个 Model Provider
- Langfuse 实例
- 演示部署环境
- 可选域名

本地 dry-run MVP 不需要这些真实 Secret。进入真实 provider、GitHub canary 或生产部署 Issue 时，未提供的对应输入保持 blocked，不得编造。

Secret 应放入受保护 GitHub Environment 或选定的生产 Secret Store；聊天、Issue、PR、Prompt、Trace 和日志中只传递 Secret 名称或引用，不传值。

AF-402 的本地与 CI 验证使用运行时生成的测试密钥，不提交凭据。真实 Provider 参数只通过环境配置注入；Bearer Token 不得进入日志、Trace、异常或仓库文件。

## Redaction

日志只记录 `secret_name=<REFERENCE>` 和 `secret_present=true|false`。
