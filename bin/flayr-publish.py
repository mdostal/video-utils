#!/usr/bin/env python3
"""Hand a staged ready/<slug>/ bundle to Flayr as draft posts.

Usage: flayr-publish.py <ready-dir> [--brand NAME|ID|personal] [--platforms a,b] [--dry-run]

Every *.mp4 in <ready-dir> becomes one Flayr draft (video + caption), filed
into the chosen brand, ready to schedule or add to a campaign in Flayr.
Captions: <clip>.md next to the clip if present, else the bundle's
caption.md. Nothing is posted — drafts only.

Config (env):
  FLAYR_API_KEY    a Flayr API key (flayr_sk_...). Required unless --dry-run.
  FLAYR_API_URL    Flayr base URL. Default: https://flayr.social
  FLAYR_BRAND      default for --brand (a brand name or id from Flayr, or
                   "personal"). Omitted: the brand last active in Flayr.
  FLAYR_PLATFORMS  default for --platforms, comma-separated (e.g. linkedin,youtube).
  VIDEO_FORCE      set to 1 to re-send clips already sent.

Resumable: sent clips are recorded in <ready-dir>/flayr.json and skipped
on re-run. No secrets are printed.
"""
import argparse
import json
import os
import pathlib
import ssl
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "lib"))
import videoconfig  # noqa: E402
videoconfig.apply_defaults()

RECEIPT = "flayr.json"
TIMEOUT = 60
UPLOAD_TIMEOUT = 600


class FlayrError(Exception):
    pass


def _ssl_context():
    """CA bundle for HTTPS. python.org builds of Python on macOS ship without
    one ("Install Certificates.command"), so the default context fails every
    verification; fall back to certifi, then the system bundle."""
    if os.environ.get("SSL_CERT_FILE"):
        return ssl.create_default_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    for bundle in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.isfile(bundle):
            return ssl.create_default_context(cafile=bundle)
    return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()


def api(base, key, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as res:
            return json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("error", "")
        except Exception:
            detail = ""
        raise FlayrError(f"{method} {path} -> HTTP {e.code} {detail}".strip()) from None
    except urllib.error.URLError as e:
        raise FlayrError(f"{method} {path} -> {e.reason}") from None


def upload(upload_url, clip):
    req = urllib.request.Request(
        upload_url, data=clip.read_bytes(), method="POST",
        headers={"Content-Type": "video/mp4"},
    )
    try:
        with urllib.request.urlopen(req, timeout=UPLOAD_TIMEOUT, context=SSL_CONTEXT) as res:
            storage_id = json.loads(res.read()).get("storageId")
    except (urllib.error.URLError, ValueError) as e:
        raise FlayrError(f"upload of {clip.name} failed: {e}") from None
    if not storage_id:
        raise FlayrError(f"upload of {clip.name} returned no storageId")
    return storage_id


def resolve_brand(base, key, wanted):
    """Brand name (case-insensitive) or id -> brandId; 'personal' passes through."""
    if not wanted:
        return None
    if wanted.lower() == "personal":
        return "personal"
    listing = api(base, key, "GET", "/api/v2/brands")
    brands = listing.get("brands", [])
    for b in brands:
        if wanted == b["id"] or wanted.lower() == b["name"].lower():
            return b["id"]
    names = ", ".join(b["name"] for b in brands) or "(none)"
    raise FlayrError(f'no Flayr brand "{wanted}". Yours: {names}, or "personal".')


def caption_for(clip, bundle):
    for candidate in (clip.with_suffix(".md"), bundle / "caption.md"):
        if candidate.is_file():
            text = candidate.read_text().strip()
            if text:
                return text
    raise FlayrError(f"no caption for {clip.name}: add {clip.stem}.md or caption.md to {bundle}")


def main():
    p = argparse.ArgumentParser(description="Send a ready/<slug>/ bundle to Flayr as draft posts.")
    p.add_argument("ready_dir")
    p.add_argument("--brand", default=os.environ.get("FLAYR_BRAND"))
    p.add_argument("--platforms", default=os.environ.get("FLAYR_PLATFORMS", ""))
    p.add_argument("--dry-run", action="store_true", help="show what would be sent; no network")
    args = p.parse_args()

    bundle = pathlib.Path(args.ready_dir).resolve()
    if not bundle.is_dir():
        sys.exit(f"[flayr-publish] not a directory: {bundle}")
    slug = bundle.name
    clips = sorted(c for c in bundle.glob("*.mp4") if not c.name.startswith("."))
    if not clips:
        sys.exit(f"[flayr-publish] no .mp4 clips in {bundle}")
    platforms = [x.strip() for x in args.platforms.split(",") if x.strip()]

    receipt_path = bundle / RECEIPT
    receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
    force = os.environ.get("VIDEO_FORCE") == "1"

    try:
        captions = {c.name: caption_for(c, bundle) for c in clips}
    except FlayrError as e:
        sys.exit(f"[flayr-publish] {e}")

    if args.dry_run:
        for c in clips:
            state = "skip (already sent)" if c.name in receipt and not force else "send"
            print(f"[flayr-publish] {state}: {c.name} -> brand={args.brand or '(last active)'} "
                  f"platforms={','.join(platforms) or '(none)'} caption={len(captions[c.name])} chars")
        return

    key = os.environ.get("FLAYR_API_KEY")
    if not key:
        sys.exit("[flayr-publish] FLAYR_API_KEY is not set (create one in Flayr → Settings → Integrations → API keys)")
    base = os.environ.get("FLAYR_API_URL", "https://flayr.social").rstrip("/")

    try:
        brand_id = resolve_brand(base, key, args.brand)
        for c in clips:
            if c.name in receipt and not force:
                print(f"[flayr-publish] skip (already sent): {c.name} -> {receipt[c.name]['id']}")
                continue
            upload_url = api(base, key, "POST", "/api/v2/media/upload-url", {})["uploadUrl"]
            storage_id = upload(upload_url, c)
            body = {
                "text": captions[c.name],
                "platforms": platforms,
                "videoStorageId": storage_id,
                "sourceLabel": f"video-pipeline: {slug}"[:80],
            }
            if brand_id:
                body["brandId"] = brand_id
            created = api(base, key, "POST", "/api/v2/content", body)
            receipt[c.name] = {"id": created["id"], "brandId": created.get("brandId")}
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(f"[flayr-publish] sent: {c.name} -> draft {created['id']}")
    except FlayrError as e:
        sys.exit(f"[flayr-publish] {e}")


if __name__ == "__main__":
    main()
