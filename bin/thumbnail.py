#!/usr/bin/env python3
"""Extract candidate thumbnail frames, optionally LLM-picking the best "hook frame".

Usage: thumbnail.py <video-path> [slug]

Config (env):
  VIDEO_THUMBNAIL_COUNT  Number of candidate frames to extract. Default: 6.
  VIDEO_JUDGE_PROVIDER   Provider used for optional best-frame picking (see
                         bin/lib/providers/). Default: gemini.
  VIDEO_WORK             output root; work/<slug>/ is written under it. Default: current dir.
  VIDEO_FORCE            set to 1 to redo extraction and/or picking.

Flow: ffmpeg extracts N evenly-spaced frames -> work/<slug>/thumbnails/frame-NN.jpg
(always — free, local, deterministic). If the resolved provider implements
pick_frame(), ask it to choose the best hook frame -> work/<slug>/thumbnail.jpg
+ work/<slug>/thumbnail-pick.md. Picking is best-effort: no pick_frame on the
provider, a missing key, or any error during picking degrades gracefully —
the extracted frames remain, and this script still exits 0.
"""
import sys, os, json, subprocess, tempfile, pathlib, importlib, shutil

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "lib"))
import videoconfig  # noqa: E402
videoconfig.apply_defaults()

WORK = pathlib.Path(os.environ.get("VIDEO_WORK", os.getcwd()))
COUNT = int(os.environ.get("VIDEO_THUMBNAIL_COUNT", "6"))
PROVIDERS_DIR = pathlib.Path(__file__).resolve().parent / "lib" / "providers"

PICK_PROMPT = """You are picking a single thumbnail frame for a short-form video.
Look at the numbered candidate frames (frame 1, frame 2, ...) and pick the one
that would work best as a "hook" thumbnail — clear, high-energy, not blurry or
mid-blink. Respond with ONLY the frame number, nothing else."""


def _sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _duration(video_path):
    r = _sh(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path])
    return float(r.stdout.strip())


def _load_provider():
    name = os.environ.get("VIDEO_JUDGE_PROVIDER", "gemini")
    available = sorted(f.stem for f in PROVIDERS_DIR.glob("*.py") if f.stem not in ("__init__", "base"))
    if name not in available:
        print(f"[thumbnail] unknown VIDEO_JUDGE_PROVIDER '{name}' — skipping pick (available: {', '.join(available)})")
        return None
    return importlib.import_module(f"providers.{name}")


def extract_frames(video_path, out_dir, force):
    existing = sorted(out_dir.glob("frame-*.jpg"))
    if existing and not force:
        print(f"[thumbnail] already have {len(existing)} frame(s) in {out_dir} (skip; set VIDEO_FORCE=1 to redo)")
        return sorted(str(p) for p in existing)
    out_dir.mkdir(parents=True, exist_ok=True)
    dur = _duration(video_path)
    paths = []
    for i in range(COUNT):
        t = dur * (i + 0.5) / COUNT
        out = out_dir / f"frame-{i+1:02d}.jpg"
        _sh(["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-frames:v", "1", "-q:v", "2",
             str(out), "-loglevel", "error"])
        paths.append(str(out))
    print(f"[thumbnail] extracted {len(paths)} candidate frame(s) -> {out_dir}/")
    return paths

def pick_best(provider, frame_paths, out_dir, force):
    thumb = out_dir.parent / "thumbnail.jpg"
    if thumb.exists() and not force:
        print(f"[thumbnail] already have {thumb} (skip; set VIDEO_FORCE=1 to redo)")
        return
    if provider is None or not hasattr(provider, "pick_frame"):
        print("[thumbnail] provider has no pick_frame — leaving candidate frames for manual selection")
        return
    try:
        idx = provider.pick_frame(frame_paths, PICK_PROMPT)
        idx = max(1, min(int(idx), len(frame_paths)))
        chosen = frame_paths[idx - 1]
        shutil.copyfile(chosen, thumb)
        (out_dir.parent / "thumbnail-pick.md").write_text(
            f"# Thumbnail pick\n\nProvider: {os.environ.get('VIDEO_JUDGE_PROVIDER', 'gemini')}\n"
            f"Chosen frame: {os.path.basename(chosen)}\n"
        )
        print(f"[thumbnail] picked {os.path.basename(chosen)} -> {thumb}")
    except (Exception, SystemExit) as e:
        print(f"[thumbnail] picking failed ({e}) — leaving candidate frames for manual selection")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: thumbnail.py <video-path> [slug]")
    path = os.path.abspath(sys.argv[1])
    if not os.path.exists(path):
        sys.exit(f"not found: {path}")
    slug = sys.argv[2] if len(sys.argv) > 2 else pathlib.Path(path).stem
    out = WORK / "work" / slug
    thumbs_dir = out / "thumbnails"
    force = os.environ.get("VIDEO_FORCE") == "1"

    frame_paths = extract_frames(path, thumbs_dir, force)
    provider = _load_provider()
    pick_best(provider, frame_paths, thumbs_dir, force)

if __name__ == "__main__":
    main()
