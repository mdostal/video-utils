#!/usr/bin/env bash
# Register a raw video: <work>/work/<slug>/ + metadata + audio extract.
# Usage: ingest.sh <video-path> [slug]
# Config: VIDEO_WORK (output root; default current dir)
set -euo pipefail
BASE="${VIDEO_WORK:-$PWD}"
MP4="${1:?usage: ingest.sh <video-path> [slug]}"
[ -f "$MP4" ] || { echo "not found: $MP4"; exit 1; }
SLUG="${2:-$(basename "${MP4%.*}")}"
W="$BASE/work/$SLUG"; mkdir -p "$W"
ABS="$(cd "$(dirname "$MP4")" && pwd)/$(basename "$MP4")"
ln -sf "$ABS" "$W/source.mp4"

if command -v ffprobe >/dev/null 2>&1; then
  ffprobe -v quiet -print_format json -show_format -show_streams "$MP4" > "$W/meta.json" || true
  DUR=$(python3 -c "import json;print(round(float(json.load(open('$W/meta.json'))['format']['duration'])))" 2>/dev/null || echo '?')
  echo "[ingest] duration: ${DUR}s"
else
  echo "[ingest] (ffprobe not found — skipping metadata)"
fi

if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -y -i "$MP4" -vn -ac 1 -ar 16000 "$W/audio.wav" >/dev/null 2>&1 \
    && echo "[ingest] audio -> $W/audio.wav (for a transcript pass)" \
    || echo "[ingest] (audio extract failed — non-fatal)"
else
  echo "[ingest] (ffmpeg not found — install: brew install ffmpeg)"
fi

echo "[ingest] ready -> $W/"
echo "[ingest] next:  review.py \"$ABS\" $SLUG   then   clip.sh \"$ABS\" $SLUG"
