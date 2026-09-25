#!/usr/bin/env python3
"""Network-free stand-in for the Flayr v2 API, for tests/smoke.sh only.

Usage: mock_flayr.py <port> <log-file>
Implements GET /api/v2/brands, POST /api/v2/media/upload-url, the upload
URL itself, and POST /api/v2/content. Appends one JSON line per created
draft to <log-file>. Requires `Authorization: Bearer flayr_sk_test`.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
STATE = {"uploads": 0, "content": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authed(self):
        if self.headers.get("Authorization") != "Bearer flayr_sk_test":
            self._json(401, {"error": "Unauthorized"})
            return False
        return True

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_GET(self):
        if self.path == "/api/v2/brands" and self._authed():
            self._json(200, {"brands": [{"id": "cp_tech", "name": "Dostal Tech"}],
                             "personal": {"id": "personal", "name": "Personal"}})

    def do_POST(self):
        if self.path == "/upload":
            size = len(self._body())
            STATE["uploads"] += 1
            return self._json(200, {"storageId": f"st_{STATE['uploads']}_{size}"})
        if not self._authed():
            return
        if self.path == "/api/v2/media/upload-url":
            self._body()
            return self._json(200, {"uploadUrl": f"http://127.0.0.1:{PORT}/upload"})
        if self.path == "/api/v2/content":
            body = json.loads(self._body())
            STATE["content"] += 1
            with open(LOG, "a") as f:
                f.write(json.dumps(body) + "\n")
            return self._json(201, {"id": f"content_{STATE['content']}", "status": "draft",
                                    "brandId": body.get("brandId")})
        self._json(404, {"error": "not found"})


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
