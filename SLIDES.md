# PulseGrid Civic AI — HackOdisha 6.0 Pitch Deck

## Slide 1: PulseGrid Civic AI: Emergency Triage & Dispatch
*Real-Time Multi-Sensor Severity Scoring & Automated Response Routing*

- **Problem**: Urban power, flood, and medical alerts arrive simultaneously without unified triage.
- **Solution**: Severity-weighted scoring + specialty/zone-matched unit dispatch & audit logs.
- **Verified Reliability**: 3/3 unit/API tests passing with zero-dependency Python + web dashboard.

## Slide 2: Architecture & Operational Lifecycle
*From Ingestion to Resolution with Deterministic Evidence Hashing*

- **1. Telemetry Scoring**: Computes [0..100] CRITICAL/HIGH/MODERATE/LOW priority via hazard & population.
- **2. Smart Dispatch**: Matches available unit specialty and zone while balancing active workload.
- **3. Full Auditability**: Logs SHA-256 evidence hashes for every triage, dispatch, and resolution event.
