# video-utils

Small, composable command-line tools for a **build-in-public video pipeline**: pull a raw recording,
ingest it, let an LLM judge it, and cut shorts — the plumbing between hitting *stop* and hitting *post*.

Deliberately Unix-y: each tool does one thing, reads/writes plain files, and configures via env vars.
Bring your own content repo; this is just the tools.

## What's here

| Tool | Does | Needs |
|---|---|---|
| `bin/loom-pull.sh <url> [name]` | Download a Loom share → `$VIDEO_RAWS` | curl |
| `bin/ingest.sh <video> [slug]` | Register a raw → `work/<slug>/` + metadata + audio | ffmpeg/ffprobe |
| `bin/review.py <video> [slug]` | **LLM judge** (Gemini) → `review.md` + `clips.json` | Gemini key |
| `bin/clip.sh <video> <slug> [start end name]` | Cut shorts from `clips.json` or a manual range | ffmpeg |

## Quick start
```bash
cp .env.example .env && edit .env      # set GEMINI_API_KEY, VIDEO_RAWS, VIDEO_WORK
set -a; source .env; set +a

bin/loom-pull.sh https://www.loom.com/share/<id> my-video   # or drop an OBS recording in $VIDEO_RAWS
bin/ingest.sh   "$VIDEO_RAWS/my-video.mp4" my-video
bin/review.py   "$VIDEO_RAWS/my-video.mp4" my-video          # writes work/my-video/review.md + clips.json
bin/clip.sh     "$VIDEO_RAWS/my-video.mp4" my-video          # cuts work/my-video/clips.json into clips/my-video/
```

## Config (env)
See `.env.example`. Key ones: `GEMINI_API_KEY` (or `GEMINI_SECRET_NAME`/`_PROJECT` to pull it from
gcloud Secret Manager), `VIDEO_RAWS` (raw archive dir), `VIDEO_WORK` (where `work/` and `clips/` are written).

## Design & roadmap
- `docs/ARCHITECTURE.md` — the pipeline stages and file conventions.
- `docs/ROADMAP.md` — the feature backlog (transcription, auto-captioning, platform publishers,
  Flayr/Opus hooks, a config/CLI, batch mode, a dashboard). This is the plan-from document.

## Status
Early but working: download, ingest, LLM review + auto clip-suggestions, and clipping all run today.
Everything in `docs/ROADMAP.md` is intended, not built. Contributions welcome once public.

## License
MIT — see `LICENSE`.
