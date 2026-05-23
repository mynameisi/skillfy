---
name: skillfy
description: "将已创建的 skill 发布到 GitHub 私有仓库：git init → 创建 README → gh repo create (private) → commit → push"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [skill, publish, github, git, workflow]
    prerequisites: [gh CLI authenticated with repo scope]
---

# Skillfy — Skill 化 + GitHub 发布

## 触发条件

当用户要求「把 xxx 保存成 skill」并要求「推到 private repo」时，加载本 skill。

## 前置条件

```bash
# 确保 gh CLI 已登录且有 repo 权限
gh auth status
# → 应有 'repo' scope
```

## 完整工作流

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

## 已实践验证的场景

| 场景 | 状态 |
|:-----|:-----|
| 全新 skill + 全新 repo | ✅ 一次成功 |
| 已有 skill + 已有 repo（旧版本） | ⚠️ force push + merge conflict |
| 多文件 skill（reference、template） | ✅ 加 git add 即可 |

## 注意事项

- `gh repo create` 的 `--source=.` 会自动从当前目录推代码
- 如果先 `git init` 再 `gh repo create --push`，注意远程是否已有历史
- force push 需要用户确认 — 这是 gh CLI 的安全机制，不是错误
- 私有仓库作用域：只有用户自己可以访问
