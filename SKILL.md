---
name: skillfy
description: >-
  Publish a skill to a private GitHub repo with mandatory README.md, then ask
  user whether to sync to Notion/Feishu (single skill upsert only, no full
  scan). Every user-built skill must have a repo + README. Uses skill-source.sh
  for per-environment Skill 来源.
version: 2.4.0
author: Hermes Agent
metadata:
  hermes:
    tags: [skill, publish, github, git, workflow, notion, feishu, sync, windows, kiro, ntn]
    prerequisites: [gh CLI with repo scope, NOTION_API_KEY optional, lark-cli user OAuth optional]
---

# Skillfy — Skill 发布 + 可选外接数据源全量同步

## 触发条件

当用户要求以下任一操作时，加载本 skill：
- 「把 xxx 保存成 skill」并要求「推到 private repo」
- 发现某个用户创建的 skill 没有 GitHub repo 且需要补上
- 「发布 skill」/「push skill」

- 仅做 Notion/飞书同步、不发布 GitHub → 加载 `notion-skill-sync` 或飞书 `feishu-skill-db-setup.sh`，不要用本 skill 代替发布流程。

**工作流检查清单（发布一条 skill 时复制跟踪）：**

```
- [ ] 0  Skill 来源（skill-source.sh get / set）
- [ ] 1  创建 skill
- [ ] 1.5  安全审核（不篡改代码、无隐私、private）
- [ ] 2  README（必选）
- [ ] 3  Git 初始化 + commit
- [ ] 4  gh repo create（private）
- [ ] 5  处理冲突（如有）
- [ ] 6  向用户报告 GitHub 结果
- [ ] 7  询问用户 → 同步 Notion/飞书（仅当前 skill，upsert）
```

## 核心政策

**用户创建的每个 skill 都必须有 GitHub 私有仓库 + README.md。** 没有 repo 和 README 的 skill 不是已完成的 skill——创建流程的最后一步一定是「推 GitHub + 同步 Notion/飞书」。

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

### 步骤 1.5：Skill 安全审核（必做）

**推送前必须审核以下三点，审核不通过不得进入下一步：**

1. **代码不变更** — 审核 skill 内容，确保**没有修改原有代码**。Skill 只能添加/编排新功能，不得篡改项目中已有的代码逻辑。
2. **无隐私内容** — 检查 SKILL.md 和所有引用文件，确保没有暴露 token、密钥、路径、内部域名等敏感信息。
3. **默认 private** — GitHub repo 必须为 private 仓库。**任何包含隐私内容的 skill 不得发出 shared link。**

> ⚠️ 用户明确要求：技能分享一定要审核，且默认 private。违反这三条的 skill 不得发布。

### 步骤 2：添加 README.md（**必选，不可跳过**）

**每个 skill 必须有 README.md。** 不建 README = skill 未完成。

README.md 内容至少包含：
- Skill 名称 + 一句话简介
- 功能列表 / 触发条件
- 文件结构 / 输出位置
- 依赖项
- 链接到 GitHub 仓库

写入：

```bash
write_file path="~/.hermes/skills/<category>/<skill-name>/README.md" content="..."
```

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

### 步骤 7：询问 → 同步 Notion / 飞书（仅当前 skill，upsert）

**GitHub 推送完成后，用 clarify 工具询问用户是否要同步到外部数据源，不得自动同步。**

> GitHub 推送完成。要同步到外接数据源吗？
>
> - **不** — 结束 skillfy
> - **仅 Notion** — 更新 Notion Skill 数据库
> - **仅飞书** — 更新飞书 Skill 数据库
> - **Notion + 飞书** — 两者都更新

用户选「不」→ 直接结束，不要调任何 API。

用户选任意同步选项后：

**同步原则**
- **只同步当前 skill（刚发布的 `<skill-name>`），禁止扫描其他 skill**
- **已存在则更新（upsert），不会重复创建**

**Notion — 单条 upsert（仅当前 skill）**

```bash
python3 ~/.hermes/skills/productivity/skillfy/scripts/notion-upsert-single.py "$(basename "$(pwd)")"
```

**飞书 — 单条 upsert（仅当前 skill）**

```bash
export HERMES_HOME="$HOME/.hermes"
bash ~/.hermes/skills/productivity/notion-skill-sync/scripts/feishu-skill-db-setup.sh upsert-single "$(basename "$(pwd)")"
```

同步后向用户报告结果：`Notion: 更新/创建 → skillfy | 飞书: 更新/创建 → skillfy`

### （旧步骤 7 已合并）

---

### 步骤 8：（已合并至步骤 7）

2.3.0 起，同步不再询问用户。该步骤已废弃，见步骤 7。

先确保步骤 0 已配置 `SKILL_SOURCE`，再执行：

```bash
bash ~/.hermes/skills/productivity/skillfy/scripts/sync-external-datasources.sh check
bash ~/.hermes/skills/productivity/skillfy/scripts/sync-external-datasources.sh sync --target all
# 或 --target notion / --target feishu
```

若在 **Cursor 项目**里还有 `.cursor/skills/<name>/`，把项目路径传给扫描器：

```bash
bash .../sync-external-datasources.sh sync --target all \
  "/path/to/project/.cursor/skills"
```

**全量同步规则（脚本已实现，勿手写重复逻辑）：**

| 规则 | 说明 |
|:-----|:-----|
| 扫描范围 | `~/.hermes/skills/**/SKILL.md`、`~/.cursor/skills/**/SKILL.md`、可选额外根目录 |
| 纳入条件 | 有 `description` + `git remote` 指向 `github.com/<org>/` |
| 排除 | 内置 skill、无 remote、Prompt 库里的 prompt 行 |
| Notion | 同名更新 properties，否则新建页面 |
| 飞书 | 仅 **新建**缺失行（已存在则 skip，避免覆盖手改） |
| 不删除 | 数据源里多出来的行**不自动删** |

详细配置、字段映射、与 Prompt 库的区别 → **[references/external-datasources.md](references/external-datasources.md)**。排除/特殊 repo 名 → **[references/skill-inventory.md](references/skill-inventory.md)**。

#### 8.4 同步后向用户报告

```
外接数据源同步完成 ✅

| 数据源 | 结果 |
|:-------|:-----|
| Notion | 新建 N 条 / 更新 M 条 |
| 飞书   | 新建 K 条（已存在跳过） |

Skill 来源 = <skill-source.sh get 的输出>
```

#### 常见错误（步骤 8）

| 症状 | 原因 | 修复 |
|:-----|:-----|:-----|
| 把 Prompt 库里的 prompt 迁入 Skill 库 | 混淆两张飞书表 | 只同步带 GitHub 的 skill；见 external-datasources.md |
| 飞书 `not_found` 触发词 | 下拉无该选项 | 全量脚本用保守词表；或先在飞书字段补选项 |
| 飞书 rate limit | 连续 batch_create | 脚本已 sleep 2s；分批重试 |
| Notion 未配置 | 无 `NOTION_API_KEY` | `~/.hermes/.env`；或用户只选飞书 |
| 全量却漏了 Cursor 项目 skill | 未传额外扫描路径 | `sync ... /path/to/project/.cursor/skills` |
| 名字全是 "SKILL.md" | path 解析错 | 用目录名 / remote 仓库名 |
| execute_code 中 `***` 截断 token | 掩码污染 shell | 用 `sync-external-datasources.sh`，勿内联 grep token |

## 已实践验证的场景

| 场景 | 状态 |
|:-----|:-----|
| 全新 skill + 全新 repo | ✅ 一次成功 |
| 已有 skill + 已有 repo（旧版本） | ⚠️ force push + merge conflict |
| skill 本身是已有 skill，但本地没有 git repo，需要新建 | ⚠️ 检查 `gh repo create` 是否报 "Name already exists"；若报，add remote → fetch → force push |
| 多文件 skill（reference、template） | ✅ 加 git add 即可 |
| skill 同步到 Notion Skill 数据库 | ✅ 已验证：15+ skill 成功写入 |
| 飞书 Skill 数据库全量/增量 | ✅ `sync-external-datasources.sh` + `feishu-skill-db-setup.sh` |
| 补填 repo 时 gh repo create 已存在 | ⚠️ `Name already exists on this account` → `git remote add origin` → `git fetch origin` → `git push -f origin main` |
| Notion 同步独立 skill | ✅ `notion-skill-sync`；skillfy 步骤 8 可委托或全量脚本 |
| 步骤 8 询问后再同步 | ✅ 2.2.0 起默认不自动写 Notion |

## 注意事项

- `gh repo create` 的 `--source=.` 会自动从当前目录推代码
- 如果先 `git init` 再 `gh repo create --push`，注意远程是否已有历史
- force push 需要用户确认 — 这是 gh CLI 的安全机制，不是错误
- 私有仓库作用域：只有用户自己可以访问
- **Notion skill 名称必须从目录名获取，不是从文件名**。路径 `category/name/SKILL.md` 中 name 在倒数第二段，不是最后一段
- **只同步用户自建 skill** — 不要把所有内置 skill 都填入数据库，用户会纠正
- **外接数据源**：GitHub 完成后**必须问**用户（步骤 7），不得自动同步
- **只同步当前 skill**：Notion 和飞书都只 upsert 刚发布的 skill，禁止全量扫描
- **已有则更新，没有则新建**：不会重复创建
- **Notion 单条同步**：`notion-skill-sync`；**全量**：`scripts/sync-external-datasources.sh`
- **飞书**：先 `feishu-connectivity` 检查 lark-cli；库未建则 `notion-skill-sync` 附带的 `feishu-skill-db-setup.sh init`
- **Prompt ≠ Skill**：勿把 [Prompt Skill 数据库](https://mf4bkrtazt.feishu.cn/wiki/GMHFwPV7ciMK3ckFN3JcAlHmntf) 的 prompt 行迁入 Skill 库

---

## 附录：Windows / Kiro 环境适配

本 skill 的主流程命令是为 macOS/Linux（bash）写的。在 **Windows**（PowerShell / cmd）或 **Kiro IDE** 环境里运行时，按下表替换等价命令。核心政策不变：每个 skill 仍必须有 private GitHub repo + README.md，GitHub 推送后仍须询问用户再同步 Notion/飞书。

### 环境判定补充

| 运行环境 | 判定（满足任一即可） | 持久化文件 |
|:---------|:---------------------|:-----------|
| **Kiro IDE** | Windows 上的 Kiro 工作区；无 `CURSOR_*`；skill 在 `%USERPROFILE%\.hermes\skills\` | `%USERPROFILE%\.hermes\skillfy.env` |

Windows 上无 `chmod`，配置文件权限由 NTFS ACL 管理，跳过 `chmod 600` 即可。

### 步骤 0：Skill 来源（PowerShell）

`skill-source.sh` 是 bash 脚本，Windows 无法直接跑（除非 WSL/Git Bash）。改用 PowerShell 直接读写 env 文件：

```powershell
# get — 读取已保存来源
$envFile = "$env:USERPROFILE\.hermes\skillfy.env"
if (Test-Path $envFile) {
    (Get-Content $envFile | Where-Object { $_ -match "^SKILL_SOURCE=" }) -replace "^SKILL_SOURCE=", ""
} else { "MISSING" }

# set — 写入来源（首次询问用户后）
"SKILL_SOURCE=<用户确认的名称>" | Out-File -FilePath $envFile -Encoding utf8
```

> ⚠️ Notion 下拉「Skill 来源」选项不会被 PowerShell 自动补全。新来源名若不存在，会在步骤 7 用 `ntn api` 创建页面时由 Notion 自动新增 select 选项（multi_select/select 写入不存在的 name 会自动建立）。

### 步骤 1：创建 skill（无 skill_manage 工具时）

Kiro 没有 `skill_manage` 工具。直接用文件工具创建目录与 SKILL.md：

```powershell
$dir = "$env:USERPROFILE\.hermes\skills\<category>\<skill-name>"
New-Item -ItemType Directory -Path $dir -Force | Out-Null
# 然后写入 SKILL.md / README.md
```

### 步骤 3-5：Git（跨平台一致）

`git` 与 `gh` 命令在 Windows 上完全相同。注意 Kiro 的文件工具受 workspace 限制，对 `~/.hermes/` 下的操作要用 shell。`cd` 在某些 shell 工具里不支持，改用 `Push-Location` / `Pop-Location` 或 cwd 参数：

```powershell
Push-Location "$env:USERPROFILE\.hermes\skills\<category>\<skill-name>"
git init
git add SKILL.md README.md
git commit -m "init: <skill-name> skill"
gh repo create mynameisi/<skill-name> --private --push --source=. --remote=origin
Pop-Location
```

默认分支可能是 `master`（取决于本机 git 配置），force push 时用实际分支名：`git push -f origin master`。

### 步骤 7：Notion 同步（用 ntn CLI，无需 Python）

Windows 上常无 `python3`，`notion-upsert-single.py` 跑不了。改用 **Notion 官方 CLI `ntn`**（https://developers.notion.com/cli）。

```powershell
# 0. 确认已登录
ntn api /v1/users/me

# 1. 找到 Skill 数据库的 data_source_id（仅首次，可缓存）
ntn api /v1/search query=Skill filter:='{"property":"object","value":"data_source"}'
#   → 记下 results[].id，例如 332a603b-c241-80af-b1a7-000bf4fb87cf
#   父 database_id 在 parent.database_id，例如 332a603b-c241-8039-8df7-f9cdbba1fc2c

# 2. 查询是否已存在（upsert 判定）
ntn api "/v1/data_sources/<data_source_id>/query" `
  filter:='{"property":"Skill Name","title":{"equals":"<skill-name>"}}'

# 3a. 不存在 → 创建页面
$body = '{ "parent": {"database_id":"<database_id>"}, "properties": { ... } }'
$body | ntn api /v1/pages

# 3b. 已存在 → 更新（results[0].id 即 page_id）
$body = '{ "properties": { ... } }'
$body | ntn api "/v1/pages/<page_id>" -X PATCH
```

**Skill 数据库字段映射**（properties JSON）：

| 字段 | 类型 | 示例 JSON |
|:-----|:-----|:----------|
| `Skill Name` | title | `{"title":[{"text":{"content":"<name>"}}]}` |
| `Skill 创建时间` | date | `{"date":{"start":"2026-06-21"}}` |
| `Skill 功能` | rich_text | `{"rich_text":[{"text":{"content":"<desc>"}}]}` |
| `触发词` | multi_select | `{"multi_select":[{"name":"<t1>"},{"name":"<t2>"}]}` |
| `Skill 来源` | select | `{"select":{"name":"<source>"}}` |
| `Skill Git repo 地址` | url | `{"url":"https://github.com/mynameisi/<name>"}` |

> 关键路径细节：`ntn api` 路径必须带前导 `/`（如 `/v1/pages`）；database 查询走 `/v1/data_sources/<id>/query`（新版 API），不再是 `/v1/databases/<id>/query`。数据库未共享给 "Notion CLI" integration 时会报 `object_not_found`，先在 Notion 里把库连接给该 integration，或用 `ntn api /v1/search` 找到已共享的 data_source。

### Windows 常见错误

| 症状 | 原因 | 修复 |
|:-----|:-----|:-----|
| `Python was not found` | Windows 无 python3 | 用 `ntn` CLI 走 Notion REST，见步骤 7 |
| `skill-source.sh: No such file` | bash 脚本不在 Windows 路径 | 用 PowerShell 读写 `skillfy.env` |
| `Invalid request URL` (ntn) | 路径缺前导 `/` 或用了旧 `/v1/databases/.../query` | 加 `/`，改用 `/v1/data_sources/<id>/query` |
| `object_not_found` (ntn) | DB 未共享给 Notion CLI integration | 在 Notion 连接该 integration，或用 search 找已共享 data_source |
| `cd` 在 shell 工具里失败 | 部分工具禁用 cd | 用 `Push-Location`/`Pop-Location` 或 cwd 参数 |
| force push 分支名错 | Windows git 默认 `master` | `git push -f origin master`（用实际分支名） |
