# 10 — Git & GitHub Workflow

## GitHub 是执行事实源

Roadmap 提供基线；Milestone 提供当前计划；Issue 提供任务状态；PR 提供实现证据；Release 提供 Gate 结果。

## Status Flow

```text
draft → ready → in-progress → review → changes-requested → approved → merged → verified
```

## One Issue, One PR

例外仅限紧急安全修复、自动依赖更新和拼写修复，即使例外也要后补 Issue。

## Branch Protection（main 已生效）

自 2026-08-02 起，`main` 已启用以下保护规则：

- 所有变更必须通过 Pull Request，管理员同样受规则约束
- 必需检查 `CI / test`（API identity：`context: test`、`app_id: 15368`）通过
- 合并前分支必须与最新 `main` 保持同步
- 所有 Review conversation 必须已解决
- 禁止 force push 和删除 `main`
- 禁止 AI 自我批准或合并；仍须由 Project Owner 完成人工 Review 与 Human Merge

当前仓库只有一位可信 Human Reviewer，PR 作者无法批准自己的 PR，因此 GitHub 的
`required_approving_review_count` 暂设为 `0`。这是单人仓库的过渡设置，不代表可以跳过人工审查。
待第二位可信 Human Reviewer 加入后，必须将该值调整为 `1`，恢复平台强制的一票 Approval。

## PR Size

推荐小于 400 行有效逻辑；超过 800 行必须解释。大改动拆 Design PR 和 Implementation PR。

## Merge

优先 Squash Merge，Commit message 含 Issue ID。

## 导入

Labels、Milestones 和 Issues 分别来自 `project/LABELS.json`、`MILESTONES.json` 和 `GITHUB_ISSUE_IMPORT.csv`。

## Tags

- `v0.0.0-docs`
- `v0.1.0-gate1a`
- `v0.2.0-gate1b`
- `v0.3.0-gate2`
- `v0.4.0-gate3`
- `v0.5.0-gate4`

只有 Gate 通过才打 Tag。
