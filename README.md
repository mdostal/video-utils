# video-utils

[![smoke](https://github.com/mdostal/video-utils/actions/workflows/smoke.yml/badge.svg)](https://github.com/mdostal/video-utils/actions/workflows/smoke.yml)

Small, composable command-line tools for a **build-in-public video pipeline**: pull a raw recording,
ingest it, let an LLM judge it, and cut shorts — the plumbing between hitting *stop* and hitting *post*.

Deliberately Unix-y: each tool does one thing, reads/writes plain files, and configures via env vars.
Bring your own content repo; this is just the tools.

## What's here

| Tool | Does | Needs |
|---|---|---|
| `bin/video <subcommand> [args...]` | One entrypoint wrapping every stage below (`--help` for usage) | — |
| `bin/loom-pull.sh <url> [name]` | Download a Loom share → `$VIDEO_RAWS` | curl |
| `bin/ingest.sh <video> [slug]` | Register a raw → `work/<slug>/` + metadata + audio | ffmpeg/ffprobe |
| `bin/transcribe.sh <slug>` | Local Whisper transcript → `transcript.vtt`/`.txt` | whisper.cpp (or `VIDEO_WHISPER_BIN`) |
| `bin/review.py <video> [slug]` | **LLM judge** (pluggable provider, Gemini by default) → `review.md` + `clips.json` (uses the transcript if present) | Gemini key (or `VIDEO_JUDGE_PROVIDER=mock` for no-key testing) |
| `bin/clip.sh <video> <slug> [start end name]` | Cut shorts from `clips.json` or a manual range | ffmpeg |
| `bin/caption.sh <slug>` | `.srt` from the transcript; optional burn-in into clips | ffmpeg (+ `libass` for burn-in) |
| `bin/reframe.sh <slug>` | 9:16 and 1:1 center-crop exports of cut clips | ffmpeg/ffprobe |
| `bin/batch.sh [raws-dir]` | Run the full pipeline unattended over every raw in a folder | (same as the stages it runs) |

## Quick start
```bash
cp .env.example .env && edit .env      # set GEMINI_API_KEY, VIDEO_RAWS, VIDEO_WORK
set -a; source .env; set +a

bin/loom-pull.sh https://www.loom.com/share/<id> my-video   # or drop an OBS recording in $VIDEO_RAWS
bin/ingest.sh   "$VIDEO_RAWS/my-video.mp4" my-video
bin/review.py   "$VIDEO_RAWS/my-video.mp4" my-video          # writes work/my-video/review.md + clips.json
bin/clip.sh     "$VIDEO_RAWS/my-video.mp4" my-video          # cuts work/my-video/clips.json into clips/my-video/
```

### Or use the CLI
Every stage above (plus `transcribe`/`caption`) is also reachable through one entrypoint:
```bash
bin/video --help
bin/video ingest "$VIDEO_RAWS/my-video.mp4" my-video
```
`bin/video <subcommand>` is a thin wrapper around the same scripts — either interface works.

## Config (env)
See `.env.example`. Key ones: `GEMINI_API_KEY` (or `GEMINI_SECRET_NAME`/`_PROJECT` to pull it from
gcloud Secret Manager), `VIDEO_RAWS` (raw archive dir), `VIDEO_WORK` (where `work/` and `clips/` are written).

### Config file (optional)
Every tool also checks a `.videorc` (`KEY=VALUE` lines) or `video.toml` (a flat `[video]` table,
`key = "value"` lines) in the current directory — or `$VIDEO_CONFIG` for an explicit path. **Env
always wins**; the config file only fills in values you haven't exported. Keys are the exact env
var name (e.g. `VIDEO_WHISPER_MODEL`, not a shortened alias). Don't commit your `.videorc`/`video.toml`
to this repo — they're per-consuming-repo config, already `.gitignore`d.

## Design & roadmap
- `docs/ARCHITECTURE.md` — the pipeline stages and file conventions.
- `docs/ROADMAP.md` — the feature backlog (transcription, auto-captioning, platform publishers,
  Flayr/Opus hooks, a config/CLI, batch mode, a dashboard). This is the plan-from document.

## Status
Working today: download, ingest, local transcription, LLM review + auto clip-suggestions, clipping,
captions/srt, 9:16/1:1 reframe, a unified CLI, an optional config file, and resumability — see
`docs/ROADMAP.md` for exactly which parts of each are verified vs. still 🚧. An automated smoke-test
suite (`tests/smoke.sh`, CI-integrated) covers most of the pipeline; contributions welcome.

## License
MIT — see `LICENSE`.
