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
   ▼  (downstream — see ROADMAP: captions, platform publishers, Flayr/Opus)
ready/  →  published/
```

## Folder contract
- `raws/` — masters. Immutable. Backed up off-repo (media is git-ignored).
- `work/<slug>/` — per-video working state: `source.mp4`, `meta.json`, `audio.wav`, `transcript.vtt`,
  `transcript.txt`, `review.md`, `clips.json`.
- `clips/<slug>/` — extracted shorts.
- `ready/<slug>/`, `published/` — staging and archive (conventions for the consuming repo).

## Data shapes
- **`clips.json`** — array of `{ "start": "M:SS", "end": "M:SS", "label": "kebab-label", "why": "..." }`.
  Produced by `review.py`, consumed by `clip.sh`. Hand-editable.
- **`meta.json`** — raw `ffprobe -show_format -show_streams` output.

## Configuration
All tools are stateless and env-configured (`.env.example`): `GEMINI_API_KEY` (or gcloud secret),
`VIDEO_RAWS`, `VIDEO_WORK`, `VIDEO_MODEL`, `VIDEO_REVIEW_PROMPT`, `VIDEO_WHISPER_BIN`,
`VIDEO_WHISPER_MODEL`. No tool hardcodes a path or secret.

## Transcription (transcribe.sh)
Runs a local Whisper (whisper.cpp by default; any CLI pointed at by `VIDEO_WHISPER_BIN` works,
including mainline `openai-whisper`) pass over `work/<slug>/audio.wav`, writing
`work/<slug>/transcript.vtt` (timestamped) and `work/<slug>/transcript.txt` (plain text). Non-fatal
if no whisper binary is found — prints an install hint and exits 0, so it's always safe to call in
a wrapped pipeline. When `transcript.txt` exists, `review.py` includes it in the judge's request.

## The judge (review.py)
Uploads the video to the Gemini File API, polls until `ACTIVE`, then calls `generateContent`
(`gemini-2.5-flash` by default) with a review prompt that asks for both a prose review and a fenced
`clips.json` block. If `work/<slug>/transcript.txt` exists, it's appended as an extra context part
in the request so the judge's clip picks are grounded in what was actually said. The key is read
from env or gcloud and never printed. Swap the prompt via `VIDEO_REVIEW_PROMPT` to retune what
"good" means for your channel.
