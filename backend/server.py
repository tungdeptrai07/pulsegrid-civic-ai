"""HTTP server for PulseGrid Civic AI Triage & Dispatch (port 8096)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.triage_engine import PulseGridDispatchEngine


class PulseGridHTTPHandler(SimpleHTTPRequestHandler):
    """Serves PulseGrid AI Web UI and JSON triage/dispatch APIs."""

    engine = PulseGridDispatchEngine()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json({"status": "ok", "service": "PulseGrid Civic AI Triage"})
            return
        if self.path == "/api/state":
            self._send_json(self.engine.get_state())
            return
        if self.path in {"", "/"}:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(min(length, 128_000))
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._send_json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            if self.path == "/api/ingest":
                inc = self.engine.ingest_incident(
                    zone=str(data.get("zone", "Central District")),
                    hazard_type=str(data.get("hazardType", "MEDICAL_EMERGENCY")),
                    sensor_reading=float(data.get("sensorReading", 150.0)),
                    threshold=float(data.get("threshold", 100.0)),
                    population_affected=int(data.get("populationAffected", 5000)),
                )
                self._send_json({"incident": asdict(inc), "state": self.engine.get_state()})
                return
            if self.path == "/api/dispatch":
                inc = self.engine.auto_dispatch(str(data.get("incidentId", "")))
                self._send_json({"incident": asdict(inc), "state": self.engine.get_state()})
                return
            if self.path == "/api/resolve":
                inc = self.engine.resolve_incident(str(data.get("incidentId", "")))
                self._send_json({"incident": asdict(inc), "state": self.engine.get_state()})
                return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8096,
    engine: PulseGridDispatchEngine | None = None,
) -> ThreadingHTTPServer:
    """Create the PulseGrid HTTP server."""

    class BoundHandler(PulseGridHTTPHandler):
        pass

    BoundHandler.engine = engine or PulseGridDispatchEngine()
    return ThreadingHTTPServer((host, port), BoundHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8096"))
    srv = create_server(port=port)
    print(f"PulseGrid Civic AI running on http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()
