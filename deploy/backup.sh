#!/usr/bin/env bash
# 知行公考 · 整包数据备份（SQLite + uploads + knowledge）
# 数据都在容器卷 /app/server/data 下，只备份库文件会丢图片，必须整包 tar。
# 用法：bash deploy/backup.sh（可放入 crontab，见 deploy/install-backup.sh）
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/zhixing-gongkao_$STAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

docker compose exec -T zhixing-gongkao tar -czf - -C /app/server data > "$FILE"

# 清理超过保留天数的旧备份
find "$BACKUP_DIR" -name "zhixing-gongkao_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete

echo "[backup] 完成: $FILE"
echo "[backup] 恢复: docker compose exec -T zhixing-gongkao sh -c 'cd /app/server && tar -xzf -' < $FILE"
