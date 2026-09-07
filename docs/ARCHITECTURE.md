# Architecture

## The flow
```
record (Loom / OBS / screen capture)
   │
   ▼  loom-pull.sh (or drop a file in $VIDEO_RAWS)
$VIDEO_RAWS/<name>.mp4        ── the master; own it, back it up (not git)
   │
   ▼  ingest.sh
$VIDEO_WORK/work/<slug>/      ── source.mp4 (symlink), meta.json, audio.wav
   │
   ▼  transcribe.sh  (local Whisper, optional)
$VIDEO_WORK/work/<slug>/transcript.vtt, transcript.txt
   │
   ▼  review.py  (LLM judge)
$VIDEO_WORK/work/<slug>/review.md      ── honest content review + verdict + ranked fixes
$VIDEO_WORK/work/<slug>/clips.json     ── suggested short moments [{start,end,label,why}]
   │
   ▼  clip.sh
$VIDEO_WORK/clips/<slug>/     ── the cut shorts (from clips.json, or a manual range)
   │
   ▼  caption.sh  (srt always; burn-in optional, needs libass)
$VIDEO_WORK/work/<slug>/transcript.srt, clips/<slug>/*.captioned.mp4
   │
   ▼  reframe.sh  (center crop; no face/subject detection)
$VIDEO_WORK/clips/<slug>/*.9x16.mp4, *.1x1.mp4
   │
   ▼  (downstream — see ROADMAP: platform publishers, Flayr/Opus)
ready/  →  published/
```

## Folder contract
- `raws/` — masters. Immutable. Backed up off-repo (media is git-ignored).
- `work/<slug>/` — per-video working state: `source.mp4`, `meta.json`, `audio.wav`, `transcript.vtt`,
  `transcript.txt`, `transcript.srt`, `review.md`, `clips.json`.
- `clips/<slug>/` — extracted shorts, plus `<name>.captioned.mp4` siblings when burn-in is used.
- `ready/<slug>/`, `published/` — staging and archive (conventions for the consuming repo).

## Data shapes
- **`clips.json`** — array of `{ "start": "M:SS", "end": "M:SS", "label": "kebab-label", "why": "..." }`.
  Produced by `review.py`, consumed by `clip.sh`. Hand-editable.
- **`meta.json`** — raw `ffprobe -show_format -show_streams` output.

## Configuration
All tools are stateless and env-configured (`.env.example`): `GEMINI_API_KEY` (or gcloud secret),
`VIDEO_RAWS`, `VIDEO_WORK`, `VIDEO_MODEL`, `VIDEO_REVIEW_PROMPT`, `VIDEO_WHISPER_BIN`,
`VIDEO_WHISPER_MODEL`. No tool hardcodes a path or secret.

Each tool also loads an optional `.videorc`/`video.toml` config-file layer (`bin/lib/videoconfig.py`,
sourced via `bin/lib/load-config.sh` in bash tools, imported directly in `review.py`) for any of the
above keys not already set in the environment — env always wins. See README.md's "Config file"
section.

## The CLI (bin/video)
A pure `exec`-based dispatcher: `video <subcommand> [args...]` routes to the matching script in
`bin/` and passes `"$@"` through untouched — it never re-parses or reimplements a subcommand's own
flags/errors. `video` / `video --help` / `video -h` prints the subcommand list; an unknown
subcommand prints the same help to stderr and exits 1. Using `video ingest ...` behaves identically
to calling `bin/ingest.sh ...` directly — both interfaces stay fully supported.

## Transcription (transcribe.sh)
Runs a local Whisper (whisper.cpp by default; any CLI pointed at by `VIDEO_WHISPER_BIN` works,
including mainline `openai-whisper`) pass over `work/<slug>/audio.wav`, writing
`work/<slug>/transcript.vtt` (timestamped) and `work/<slug>/transcript.txt` (plain text). Non-fatal
if no whisper binary is found — prints an install hint and exits 0, so it's always safe to call in
a wrapped pipeline. When `transcript.txt` exists, `review.py` includes it in the judge's request.

## Captions (caption.sh)
Converts `work/<slug>/transcript.vtt` to `work/<slug>/transcript.srt` (always — cheap, no ffmpeg
call). Burning captions into `clips/<slug>/*.mp4` is opt-in via `VIDEO_CAPTION_BURN=1` and writes a
`<name>.captioned.mp4` sibling per clip rather than overwriting it (lossy re-encode). Requires an
ffmpeg build with `libass` (the `subtitles` filter) — a plain Homebrew `ffmpeg` install is not
guaranteed to have it; `caption.sh` detects this and skips burn-in gracefully (srt generation still
succeeds) rather than failing on a cryptic ffmpeg filter-parse error.

## Resumability
Every stage (`ingest.sh`, `transcribe.sh`, `review.py`, `caption.sh`, `reframe.sh`, `clip.sh`) checks
for its own expected output up front and skips the real work — printing a one-line notice, exit 0 —
when it already exists. `VIDEO_FORCE=1` forces a redo. `review.py`'s skip runs before any Gemini call
or key lookup, so re-running it on an already-reviewed slug costs nothing. Per-file stages
(`caption.sh`'s burn-in loop, `reframe.sh`, `clip.sh`'s JSON-driven mode) skip individually, so adding
a new clip to an existing slug still processes just the new one.

## Reframe (reframe.sh)
Exports 9:16 and 1:1 center crops of every `clips/<slug>/*.mp4` as `<name>.9x16.mp4`/`<name>.1x1.mp4`
siblings (originals untouched; already-derived `.9x16.mp4`/`.1x1.mp4`/`.captioned.mp4` files are
skipped as sources). Plain center crop computed from the probed source width/height — **no
face/subject-aware centering** (that would need a detection model dependency; out of scope for now,
tracked as a gap in docs/ROADMAP.md rather than silently dropped).

## The judge (review.py)
Uploads the video to the Gemini File API, polls until `ACTIVE`, then calls `generateContent`
(`gemini-2.5-flash` by default) with a review prompt that asks for both a prose review and a fenced
`clips.json` block. If `work/<slug>/transcript.txt` exists, it's appended as an extra context part
in the request so the judge's clip picks are grounded in what was actually said. The key is read
from env or gcloud and never printed. Swap the prompt via `VIDEO_REVIEW_PROMPT` to retune what
"good" means for your channel.
