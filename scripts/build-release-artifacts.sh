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

# 只改归档副本。仓库里的 project.config.json 保持 touristappid。不读取、不打印 AppSecret。
echo "[综合] 写入归档小程序 AppID（值不显示）"
python3 - "$ROOT" "$OUTPUT_DIR/weapp/project.config.json" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
target = Path(sys.argv[2])
WANTED = ("MINIPROGRAM_APP_ID", "MINIPROGRAM_NAME")
APPID_RE = re.compile(r"wx[0-9a-fA-F]{16}\Z")


def read_dotenv(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in WANTED:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        found[key] = value.strip()
    return found


def pick(file_values: dict[str, str], key: str) -> str:
    file_value = file_values.get(key, "").strip()
    if file_value:
        return file_value
    return os.environ.get(key, "").strip()


def fail_appid() -> None:
    print(
        "MINIPROGRAM_APP_ID 不可用：仓库根 .env 与当前环境变量里该键为空、仍为 touristappid，或不是小程序 AppID。"
        "请设置 MINIPROGRAM_APP_ID 后重跑。脚本不会把 AppID 写回仓库 project.config.json，也不会打印该值。",
        file=sys.stderr,
    )
    raise SystemExit(1)


file_values = read_dotenv(root / ".env")
appid = pick(file_values, "MINIPROGRAM_APP_ID")
if not appid or appid == "touristappid" or not APPID_RE.fullmatch(appid):
    fail_appid()

data = json.loads(target.read_text(encoding="utf-8"))
data["appid"] = appid
name = pick(file_values, "MINIPROGRAM_NAME")
if name:
    data["projectname"] = name
target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("已写入归档 weapp/project.config.json 的 appid（值不显示）")
PY

{
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "api_url=$API_URL"
  echo "git_commit=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
} > "$OUTPUT_DIR/RELEASE.txt"

echo "发布产物已生成: $OUTPUT_DIR"
echo "  H5:    $OUTPUT_DIR/h5"
echo "  小程序: $OUTPUT_DIR/weapp"
echo "下一步: python3 scripts/release-preflight.py --artifact-dir '$OUTPUT_DIR'"
