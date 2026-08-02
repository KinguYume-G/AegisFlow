# 19 — Threat Model

## Assets

GitHub repositories、source code、tenant data、model credentials、GitHub App credentials、OIDC tokens、workflow state、audit logs、prompts、knowledge documents 和 sandbox capability。

## Adversaries

Malicious tenant user、compromised repository content、malicious prompt/document、compromised MCP server、external attacker、supply-chain dependency、misconfigured agent 和 operator error。

## Threats and Mitigations

| Threat | Mitigation |
|---|---|
| Prompt Injection | source boundary、schema、policy、approval、audit |
| Tool Abuse | registry、scope、contextual policy、budget |
| Cross-Tenant Leakage | tenant_id、filter、namespace、tests |
| Webhook Forgery/Replay | signature、timestamp、delivery ID、idempotency |
| Secret Leakage | reference、redaction、no prompt/sandbox secret |
| Sandbox Escape | non-root、read-only、no host mount/socket、network policy |
| Model Output Injection | structured output、validation、policy |
| Audit Tampering | append-only、restricted role、integrity backup |

每个 Threat 必须映射 Issue 和测试。
