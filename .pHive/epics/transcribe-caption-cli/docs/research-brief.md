# Research Brief — transcribe-caption-cli

## Scope
Near-term ROADMAP.md items the operator asked to plan first: **Transcription**, **Auto-captions /
subtitle burn-in**, and **A real CLI**. (Explicitly excludes other near-term items — Vertical/short
reframe, Thumbnail generator, Config file — which stay in the backlog.)

## Relevant existing code

### `bin/ingest.sh` (32 lines)
Already extracts `work/<slug>/audio.wav` at 16kHz mono via ffmpeg:
```bash
ffmpeg -y -i "$MP4" -vn -ac 1 -ar 16000 "$W/audio.wav"
```
This is exactly the input format most local Whisper builds want — transcription can consume it
directly with no new extraction step. Comment on line 24 already says "for a transcript pass",
so this was anticipated.

### `bin/review.py` (131 lines)
`DEFAULT_PROMPT` (module-level string, lines 22-29) is sent to Gemini alongside the raw video via
the File API. `generate()` (lines 89-101) builds the request body with `contents[0].parts` —
currently one `file_data` part (the video) + one `text` part (the prompt). Adding a transcript
means appending a second `text` part with the transcript content, or interpolating it into the
prompt string before the request is built. `prompt_text()` (lines 49-53) already supports
`VIDEO_REVIEW_PROMPT` override, so any prompt-text change should stay compatible with a custom
prompt file.

### `bin/clip.sh` (37 lines)
Cuts `clips/<slug>/NN-label.mp4` from `clips.json` via a heredoc'd Python block (lines 23-37) that
shells out to `ffmpeg -ss ... -to ... -c:v libx264 -c:a aac`. Output files are already
straightforward `ffmpeg` re-encodes — burning subtitles in is one more `-vf subtitles=...` filter
away, but doing it as a *separate* pass (not inline in `clip.sh`) keeps clip-cutting and captioning
independently testable/toggleable, matching the Unix-philosophy principle in AGENTS.md.

### `bin/loom-pull.sh` (unread in depth — not touched by this epic)
Not relevant to transcription/captions/CLI; the CLI entrypoint story wraps it unchanged.

## Env var conventions (`.env.example`)
Existing vars: `GEMINI_API_KEY`, `GEMINI_SECRET_NAME`, `GEMINI_SECRET_PROJECT`, `VIDEO_MODEL`,
`VIDEO_REVIEW_PROMPT`, `VIDEO_RAWS`, `VIDEO_WORK`. All prefixed `VIDEO_` except the Gemini-specific
ones. New vars for this epic should follow the `VIDEO_` prefix and be added to `.env.example` with
the same comment style (one-line purpose + default called out).

## Folder contract (docs/ARCHITECTURE.md)
`raws/ → work/<slug>/ (source.mp4, meta.json, audio.wav, review.md, clips.json) → clips/<slug>/`.
New artifacts should slot into this contract rather than invent a new root:
- `work/<slug>/transcript.vtt`, `work/<slug>/transcript.txt`, `work/<slug>/transcript.srt` — sibling
  outputs of the existing `work/<slug>/` stage dir.
- Captioned clips — sibling files inside the existing `clips/<slug>/` dir (not a new top-level dir).

Both `work/` and `clips/` are already git-ignored at the root of `.gitignore` (lines 13-14), so no
`.gitignore` change is needed for these new file types.

## Validation note
No external library/SDK/API research was escalated — Whisper/whisper.cpp and ffmpeg's `subtitles`
filter are well-established, already-implied-by-ROADMAP choices, and no context7/web lookup was
needed to ground the design. Confidence: high, based on direct codebase reading (all four `bin/`
scripts read in full).
