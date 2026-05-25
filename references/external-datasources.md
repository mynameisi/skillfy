# 外接数据源 — Skill 登记全量同步

skillfy 在 **GitHub 发布完成后（步骤 8）** 可询问用户是否做**全量同步**：把当前环境里所有「用户自建 skill」的元数据，与下列数据源里的记录**对齐**（有则更新、无则新建；**不删**数据源里多出来的行）。

## 数据源一览

| ID | 名称 | 类型 | 入口 |
|:---|:-----|:-----|:-----|
| `notion` | Notion ⛸️ Skill数据库 | API | [数据库](https://www.notion.so/332a603bc24180398df7f9cdbba1fc2c) |
| `feishu` | 飞书 Skill数据库 | 多维表格 + lark-cli | [Wiki](https://mf4bkrtazt.feishu.cn/wiki/JQ93wrw2Ei0CFCkuzkwckp2nnjh) |

**不是 skill、不要同步进去的数据源：**

| 名称 | 说明 |
|:-----|:-----|
| [Prompt Skill 数据库](https://mf4bkrtazt.feishu.cn/wiki/GMHFwPV7ciMK3ckFN3JcAlHmntf) | 存 **prompt 模板**，只有 `类型=skill` 且带 GitHub 的 2 条才算 skill；其余禁止迁入 Skill数据库 |

## 字段对齐（两库相同语义）

| 字段 | 来源 |
|:-----|:-----|
| Skill Name | 目录名 / `name:` frontmatter |
| Skill 创建时间 | `SKILL.md` mtime → `YYYY-MM-DD`（Notion）/ ms timestamp（飞书） |
| 触发词 | 从 description 提炼 2–7 个词；飞书须为已存在下拉项或先 `field-update` 补选项 |
| Skill 来源 | `skill-source.sh get`（步骤 0） |
| Skill 功能 | frontmatter `description` |
| Skill Git repo 地址 | `https://github.com/mynameisi/<repo-name>`（须已 push） |

## 全量同步包含哪些 skill？

脚本 `scripts/sync-external-datasources.sh` 扫描：

1. `~/.hermes/skills/**/SKILL.md`（2–3 层目录，目录取倒数第二段为 skill 名）
2. `~/.cursor/skills/**/SKILL.md`
3. 当前项目 `.cursor/skills/**/SKILL.md`（若在 skillfy 会话中）

**纳入条件（须同时满足）：**

- 目录内有 `SKILL.md`，且能解析出 `description`
- 存在 `git remote` 且 URL 含 `github.com/mynameisi/`（或用户确认的 org）
- **不是**内置/第三方克隆的 reference skill（见 `references/skill-inventory.md` 排除表）

## 执行命令

```bash
export HERMES_HOME="$HOME/.hermes"
SCRIPT=~/.hermes/skills/productivity/skillfy/scripts/sync-external-datasources.sh

# 发布 skillfy 后，用户确认「全量同步」时：
bash "$SCRIPT" check                    # 检查 Notion token + 飞书 lark-cli
bash "$SCRIPT" sync --target notion     # 仅 Notion 全量
bash "$SCRIPT" sync --target feishu     # 仅飞书全量
bash "$SCRIPT" sync --target all        # 两者都全量
```

环境变量（可选）：

| 变量 | 默认 |
|:-----|:-----|
| `GITHUB_ORG` | `mynameisi` |
| `FEISHU_SKILL_DB_ENV` | `~/.cursor/feishu-skill-db.env` |
| `NOTION_DB_ID` | `332a603bc24180398df7f9cdbba1fc2c` |

## 与单条同步的关系

| 场景 | 用哪个 |
|:-----|:-------|
| skillfy 刚发布完 **一个** skill，用户只要登记这一条 | 步骤 8 选「仅同步当前 skill」→ `notion-skill-sync` 或增量逻辑 |
| 用户要 **整库对齐**、补历史遗漏 | 步骤 8 选「全量」→ `sync --target all` |
| 只做 Notion、不做飞书 | `--target notion` |

## 依赖 skill

- **Notion**：`notion-skill-sync`（字段与 API 细节）
- **飞书**：`feishu-connectivity` + `feishu-lark-cli`（OAuth、`lark-cli` 路径）
- **来源字段**：`skill-source.sh`（与 skillfy 步骤 0 共用）
