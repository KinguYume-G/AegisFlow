# ADR-0007 — RBAC with Contextual Policy Rules

- **Status**: Accepted
- **Decision**:
  - 身份授权使用 RBAC。
  - 工具副作用使用确定性的 Contextual Policy Rules。
  - 不实现通用 ABAC 管理平台。
- **Inputs**: role、tenant、repository、environment、risk、approval、tool scope。
- **Rule**: LLM 不可覆盖 Policy 结论。
