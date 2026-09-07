# Roadmap

The plan-from document. Each bullet is a candidate feature — decompose into an epic + stories.
Legend: ✅ built · 🚧 partial · 🔲 planned.

## Built today
- ✅ `loom-pull.sh` — Loom share → raw mp4.
- ✅ `ingest.sh` — register raw, ffprobe metadata, audio extract.
- ✅ `review.py` — Gemini multimodal judge → `review.md` + `clips.json`.
- ✅ `clip.sh` — cut shorts from `clips.json` or a manual range.
- ✅ Env-driven config, media/secret git-ignored.
- ✅ **A real CLI** — one `video` entrypoint wrapping all six stages
  (`video pull|ingest|transcribe|review|caption|clip`) with `--help`, instead of separate scripts.

## Near-term
- 🚧 **Transcription** — `bin/transcribe.sh` + judge integration are built (local `whisper`/whisper.cpp
  pass over `audio.wav` → timestamped `transcript.vtt`/`.txt`, fed to `review.py`'s judge prompt when
  present); not yet verified end-to-end against a real recording with a whisper binary installed.
- 🚧 **Auto-captions / subtitle burn-in** — `bin/caption.sh` generates `.srt` from the transcript
  (verified) and can burn styled captions into shorts via ffmpeg's `subtitles` filter, but that needs
  an ffmpeg build with `libass`, which a plain `brew install ffmpeg` does not guarantee — burn-in
  itself is implemented but not yet verified end-to-end on a libass-enabled build.
- 🔲 **Vertical/short reframe** — export 9:16 and 1:1 crops (with a face/subject-aware center) for
  TikTok/Reels/Shorts from a 16:9 master.
- 🔲 **Thumbnail generator** — pull candidate frames + an LLM-picked "best hook frame."
- 🔲 **Config file** — support a `video.toml`/`.videorc` in the consuming repo in addition to env.

## Integrations
- 🔲 **Flayr publish hook** — POST finished `ready/<slug>/` assets + caption to the Flayr API for
  cross-post scheduling.
- 🔲 **Opus Clip hook** — if/when a public API exists, hand off the raw for auto-shorts; until then,
  document the manual upload path.
- 🔲 **Platform publishers** — native upload to LinkedIn / YouTube / etc. via their APIs.
- 🔲 **Backup adapter** — push raws to a backup target (Google Drive, S3, rclone) since media isn't in git.

## Robustness / quality
- 🔲 **Test harness** — a tiny sample clip + smoke tests per tool in CI.
- 🔲 **Batch mode** — process a folder of raws unattended.
- 🔲 **Provider abstraction** — pluggable judge backend (Gemini today; allow others) behind one interface.
- 🔲 **Resumability** — skip stages whose outputs already exist; `--force` to redo.
- 🔲 **Dashboard** — a small local web view of `work/`/`clips/` with the reviews and clip previews.

## Non-goals (for now)
- Not a video *editor* (no timeline UI) — it orchestrates capture→judge→clip→handoff.
- Not a hosting/CDN — masters live in your own backup, not here.
