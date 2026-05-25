# Notion Skill 数据库配置

## 数据库信息

| 属性 | 值 |
|:-----|:----|
| 名称 | ⛸️ Skill数据库 |
| ID | `332a603bc24180398df7f9cdbba1fc2c` |
| URL | `https://www.notion.so/332a603bc24180398df7f9cdbba1fc2c` |
| 父页面 | Hermes Sync |
| API Version | `2022-06-28` |

## 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|:-------|:-----|:----:|:-----|
| Skill Name | title | ✅ | skill 名称，从目录名获取，不是文件名 |
| Skill 创建时间 | date | ✅ | SKILL.md 文件修改日期，YYYY-MM-DD |
| 触发词 | multi_select | ✅ | 触发该 skill 的中英文关键词 |
| Skill 来源 | select | ✅ | **当前运行环境**的来源标识（见下） |
| Skill 功能 | rich_text | ✅ | SKILL.md frontmatter 的 description |
| Skill Git repo 地址 | url | ✅ | GitHub 私有仓库 URL |

## Skill 来源（动态，不要写死）

**禁止**默认填 `Hermes Agent`。值来自 skillfy **步骤 0**：

```bash
bash ~/.hermes/skills/productivity/skillfy/scripts/skill-source.sh get
```

- 已配置 → 用打印的名称
- `MISSING` → 先问用户（见 skillfy `SKILL.md` 步骤 0.2），再 `skill-source.sh set "<名称>"`

持久化（按环境分开，同一环境只问一次）：

| 环境 | 文件 |
|:-----|:-----|
| Cursor | `~/.cursor/skillfy.env` |
| Hermes Agent | `~/.hermes/skillfy.env` |

拉取 Notion 已有下拉项：`skill-source.sh list`。用户可选手头选项或**自定义新名称**（脚本会同步加到 Notion select）。

### 历史/常见选项（仅供参考，以 `list` 为准）

| 名称 | 说明 |
|:-----|:-----|
| `Hermes Agent` | Hermes Agent 环境 |
| `MacMINI claw` | MacMINI claw 环境 |
| `macbookpro-cursor` | MacBook Pro 上的 Cursor |

## 路径解析规则（核心坑）

不要从文件名获取 skill 名称。路径结构：

```
~/.hermes/skills/<category>/<skill-name>/SKILL.md
                ↑category  ↑skill-name  ↑不要取这个
```

- 2 层路径：`productivity/group-task-auditor/SKILL.md` → name = `group-task-auditor`（倒数第 2 段）
- 3 层路径：`mlops/inference/gguf/SKILL.md` → name = `gguf`（倒数第 2 段）
- 1 层路径：`anysearch/SKILL.md` → name = `anysearch`（第 1 段）

## 只加用户自建 skill（核心坑）

不要遍历所有 `~/.hermes/skills/**/SKILL.md` 往数据库里填。只加以下列表中的：

**Hermes Agent 自建 skill（11 个）：**
- `group-task-auditor` — 团队任务管理
- `group-task-auditor` — 团队任务管理
- `welike-pending-tasks` — 未开始任务检测
- `skillfy` — 本 skill 自身
- `notion-skill-sync` — Notion 同步
- `feishu-lark-cli` — 飞书 CLI 数据访问
- `feishu-whiteboard-analyzer` — 白板分析
- `xlsx-analysis` — Excel 数据分析
- `wecom-agent-analysis` — 企微经纪人分析
- `feishu-connectivity` — 飞书连接诊断
- `article-resonance-analysis` — 文章共振分析
- `article-resonance-analysis` — 文章共振分析
- `video-summarization` — 视频摘要（BibiGPT）

**MacMINI claw 自建 skill（4 个，已存在 DB 中）：**
- `x-article-pdf` — X Article PDF 导出
- `skill-publisher` — Skill 发布器
- `tdd-debugger` — TDD 调试器
- `wechat-album-scraper` — 微信专辑抓取

**其他来源（不归入自建，已有 DB 记录不下表）：**
- `bibigpt-video-analysis`
- `xiaohongshu-cli`

## 同步时的常见错误

| 问题 | 导致 | 修正 |
|:-----|:-----|:-----|
| 创建新数据库而非用现有的 | 用户纠正 | 直接用 `332a603bc24180398df7f9cdbba1fc2c` |
| 名字全是 "SKILL.md" | `parts[-1]` 取了文件名 | 用 `parts[-2]` 取目录名 |
| 塞入 113 个内置 skill | 遍历了全部 SKILL.md | 只取上表列出的用户自建 skill |
| 缺少 Skill 创建时间 | 没传 date 字段 | 用 `os.path.getmtime()` 获取 |
| 缺少 Git repo | skill 没创建 GitHub 仓库 | 先执行 git init → gh repo create |
| execute_code 中 `os.popen(grep...)` 被 `***` 掩码截断 | 掩码插入到 shell 命令中导致语法错误 | 将脚本写入临时文件再通过 terminal 执行：`write_file` → `python3 /tmp/script.py` |
