#!/usr/bin/env python3
"""Judge a video with Gemini multimodal → writes <work>/work/<slug>/review.md + clips.json.

Usage: review.py <video-path> [slug]

Config (env):
  GEMINI_API_KEY        API key (preferred). If unset, falls back to gcloud (below).
  GEMINI_SECRET_NAME    gcloud Secret Manager secret to read the key from (optional fallback).
  GEMINI_SECRET_PROJECT gcloud project for that secret (optional).
  VIDEO_WORK            output root; work/<slug>/ is written under it. Default: current dir.
  VIDEO_MODEL           Gemini model. Default: gemini-2.5-flash.
  VIDEO_REVIEW_PROMPT   path to a custom prompt file (optional; overrides the built-in).

Flow: upload to the Gemini File API → poll ACTIVE → generateContent. No secrets are printed.
"""
import sys, os, json, time, subprocess, tempfile, pathlib, re

API = "https://generativelanguage.googleapis.com"
MODEL = os.environ.get("VIDEO_MODEL", "gemini-2.5-flash")
WORK = pathlib.Path(os.environ.get("VIDEO_WORK", os.getcwd()))

DEFAULT_PROMPT = """You are reviewing a short build-in-public / product video for a creator's content engine (LinkedIn + YouTube). Return TWO clearly separated sections.

## REVIEW
A tight, honest content review: (a) hook (first 10s), (b) clarity of the core idea, (c) pacing & any dead air/rambling — cite timestamps, (d) delivery/energy, (e) audio & visual quality, (f) does the payoff/demo land. Then a VERDICT (post as-is / minor edits then post / re-record) and the TOP 3 concrete fixes, ranked, each with a timestamp. Be specific; quote moments with timestamps. Do NOT write a generic emoji/hashtag caption.

## CLIPS_JSON
Then a single fenced ```json block ONLY: an array of the 3-6 best short-clip moments to cut for shorts. Each item: {"start":"M:SS","end":"M:SS","label":"...","why":"..."}. Pick self-contained, punchy moments.
"""

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def get_key():
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    name = os.environ.get("GEMINI_SECRET_NAME")
    if name:
        cmd = ["gcloud", "secrets", "versions", "access", "latest", f"--secret={name}"]
        proj = os.environ.get("GEMINI_SECRET_PROJECT")
        if proj:
            cmd.append(f"--project={proj}")
        r = sh(cmd)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    sys.exit("No Gemini key. Set GEMINI_API_KEY, or GEMINI_SECRET_NAME (+ optional GEMINI_SECRET_PROJECT).")

def prompt_text():
    p = os.environ.get("VIDEO_REVIEW_PROMPT")
    if p and os.path.exists(p):
        return open(p).read()
    return DEFAULT_PROMPT

def upload(key, path):
    size = os.path.getsize(path)
    meta = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"file": {"display_name": os.path.basename(path)}}, meta); meta.close()
    hdr = tempfile.NamedTemporaryFile(suffix=".hdr", delete=False); hdr.close()
    sh(["curl", "-s", "-D", hdr.name, "-o", "/dev/null", "-X", "POST",
        f"{API}/upload/v1beta/files?key={key}",
        "-H", "X-Goog-Upload-Protocol: resumable", "-H", "X-Goog-Upload-Command: start",
        "-H", f"X-Goog-Upload-Header-Content-Length: {size}",
        "-H", "X-Goog-Upload-Header-Content-Type: video/mp4",
        "-H", "Content-Type: application/json", "-d", f"@{meta.name}"])
    up = None
    for line in open(hdr.name, errors="ignore"):
        if line.lower().startswith("x-goog-upload-url:"):
            up = line.split(":", 1)[1].strip()
    if not up:
        sys.exit("No upload URL returned by the Gemini File API.")
    r = sh(["curl", "-s", "-X", "POST", up, "-H", f"Content-Length: {size}",
            "-H", "X-Goog-Upload-Offset: 0", "-H", "X-Goog-Upload-Command: upload, finalize",
            "--data-binary", f"@{path}"])
    info = json.loads(r.stdout)
    return info["file"]["name"], info["file"]["uri"]

def wait_active(key, name):
    for _ in range(80):
        r = sh(["curl", "-s", f"{API}/v1beta/{name}?key={key}"])
        st = json.loads(r.stdout).get("state")
        if st == "ACTIVE":
            return
        if st == "FAILED":
            sys.exit("Gemini file processing FAILED.")
        time.sleep(3)
    sys.exit("Timed out waiting for file to become ACTIVE.")

def generate(key, uri, transcript=None):
    parts = [
        {"file_data": {"mime_type": "video/mp4", "file_uri": uri}},
        {"text": prompt_text()},
    ]
    if transcript:
        parts.append({"text": f"TRANSCRIPT (for reference, use timestamps loosely):\n{transcript}"})
    body = {"contents": [{"parts": parts}]}
    bf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(body, bf); bf.close()
    r = sh(["curl", "-s", "-X", "POST",
            f"{API}/v1beta/models/{MODEL}:generateContent?key={key}",
            "-H", "Content-Type: application/json", "-d", f"@{bf.name}"])
    d = json.loads(r.stdout)
    if "candidates" not in d:
        sys.exit(f"Gemini error: {json.dumps(d)[:400]}")
    return d["candidates"][0]["content"]["parts"][0]["text"]

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: review.py <video-path> [slug]")
    path = os.path.abspath(sys.argv[1])
    if not os.path.exists(path):
        sys.exit(f"not found: {path}")
    slug = sys.argv[2] if len(sys.argv) > 2 else pathlib.Path(path).stem
    out = WORK / "work" / slug
    out.mkdir(parents=True, exist_ok=True)
    key = get_key()
    transcript_file = out / "transcript.txt"
    transcript = transcript_file.read_text() if transcript_file.exists() else None
    if transcript:
        print(f"[review] using transcript from {transcript_file}")
    print(f"[review] uploading {os.path.basename(path)} ...")
    name, uri = upload(key, path)
    print(f"[review] uploaded; waiting for ACTIVE ...")
    wait_active(key, name)
    print("[review] generating review ...")
    text = generate(key, uri, transcript)
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
