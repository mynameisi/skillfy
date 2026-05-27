# 用户自建 Skill 清单（全量同步排除/包含参考）

全量同步脚本会**自动扫描** `~/.hermes/skills` 与 `~/.cursor/skills` 下带 GitHub remote 的目录。下表用于**排除**内置 skill、或标注 repo 名与目录名不一致的特殊项。

## 明确纳入（Hermes / Cursor 自建）

| Skill Name | 典型路径 | GitHub repo |
|:-----------|:---------|:------------|
| skillfy | `~/.hermes/skills/productivity/skillfy` | `mynameisi/skillfy` |
| skill-inventory-audit | `~/.hermes/skills/productivity/skill-inventory-audit` | `mynameisi/skill-inventory-audit` |
| notion-skill-sync | `~/.cursor/skills/notion-skill-sync` | `mynameisi/notion-skill-sync` |
| grafana-dash-builder | 项目或 `~/.cursor/skills/grafana-dash-builder` | `mynameisi/grafana-dash-builder-skill` |
| session-docs-git-wrap-up | Hermes productivity | `mynameisi/session-docs-git-wrap-up` |
| learnfrom | Hermes productivity | `mynameisi/learnfrom` |
| feishu-connectivity | Hermes software-development | （按实际 remote） |
| feishu-lark-cli | Hermes productivity | （按实际 remote） |
| group-task-auditor | Hermes productivity | （按实际 remote） |
| welike-pending-tasks | Hermes productivity | （按实际 remote） |
| xlsx-analysis | Hermes productivity | （按实际 remote） |
| wecom-agent-analysis | Hermes productivity | （按 actual remote） |

> 上表不必手工维护全；以扫描 + `git remote` 为准。repo 名与目录名不同时，以 **remote 仓库名** 为 Skill Name。

## 明确排除（不要写入 Skill 数据库）

| 模式 | 原因 |
|:-----|:-----|
| `references/` 下克隆的第三方仓库 | 非自建 |
| 无 `git remote` 或 remote 不是 `github.com/<org>/` | 未发布 |
| Prompt Skill 数据库里的 **prompt 行** | 不是 skill |
| 仅含 `SKILL.md` 但无 `description` frontmatter | 不完整 |

## 目录名 ≠ repo 名

| 目录名 | repo 名 |
|:-------|:--------|
| `grafana-dash-builder` | `grafana-dash-builder-skill` |

脚本以 `git remote get-url origin` 解析 repo 名。
