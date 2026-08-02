# ADR-0002 — Separate LangGraph and Temporal State Ownership

- **Status**: Accepted
- **Decision**:
  - LangGraph 管 Agent 图状态。
  - Temporal 管长流程、等待、外部副作用和恢复。
  - PostgreSQL 管业务事实。
  - Redis 仅做实时事件。
- **Reason**: 避免双重 Retry、状态冲突和重复副作用。
- **Rule**: 同一状态只能有一个 authoritative owner。
