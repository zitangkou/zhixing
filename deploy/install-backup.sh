#!/usr/bin/env bash
# 安装知行公考每日数据备份定时任务（每天 03:00）
set -euo pipefail
cd "$(dirname "$0")/.."

SCRIPT_PATH="$(pwd)/deploy/backup.sh"
CRON_LINE="0 3 * * * /bin/bash $SCRIPT_PATH >> /var/log/zhixing-gongkao-backup.log 2>&1"

# 避免重复安装：先移除已存在的该备份任务
(crontab -l 2>/dev/null | grep -v "zhixing-gongkao/deploy/backup.sh" || true; echo "$CRON_LINE") | crontab -

echo "已安装每日 03:00 自动备份：$SCRIPT_PATH"
echo "备份目录默认 /opt/backups，保留 14 天（可用 BACKUP_DIR / BACKUP_RETENTION_DAYS 覆盖）"
echo "查看任务：crontab -l"
