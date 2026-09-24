#!/usr/bin/env bash
# 日常上线（默认）：在开发机构建 linux/amd64 镜像，scp 到服务器后只 load + up。
# 禁止在 2G 云服务器上 docker compose --build（会打满内存、SSH 假死）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SSH_HOST="${DEPLOY_SSH_HOST:-zhixing-aliyun}"
REMOTE_DIR="${DEPLOY_REMOTE_DIR:-/opt/zhixing-gongkao}"
IMAGE="${DEPLOY_IMAGE:-zhixing-gongkao-zhixing-gongkao:latest}"
TAR="${TMPDIR:-/tmp}/zhixing-gongkao.tar.gz"

cleanup_local_tar() {
  rm -f "$TAR"
}

# 失败中断也删掉本机打包文件，避免 /tmp 堆 80MB+ 的 tar.gz
trap cleanup_local_tar EXIT

if ! command -v docker >/dev/null 2>&1; then
  echo "本机未检测到 Docker，请先启动 Docker Desktop。"
  exit 1
fi

echo "[1/4] 本机构建 ${IMAGE}（compose 已指定 linux/amd64）"
attempt=1
until docker compose build; do
  if (( attempt >= 3 )); then
    echo "本机构建失败（已重试 ${attempt} 次）。常见原因：npm 镜像网络中断，可再跑一次本脚本。"
    exit 1
  fi
  attempt=$((attempt + 1))
  echo "构建失败，3 秒后重试（${attempt}/3）…"
  sleep 3
done

echo "[2/4] 打包镜像"
docker save "$IMAGE" | gzip > "$TAR"
ls -lh "$TAR"

echo "[3/4] 传到 ${SSH_HOST}（镜像 + 部署脚本约定）"
scp -o BatchMode=yes "$TAR" "${SSH_HOST}:/opt/zhixing-gongkao.tar.gz"
scp -o BatchMode=yes "$ROOT/deploy.sh" "${SSH_HOST}:${REMOTE_DIR}/deploy.sh" 2>/dev/null || true
scp -o BatchMode=yes "$ROOT/scripts/deploy-update.sh" "$ROOT/scripts/deploy-from-local.sh" \
  "${SSH_HOST}:${REMOTE_DIR}/scripts/" 2>/dev/null || true

SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "[4/4] 服务器 load + compose up --no-build（${SHA}）"
ssh -o BatchMode=yes "$SSH_HOST" "set -euo pipefail
  docker load -i /opt/zhixing-gongkao.tar.gz
  cd '${REMOTE_DIR}'
  HTTP_PORT=\$(awk -F= '/^HTTP_PORT=/{print \$2; exit}' .env)
  HTTP_PORT=\${HTTP_PORT:-8081}
  docker compose up -d --no-build
  printf '%s\n' '${SHA}' > .deployed-sha
  rm -f /opt/zhixing-gongkao.tar.gz
  ok=
  for _ in \$(seq 1 40); do
    if curl --connect-timeout 3 --max-time 8 -fsS -o /dev/null \"http://127.0.0.1:\${HTTP_PORT}/health\"; then
      ok=1
      break
    fi
    sleep 2
  done
  if [[ -z \"\$ok\" ]]; then
    echo '健康检查失败：docker compose logs --tail=80'
    docker compose logs --tail=80
    exit 1
  fi
  echo \"/health OK  http://127.0.0.1:\${HTTP_PORT}\"
  docker compose ps
"

echo "[清理] 本机：打包文件 + 悬空镜像 + 未使用的构建缓存（保留 ${IMAGE}，下次仍可增量编）"
docker image prune -f
docker builder prune -f
echo "部署完成。请用域名再验 / 与 /manage/。"
