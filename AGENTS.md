# AGENTS.md — AegisFlow AI 开发总协议

本文件约束所有参与 AegisFlow 的 AI 编码代理、Chat Assistant、Codex、IDE Agent 与自动化工具。

首次进入仓库或开始新会话时，必须先阅读 [`START_HERE.md`](START_HERE.md)。本文件继续作为 AI 开发约束的权威协议。

## 最高优先级

1. 不修改产品方向。
2. 不绕过 GitHub Issue。
3. 不在设计和测试计划之前写业务代码。
4. 不使用或编造密钥。
5. 不自我批准或自我 Merge。
6. 不把目标写成已经实现。
7. 不引入被否决的 Kafka、Terraform、SFT/LoRA、CrewAI、通用 ABAC、微服务拆分或 Workflow Builder。

## 冲突解决顺序

1. `docs/DESIGN_BLUEPRINT.md`
2. `docs/00_PROJECT_CHARTER.md`
3. Accepted ADR
4. `docs/02_ARCHITECTURE.md`
5. 当前 Milestone / GitHub Issue
6. Developer Guide 和其他文档
7. 聊天上下文或 AI 记忆

低优先级内容与高优先级冲突时，立即停止并报告。

## 每次会话必须读取

- `START_HERE.md`
- `AGENTS.md`
- `docs/index.md`
- Project Charter
- Architecture
- 当前 Milestone
- 当前 Issue
- 相关 ADR
- 相关测试策略
- 最近 Handoff

## 固定开发循环

```text
读取文档
→ 选择 ready Issue
→ 确认依赖
→ 写 Design Note
→ 写或更新测试
→ 最小实现
→ 跑测试
→ 修复
→ 安全与质量检查
→ 更新文档与 Traceability
→ 提 PR
→ 等待 Human Review
→ 修复 Review
→ Human Merge
→ 更新 Issue / Milestone
→ 下一个 Issue
```

## Issue 选择

只能领取：

- `status:ready`
- 无未完成依赖
- 验收标准明确
- 安全和测试范围明确
- 一个 PR 内可完成
- 不越过冻结范围

## 设计规则

非文档 Issue 必须先有 Design Note，说明问题、非目标、受影响模块、状态所有权、外部副作用、幂等、失败、安全、测试、文档和回滚。

## 实现规则

- 最小改动，不顺手重构；
- 新依赖需 Issue 批准；
- 外部副作用必须幂等；
- LLM 不得决定最终权限；
- Redis 不是业务事实源；
- Temporal 与 LangGraph 不得重复拥有同一状态；
- MCP 写工具必须经过 Policy Gate；
- Secret 不进入 Prompt、Trace 或日志。

## 测试规则

- Bug 先有失败测试；
- 副作用有重复执行测试；
- 安全改动有负向测试；
- 跨租户改动有隔离测试；
- Temporal 改动考虑 replay/retry/signal；
- LangGraph 改动考虑 checkpoint/resume；
- 不允许通过删断言、跳过测试或降低门槛来修复失败。

## Git 规则

- 默认 One Issue、One Branch、One PR；仅在 Project Owner 明确批准时，可将最多 10 个依赖闭合 Issue 合并为一个批次 Branch/PR，并逐 Issue 保留 AC、测试证据、Traceability 与回滚边界；
- Branch：`type/AF-xxx-short-name`；
- Conventional Commits；
- AI 不得直接推送 main；
- AI 不得自行 Merge。

## 停止条件

需要真实 Secret、未授权仓库、高风险外部写操作、缺少验收标准、架构冲突、冻结范围外技术或无法安全测试时，停止并要求人工输入。

## Handoff

会话结束记录 Issue、Branch、PR、完成内容、测试、变更文件、风险、阻塞和下一步。
