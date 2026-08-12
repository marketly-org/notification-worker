"""Tiny stdlib HTTP health server for k8s probes.

Celery workers don't serve HTTP, so we run a :mod:`http.server` listener
in a daemon thread. It is started on the ``worker_ready`` Celery signal
and stopped on ``worker_shutdown``.

Exposes:
    GET /health  — process is alive (always 200 once booted)
    GET /ready   — broker (Redis) is reachable (200) or not (503)
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import settings

_server: ThreadingHTTPServer | None = None
_thread: threading.Thread | None = None

def _redis_ping() -> bool:
    try:
        import redis  # local import keeps the health module importable in tests

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # silence default logging
        pass

    def _send(self, status: int, body: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):  # noqa: N802 — http.server API
        if self.path == "/health":
            self._send(200, {"status": "ok", "service": "notification-worker"})
        elif self.path == "/ready":
            ok = _redis_ping()
            self._send(200 if ok else 503, {"status": "ready" if ok else "not_ready"})
        else:
            self._send(404, {"error": "not found"})

def start() -> None:
    global _server, _thread
    port = int(os.getenv("HEALTH_PORT", "8080"))
    _server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True, name="health-server")
    _thread.start()

def stop() -> None:
    global _server, _thread
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None
    if _thread is not None:
        _thread.join(timeout=2)
        _thread = None
