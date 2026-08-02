# 11 — Documentation Governance

## 分类

| 类型 | 作用 | 变更 |
|---|---|---|
| Design Blueprint | 冻结方向 | 正式变更 |
| Charter | 使命与范围 | 严格控制 |
| Architecture | 当前架构 | 随实现更新 |
| ADR | 决策与原因 | Accepted 后结论不改 |
| Roadmap | 阶段计划 | Gate Review |
| Issue | 单次工作 | GitHub 实时 |
| Guides | 实施规则 | 随工具链更新 |
| Reports | 测量证据 | 不覆盖历史 |

## 状态

Draft、Proposed、Accepted、Superseded、Deprecated。

## 同步

代码改变架构、行为、配置、权限、测试或部署时，必须同 PR 更新文档。

## 审查

Architecture 需 Architect Review；Security 需 Security Review；ADR 需 Project Owner 接受；README 指标需链接报告。

## 禁止

文档与实现不一致、删除失败历史、把目标写成结果、放 Secret、用聊天替代 ADR。
