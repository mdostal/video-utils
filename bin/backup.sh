#!/usr/bin/env bash
# Push raws to a backup target via rclone (Google Drive, S3, or anything else
# rclone supports — this script is backend-agnostic).
# Usage: backup.sh [raws-dir]   (default: $VIDEO_RAWS, then ./raws)
# Config: VIDEO_BACKUP_REMOTE (rclone destination, e.g. "gdrive:my-backups")
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/load-config.sh"
DIR="${1:-${VIDEO_RAWS:-./raws}}"
[ -d "$DIR" ] || { echo "[backup] no such directory: $DIR"; exit 1; }

if [ -z "${VIDEO_BACKUP_REMOTE:-}" ]; then
  echo "[backup] VIDEO_BACKUP_REMOTE not set — nothing to do"
  echo "[backup] (set it to an rclone destination, e.g. gdrive:my-backups or s3:my-bucket/raws)"
  exit 0
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "[backup] rclone not found — install: brew install rclone"
  exit 0
fi

echo "[backup] rclone copy $DIR -> $VIDEO_BACKUP_REMOTE ..."
rclone copy "$DIR" "$VIDEO_BACKUP_REMOTE" --stats-one-line -v
echo "[backup] done"
