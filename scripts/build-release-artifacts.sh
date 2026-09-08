#!/usr/bin/env bash
# 构建综合版 H5 / 微信小程序，并归档产物。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL=""
OUTPUT_DIR=""

usage() {
  echo "用法: bash scripts/build-release-artifacts.sh --api-url https://你的正式域名 [--output /绝对/输出目录]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url)
      API_URL="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ ! "$API_URL" =~ ^https://[^/[:space:]]+(/.*)?$ ]]; then
  echo "--api-url 必须是正式 HTTPS 地址，例如 https://zhixinggk.ltd"
  exit 2
fi

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="${TMPDIR:-/tmp}/zhixing-release-$(date +%Y%m%d-%H%M%S)"
fi

if [[ "$OUTPUT_DIR" != /* ]]; then
  echo "--output 必须使用绝对路径"
  exit 2
fi
if [[ -e "$OUTPUT_DIR" ]]; then
  echo "输出目录已存在，拒绝覆盖: $OUTPUT_DIR"
  exit 2
fi

mkdir -p "$OUTPUT_DIR/h5" "$OUTPUT_DIR/weapp/dist"

echo "[综合] 构建 H5"
(
  cd "$ROOT"
  TARO_APP_API_URL= npm run build:h5
)
cp -R "$ROOT/dist/." "$OUTPUT_DIR/h5/"

echo "[综合] 构建微信小程序"
(
  cd "$ROOT"
  TARO_APP_API_URL="$API_URL" npm run build:weapp
)
cp -R "$ROOT/dist/." "$OUTPUT_DIR/weapp/dist/"
cp "$ROOT/project.config.json" "$OUTPUT_DIR/weapp/project.config.json"

{
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "api_url=$API_URL"
  echo "git_commit=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
} > "$OUTPUT_DIR/RELEASE.txt"

echo "发布产物已生成: $OUTPUT_DIR"
echo "  H5:    $OUTPUT_DIR/h5"
echo "  小程序: $OUTPUT_DIR/weapp"
echo "下一步: python3 scripts/release-preflight.py --artifact-dir '$OUTPUT_DIR'"
