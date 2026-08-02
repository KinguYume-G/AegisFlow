# 07 — AI Collaboration Protocol

## 目标

让不同 AI 在数月内持续开发同一项目，而不依赖单次聊天记忆。

## 文档是外部记忆

项目事实必须写入 Charter、Architecture、ADR、Roadmap、Issue、Design Note、Test Plan、PR、Handoff 和 Decision Log。

## 会话启动协议

AI 先确认：

```text
Current Milestone:
Selected Issue:
Dependencies:
Relevant ADRs:
Security Risk:
Required External Inputs:
```

任何一项不明确时停止实现。

## Context Packet

每个 Issue 包含：

1. Issue body
2. Relevant architecture
3. Relevant ADR
4. Affected interfaces
5. Current tests
6. Security constraints
7. Last handoff
8. Definition of Done

## Design First

非文档 Issue 必须先输出 Design Note，未通过 Review 前不写业务实现。

## Test First

先确定测试类型、Fixture、Mock 边界、外部副作用、失败注入、安全负向测试和预期结果。

## Small Iterations

一次 PR 只交付一个行为变化。禁止大规模重构、跨 Milestone、同时新增框架和业务、为未来提前抽象、批量生成未使用接口。

## AI Review Checklist

- [ ] 冻结方向一致
- [ ] Issue 范围内
- [ ] 无真实 Secret
- [ ] 测试先行
- [ ] 失败路径
- [ ] 权限路径
- [ ] 幂等
- [ ] 文档同步
- [ ] 无虚构结果
- [ ] 无被否决技术
- [ ] 可回滚

## Handoff

记录 Issue、Branch、PR、完成度、设计、变更文件、测试、错误、风险、人工输入和下一条最小动作。

## 禁止

AI 不得改变方向、创建新平级 Agent、自行提供 Secret、访问生产、自行 Merge、降低测试门槛、伪造指标或用聊天替代文档更新。
