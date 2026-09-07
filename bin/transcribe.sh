#!/usr/bin/env bash
# Local Whisper transcript of an ingested video's audio.
# Usage: transcribe.sh <slug>
# Config: VIDEO_WORK (base dir holding work/; default current dir)
#         VIDEO_WHISPER_BIN (path to whisper/whisper.cpp binary; default: auto-detect)
#         VIDEO_WHISPER_MODEL (model name/path passed to the binary; default: base)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/load-config.sh"
BASE="${VIDEO_WORK:-$PWD}"
SLUG="${1:?usage: transcribe.sh <slug>}"
W="$BASE/work/$SLUG"
AUDIO="$W/audio.wav"
MODEL="${VIDEO_WHISPER_MODEL:-base}"

[ -f "$AUDIO" ] || { echo "[transcribe] no $AUDIO — run ingest.sh first"; exit 1; }

if [ "${VIDEO_FORCE:-0}" != "1" ] && [ -f "$W/transcript.vtt" ] && [ -f "$W/transcript.txt" ]; then
  echo "[transcribe] already transcribed -> $W/transcript.{vtt,txt} (skip; set VIDEO_FORCE=1 to redo)"
  exit 0
fi

resolve_bin() {
  if [ -n "${VIDEO_WHISPER_BIN:-}" ]; then
    echo "$VIDEO_WHISPER_BIN"; return 0
  fi
  for c in whisper-cli main whisper; do
    if command -v "$c" >/dev/null 2>&1; then echo "$c"; return 0; fi
  done
  return 1
}

BIN="$(resolve_bin || true)"
if [ -z "$BIN" ]; then
  echo "[transcribe] no whisper binary found — set VIDEO_WHISPER_BIN, or install whisper.cpp"
  echo "[transcribe] (brew install whisper-cpp, or pip install openai-whisper)"
  exit 0
fi

echo "[transcribe] running $BIN (model: $MODEL) on $AUDIO ..."
OUT_PREFIX="$W/transcript"
if "$BIN" --help 2>&1 | grep -qi 'output-vtt\|--ovtt'; then
  # whisper.cpp CLI: -m model, -f audio, -otxt -ovtt, -of output-prefix
  "$BIN" -m "$MODEL" -f "$AUDIO" -otxt -ovtt -of "$OUT_PREFIX" >/dev/null
else
  # openai-whisper CLI: --model, positional audio, --output_format, --output_dir
  "$BIN" "$AUDIO" --model "$MODEL" --output_format all --output_dir "$W" >/dev/null
  [ -f "$W/audio.vtt" ] && mv -f "$W/audio.vtt" "$OUT_PREFIX.vtt"
  [ -f "$W/audio.txt" ] && mv -f "$W/audio.txt" "$OUT_PREFIX.txt"
fi

if [ -f "$OUT_PREFIX.vtt" ] && [ -f "$OUT_PREFIX.txt" ]; then
  echo "[transcribe] wrote $OUT_PREFIX.vtt + $OUT_PREFIX.txt"
else
  echo "[transcribe] (transcription ran but expected output files are missing — check the binary's flags)"
  exit 1
fi
