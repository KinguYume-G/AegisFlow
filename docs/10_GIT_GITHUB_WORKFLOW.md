# 10 — Git & GitHub Workflow

## GitHub 是执行事实源

Roadmap 提供基线；Milestone 提供当前计划；Issue 提供任务状态；PR 提供实现证据；Release 提供 Gate 结果。

## Status Flow

```text
draft → ready → in-progress → review → changes-requested → approved → merged → verified
```

## One Issue, One PR

例外仅限紧急安全修复、自动依赖更新和拼写修复，即使例外也要后补 Issue。

## Branch Protection 目标

- 禁止直接 push main
- 至少 1 个 Human Review
- 必需检查通过
- Review conversation 已解决
- 禁止 force push
- 禁止 AI 自我批准

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
