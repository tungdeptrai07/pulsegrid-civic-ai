"""Unit and integration tests for PulseGrid Civic AI Triage & Dispatch."""

from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.triage_engine import PulseGridDispatchEngine, compute_severity_score
from backend.server import create_server


class TestPulseGrid(unittest.TestCase):
    """Tests severity scoring, specialty-matched dispatch, resolution, and REST API."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.srv = create_server(port=0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_severity_scoring_bounds_and_tiers(self) -> None:
        score, tier = compute_severity_score("FLOOD_SURGE", 5.5, 2.5, 25000)
        self.assertGreaterEqual(score, 82.0)
        self.assertEqual(tier, "CRITICAL")

        low_score, low_tier = compute_severity_score("TRAFFIC_BOTTLENECK", 20.0, 50.0, 100)
        self.assertLess(low_score, 45.0)
        self.assertEqual(low_tier, "LOW")

    def test_dispatch_and_resolve_lifecycle(self) -> None:
        eng = PulseGridDispatchEngine()
        dispatched = eng.auto_dispatch("inc_001")
        self.assertEqual(dispatched.status, "DISPATCHED")
        self.assertEqual(dispatched.assigned_unit, "UNIT-GRID-01")
        self.assertFalse(eng.units["UNIT-GRID-01"].available)

        resolved = eng.resolve_incident("inc_001")
        self.assertEqual(resolved.status, "RESOLVED")
        self.assertTrue(eng.units["UNIT-GRID-01"].available)

    def test_http_api_end_to_end(self) -> None:
        ing = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/ingest",
            data=json.dumps({"zone": "Central District", "hazardType": "MEDICAL_EMERGENCY", "sensorReading": 160, "threshold": 100, "populationAffected": 15000}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(ing, timeout=5) as r1:
            d1 = json.loads(r1.read().decode("utf-8"))
        inc_id = d1["incident"]["incident_id"]

        disp = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/dispatch",
            data=json.dumps({"incidentId": inc_id}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(disp, timeout=5) as r2:
            d2 = json.loads(r2.read().decode("utf-8"))
        self.assertEqual(d2["incident"]["assigned_unit"], "UNIT-MED-03")


if __name__ == "__main__":
    unittest.main()
