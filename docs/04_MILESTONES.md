# 04 — Milestones

| ID | 名称 | 周期 | Gate |
|---|---|---:|---|
| M0 | Engineering System | Phase 0 | Documentation Gate |
| M1 | Demand to Plan | Week 1–1.5 | Gate 1A |
| M2 | Plan to Draft PR | Week 1.5–3 | Gate 1B |
| M3 | Reliable Runtime | Week 4–6 | Gate 2 |
| M4 | Governance & Security | Week 7–9 | Gate 3 |
| M5 | Evaluation & Deployment | Week 10–12 | Gate 4 |
| MR | Post-MVP Roadmap | After M5 | Optional |

## M0 Exit

Required docs complete, ADR accepted, Issue backlog importable, AI protocol active, no business code.

## M1 Exit

真实 Issue 被标准化；Clarifier 可等待回复；Context 有引用；Planner 输出 Plan/Risk/Budget；Trace 可见；Gate 1A E2E 通过。

## M2 Exit

Policy 在 Executor 前执行；沙箱改码和测试；Reviewer 有证据；高风险等待审批；Draft PR 成功；重复 Webhook 不重复建 PR。

## M3 Exit

Worker Kill 后恢复；重复副作用为 0；主模型故障可降级；20 次故障注入报告、Demo 和 Blog 完成。

## M4 Exit

Tenant A 不可读取 B；无权限角色不能调用写工具；RAG Injection 被标记且 Policy 拒绝；Audit 可追踪。

## M5 Exit

评测集可重复；Prompt 退化被 CI 拦截；100 并发报告完成；k3s + Helm 可演示；四个必做演示通过；README 只有真实数字。

## Milestone Review

Review Scope、测试、安全、文档、风险、Gate 和是否允许下一阶段。
