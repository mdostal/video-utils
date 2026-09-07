# Project CONTEXT

video-utils is a small MIT-licensed toolkit of composable CLI tools for a build-in-public
video pipeline: pull a raw recording, ingest it, let an LLM judge it, and cut shorts.

## Terminology

- **Slug** — the short identifier for one video across the pipeline (e.g. `my-video`). Used as
  the directory name under `work/<slug>/` and `clips/<slug>/`.
- **Raw** — the untouched master recording, saved to `$VIDEO_RAWS`. Immutable, never in git.
- **Ingest** — the `bin/ingest.sh` step that registers a raw: symlinks it into `work/<slug>/`,
  extracts `meta.json` (ffprobe) and `audio.wav`.
- **The judge** — `bin/review.py`, which uploads the video to the Gemini File API and asks it
  for a prose review plus a fenced `clips.json` block. "Judge" and "review" are used interchangeably.
- **clips.json** — the array of `{start, end, label, why}` clip suggestions produced by the judge
  and consumed by `bin/clip.sh`. Hand-editable.
- **Stage** — one step in the pipeline (pull → ingest → review → clip). See
  [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the full flow diagram.
- **Ready** — the staging convention (`ready/<slug>/`) for a clip that's finished and awaiting
  publish; a convention for the *consuming* repo, not something video-utils writes today.

## Key paths

- `bin/` — the tools: `loom-pull.sh`, `ingest.sh`, `review.py`, `clip.sh`. One tool = one file,
  single responsibility.
- `docs/ARCHITECTURE.md` — the pipeline flow, folder contract, and data shapes.
- `docs/ROADMAP.md` — the feature backlog; the plan-from document for `/plugin-hive:plan`. Each
  bullet is a candidate epic/story.
- `.env.example` — the only place env vars are documented; no tool hardcodes a path or secret.
- `$VIDEO_RAWS` / `$VIDEO_WORK` — env-configured roots for masters and pipeline outputs
  (`work/<slug>/`, `clips/<slug>/`), never fixed in code.

## Conventions

- Unix philosophy: each tool does one thing, reads/writes plain files, exits non-zero on failure.
- Config via env only — see the `env-config-only` cross-cutting concern in
  [cross-cutting-concerns.yaml](cross-cutting-concerns.yaml).
- No secrets, no media in git — enforced by `.gitignore`; see the `no-secrets-no-media-in-git` concern.
- `docs/ROADMAP.md` status markers (✅/🚧/🔲) must stay honest — see the `honest-status` concern.

## Canonical references

- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) — pipeline stages, folder contract, data shapes.
- [../docs/ROADMAP.md](../docs/ROADMAP.md) — feature backlog and non-goals.
- [../AGENTS.md](../AGENTS.md) — principles agents must hold, and how to add a new tool.
- [project-profile.yaml](project-profile.yaml) — full discovery profile, including `north_star`
  and the `planned_ui` note (a GitHub Pages showcase site, modeled on the sibling `drone-hub` project).
