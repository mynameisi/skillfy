---
name: skillfy
description: "发布 skill 到 GitHub 私有仓库 + 同步到 Notion Skill 数据库。所有自建 skill 必须有 repo。"
version: 2.1.0
author: Hermes Agent
metadata:
  hermes:
    tags: [skill, publish, github, git, workflow, notion]
    prerequisites: [gh CLI authenticated with repo scope, NOTION_API_KEY in .env]
---

# Skillfy — Skill 发布 + 同步到 GitHub + Notion

## 触发条件

当用户要求以下任一操作时，加载本 skill：
- 「把 xxx 保存成 skill」并要求「推到 private repo」
- 发现某个用户创建的 skill 没有 GitHub repo 且需要补上
- 「发布 skill」/「push skill」

对于纯 Notion 同步（不涉及 GitHub 发布），应加载 `notion-skill-sync` 而非本 skill。

## 核心政策

**用户创建的每个 skill 都必须有 GitHub 私有仓库。** 没有 repo 的 skill 不是已完成的 skill——创建流程的最后一步一定是推 GitHub。

## 前置条件

```bash
# 确保 gh CLI 已登录且有 repo 权限
gh auth status
# → 应有 'repo' scope

# Notion 同步需要
grep NOTION_API_KEY ~/.hermes/.env
# Cursor 环境也可放在 ~/.cursor/.env
```

## 完整工作流

### 步骤 0：确定当前环境的 Skill 来源（仅首次询问）

Notion 字段 **Skill 来源** 表示「这条 skill 是在哪个运行环境里建的」。**同一环境里之后再用 skillfy，不要再问**——写入本机配置文件一次即可。

| 运行环境 | 判定（满足任一即可） | 持久化文件 |
|:---------|:---------------------|:-----------|
| **Cursor** | `CURSOR_*` 环境变量；或工作区有 `.cursor/`；或 skill 在 `~/.cursor/skills/` / 项目 `.cursor/skills/` | `~/.cursor/skillfy.env` |
| **Hermes Agent** | skill 在 `~/.hermes/skills/`；或上述均不满足时的默认 | `~/.hermes/skillfy.env` |

文件内容一行：`SKILL_SOURCE=<名称>`（chmod 600，**不要**提交到 git）。

#### 0.1 读取已保存的来源

```bash
bash ~/.hermes/skills/productivity/skillfy/scripts/skill-source.sh get
# 已配置 → 打印来源名，例如 macbookpro-cursor
# 未配置 → 打印 MISSING
```

（脚本在 Cursor 项目里也可写相对路径：`bash .cursor/skills/.../skillfy/scripts/skill-source.sh`，若已 clone 到个人 skills 则用 `~/.hermes/skills/productivity/skillfy/scripts/skill-source.sh`。）

#### 0.2 首次使用：必须问用户

当 `get` 输出 **MISSING** 时：

1. 拉取 Notion 已有选项：
   ```bash
   bash .../scripts/skill-source.sh list
   # → JSON 数组，如 ["MacMINI claw","Hermes Agent","macbookpro-cursor"]
   ```
2. **用 AskQuestion（或一轮对话）问用户**，文案要点：
   - 「当前运行环境的 Skill 来源应该记成什么？」
   - 选项 = `list` 里的每一项 + **「其他（自定义新名称）」**
   - 若选自定义：让用户输入新名称（例如 `macbookpro-cursor`）
3. 用户确认后持久化（会自动在 Notion 下拉中补选项，若尚不存在）：
   ```bash
   bash .../scripts/skill-source.sh set "<用户确认的名称>"
   ```
4. 向用户简短确认：`已记住：本环境 Skill 来源 = <名称>，保存在 <config-path>`。

**禁止**在未询问的情况下擅自填 `Hermes Agent` / `MacMINI claw`。

#### 0.3 之后每次 skillfy

先 `get`；只要不是 MISSING，**直接使用该值**写入 Notion，不要再问。

若要更换来源：`skill-source.sh set "<新名称>"`（会覆盖配置文件）。

---

### 步骤 1：创建/更新 skill

使用 `skill_manage` 工具创建或更新 skill：

```bash
# 创建新 skill
skill_manage(action='create', name='skill-name', category='category', content='SKILL.md content')

# 或更新已有 skill
skill_manage(action='patch', name='skill-name', old_string='...', new_string='...')
```

Skill 文件默认路径：
```
~/.hermes/skills/<category>/<skill-name>/SKILL.md
```

### 步骤 2：添加 README.md（可选但推荐）

向 skill 目录写入简要的 README.md，介绍用途和工作流。

### 步骤 3：Git 初始化

```bash
cd ~/.hermes/skills/<category>/<skill-name>/
git init
git add SKILL.md README.md
git commit -m "init: <skill-name> skill"
```

### 步骤 4：创建 GitHub 私有仓库

```bash
cd ~/.hermes/skills/<category>/<skill-name>/
gh repo create mynameisi/<skill-name> --private --push --source=. --remote=origin
```

⚠️ **坑：远程已有内容时如何处理**

如果 `gh repo create` 报错 `Name already exists on this account`，说明该 repo 已在远程存在（可能是之前创建过）：

```bash
# 方案 A：已有远程内容，需 force push（需用户确认）
git remote add origin git@github.com:mynameisi/<skill-name>.git  # 如果还没加
git push -f origin main  # 需要用户 approval
```

### 步骤 5：处理冲突（如有）

当远程和本地历史分叉时：

```bash
# 查看状态
git diff HEAD -- SKILL.md

# 如确认本地版本是更新版，直接 force push
git push -f origin main
```

⚠️ **`git push -f` 需要用户手动 approval** — 在 terminal 工具中会触发安全确认，等用户通过即可。

### 步骤 6：向用户报告结果

```
已推到 GitHub ✅

Repo：github.com/mynameisi/<skill-name>（PRIVATE）

| 文件 | 内容 |
|:-----|:-----|
| SKILL.md | 完整 skill |
| README.md | 简要说明 |
```

### 步骤 7：同步到 Notion Skill 数据库

发布到 GitHub 后，同步 skill 元数据到 **[已有] Skill 数据库**。推荐加载 `notion-skill-sync` 来执行同步，该 skill 是独立的、更专注的 Notion 同步 skill。

⚠️ **绝对不要创建新的数据库**——用户已有现成的 Skill 数据库（ID=`332a603bc24180398df7f9cdbba1fc2c`）。

如果选择在 skillfy 工作流内完成同步：

0. **Skill 来源**：`bash .../scripts/skill-source.sh get`（见步骤 0；MISSING 则先完成 0.2 再问用户）
1. 查询 DB 当前已有条目（避免重复）
2. 为新 skill 创建 Notion 页面（字段见 `references/notion-skill-db.md`），其中 **Skill 来源** = 步骤 0 得到的值
3. 只加用户自建的 skill，不塞入内置 skill

⚠️ **execute_code 中的 .env 读取坑**：直接使用 `os.popen("grep NOTION_API_KEY...")` 在 execute_code 中可能因 `***` 掩码导致 shell 命令被截断。可靠方案：用 `write_file` 写入临时脚本 → `python3 /tmp/notion_sync.py` 通过 `terminal()` 执行。

#### 常见错误

| 症状 | 原因 | 修复 |
|:-----|:-----|:-----|
| 名字全是 "SKILL.md" | path 解析错了——取了文件名而非目录名 | name = parts[-2]（倒数第二段） |
| 数据库里塞满 113 个内置 skill | 没过滤，直接遍历了所有 SKILL.md | 只取用户自建的（约 10 个） |
| 没有创建时间 | 忘了传 date 字段 | 加 `Skill 创建时间` |
| 没有 repo URL | skill 没有 GitHub 仓库 | 先执行步骤 1-6 创建 repo |
| Skill 来源填错 / 每次都被问 | 未跑步骤 0；或不同环境共用了错误默认值 | `skill-source.sh get/set`；Cursor 与 Hermes 各有一份 `skillfy.env` |
| execute_code 中 shell 命令被 `***` 截断 | API key 被日志掩码系统重写 | write_file → terminal 执行 |

## 已实践验证的场景

| 场景 | 状态 |
|:-----|:-----|
| 全新 skill + 全新 repo | ✅ 一次成功 |
| 已有 skill + 已有 repo（旧版本） | ⚠️ force push + merge conflict |
| skill 本身是已有 skill，但本地没有 git repo，需要新建 | ⚠️ 检查 `gh repo create` 是否报 "Name already exists"；若报，add remote → fetch → force push |
| 多文件 skill（reference、template） | ✅ 加 git add 即可 |
| skill 同步到 Notion Skill 数据库 | ✅ 已验证：15+ skill 成功写入 |
| 补填 repo 时 gh repo create 已存在 | ⚠️ `Name already exists on this account` → `git remote add origin` → `git fetch origin` → `git push -f origin main` |
| 提取 Notion 同步为独立 skill notion-skill-sync | ✅ 本 skill 的 Step 7 内容已提取为独立 skill，GitHub + Notion 全链路 |

## 注意事项

- `gh repo create` 的 `--source=.` 会自动从当前目录推代码
- 如果先 `git init` 再 `gh repo create --push`，注意远程是否已有历史
- force push 需要用户确认 — 这是 gh CLI 的安全机制，不是错误
- 私有仓库作用域：只有用户自己可以访问
- **Notion skill 名称必须从目录名获取，不是从文件名**。路径 `category/name/SKILL.md` 中 name 在倒数第二段，不是最后一段
- **只同步用户自建 skill** — 不要把所有内置 skill 都填入数据库，用户会纠正
- **Notion 同步已提取为独立 skill** `notion-skill-sync`。如果只需同步 skill 元数据到 Notion DB，直接加载该 skill
