# ADR-0003 — Do Not Use Kafka in MVP

- **Status**: Accepted
- **Decision**: 使用 Temporal Signal / Task Queue 和 Redis Streams，不引入 Kafka。
- **Reason**: 当前规模和一致性需求不需要独立事件流平台。
- **Redis Scope**: UI 实时事件和轻量通知，不负责 Durable Workflow。
- **Revisit When**: 多消费者事件回放、长期保留或跨团队事件平台成为真实需求。
