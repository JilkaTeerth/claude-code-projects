#!/usr/bin/env python3
"""Money: localhost:7575. One page, fed by core.py. Binds to 127.0.0.1 only."""
import json, os, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import core

PORT = int(os.environ.get("MONEY_PORT", 7575))
PAGE = os.path.join(core.HOME, "index.html")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.path = self.path.split("?")[0]
        if self.path in ("/", "/index.html"):
            return self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
        if self.path.startswith("/img/"):
            root = os.path.realpath(os.path.join(core.HOME, "img"))
            f = os.path.realpath(os.path.join(root, self.path[5:]))
            if f.startswith(root + os.sep) and os.path.isfile(f):
                ext = f.rsplit(".", 1)[-1].lower()
                ctype = {"json": "application/json", "png": "image/png", "gif": "image/gif",
                         "mp4": "video/mp4", "webp": "image/webp"}.get(ext, "image/jpeg")
                return self.send(200, open(f, "rb").read(), ctype)
            return self.send(404, {"error": "no such image"})
        if self.path == "/api/summary":
            return self.send(200, core.summary())
        self.send(404, {"error": "not found"})

    def do_POST(self):
        # Only this page may write. Blocks other sites poking localhost from a browser tab.
        origin = self.headers.get("Origin", "")
        if origin and origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.send(403, {"error": "bad origin"})
        n = int(self.headers.get("Content-Length") or 0)
        b = json.loads(self.rfile.read(n) or b"{}")
        try:
            p = self.path
            if p == "/api/add":
                name, amt, lo = core.parse(b["text"])
                if b.get("feel") == "wish":
                    r = {"wish": core.add_wish(name, amt, lo, b.get("where", ""))}
                else:
                    tid = core.add_expense(name, amt, b.get("feel"))
                    r = {"id": tid, **core.reaction(core.db(), tid)}
            elif p == "/api/delete":    core.delete_tx(b["id"]); r = {"ok": True}
            elif p == "/api/unwish":    core.delete_wish(b["wish_id"]); r = {"ok": True}
            elif p == "/api/buy":       core.buy_wish(b["wish_id"], b["price"]); r = {"ok": True}
            elif p == "/api/ceremony":  core.ceremony_done(b["key"]); r = {"ok": True}
            elif p == "/api/pot":       core.set_pot(b["pot"]); r = {"ok": True}
            elif p == "/api/alt":       core.set_alt(b["wish_id"], b.get("alt", "")); r = {"ok": True}
            elif p == "/api/tag":       core.tag(b["id"], b.get("verdict"), b.get("category")); r = {"ok": True}
            else:                       return self.send(404, {"error": "not found"})
            self.send(200, r)
        except Exception as e:
            traceback.print_exc()
            self.send(500, {"error": str(e)})


if __name__ == "__main__":
    core.db()
    print(f"money on http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
