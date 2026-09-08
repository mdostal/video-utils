#!/usr/bin/env python3
"""Local-only web dashboard: browse work/<slug>/ reviews + clips/<slug>/ files.

Usage: dashboard.py [port]

Config (env):
  VIDEO_WORK             root holding work/ and clips/. Default: current dir.
  VIDEO_DASHBOARD_PORT   port to listen on if not given positionally. Default: 8420.

Read-only. Binds to 127.0.0.1 only — a local dev convenience tool, not a
deployed service, no authentication. stdlib http.server only, no new
dependency; review.md is shown as escaped plain text (not rendered Markdown)
as a deliberate v1 simplification.
"""
import sys, os, json, pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

WORK = pathlib.Path(os.environ.get("VIDEO_WORK", os.getcwd()))
WORK_DIR = WORK / "work"
CLIPS_DIR = WORK / "clips"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page(title, body):
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{esc(title)}</title></head><body>{body}</body></html>"


def list_slugs():
    if not WORK_DIR.is_dir():
        return []
    return sorted(p.name for p in WORK_DIR.iterdir() if p.is_dir())


def safe_join(base, rel_path):
    """Resolve rel_path under base; return None if it escapes base (path traversal)."""
    base = base.resolve()
    target = (base / rel_path).resolve()
    if target != base and base not in target.parents:
        return None
    return target


def render_index():
    slugs = list_slugs()
    if not slugs:
        body = "<h1>video-utils dashboard</h1><p>No slugs found under work/.</p>"
    else:
        items = "".join(f'<li><a href="/slug/{esc(s)}">{esc(s)}</a></li>' for s in slugs)
        body = f"<h1>video-utils dashboard</h1><ul>{items}</ul>"
    return page("Dashboard", body)


def render_slug(slug):
    wdir = WORK_DIR / slug
    if not wdir.is_dir():
        return None
    parts = [f"<h1>{esc(slug)}</h1>", '<p><a href="/">&larr; all slugs</a></p>']

    thumb = wdir / "thumbnail.jpg"
    if thumb.is_file():
        parts.append(f'<img src="/media/work/{esc(slug)}/thumbnail.jpg" style="max-width:320px" alt="thumbnail">')

    review = wdir / "review.md"
    if review.is_file():
        parts.append("<h2>Review</h2><pre>" + esc(review.read_text(encoding="utf-8")) + "</pre>")

    clips_json = wdir / "clips.json"
    if clips_json.is_file():
        try:
            clips = json.loads(clips_json.read_text(encoding="utf-8"))
            rows = "".join(
                f"<li>{esc(c.get('label', ''))} ({esc(c.get('start', ''))}-{esc(c.get('end', ''))}): {esc(c.get('why', ''))}</li>"
                for c in clips
            )
            parts.append(f"<h2>Suggested clips</h2><ul>{rows}</ul>")
        except (json.JSONDecodeError, AttributeError):
            parts.append("<h2>Suggested clips</h2><p>(clips.json present but invalid)</p>")

    cdir = CLIPS_DIR / slug
    if cdir.is_dir():
        files = sorted(p.name for p in cdir.iterdir() if p.is_file())
        if files:
            rows = "".join(f'<li><a href="/media/clips/{esc(slug)}/{esc(f)}">{esc(f)}</a></li>' for f in files)
            parts.append(f"<h2>Clips ({len(files)})</h2><ul>{rows}</ul>")
        else:
            parts.append("<h2>Clips</h2><p>none yet</p>")

    return page(slug, "".join(parts))


CONTENT_TYPES = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".srt": "text/plain", ".vtt": "text/vtt"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self._html(render_index())
        elif path.startswith("/slug/"):
            html = render_slug(path[len("/slug/"):])
            self._html(html) if html is not None else self._error(404, "unknown slug")
        elif path.startswith("/media/work/"):
            self._media(WORK_DIR, path[len("/media/work/"):])
        elif path.startswith("/media/clips/"):
            self._media(CLIPS_DIR, path[len("/media/clips/"):])
        else:
            self._error(404, "not found")

    def _html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _media(self, base, rel):
        target = safe_join(base, rel)
        if target is None or not target.is_file():
            self._error(404, "not found")
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("VIDEO_DASHBOARD_PORT", "8420"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[dashboard] serving http://127.0.0.1:{port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
