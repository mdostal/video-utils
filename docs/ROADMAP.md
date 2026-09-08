# Roadmap

The plan-from document. Each bullet is a candidate feature — decompose into an epic + stories.
Legend: ✅ built · 🚧 partial · 🔲 planned.

## Built today
- ✅ `loom-pull.sh` — Loom share → raw mp4.
- ✅ `ingest.sh` — register raw, ffprobe metadata, audio extract.
- ✅ `review.py` — pluggable-provider judge (Gemini by default) → `review.md` + `clips.json`.
- ✅ `clip.sh` — cut shorts from `clips.json` or a manual range.
- ✅ Env-driven config, media/secret git-ignored.
- ✅ **A real CLI** — one `video` entrypoint wrapping all six stages
  (`video pull|ingest|transcribe|review|caption|clip`) with `--help`, instead of separate scripts.
- ✅ **Config file** — every tool loads an optional `.videorc`/`video.toml` (via `bin/lib/videoconfig.py`)
  for keys not already set in the environment; env always wins.
- ✅ **Resumability** — every stage skips work whose output already exists; `VIDEO_FORCE=1` to redo
  (an env toggle, not a `--force` CLI flag, matching the project's existing env-config convention).
  Verified for ingest/transcribe/review/reframe/clip; caption.sh's burn-in skip is implemented but
  unverified (blocked by the same missing-libass gap as burn-in itself).
- ✅ **Test harness** — `tests/smoke.sh` (CI-integrated, `.github/workflows/smoke.yml`) generates its
  own synthetic sample and covers ingest/review(mock)/caption/clip/reframe + resumability;
  `review.py`'s real Gemini call and `transcribe.sh`'s real-transcription path (needs a real whisper
  binary) are intentionally excluded from automated CI coverage.
- ✅ **Provider abstraction** — `review.py`'s Gemini calls moved behind `bin/lib/providers/`, selected
  via `VIDEO_JUDGE_PROVIDER` (default `gemini`); a network-free `mock` provider proves it's genuinely
  pluggable and now makes `review.py`'s own logic CI-testable. Only one real backend ships — adding a
  second (OpenAI/Claude/etc.) would need its own API key decision.
- ✅ **Batch mode** — `bin/batch.sh` runs the full pipeline unattended over every raw in a folder,
  continuing past a failing video rather than aborting the batch; a summary prints at the end.
- ✅ **Dashboard** — `bin/dashboard.py`, a stdlib-only local web view (`127.0.0.1` only, no auth) of
  `work/`/`clips/` — slug index, per-slug review/clips/thumbnail view, path-traversal-guarded media
  serving. `review.md` is shown as escaped plain text, not rendered Markdown (v1 simplification).
- ✅ **Backup adapter** — `bin/backup.sh` pushes `$VIDEO_RAWS` to any rclone-supported destination
  (Google Drive, S3, plain paths, etc.) via `rclone copy`; no rclone or no `VIDEO_BACKUP_REMOTE` is
  non-fatal, no backend credentials touch this repo (rclone's own config holds those).

## Near-term
- 🚧 **Transcription** — `bin/transcribe.sh` + judge integration are built (local `whisper`/whisper.cpp
  pass over `audio.wav` → timestamped `transcript.vtt`/`.txt`, fed to `review.py`'s judge prompt when
  present); not yet verified end-to-end against a real recording with a whisper binary installed.
- 🚧 **Auto-captions / subtitle burn-in** — `bin/caption.sh` generates `.srt` from the transcript
  (verified) and can burn styled captions into shorts via ffmpeg's `subtitles` filter, but that needs
  an ffmpeg build with `libass`, which a plain `brew install ffmpeg` does not guarantee — burn-in
  itself is implemented but not yet verified end-to-end on a libass-enabled build.
- 🚧 **Vertical/short reframe** — `bin/reframe.sh` exports 9:16/1:1 crops of cut clips, verified
  end-to-end; the face/subject-aware center from the original ask is NOT built (plain center crop
  only) — would need a real detection-model dependency.
- 🚧 **Thumbnail generator** — `bin/thumbnail.py` extracts candidate frames via ffmpeg (verified) and
  can ask the judge provider to pick the best one via a new `pick_frame` provider capability
  (verified via the mock provider and the no-key graceful-degradation path); the real Gemini pick is
  unverified end-to-end (no key in this environment).

## Integrations
All four items below need an operator decision (which service, which API key/credential) before any
code can be written — none are silently buildable the way Backup adapter turned out to be.
- 🔲 **Flayr publish hook** — POST finished `ready/<slug>/` assets + caption to the Flayr API for
  cross-post scheduling. Operator follow-up in progress (as of 2026-09-08).
- 🔲 **Opus Clip hook** — a public API now exists (`developer.opus.pro`, v2, API-key auth, checked
  2026-09-08) — this bullet is no longer gated on "if/when a public API exists". Needs an
  `OPUS_API_KEY` decision from the operator before building the integration; the manual-upload
  path remains the fallback until then.
- 🔲 **Platform publishers** — native upload to LinkedIn / YouTube / etc. via their APIs. Needs a
  per-platform OAuth app + credentials decision.

## Non-goals (for now)
- Not a video *editor* (no timeline UI) — it orchestrates capture→judge→clip→handoff.
- Not a hosting/CDN — masters live in your own backup, not here.
