#!/usr/bin/env bash
# End-to-end smoke test against a synthetic (never committed) sample clip.
# Covers: ingest.sh, caption.sh, clip.sh, reframe.sh, transcribe.sh's
# missing-binary path, and resumability (VIDEO_FORCE=1) for each.
# NOT covered: review.py (needs a real paid GEMINI_API_KEY) and
# transcribe.sh's real-transcription happy path (needs a real whisper binary).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HERE/../bin"

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

export VIDEO_WORK="$TMP"
unset VIDEO_FORCE VIDEO_CONFIG 2>/dev/null || true

pass() { echo "[smoke] PASS: $1"; }
fail() { echo "[smoke] FAIL: $1"; exit 1; }
assert_file() { [ -f "$1" ] || fail "expected file missing: $1 ($2)"; }
assert_no_file() { [ ! -f "$1" ] || fail "expected file absent, found: $1 ($2)"; }
mtime() { stat -f%m "$1" 2>/dev/null || stat -c%Y "$1"; }

SAMPLE="$TMP/sample.mp4"
ffmpeg -y -f lavfi -i color=c=gray:s=640x360:d=1 -f lavfi -i anullsrc=r=16000:cl=mono \
  -t 1 -shortest "$SAMPLE" -loglevel error

# --- ingest.sh ---
"$BIN/ingest.sh" "$SAMPLE" demo >/dev/null
assert_file "$TMP/work/demo/source.mp4" "ingest"
assert_file "$TMP/work/demo/meta.json" "ingest"
assert_file "$TMP/work/demo/audio.wav" "ingest"
pass "ingest.sh produced expected files"

# resumability: ingest.sh
m1=$(mtime "$TMP/work/demo/audio.wav"); sleep 1.1
out="$("$BIN/ingest.sh" "$SAMPLE" demo)"
echo "$out" | grep -qi "skip" || fail "ingest.sh did not report a skip on re-run"
m2=$(mtime "$TMP/work/demo/audio.wav")
[ "$m1" = "$m2" ] || fail "ingest.sh re-ran despite existing output"
sleep 1.1
VIDEO_FORCE=1 "$BIN/ingest.sh" "$SAMPLE" demo >/dev/null
m3=$(mtime "$TMP/work/demo/audio.wav")
[ "$m3" != "$m2" ] || fail "VIDEO_FORCE=1 did not force a redo (ingest.sh)"
pass "ingest.sh resumability (skip + VIDEO_FORCE=1)"

# --- transcribe.sh: missing-binary graceful path (no whisper assumed in CI) ---
if command -v whisper-cli >/dev/null 2>&1 || command -v main >/dev/null 2>&1 || command -v whisper >/dev/null 2>&1; then
  echo "[smoke] SKIP: transcribe.sh missing-binary check (a whisper binary IS on PATH here)"
else
  rc=0; "$BIN/transcribe.sh" demo >/dev/null || rc=$?
  [ "$rc" -eq 0 ] || fail "transcribe.sh should exit 0 with no whisper binary, got $rc"
  assert_no_file "$TMP/work/demo/transcript.vtt" "transcribe.sh missing-binary"
  pass "transcribe.sh missing-binary path exits 0, writes nothing"
fi

# --- caption.sh: no transcript -> expected failure ---
rc=0; "$BIN/caption.sh" demo >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] || fail "caption.sh should fail without a transcript"
pass "caption.sh fails as expected with no transcript.vtt"

# Inject a minimal fixture transcript (independent of a real whisper binary)
# so caption.sh's srt-generation and resumability paths are still covered.
cat > "$TMP/work/demo/transcript.vtt" <<'EOF'
WEBVTT

1
00:00:00.000 --> 00:00:01.000
Smoke test cue.
EOF

"$BIN/caption.sh" demo >/dev/null
assert_file "$TMP/work/demo/transcript.srt" "caption.sh srt"
pass "caption.sh generated transcript.srt from a fixture transcript"

m1=$(mtime "$TMP/work/demo/transcript.srt"); sleep 1.1
out="$("$BIN/caption.sh" demo)"
echo "$out" | grep -qi "skip" || fail "caption.sh did not report a skip on re-run"
m2=$(mtime "$TMP/work/demo/transcript.srt")
[ "$m1" = "$m2" ] || fail "caption.sh re-ran despite existing transcript.srt"
sleep 1.1
VIDEO_FORCE=1 "$BIN/caption.sh" demo >/dev/null
m3=$(mtime "$TMP/work/demo/transcript.srt")
[ "$m3" != "$m2" ] || fail "VIDEO_FORCE=1 did not force a redo (caption.sh srt)"
pass "caption.sh resumability (skip + VIDEO_FORCE=1)"

# --- clip.sh: manual-range mode + resumability ---
"$BIN/clip.sh" "$SAMPLE" demo 0 1 testclip >/dev/null 2>&1
assert_file "$TMP/clips/demo/testclip.mp4" "clip.sh manual-range"
pass "clip.sh manual-range wrote testclip.mp4"

m1=$(mtime "$TMP/clips/demo/testclip.mp4"); sleep 1.1
out="$("$BIN/clip.sh" "$SAMPLE" demo 0 1 testclip 2>&1)"
echo "$out" | grep -qi "skip" || fail "clip.sh did not report a skip on re-run"
m2=$(mtime "$TMP/clips/demo/testclip.mp4")
[ "$m1" = "$m2" ] || fail "clip.sh re-ran despite existing output"
sleep 1.1
VIDEO_FORCE=1 "$BIN/clip.sh" "$SAMPLE" demo 0 1 testclip >/dev/null 2>&1
m3=$(mtime "$TMP/clips/demo/testclip.mp4")
[ "$m3" != "$m2" ] || fail "VIDEO_FORCE=1 did not force a redo (clip.sh)"
pass "clip.sh resumability (skip + VIDEO_FORCE=1)"

# --- reframe.sh: both aspects + resumability ---
"$BIN/reframe.sh" demo >/dev/null
assert_file "$TMP/clips/demo/testclip.9x16.mp4" "reframe.sh"
assert_file "$TMP/clips/demo/testclip.1x1.mp4" "reframe.sh"
pass "reframe.sh wrote both 9x16 and 1x1 crops"

m1=$(mtime "$TMP/clips/demo/testclip.9x16.mp4"); sleep 1.1
out="$("$BIN/reframe.sh" demo)"
echo "$out" | grep -qi "skip" || fail "reframe.sh did not report a skip on re-run"
m2=$(mtime "$TMP/clips/demo/testclip.9x16.mp4")
[ "$m1" = "$m2" ] || fail "reframe.sh re-ran despite existing output"
sleep 1.1
VIDEO_FORCE=1 "$BIN/reframe.sh" demo >/dev/null
m3=$(mtime "$TMP/clips/demo/testclip.9x16.mp4")
[ "$m3" != "$m2" ] || fail "VIDEO_FORCE=1 did not force a redo (reframe.sh)"
pass "reframe.sh resumability (skip + VIDEO_FORCE=1)"

echo "[smoke] ALL PASS"
