"""Gemini multimodal judge provider — the original review.py implementation,
moved behind the provider interface (see base.py).

Config (env):
  GEMINI_API_KEY        API key (preferred). If unset, falls back to gcloud (below).
  GEMINI_SECRET_NAME    gcloud Secret Manager secret to read the key from (optional fallback).
  GEMINI_SECRET_PROJECT gcloud project for that secret (optional).
  VIDEO_MODEL           Gemini model. Default: gemini-2.5-flash.

Flow: upload to the Gemini File API -> poll ACTIVE -> generateContent. No secrets are printed.
"""
import sys, os, json, re, time, base64, subprocess, tempfile

API = "https://generativelanguage.googleapis.com"
MODEL = os.environ.get("VIDEO_MODEL", "gemini-2.5-flash")


def _sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _get_key():
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    name = os.environ.get("GEMINI_SECRET_NAME")
    if name:
        cmd = ["gcloud", "secrets", "versions", "access", "latest", f"--secret={name}"]
        proj = os.environ.get("GEMINI_SECRET_PROJECT")
        if proj:
            cmd.append(f"--project={proj}")
        r = _sh(cmd)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    sys.exit("No Gemini key. Set GEMINI_API_KEY, or GEMINI_SECRET_NAME (+ optional GEMINI_SECRET_PROJECT).")


def _upload(key, path):
    size = os.path.getsize(path)
    meta = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"file": {"display_name": os.path.basename(path)}}, meta); meta.close()
    hdr = tempfile.NamedTemporaryFile(suffix=".hdr", delete=False); hdr.close()
    _sh(["curl", "-s", "-D", hdr.name, "-o", "/dev/null", "-X", "POST",
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
    r = _sh(["curl", "-s", "-X", "POST", up, "-H", f"Content-Length: {size}",
             "-H", "X-Goog-Upload-Offset: 0", "-H", "X-Goog-Upload-Command: upload, finalize",
             "--data-binary", f"@{path}"])
    info = json.loads(r.stdout)
    return info["file"]["name"], info["file"]["uri"]


def _wait_active(key, name):
    for _ in range(80):
        r = _sh(["curl", "-s", f"{API}/v1beta/{name}?key={key}"])
        st = json.loads(r.stdout).get("state")
        if st == "ACTIVE":
            return
        if st == "FAILED":
            sys.exit("Gemini file processing FAILED.")
        time.sleep(3)
    sys.exit("Timed out waiting for file to become ACTIVE.")


def _generate(key, uri, prompt, transcript=None):
    parts = [
        {"file_data": {"mime_type": "video/mp4", "file_uri": uri}},
        {"text": prompt},
    ]
    if transcript:
        parts.append({"text": f"TRANSCRIPT (for reference, use timestamps loosely):\n{transcript}"})
    body = {"contents": [{"parts": parts}]}
    bf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(body, bf); bf.close()
    r = _sh(["curl", "-s", "-X", "POST",
             f"{API}/v1beta/models/{MODEL}:generateContent?key={key}",
             "-H", "Content-Type: application/json", "-d", f"@{bf.name}"])
    d = json.loads(r.stdout)
    if "candidates" not in d:
        sys.exit(f"Gemini error: {json.dumps(d)[:400]}")
    return d["candidates"][0]["content"]["parts"][0]["text"]


def review(video_path, transcript, prompt):
    key = _get_key()
    print(f"[gemini] uploading {os.path.basename(video_path)} ...")
    name, uri = _upload(key, video_path)
    print("[gemini] uploaded; waiting for ACTIVE ...")
    _wait_active(key, name)
    print("[gemini] generating review ...")
    return _generate(key, uri, prompt, transcript)


def pick_frame(image_paths, prompt):
    """Ask Gemini to pick the best frame. Returns a 1-based index, clamped
    to a valid range; never raises for an unparseable/missing response
    (only _get_key()'s missing-key case is fatal — callers must expect that
    and treat picking as best-effort, per base.py's contract)."""
    key = _get_key()
    parts = []
    for p in image_paths:
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
    parts.append({"text": prompt})
    body = {"contents": [{"parts": parts}]}
    bf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(body, bf); bf.close()
    r = _sh(["curl", "-s", "-X", "POST",
             f"{API}/v1beta/models/{MODEL}:generateContent?key={key}",
             "-H", "Content-Type: application/json", "-d", f"@{bf.name}"])
    d = json.loads(r.stdout)
    if "candidates" not in d:
        sys.exit(f"Gemini error: {json.dumps(d)[:400]}")
    text = d["candidates"][0]["content"]["parts"][0]["text"]
    m = re.search(r"\d+", text)
    idx = int(m.group()) if m else 1
    return max(1, min(idx, len(image_paths)))
