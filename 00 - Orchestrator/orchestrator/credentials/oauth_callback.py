"""Loopback callback capture and manual redirect parsing for Orchestrator OAuth."""

from __future__ import annotations

import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse


def parse_callback_input(value: str, *, expected_state: str) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        raise ValueError("No callback URL or authorization code provided.")
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        params = parse_qs(parsed.query)
        code = _first(params, "code")
        state = _first(params, "state")
        if not code:
            raise ValueError("Callback URL does not contain a code.")
        if state != expected_state:
            raise ValueError("OAuth state does not match.")
        return code, state
    return text, expected_state


class LoopbackCallbackServer:
    def __init__(self, *, port: int, expected_state: str) -> None:
        self._port = int(port)
        self._expected_state = expected_state
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=1)
        self._server = HTTPServer(("127.0.0.1", self._port), self._build_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def callback_url(self) -> str:
        return f"http://localhost:{self._port}/auth/callback"

    def start(self) -> None:
        self._thread.start()

    def wait_for_code(self, timeout_seconds: float) -> tuple[str, str]:
        deadline = time.monotonic() + float(timeout_seconds)
        while time.monotonic() < deadline:
            try:
                return self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
        raise TimeoutError("Timed out while waiting for the OAuth callback.")

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1.0)

    def _build_handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                try:
                    full_url = f"http://localhost:{owner._port}{self.path}"
                    code, state = parse_callback_input(full_url, expected_state=owner._expected_state)
                    owner._queue.put_nowait((code, state))
                    self._write(200, "OAuth callback received. You can return to the Orchestrator.")
                except Exception as exc:
                    self._write(400, f"Invalid OAuth callback: {exc}")

            def log_message(self, _format: str, *_args) -> None:
                return None

            def _write(self, status_code: int, body: str) -> None:
                encoded = body.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler


def read_manual_callback(reader: Callable[[str], str], *, expected_state: str) -> tuple[str, str]:
    return parse_callback_input(reader("Paste redirect URL or authorization code: "), expected_state=expected_state)


def _first(params: dict[str, list[str]], key: str) -> str:
    values = params.get(key) or []
    return str(values[0]) if values else ""
