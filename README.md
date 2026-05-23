# skillfy — Skill 化 + GitHub 发布

将 Hermes Agent skill 发布到 GitHub 私有仓库的标准化工作流。

## 用途

创建一个新的 skill 后，一键推送到 GitHub 私有仓库存档和版本管理。

## 工作流

1. 创建/更新 skill（`skill_manage`）
2. 写入 README.md
3. `git init` → `git add` → `git commit`
4. `gh repo create --private --push`
5. 处理远程冲突（如已有旧版本，force push）

## 前提

- `gh` CLI 已安装并登录（`gh auth status`）
- 需有 `repo` scope
