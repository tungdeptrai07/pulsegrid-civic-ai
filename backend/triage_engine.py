"""PulseGrid AI — Real-Time Civic Telemetry & Emergency Dispatch Triage Engine.

Built for HackOdisha 6.0 (Devfolio Open Online Hackathon).
Combines multi-sensor anomaly scoring, severity-weighted response routing,
resource allocation constraints, and offline-resilient audit logs.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any

HAZARD_BASE_WEIGHT = {
    "POWER_GRID_OVERLOAD": 0.90,
    "FLOOD_SURGE": 0.95,
    "MEDICAL_EMERGENCY": 0.98,
    "TRAFFIC_BOTTLENECK": 0.65,
    "WATER_QUALITY_DROP": 0.82,
}


@dataclass
class CivicIncident:
    """Represents a live urban telemetry / citizen incident report."""

    incident_id: str
    zone: str
    hazard_type: str
    sensor_reading: float
    threshold: float
    population_affected: int
    severity_score: float
    priority_tier: str  # "CRITICAL", "HIGH", "MODERATE", "LOW"
    assigned_unit: str | None
    status: str  # "OPEN", "DISPATCHED", "RESOLVED"
    evidence_hash: str
    created_at: float


@dataclass
class ResponseUnit:
    """Available civic emergency/utility response team."""

    unit_id: str
    specialty: str
    zone: str
    available: bool = True
    dispatches_completed: int = 0


def compute_severity_score(
    hazard_type: str,
    sensor_reading: float,
    threshold: float,
    population_affected: int,
) -> tuple[float, str]:
    """Compute bounded [0..100] severity score and priority tier."""
    base = HAZARD_BASE_WEIGHT.get(hazard_type.upper(), 0.70)
    ratio = max(0.2, float(sensor_reading) / max(float(threshold), 1e-6))
    overload_factor = min(1.35, 0.55 + 0.45 * ratio)
    pop_boost = min(0.22, math.log10(max(10, int(population_affected))) * 0.045)

    raw = (base * overload_factor + pop_boost) * 78.0
    score = round(min(99.9, max(5.0, raw)), 1)

    if score >= 82.0:
        tier = "CRITICAL"
    elif score >= 65.0:
        tier = "HIGH"
    elif score >= 45.0:
        tier = "MODERATE"
    else:
        tier = "LOW"
    return score, tier


SEED_UNITS = [
    ResponseUnit("UNIT-GRID-01", "POWER_GRID_OVERLOAD", "Sector Alpha"),
    ResponseUnit("UNIT-HYDRO-02", "FLOOD_SURGE", "Riverfront Delta"),
    ResponseUnit("UNIT-MED-03", "MEDICAL_EMERGENCY", "Central District"),
    ResponseUnit("UNIT-CHEM-04", "WATER_QUALITY_DROP", "East Reservoir"),
]

SEED_INCIDENTS = [
    ("Sector Alpha", "POWER_GRID_OVERLOAD", 142.0, 100.0, 12500),
    ("Riverfront Delta", "FLOOD_SURGE", 4.6, 3.2, 8400),
    ("East Reservoir", "WATER_QUALITY_DROP", 7.8, 5.0, 19200),
]


class PulseGridDispatchEngine:
    """Coordinates incident scoring, optimal unit dispatch, and resolution audit logs."""

    def __init__(self) -> None:
        self.units: dict[str, ResponseUnit] = {
            u.unit_id: ResponseUnit(**asdict(u)) for u in SEED_UNITS
        }
        self.incidents: dict[str, CivicIncident] = {}
        self.dispatch_log: list[dict[str, Any]] = []

        for zone, hazard, reading, thresh, pop in SEED_INCIDENTS:
            self.ingest_incident(zone, hazard, reading, thresh, pop)

    def ingest_incident(
        self,
        zone: str,
        hazard_type: str,
        sensor_reading: float,
        threshold: float,
        population_affected: int,
    ) -> CivicIncident:
        """Score and register a new civic telemetry or citizen incident."""
        clean_zone = (zone or "").strip()
        clean_hazard = (hazard_type or "").strip().upper()
        if not clean_zone or not clean_hazard:
            raise ValueError("Both 'zone' and 'hazard_type' are required.")
        if sensor_reading <= 0 or threshold <= 0 or population_affected < 0:
            raise ValueError("Sensor reading and threshold must be positive.")

        score, tier = compute_severity_score(
            clean_hazard, sensor_reading, threshold, population_affected
        )
        inc_id = f"inc_{len(self.incidents) + 1:03d}"
        now = round(time.time(), 3)
        ev_hash = "0x" + hashlib.sha256(
            f"{inc_id}:{clean_zone}:{clean_hazard}:{sensor_reading}:{now}".encode("utf-8")
        ).hexdigest()[:20]

        inc = CivicIncident(
            incident_id=inc_id,
            zone=clean_zone,
            hazard_type=clean_hazard,
            sensor_reading=round(float(sensor_reading), 2),
            threshold=round(float(threshold), 2),
            population_affected=int(population_affected),
            severity_score=score,
            priority_tier=tier,
            assigned_unit=None,
            status="OPEN",
            evidence_hash=ev_hash,
            created_at=now,
        )
        self.incidents[inc_id] = inc
        self.dispatch_log.append(
            {
                "seq": len(self.dispatch_log) + 1,
                "event": "INCIDENT_SCORED",
                "incidentId": inc_id,
                "detail": f"[{tier} {score}] {clean_hazard} at {clean_zone} ({population_affected} residents).",
                "timestamp": now,
            }
        )
        return inc

    def auto_dispatch(self, incident_id: str) -> CivicIncident:
        """Assign the best available specialty/zone response unit to an OPEN incident."""
        if incident_id not in self.incidents:
            raise ValueError(f"Unknown incident_id: {incident_id}")
        inc = self.incidents[incident_id]
        if inc.status != "OPEN":
            raise ValueError(f"Incident {incident_id} is already {inc.status}.")

        available = [u for u in self.units.values() if u.available]
        if not available:
            raise ValueError("No available response units at this moment.")

        def rank_unit(u: ResponseUnit) -> tuple[int, int]:
            spec_match = 1 if u.specialty == inc.hazard_type else 0
            zone_match = 1 if u.zone.lower() == inc.zone.lower() else 0
            return (spec_match * 2 + zone_match, -u.dispatches_completed)

        best = max(available, key=rank_unit)
        best.available = False
        best.dispatches_completed += 1
        inc.assigned_unit = best.unit_id
        inc.status = "DISPATCHED"

        self.dispatch_log.append(
            {
                "seq": len(self.dispatch_log) + 1,
                "event": "UNIT_DISPATCHED",
                "incidentId": inc.incident_id,
                "detail": f"Assigned {best.unit_id} ({best.specialty}) to {inc.zone}.",
                "timestamp": round(time.time(), 3),
            }
        )
        return inc

    def resolve_incident(self, incident_id: str) -> CivicIncident:
        """Mark a dispatched incident as resolved and release its response unit."""
        if incident_id not in self.incidents:
            raise ValueError(f"Unknown incident_id: {incident_id}")
        inc = self.incidents[incident_id]
        if inc.status != "DISPATCHED":
            raise ValueError("Incident must be DISPATCHED before resolving.")
        if inc.assigned_unit and inc.assigned_unit in self.units:
            self.units[inc.assigned_unit].available = True
        inc.status = "RESOLVED"
        self.dispatch_log.append(
            {
                "seq": len(self.dispatch_log) + 1,
                "event": "INCIDENT_RESOLVED",
                "incidentId": inc.incident_id,
                "detail": f"Resolved {inc.incident_id}; released {inc.assigned_unit}.",
                "timestamp": round(time.time(), 3),
            }
        )
        return inc

    def get_state(self) -> dict[str, Any]:
        """Return prioritized incidents, response unit readiness, and audit log."""
        ordered = sorted(
            self.incidents.values(),
            key=lambda x: (x.status == "OPEN", x.severity_score),
            reverse=True,
        )
        return {
            "metrics": {
                "openCount": sum(1 for i in self.incidents.values() if i.status == "OPEN"),
                "dispatchedCount": sum(1 for i in self.incidents.values() if i.status == "DISPATCHED"),
                "resolvedCount": sum(1 for i in self.incidents.values() if i.status == "RESOLVED"),
                "unitsReady": sum(1 for u in self.units.values() if u.available),
            },
            "incidents": [asdict(i) for i in ordered],
            "units": [asdict(u) for u in self.units.values()],
            "dispatchLog": list(reversed(self.dispatch_log[-15:])),
        }
