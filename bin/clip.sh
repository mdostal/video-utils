#!/usr/bin/env bash
# Cut short clips from a video.
#   clip.sh <video> <slug>                      # cut every clip in <work>/work/<slug>/clips.json
#   clip.sh <video> <slug> <start> <end> [name] # cut one manual range (M:SS or seconds)
# Config: VIDEO_WORK (base dir holding work/ and clips/; default current dir)
set -euo pipefail
BASE="${VIDEO_WORK:-$PWD}"
MP4="${1:?usage: clip.sh <video> <slug> [start end name]}"
SLUG="${2:?need a slug}"
OUT="$BASE/clips/$SLUG"; mkdir -p "$OUT"
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg required (brew install ffmpeg)"; exit 1; }

to_sec(){ awk -F: '{ if (NF==2) print $1*60+$2; else print $1 }' <<<"$1"; }

if [ "${3:-}" != "" ]; then
  S=$(to_sec "$3"); E=$(to_sec "$4"); NAME="${5:-clip}"
  ffmpeg -y -i "$MP4" -ss "$S" -to "$E" -c:v libx264 -c:a aac "$OUT/${NAME}.mp4"
  echo "[clip] wrote $OUT/${NAME}.mp4"; exit 0
fi

JSON="$BASE/work/$SLUG/clips.json"
[ -f "$JSON" ] || { echo "[clip] no $JSON — run review.py first, or pass a manual range"; exit 1; }
python3 - "$MP4" "$OUT" "$JSON" <<'PY'
import sys, json, subprocess, os
mp4, out, jf = sys.argv[1], sys.argv[2], sys.argv[3]
def sec(x):
    p = str(x).split(":"); return int(p[0])*60+float(p[1]) if len(p)==2 else float(p[0])
clips = json.load(open(jf))
for i, c in enumerate(clips, 1):
    s, e = sec(c["start"]), sec(c["end"])
    lab = (c.get("label","clip").lower().replace(" ","-")[:30]).strip("-")
    fn = os.path.join(out, f"{i:02d}-{lab}.mp4")
    subprocess.run(["ffmpeg","-y","-i",mp4,"-ss",str(s),"-to",str(e),
                    "-c:v","libx264","-c:a","aac",fn], check=True)
    print("[clip] wrote", fn)
print(f"[clip] {len(clips)} clip(s) -> {out}/")
PY
