const openPill = document.getElementById("openPill");
const unitsPill = document.getElementById("unitsPill");
const unitsList = document.getElementById("unitsList");
const logList = document.getElementById("logList");
const incidentsList = document.getElementById("incidentsList");

let staticState = {
  metrics: { openCount: 3, dispatchedCount: 0, resolvedCount: 0, unitsReady: 4 },
  incidents: [
    { incident_id: "inc_001", zone: "Sector Alpha", hazard_type: "POWER_GRID_OVERLOAD", sensor_reading: 142, threshold: 100, population_affected: 12500, severity_score: 97.6, priority_tier: "CRITICAL", assigned_unit: null, status: "OPEN" },
    { incident_id: "inc_002", zone: "Riverfront Delta", hazard_type: "FLOOD_SURGE", sensor_reading: 4.6, threshold: 3.2, population_affected: 8400, severity_score: 99.9, priority_tier: "CRITICAL", assigned_unit: null, status: "OPEN" },
  ],
  units: [
    { unit_id: "UNIT-GRID-01", specialty: "POWER_GRID_OVERLOAD", zone: "Sector Alpha", available: true },
    { unit_id: "UNIT-HYDRO-02", specialty: "FLOOD_SURGE", zone: "Riverfront Delta", available: true },
    { unit_id: "UNIT-MED-03", specialty: "MEDICAL_EMERGENCY", zone: "Central District", available: true },
  ],
  dispatchLog: [],
};

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function render(state) {
  const m = state.metrics || {};
  openPill.textContent = "Open: " + m.openCount + " · Dispatched: " + m.dispatchedCount + " · Resolved: " + m.resolvedCount;
  unitsPill.textContent = "Units Ready: " + m.unitsReady;

  unitsList.innerHTML = (state.units || []).map((u) => `
    <div class="item-box row-between">
      <span><strong>${esc(u.unit_id)}</strong> (${esc(u.specialty)})</span>
      <span class="${u.available ? "ok" : "muted"}">${u.available ? "READY" : "BUSY"}</span>
    </div>
  `).join("");

  incidentsList.innerHTML = (state.incidents || []).map((inc) => `
    <div class="item-box row-between">
      <div>
        <strong class="${inc.priority_tier === "CRITICAL" ? "crit" : "ok"}">[${esc(inc.priority_tier)} ${inc.severity_score}]</strong>
        <strong>${esc(inc.hazard_type)}</strong> · ${esc(inc.zone)} (${inc.population_affected} residents)
        <div class="muted">Reading ${inc.sensor_reading} / Threshold ${inc.threshold} · Status: ${esc(inc.status)} ${inc.assigned_unit ? "→ " + esc(inc.assigned_unit) : ""}</div>
      </div>
      <div>
        ${inc.status === "OPEN" ? '<button type="button" class="btn primary" data-disp="' + esc(inc.incident_id) + '">Auto-Dispatch</button>' : ""}
        ${inc.status === "DISPATCHED" ? '<button type="button" class="btn ok" data-res="' + esc(inc.incident_id) + '">Resolve</button>' : ""}
      </div>
    </div>
  `).join("");

  incidentsList.querySelectorAll("button[data-disp]").forEach((b) => {
    b.addEventListener("click", () => act("/api/dispatch", { incidentId: b.dataset.disp }));
  });
  incidentsList.querySelectorAll("button[data-res]").forEach((b) => {
    b.addEventListener("click", () => act("/api/resolve", { incidentId: b.dataset.res }));
  });

  logList.innerHTML = (state.dispatchLog || []).slice(0, 4).map((l) => `
    <div class="item-box muted">#${l.seq} · ${esc(l.event)}: ${esc(l.detail)}</div>
  `).join("");
}

async function load() {
  try {
    const r = await fetch("/api/state");
    const ct = r.headers.get("content-type") || "";
    if (r.ok && ct.includes("application/json")) staticState = await r.json();
  } catch {}
  render(staticState);
}

async function act(url, body) {
  try {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const ct = r.headers.get("content-type") || "";
    if (!ct.includes("application/json")) throw new Error("Static fallback");
    const d = await r.json();
    if (d.state) staticState = d.state;
  } catch {}
  render(staticState);
}

document.getElementById("ingestBtn").addEventListener("click", () => {
  act("/api/ingest", {
    zone: document.getElementById("zoneInput").value.trim(),
    hazardType: document.getElementById("hazardInput").value,
    sensorReading: Number(document.getElementById("readInput").value) || 120,
    threshold: Number(document.getElementById("threshInput").value) || 100,
    populationAffected: Number(document.getElementById("popInput").value) || 5000,
  });
});

load();
