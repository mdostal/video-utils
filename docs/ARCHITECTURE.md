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

## Thumbnails (thumbnail.py)
Always extracts `VIDEO_THUMBNAIL_COUNT` (default 6) evenly-spaced candidate frames via ffmpeg into
`work/<slug>/thumbnails/frame-NN.jpg` — free, local, deterministic. If the resolved judge provider
implements the optional `pick_frame(image_paths, prompt) -> int` capability (see below), asks it to
pick the best "hook frame" -> `work/<slug>/thumbnail.jpg` + `thumbnail-pick.md`. Picking is
best-effort: no `pick_frame` on the provider, a missing key, or any error during picking degrades
gracefully (extraction's output is untouched, exit 0) rather than failing the whole run.

## Batch mode (batch.sh)
`batch.sh [raws-dir]` (default `$VIDEO_RAWS`, then `./raws`) runs the full pipeline — ingest ->
transcribe -> review -> clip (JSON-driven) -> caption -> reframe — unattended over every
`.mp4`/`.mov`/`.mkv`/`.webm` file found directly in that directory (non-recursive). A failing stage
for one video does not abort the batch; a `$ok ok, $failed failed, $total total` summary prints at
the end, and `batch.sh` exits non-zero only if any video had a failed stage. Resumability (above)
makes re-running `batch.sh` over the same folder cheap — already-completed stages skip.

## Backup (backup.sh)
`backup.sh [raws-dir]` pushes `$VIDEO_RAWS` to a backend-agnostic destination via `rclone copy` —
one optional external tool covers Google Drive, S3, and everything else rclone supports, rather than
a bespoke client per backend. `VIDEO_BACKUP_REMOTE` unset, or no `rclone` on `$PATH`, are both
non-fatal (same graceful-degradation pattern as `transcribe.sh`'s whisper binary). No backend
credentials are read or stored by this repo — they live entirely in rclone's own `rclone config`.
`rclone copy` is incremental by construction, so no custom resumability logic is needed on top of it.

## Dashboard (dashboard.py)
A stdlib-only (`http.server`) local web view: `GET /` lists every slug under `work/`; `GET
/slug/<slug>` renders that slug's `review.md` (escaped plain text — not rendered Markdown, a
deliberate v1 simplification), lists `clips.json`'s suggestions, and links to files under
`clips/<slug>/`; `GET /media/{work,clips}/<slug>/<file>` serves those files (so a browser can play a
clip or view a thumbnail). Read-only, no authentication, binds to `127.0.0.1` only — a local dev
convenience tool, not a deployed service. The media route resolves every path against its base
directory and rejects anything that would escape it (path-traversal guard) rather than trusting the
URL.

## Judge providers (bin/lib/providers/)
`review.py` is a thin, provider-agnostic CLI: it resolves the transcript (if any) and the review
prompt (`VIDEO_REVIEW_PROMPT` or the built-in default), then delegates to a provider module selected
by `VIDEO_JUDGE_PROVIDER` (default `gemini`). A provider exposes `review(video_path, transcript,
prompt) -> str` (see `bin/lib/providers/base.py`) and, optionally, `pick_frame(image_paths, prompt)
-> int` (used by `thumbnail.py` — a provider may implement either, both, or neither). Providers own
all of their own config (API keys, model names). `review.py` parses the returned text for a `REVIEW`
section and a fenced `clips.json` block; that parsing is provider-agnostic.

- **`gemini`** (default) — uploads the video to the Gemini File API, polls until `ACTIVE`, then calls
  `generateContent` (`gemini-2.5-flash` by default, `VIDEO_MODEL` to override) for `review()`; for
  `pick_frame()`, sends the candidate JPEGs as inline base64 image parts (no File API upload needed —
  they're small) and parses the first number out of the response. The key is read from
  `GEMINI_API_KEY` or gcloud (`GEMINI_SECRET_NAME`/`GEMINI_SECRET_PROJECT`) and never printed.
- **`mock`** — a network-free provider for tests and local iteration: `review()` returns a canned
  response (echoing the transcript back if one was passed); `pick_frame()` always returns `1`. No key
  or network needed. `VIDEO_JUDGE_PROVIDER=mock`.

Only one real backend ships today; the interface is proven pluggable via `mock`, not via a second
real provider (adding e.g. OpenAI/Claude would be a future ROADMAP item needing its own API key).
