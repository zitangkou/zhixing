#!/usr/bin/env bash
# 在服务器 /opt/zhixing-gongkao 下执行：拉代码并一键重建
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "缺少 .env，请先: cp .env.docker.example .env 并编辑，或直接 bash deploy.sh 自动生成"
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
bash deploy.sh
