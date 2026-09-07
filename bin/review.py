#!/usr/bin/env python3
"""Judge a video → writes <work>/work/<slug>/review.md + clips.json.

Usage: review.py <video-path> [slug]

Config (env):
  VIDEO_JUDGE_PROVIDER  Which provider to use (see bin/lib/providers/). Default: gemini.
  VIDEO_WORK            output root; work/<slug>/ is written under it. Default: current dir.
  VIDEO_REVIEW_PROMPT   path to a custom prompt file (optional; overrides the built-in).
  VIDEO_FORCE           set to 1 to redo an already-reviewed slug.

  Provider-specific config (e.g. GEMINI_API_KEY, VIDEO_MODEL for the gemini
  provider) is documented in that provider's module, not here.

Flow: resolve the provider (VIDEO_JUDGE_PROVIDER) -> provider.review(...) ->
parse REVIEW + fenced clips.json out of the response. No secrets are printed.
"""
import sys, os, json, pathlib, re, importlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "lib"))
import videoconfig  # noqa: E402
videoconfig.apply_defaults()

WORK = pathlib.Path(os.environ.get("VIDEO_WORK", os.getcwd()))
PROVIDERS_DIR = pathlib.Path(__file__).resolve().parent / "lib" / "providers"

DEFAULT_PROMPT = """You are reviewing a short build-in-public / product video for a creator's content engine (LinkedIn + YouTube). Return TWO clearly separated sections.

## REVIEW
A tight, honest content review: (a) hook (first 10s), (b) clarity of the core idea, (c) pacing & any dead air/rambling — cite timestamps, (d) delivery/energy, (e) audio & visual quality, (f) does the payoff/demo land. Then a VERDICT (post as-is / minor edits then post / re-record) and the TOP 3 concrete fixes, ranked, each with a timestamp. Be specific; quote moments with timestamps. Do NOT write a generic emoji/hashtag caption.

## CLIPS_JSON
Then a single fenced ```json block ONLY: an array of the 3-6 best short-clip moments to cut for shorts. Each item: {"start":"M:SS","end":"M:SS","label":"...","why":"..."}. Pick self-contained, punchy moments.
"""

def prompt_text():
    p = os.environ.get("VIDEO_REVIEW_PROMPT")
    if p and os.path.exists(p):
        return open(p).read()
    return DEFAULT_PROMPT

def available_providers():
    return sorted(
        f.stem for f in PROVIDERS_DIR.glob("*.py")
        if f.stem not in ("__init__", "base")
    )

def load_provider():
    name = os.environ.get("VIDEO_JUDGE_PROVIDER", "gemini")
    if name not in available_providers():
        sys.exit(f"Unknown VIDEO_JUDGE_PROVIDER '{name}'. Available: {', '.join(available_providers())}")
    return importlib.import_module(f"providers.{name}")

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: review.py <video-path> [slug]")
    path = os.path.abspath(sys.argv[1])
    if not os.path.exists(path):
        sys.exit(f"not found: {path}")
    slug = sys.argv[2] if len(sys.argv) > 2 else pathlib.Path(path).stem
    out = WORK / "work" / slug
    out.mkdir(parents=True, exist_ok=True)
    if os.environ.get("VIDEO_FORCE") != "1" and (out / "review.md").exists() and (out / "clips.json").exists():
        print(f"[review] already reviewed -> {out}/{{review.md,clips.json}} (skip; set VIDEO_FORCE=1 to redo)")
        return

    provider = load_provider()
    transcript_file = out / "transcript.txt"
    transcript = transcript_file.read_text() if transcript_file.exists() else None
    if transcript:
        print(f"[review] using transcript from {transcript_file}")

    text = provider.review(path, transcript, prompt_text())

    (out / "review.md").write_text(f"# Review — {slug}\n\n{text}\n")
    m = re.search(r"```json\s*(\[.*?\])\s*```", text, re.S)
    if m:
        try:
            json.loads(m.group(1))
            (out / "clips.json").write_text(m.group(1).strip() + "\n")
            print(f"[review] wrote {out}/clips.json")
        except Exception:
            print("[review] clips block present but not valid JSON — left in review.md only")
    print(f"[review] wrote {out}/review.md")

if __name__ == "__main__":
    main()
