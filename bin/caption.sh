#!/usr/bin/env bash
# Generate .srt from a transcript, and optionally burn captions into cut clips.
# Usage: caption.sh <slug>
# Config: VIDEO_WORK (base dir holding work/ and clips/; default current dir)
#         VIDEO_CAPTION_BURN=1 (opt-in: burn captions into clips/<slug>/*.mp4)
#         VIDEO_CAPTION_STYLE (optional ffmpeg subtitles force_style string)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/load-config.sh"
BASE="${VIDEO_WORK:-$PWD}"
SLUG="${1:?usage: caption.sh <slug>}"
W="$BASE/work/$SLUG"
VTT="$W/transcript.vtt"
SRT="$W/transcript.srt"

[ -f "$VTT" ] || { echo "[caption] no $VTT — run transcribe.sh first"; exit 1; }

python3 - "$VTT" "$SRT" <<'PY'
import sys, re
vtt_path, srt_path = sys.argv[1], sys.argv[2]
text = open(vtt_path, encoding="utf-8").read()
# Strip WEBVTT header and NOTE blocks; VTT timestamps use '.', SRT uses ','.
blocks = re.split(r"\n\n+", text.strip())
out = []
n = 0
for b in blocks:
    if b.strip().upper().startswith("WEBVTT") or b.strip().startswith("NOTE"):
        continue
    lines = b.strip().splitlines()
    if not lines:
        continue
    # Drop an optional cue identifier line before the timestamp line.
    if "-->" not in lines[0] and len(lines) > 1 and "-->" in lines[1]:
        lines = lines[1:]
    if "-->" not in lines[0]:
        continue
    n += 1
    ts = lines[0].replace(".", ",")
    out.append(str(n))
    out.append(ts)
    out.extend(lines[1:])
    out.append("")
open(srt_path, "w", encoding="utf-8").write("\n".join(out).rstrip() + "\n")
print(f"[caption] wrote {srt_path} ({n} cue(s))")
PY

BURN="${VIDEO_CAPTION_BURN:-0}"
if [ "$BURN" != "1" ]; then
  exit 0
fi

command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg required (brew install ffmpeg)"; exit 1; }
if ! ffmpeg -filters 2>/dev/null | grep -q ' subtitles '; then
  echo "[caption] this ffmpeg build has no 'subtitles' filter (needs libass) — skipping burn-in"
  echo "[caption] (transcript.srt was still written; rebuild ffmpeg with libass to enable burn-in)"
  exit 0
fi
CLIPS="$BASE/clips/$SLUG"
shopt -s nullglob
files=("$CLIPS"/*.mp4)
if [ ${#files[@]} -eq 0 ]; then
  echo "[caption] no clips found in $CLIPS — nothing to burn"
  exit 0
fi

STYLE="${VIDEO_CAPTION_STYLE:-}"
FILTER="subtitles=$(printf '%s' "$SRT" | sed "s/:/\\\\:/g")"
[ -n "$STYLE" ] && FILTER="${FILTER}:force_style='${STYLE}'"

for f in "${files[@]}"; do
  case "$f" in *.captioned.mp4) continue;; esac
  name="$(basename "${f%.mp4}")"
  out="$CLIPS/${name}.captioned.mp4"
  ffmpeg -y -i "$f" -vf "$FILTER" -c:a copy "$out" -loglevel error
  echo "[caption] wrote $out"
done
