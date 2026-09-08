#!/usr/bin/env bash
# 知行公考 · Docker 环境初始化（全新独立服务器只执行一次）
#
# 重要：
# - 若 Docker / Compose 已就绪，本脚本会直接跳过，
#   **不会**覆盖 /etc/docker/daemon.json，也不会重启 docker 守护进程。
# - 只有全新服务器（docker 未安装）才会安装 Docker 并首次配置镜像加速。
set -euo pipefail

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi

has_docker=""
has_compose=""
command -v docker >/dev/null 2>&1 && has_docker=1
docker compose version >/dev/null 2>&1 && has_compose=1

if [[ -n "$has_docker" && -n "$has_compose" ]]; then
  echo "Docker 与 Docker Compose 已就绪，跳过全局配置（不影响其它项目）。"
  echo "直接执行：bash deploy.sh"
  exit 0
fi

echo "=========================================="
echo " Docker 环境初始化（仅在缺失时执行）"
echo "=========================================="

if [[ -z "$has_docker" ]]; then
  echo "[1/3] 安装 Docker（官方脚本，失败回退 apt）..."
  curl -fsSL https://get.docker.com | sh || $SUDO apt-get install -y docker.io
  $SUDO systemctl enable --now docker || true
fi

if [[ -z "$has_compose" ]]; then
  echo "[2/3] 安装 Docker Compose v2（仅补装插件，不重启守护进程）..."
  $SUDO apt-get install -y docker-compose-plugin 2>/dev/null || {
    $SUDO mkdir -p /usr/local/lib/docker/cli-plugins
    $SUDO curl -SL \
      https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    $SUDO chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  }
fi

if [[ -z "$has_docker" ]]; then
  echo "[3/3] 首次配置 Docker 镜像加速（仅在 /etc/docker/daemon.json 不存在时）"
  if [[ ! -f /etc/docker/daemon.json ]]; then
    MIRRORS='["https://mirror.ccs.tencentyun.com", "https://mirror.baidubce.com", "https://docker.1panel.live", "https://docker.m.daocloud.io"]'
    if [ -n "${DOCKER_MIRROR:-}" ]; then
      MIRRORS="[\"https://$DOCKER_MIRROR\"]"
    fi
    $SUDO mkdir -p /etc/docker
    cat <<EOF | $SUDO tee /etc/docker/daemon.json >/dev/null
{
  "registry-mirrors": $MIRRORS
}
EOF
    $SUDO systemctl daemon-reload
    $SUDO systemctl restart docker || $SUDO service docker restart || true
  else
    echo "  已存在 /etc/docker/daemon.json，保留现有配置（不覆盖、不重启）。"
  fi
fi

echo ""
echo "Docker 环境就绪。本项目部署：bash deploy.sh"
