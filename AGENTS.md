# AGENTS.md — working on video-utils

This is a small, open-source (MIT) toolkit of composable CLI tools for a build-in-public video
pipeline. It is a **library of tools**, not a content repo — no videos, no personal data live here.

## Principles (hold these)
- **Unix philosophy.** Each tool does one thing, reads/writes plain files, exits non-zero on failure.
- **Config via env, never hardcode.** No absolute paths, no personal secret names, no usernames in
  committed code. Everything configurable comes from env vars documented in `.env.example`.
- **No secrets, no media in git.** `.gitignore` blocks `.env` and all media. Keep it that way.
- **Portable.** macOS + Linux; depend only on common tools (bash, python3, curl, ffmpeg, optional gcloud).
- **Honest status.** `docs/ROADMAP.md` marks what's built vs. intended. Don't claim a stub works.

## Layout
- `bin/` — the tools (`loom-pull.sh`, `ingest.sh`, `review.py`, `clip.sh`).
- `docs/ARCHITECTURE.md` — the stage/flow/file conventions.
- `docs/ROADMAP.md` — the feature backlog (the plan-from document).

## Adding a tool
1. Put it in `bin/`, single responsibility, env-configured (mirror the existing tools).
2. Document it in `README.md` (the table) and `docs/ARCHITECTURE.md` (where it sits in the flow).
3. Add any new env var to `.env.example`.
4. If it's a stage, keep the folder contract: raws → `work/<slug>/` → `clips/<slug>/` → `ready/`.

## Testing
`bash tests/smoke.sh` (also run in CI on push/PR, `.github/workflows/smoke.yml`) generates its own
synthetic sample via ffmpeg and covers `ingest.sh`, `review.py` (via `VIDEO_JUDGE_PROVIDER=mock`, no
real API call), `caption.sh`, `clip.sh`, `reframe.sh`, `transcribe.sh`'s missing-binary path, and
resumability (`VIDEO_FORCE=1`) for each — never commits any media. NOT covered: `review.py`'s real
Gemini call (needs a real paid `GEMINI_API_KEY`) and `transcribe.sh`'s real transcription (needs a
real whisper binary) — for those, run the tool by hand against a short sample clip and confirm the
expected output files appear and the exit code is 0. Don't commit the sample.

## For the planner (Hive)
`docs/ROADMAP.md` is written to be decomposed into an epic + stories. When planning, treat each
roadmap bullet as a candidate feature; respect the principles above (especially: config-driven,
no secrets/media in git, honest status).
