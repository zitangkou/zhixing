#!/usr/bin/env bash
# 知行公考 · 一键部署（单台云服务器，Docker Compose）
# 首次使用前先执行一次：bash deploy/setup-docker.sh
# 用法：
#   bash deploy.sh          # 首次部署 / 更新重建
#   bash deploy.sh update   # 同 deploy.sh（拉代码后调用本脚本）
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "未检测到 Docker / Docker Compose，请先执行：bash deploy/setup-docker.sh"
  exit 1
fi

http_get() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl --connect-timeout 5 --max-time 15 -fsS -o /dev/null "$url"
  else
    python3 -c "import urllib.request,sys; urllib.request.urlopen(sys.argv[1], timeout=15)" "$url"
  fi
}

env_value() {
  local key="$1"
  awk -v key="$key" '$0 ~ "^" key "=" { sub(/^[^=]*=/, ""); print; exit }' .env
}

# ---------- 1/5 准备 .env ----------
if [[ ! -f .env ]]; then
  echo "[1/5] 生成 .env（基于 .env.docker.example，并自动生成密钥）"
  cp .env.docker.example .env
  SECRET="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  ADMIN_PASS="$(openssl rand -hex 8 2>/dev/null || head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  # 微信公众平台 Token 仅接受 3～32 位英文或数字；使用 32 位十六进制随机值。
  WECHAT_TOKEN="$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  perl -0pi -e "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET}/; s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=${ADMIN_PASS}/; s/^WECHAT_OFFICIAL_TOKEN=.*/WECHAT_OFFICIAL_TOKEN=${WECHAT_TOKEN}/" .env
  echo "  已生成 SECRET_KEY；管理员账号：admin / ${ADMIN_PASS}（请保存）"
  echo "  已生成公众号 Token（不在日志显示）；启用回调前从服务器 .env 安全复制到微信后台。"
  echo "  建议继续编辑 .env：公网入口、公众号 AppID、CORS_ORIGINS、ALLOW_REGISTER"
else
  echo "[1/5] 使用现有 .env"
fi

HTTP_PORT="$(env_value HTTP_PORT)"
HTTP_PORT="${HTTP_PORT:-80}"
HTTP_BIND="$(env_value HTTP_BIND)"
HTTP_BIND="${HTTP_BIND:-0.0.0.0}"

if [[ ! "$HTTP_PORT" =~ ^[0-9]+$ ]] || (( HTTP_PORT < 1 || HTTP_PORT > 65535 )); then
  echo "HTTP_PORT 必须是 1～65535 的整数。"
  exit 1
fi
if [[ "$HTTP_BIND" != "0.0.0.0" && "$HTTP_BIND" != "127.0.0.1" ]]; then
  echo "HTTP_BIND 只允许 0.0.0.0（公网直连）或 127.0.0.1（域名网关）。"
  exit 1
fi

if [[ "$(env_value SECRET_KEY)" == "please-change-me-use-openssl-rand-hex-32" ]] || [[ -z "$(env_value SECRET_KEY)" ]]; then
  echo "SECRET_KEY 未安全配置，拒绝部署。请在 .env 中使用随机密钥。"
  exit 1
fi
if [[ "$(env_value ADMIN_PASSWORD)" == "change-this-password" ]] || [[ -z "$(env_value ADMIN_PASSWORD)" ]]; then
  echo "ADMIN_PASSWORD 未安全配置，拒绝部署。请在 .env 中设置强密码。"
  exit 1
fi

WECHAT_ENABLED="$(env_value WECHAT_OFFICIAL_ENABLED)"
WECHAT_TOKEN="$(env_value WECHAT_OFFICIAL_TOKEN)"
if [[ "${WECHAT_ENABLED,,}" == "true" ]] && [[ ! "$WECHAT_TOKEN" =~ ^[A-Za-z0-9]{16,32}$ ]]; then
  echo "WECHAT_OFFICIAL_TOKEN 必须为 16～32 位英文或数字（微信平台上限为 32 位）。"
  exit 1
fi

# ---------- 2/5 构建并启动 ----------
echo "[2/5] 构建并启动容器（http://127.0.0.1:${HTTP_PORT}）"
docker compose up -d --build

# ---------- 3/5 健康检查 ----------
echo "[3/5] 等待健康检查..."
ok=""
for _ in $(seq 1 60); do
  if http_get "http://127.0.0.1:${HTTP_PORT}/health"; then ok=1; break; fi
  sleep 2
done
if [[ -z "$ok" ]]; then
  echo "健康检查失败，请查看日志：docker compose logs"
  exit 1
fi
echo "  /health OK"

# ---------- 4/5 验证关键路由 ----------
echo "[4/5] 验证关键路由"
http_get "http://127.0.0.1:${HTTP_PORT}/" && echo "  /           综合 H5 OK"
http_get "http://127.0.0.1:${HTTP_PORT}/theory/" && echo "  /theory/    知行日知 H5 OK"
http_get "http://127.0.0.1:${HTTP_PORT}/shenlun/" && echo "  /shenlun/   知行策论 H5 OK"
http_get "http://127.0.0.1:${HTTP_PORT}/api/config" && echo "  /api/       学员 API OK"
http_get "http://127.0.0.1:${HTTP_PORT}/manage/" && echo "  /manage/    管理后台 OK"

# ---------- 5/5 汇总 ----------
DOMAIN="$(env_value DOMAIN)"
echo ""
echo "部署完成！"
if [[ -n "${DOMAIN:-}" ]]; then
  echo "  综合 H5:   http://${DOMAIN}/"
  echo "  知行日知:  http://${DOMAIN}/theory/"
  echo "  知行策论:  http://${DOMAIN}/shenlun/"
  echo "  管理后台:  http://${DOMAIN}/manage/  （账号与密码见 .env）"
  echo "  正式发布前请配置 HTTPS，并再次执行：python3 scripts/release-preflight.py --base-url https://${DOMAIN} --env-file .env"
else
  if [[ "$HTTP_BIND" == "0.0.0.0" ]]; then
    PUBLIC_BASE="$(env_value WECHAT_OFFICIAL_PUBLIC_BASE_URL)"
    if [[ "$PUBLIC_BASE" =~ ^https?:// ]]; then
      echo "  综合 H5:   ${PUBLIC_BASE%/}/"
      echo "  知行日知:  ${PUBLIC_BASE%/}/theory/"
      echo "  知行策论:  ${PUBLIC_BASE%/}/shenlun/"
      echo "  管理后台:  ${PUBLIC_BASE%/}/manage/"
      echo "  公众号回调: ${PUBLIC_BASE%/}/api/wechat/callback"
    else
      PORT_SUFFIX=":${HTTP_PORT}"
      [[ "$HTTP_PORT" == "80" ]] && PORT_SUFFIX=""
      echo "  公网访问:  http://服务器公网IP${PORT_SUFFIX}/"
      echo "  公众号回调: http://服务器公网IP${PORT_SUFFIX}/api/wechat/callback"
    fi
    echo "  当前直接监听公网；请在云安全组放行 80，并暂时避免通过 HTTP 登录管理后台。"
  else
    echo "  综合 H5:   http://127.0.0.1:${HTTP_PORT}/"
    echo "  知行日知:  http://127.0.0.1:${HTTP_PORT}/theory/"
    echo "  知行策论:  http://127.0.0.1:${HTTP_PORT}/shenlun/"
    echo "  管理后台:  http://127.0.0.1:${HTTP_PORT}/manage/"
    echo "  当前仅监听本机；公网访问需配置域名网关，或在临时联调时明确改为 HTTP_BIND=0.0.0.0。"
  fi
fi
echo ""
echo "常用命令："
echo "  日志:    docker compose logs -f zhixing-gongkao"
echo "  重启:    docker compose restart"
echo "  更新:    bash scripts/deploy-update.sh"
echo "  备份:    bash deploy/backup.sh（每日定时：bash deploy/install-backup.sh）"
echo "  停止:    docker compose down"
