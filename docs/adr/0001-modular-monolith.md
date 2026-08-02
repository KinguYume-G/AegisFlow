# ADR-0001 — Adopt a Modular Monolith

- **Status**: Accepted
- **Decision**: AegisFlow Core 使用单一 FastAPI 服务和明确模块边界，不拆成十个微服务。
- **Context**: 个人项目要深度验证状态、治理和评测；过早微服务增加部署、网络和一致性成本。
- **Consequences**: 开发快、事务简单、调试清晰；代价是必须严格控制模块依赖。
- **Revisit When**: 出现独立扩缩容、安全边界或团队所有权的真实需求和测量证据。
