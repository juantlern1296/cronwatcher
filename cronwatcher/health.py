"""Simple health check endpoint for cronwatcher daemon."""

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional

from cronwatcher.metrics import MetricsStore

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    metrics_store: Optional[MetricsStore] = None

    def do_GET(self) -> None:
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        elif self.path == "/metrics":
            self._respond_metrics()
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _respond_metrics(self) -> None:
        store = self.__class__.metrics_store
        if store is None:
            self._respond(503, {"error": "metrics unavailable"})
            return
        data = {job: vars(m) for job, m in store._data.items()}
        self._respond(200, data)

    def log_message(self, fmt: str, *args) -> None:  # suppress default access logs
        pass


class HealthServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, metrics_store: Optional[MetricsStore] = None):
        if port < 1 or port > 65535:
            raise ValueError(f"Invalid port: {port}")
        self.host = host
        self.port = port
        HealthHandler.metrics_store = metrics_store
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        self._server = HTTPServer((self.host, self.port), HealthHandler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Health server listening on %s:%d", self.host, self.port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            logger.info("Health server stopped")
