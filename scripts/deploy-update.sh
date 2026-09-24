#!/usr/bin/env bash
# 仅在「≥4G 且允许服务器构建」且目录为 git 仓库时使用。
# 2G 机 / 无 .git 的生产机日常更新请在开发机：
#   bash scripts/deploy-from-local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "${ALLOW_SERVER_BUILD:-}" != "1" ]]; then
  echo "已停止：不要在云服务器上 pull + --build（2G 机会把 SSH 打挂）。"
  echo "日常上线在开发机执行：bash scripts/deploy-from-local.sh"
  echo "若确认机器 ≥4G、有 .git、且要在服务器构建：ALLOW_SERVER_BUILD=1 bash scripts/deploy-update.sh"
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "缺少 .env，请先: cp .env.docker.example .env 并编辑，或直接 bash deploy.sh 自动生成"
  exit 1
fi

if [[ ! -d .git ]]; then
  echo "当前目录不是 git 仓库，无法 pull。请改用开发机：bash scripts/deploy-from-local.sh"
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "检测到服务器存在未提交的 tracked 文件修改，已停止更新。"
  echo "请先确认并提交、暂存或人工处理这些修改；脚本不会自动覆盖服务器文件。"
  git status --short --untracked-files=no
  exit 1
fi

BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" ]]; then
  echo "当前处于 detached HEAD，无法安全执行自动更新。请先切换到目标分支。"
  exit 1
fi

git fetch origin
if ! git pull --ff-only origin "$BRANCH"; then
  echo "远端分支无法快进合并，已停止部署。"
  echo "请人工检查 git log --oneline --decorate --graph --all，确认后再更新。"
  exit 1
fi
ALLOW_SERVER_BUILD=1 bash deploy.sh
