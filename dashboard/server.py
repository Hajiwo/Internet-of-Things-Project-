"""Dependency-free HTTP server for dashboard assets and JSON APIs."""

from __future__ import annotations

import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from services.camera_service import CameraRequestError

logger = logging.getLogger(__name__)
STATIC_ROOT = Path(__file__).resolve().parent / "static"


class DashboardServer:
    """Serve the dashboard and bridge its API to the backend service."""

    def __init__(
        self,
        state_provider: Callable[[], dict[str, Any]],
        camera_handler: Callable[[str], dict[str, Any]],
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self.state_provider = state_provider
        self.camera_handler = camera_handler
        self.host = host
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._server is None:
            return self.host, self.port
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def start(self) -> None:
        handler = self._build_handler()
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="smart-garage-dashboard",
            daemon=True,
        )
        self._thread.start()
        logger.info("Dashboard server listening on http://%s:%s", *self.address)

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        dashboard = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/api/state":
                    self._send_json(dashboard.state_provider())
                    return

                assets = {
                    "/": ("index.html", "text/html; charset=utf-8"),
                    "/index.html": ("index.html", "text/html; charset=utf-8"),
                    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                }
                asset = assets.get(path)
                if asset is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                filename, content_type = asset
                self._send_bytes((STATIC_ROOT / filename).read_bytes(), content_type)

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                directions = {
                    "/api/camera/enter": "enter",
                    "/api/camera/exit": "exit",
                }
                direction = directions.get(path)
                if direction is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    result = dashboard.camera_handler(direction)
                except CameraRequestError as error:
                    self._send_json(
                        {"ok": False, "error": str(error)}, error.status_code
                    )
                    return
                except Exception as error:
                    logger.exception("Unhandled camera API error")
                    self._send_json(
                        {"ok": False, "error": str(error)},
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
                    return
                self._send_json({"ok": True, "result": result})

            def _send_json(
                self, payload: dict[str, Any], status: int = HTTPStatus.OK
            ) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send_bytes(body, "application/json; charset=utf-8", status)

            def _send_bytes(
                self,
                body: bytes,
                content_type: str,
                status: int = HTTPStatus.OK,
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                logger.debug("Dashboard: " + format, *args)

        return RequestHandler
