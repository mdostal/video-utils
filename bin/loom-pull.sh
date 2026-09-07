#!/usr/bin/env bash
# Download a Loom share to the raws dir. Usage: loom-pull.sh <loom-share-url-or-id> [name]
# Config: VIDEO_RAWS (dir to save into; default ./raws)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/load-config.sh"
RAW="${VIDEO_RAWS:-$PWD/raws}"
mkdir -p "$RAW"
IN="${1:?usage: loom-pull.sh <loom-url-or-id> [name]}"
SID="${IN##*/}"; SID="${SID%%\?*}"
NAME="${2:-$SID}"
echo "[loom] fetching signed URL for $SID ..."
URL=$(curl -s -X POST "https://www.loom.com/api/campaigns/sessions/$SID/transcoded-url" \
        -H "Content-Type: application/json" -d '{}' \
      | python3 -c "import sys,json;print(json.load(sys.stdin).get('url',''))")
[ -n "$URL" ] || { echo "[loom] no transcoded URL for $SID (private? expired?)"; exit 1; }
echo "[loom] downloading ..."
curl -s -L "$URL" -o "$RAW/$NAME.mp4"
SIZE=$(stat -f%z "$RAW/$NAME.mp4" 2>/dev/null || stat -c%s "$RAW/$NAME.mp4")
echo "[loom] saved $RAW/$NAME.mp4 (${SIZE} bytes)"
