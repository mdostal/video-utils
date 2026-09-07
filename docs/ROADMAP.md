# Roadmap

The plan-from document. Each bullet is a candidate feature — decompose into an epic + stories.
Legend: ✅ built · 🚧 partial · 🔲 planned.

## Built today
- ✅ `loom-pull.sh` — Loom share → raw mp4.
- ✅ `ingest.sh` — register raw, ffprobe metadata, audio extract.
- ✅ `review.py` — Gemini multimodal judge → `review.md` + `clips.json`.
- ✅ `clip.sh` — cut shorts from `clips.json` or a manual range.
- ✅ Env-driven config, media/secret git-ignored.

## Near-term
- 🔲 **Transcription** — local `whisper` (or whisper.cpp) pass over `audio.wav` → timestamped
  `transcript.vtt`/`.txt`; feed the transcript to the judge for better clip picks.
- 🔲 **Auto-captions / subtitle burn-in** — generate `.srt` and optionally burn styled captions into
  shorts (retention lever on silent-autoplay feeds).
- 🔲 **Vertical/short reframe** — export 9:16 and 1:1 crops (with a face/subject-aware center) for
  TikTok/Reels/Shorts from a 16:9 master.
- 🔲 **Thumbnail generator** — pull candidate frames + an LLM-picked "best hook frame."
- 🔲 **A real CLI** — one `video` entrypoint wrapping the stages (`video pull|ingest|review|clip|export`)
  with `--help`, instead of separate scripts.
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
