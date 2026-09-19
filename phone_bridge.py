import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


def start(*, host: str, port: int, token: str, enqueue_text, get_last_reply, log):
    server_state = {
        "token": token or "",
        "enqueue_text": enqueue_text,
        "get_last_reply": get_last_reply,
        "log": log,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send_json(self, status: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _auth_ok(self) -> bool:
            token_cfg = server_state["token"]
            if not token_cfg:
                return False

            auth = (self.headers.get("Authorization") or "").strip()
            if auth.lower().startswith("bearer "):
                presented = auth.split(" ", 1)[1].strip()
            else:
                presented = (self.headers.get("X-Token") or "").strip()

            if not presented:
                return False

            return secrets.compare_digest(presented, token_cfg)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json(200, {"ok": True})
                return

            if parsed.path == "/last":
                if not self._auth_ok():
                    self._send_json(403, {"ok": False, "error": "forbidden"})
                    return

                last = server_state["get_last_reply"]()
                self._send_json(200, {"ok": True, "last": last})
                return

            self._send_json(404, {"ok": False, "error": "not_found"})

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != "/prompt":
                self._send_json(404, {"ok": False, "error": "not_found"})
                return

            if not self._auth_ok():
                self._send_json(403, {"ok": False, "error": "forbidden"})
                return

            try:
                length = int(self.headers.get("Content-Length") or "0")
            except Exception:
                length = 0

            if length <= 0 or length > 64_000:
                self._send_json(400, {"ok": False, "error": "bad_request"})
                return

            raw = self.rfile.read(length)
            ctype = (self.headers.get("Content-Type") or "").lower()

            text = ""
            if "application/json" in ctype:
                try:
                    obj = json.loads(raw.decode("utf-8", errors="replace"))
                    text = (obj.get("text") or "").strip()
                except Exception:
                    text = ""
            else:
                text = raw.decode("utf-8", errors="replace").strip()

            if not text:
                self._send_json(400, {"ok": False, "error": "empty_text"})
                return

            server_state["enqueue_text"](text)
            server_state["log"](f'Phone prompt queued: "{text}"', "info")
            self._send_json(200, {"ok": True, "queued": True, "ts": time.time()})

    httpd = ThreadingHTTPServer((host, int(port)), Handler)

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    log(f"Phone bridge listening on http://{host}:{port}", "info")
    return httpd
