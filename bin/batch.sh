#!/usr/bin/env bash
# Run the full pipeline (ingest -> transcribe -> review -> clip -> caption ->
# reframe) unattended over every raw video in a folder. A failing stage/video
# does not abort the batch; a summary prints at the end.
# Usage: batch.sh [raws-dir]   (default: $VIDEO_RAWS, then ./raws)
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/load-config.sh"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${1:-${VIDEO_RAWS:-./raws}}"
[ -d "$DIR" ] || { echo "[batch] no such directory: $DIR"; exit 1; }

shopt -s nullglob
files=("$DIR"/*.mp4 "$DIR"/*.mov "$DIR"/*.mkv "$DIR"/*.webm)
if [ ${#files[@]} -eq 0 ]; then
  echo "[batch] no video files found in $DIR"
  exit 0
fi

ok=0; failed=0
for f in "${files[@]}"; do
  slug="$(basename "${f%.*}")"
  echo "[batch] === $slug ($f) ==="
  stage_failed=0
  "$HERE/ingest.sh" "$f" "$slug" || stage_failed=1
  "$HERE/transcribe.sh" "$slug" || true
  "$HERE/review.py" "$f" "$slug" || stage_failed=1
  "$HERE/clip.sh" "$f" "$slug" || stage_failed=1
  "$HERE/caption.sh" "$slug" || true
  "$HERE/reframe.sh" "$slug" || true
  if [ "$stage_failed" = "1" ]; then
    echo "[batch] $slug: one or more stages FAILED"
    failed=$((failed+1))
  else
    echo "[batch] $slug: OK"
    ok=$((ok+1))
  fi
done

total=$((ok+failed))
echo "[batch] done: $ok ok, $failed failed, $total total"
[ "$failed" -eq 0 ]
