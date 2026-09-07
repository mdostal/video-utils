#!/usr/bin/env bash
# Export 9:16 and 1:1 center crops of every cut clip. Plain center crop —
# no face/subject detection (see docs/ROADMAP.md).
# Usage: reframe.sh <slug>
# Config: VIDEO_WORK (base dir holding clips/; default current dir)
#         VIDEO_REFRAME_ASPECTS (comma-separated "9:16"/"1:1"; default: 9:16,1:1)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/load-config.sh"
BASE="${VIDEO_WORK:-$PWD}"
SLUG="${1:?usage: reframe.sh <slug>}"
CLIPS="$BASE/clips/$SLUG"
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg required (brew install ffmpeg)"; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ffprobe required (brew install ffmpeg)"; exit 1; }

shopt -s nullglob
files=()
for f in "$CLIPS"/*.mp4; do
  case "$f" in
    *.captioned.mp4|*.9x16.mp4|*.1x1.mp4) continue ;;
  esac
  files+=("$f")
done
if [ ${#files[@]} -eq 0 ]; then
  echo "[reframe] no clips found in $CLIPS"
  exit 0
fi

ASPECTS="${VIDEO_REFRAME_ASPECTS:-9:16,1:1}"
IFS=',' read -ra WANT <<< "$ASPECTS"
VALID=()
for a in "${WANT[@]}"; do
  case "$a" in
    "9:16"|"1:1") VALID+=("$a") ;;
    *) echo "[reframe] unsupported aspect '$a' — skipping (only 9:16 and 1:1 are supported)" ;;
  esac
done
if [ ${#VALID[@]} -eq 0 ]; then
  echo "[reframe] no valid aspects in VIDEO_REFRAME_ASPECTS='$ASPECTS' — nothing to do"
  exit 0
fi

crop_filter() {
  # crop_filter <src_w> <src_h> <target_num> <target_den>
  local sw="$1" sh="$2" tn="$3" td="$4"
  python3 -c "
sw, sh, tn, td = $sw, $sh, $tn, $td
target = tn / td
src = sw / sh
if src > target:
    cw = round(sh * target); ch = sh
else:
    cw = sw; ch = round(sw / target)
cw -= cw % 2; ch -= ch % 2
x = (sw - cw) // 2; y = (sh - ch) // 2
print(f'crop={cw}:{ch}:{x}:{y}')
"
}

for f in "${files[@]}"; do
  DIMS=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$f")
  W="${DIMS%,*}"; H="${DIMS#*,}"
  name="$(basename "${f%.mp4}")"
  for a in "${VALID[@]}"; do
    case "$a" in
      "9:16") tn=9; td=16; suffix="9x16" ;;
      "1:1")  tn=1; td=1;  suffix="1x1" ;;
    esac
    FILTER="$(crop_filter "$W" "$H" "$tn" "$td")"
    out="$CLIPS/${name}.${suffix}.mp4"
    ffmpeg -y -i "$f" -vf "$FILTER" -c:a copy "$out" -loglevel error
    echo "[reframe] wrote $out"
  done
done
