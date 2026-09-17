"""
l2_bridge.py — Level 3 → Level 2 Data Bridge
==============================================
Consumed by Level 3 workstation routes to pull live physics data and
security alerts from the Level 2 physics REST API and historian API.

Cross-layer integration flow:
  L3 Workstation (historian-workstation)
    → HTTP GET  http://172.28.0.10:5100/api/physics/metrics  (Level 2 physics)
    → HTTP GET  http://172.28.0.10:5001/api/alerts           (Level 2 historian_api)
    → HTTP POST http://172.28.0.10:5001/api/external-event   (push L3 events to L2)

ATT&CK Technique surfaced by this bridge:
  T0802 — Automated Collection:
    The OPC-UA server and workstations continuously pull live data from L2.
    An attacker who compromises this endpoint can inject false readings
    into the L3 view without touching L2 directly (Loss of View).

Modularity note:
  LEVEL2_PHYSICS_URL and LEVEL2_HISTORIAN_URL are environment-variable
  driven, so swapping the L2 backend (e.g., to a real Modbus → REST
  adapter) requires only a config change, not code changes.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

# ── Configuration (env-driven for easy swapping) ───────────────────────────────
# Points at the l2l3-bridge-net IP assigned to ics_scada_ssh (physics API)
LEVEL2_PHYSICS_URL   = os.environ.get(
    "LEVEL2_PHYSICS_URL",
    "http://172.28.0.10:5100",        # default: ics_scada_ssh physics API
)
# Points at the l2l3-bridge-net IP assigned to historian_api (alerts + summary)
LEVEL2_HISTORIAN_URL = os.environ.get(
    "LEVEL2_HISTORIAN_URL",
    "http://172.28.0.10:5001",        # default: ics_historian_api
)
LEVEL2_SHARED_TOKEN  = os.environ.get("LEVEL2_SHARED_TOKEN", "change-this-token")
LEVEL2_TIMEOUT       = float(os.environ.get("LEVEL2_TIMEOUT", "3.0"))

# ── Request headers for bridge-to-bridge calls ─────────────────────────────────
_BRIDGE_HEADERS = {
    "X-Bridge-Token": LEVEL2_SHARED_TOKEN,
    "User-Agent":     "L3-Workstation-Bridge/1.0",
}


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None) -> dict | None:
    """
    Perform a GET request against a Level 2 service.

    Returns the parsed JSON dict on success, or None on any failure
    (connection refused, timeout, bad JSON, etc.).
    """
    try:
        resp = requests.get(
            url,
            params=params,
            headers=_BRIDGE_HEADERS,
            timeout=LEVEL2_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _post(url: str, body: dict) -> dict | None:
    """
    Perform a POST request against a Level 2 service.

    Returns the parsed JSON response or None on failure.
    """
    try:
        resp = requests.post(
            url,
            json=body,
            headers={**_BRIDGE_HEADERS, "Content-Type": "application/json"},
            timeout=LEVEL2_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def get_physics_metrics() -> dict[str, Any]:
    """
    Pull live process telemetry from the Level 2 physics REST API.

    Returns a dict with keys:
      pressure, temperature, flow_rate, valve_pos, pump_rpm, viscosity, timestamp

    Falls back to a static "disconnected" payload if the bridge is down.
    This ensures the L3 dashboard always renders — even during L2 outages.
    """
    data = _get(f"{LEVEL2_PHYSICS_URL}/api/physics/metrics")
    if data:
        return data

    # Fallback — static disconnected state for graceful degradation
    return {
        "pressure":    None,
        "temperature": None,
        "flow_rate":   None,
        "valve_pos":   None,
        "pump_rpm":    None,
        "viscosity":   None,
        "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "_bridge_error": "Level 2 physics API unreachable",
    }


def get_physics_status() -> dict[str, Any]:
    """
    Pull the high-level system status from the Level 2 physics API.

    Returns:
      { "system": "PUMP_STATION_01", "status": "RUNNING", "valve": "OPEN",
        "alerts": [], "timestamp": "..." }
    """
    data = _get(f"{LEVEL2_PHYSICS_URL}/api/physics/status")
    if data:
        return data
    return {
        "system":  "PUMP_STATION_01",
        "status":  "DISCONNECTED",
        "valve":   "UNKNOWN",
        "alerts":  ["BRIDGE_OFFLINE"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "_bridge_error": "Level 2 physics API unreachable",
    }


def get_l2_alerts(lookback: str = "-1h", limit: int = 50) -> list[dict]:
    """
    Pull recent security alerts from the Level 2 historian API.

    Parameters
    ----------
    lookback : InfluxDB range string, e.g. ``"-1h"`` or ``"-30m"``
    limit    : max number of alert records to return

    Returns a list of alert dicts (possibly empty on bridge failure).
    """
    data = _get(
        f"{LEVEL2_HISTORIAN_URL}/api/alerts",
        params={"lookback": lookback, "limit": limit},
    )
    if data:
        return data.get("alerts", [])
    return []


def get_l2_summary() -> dict[str, Any]:
    """
    Pull the high-level dashboard summary from the Level 2 historian API.

    This is the primary data source for the L3 workstation dashboard.
    Includes:
      - total_alerts, alert_breakdown, latest_alert
      - physical_process (pressure / temp / flow / RPM)
      - ml_engine_ready

    Falls back to an empty skeleton on bridge failure.
    """
    data = _get(f"{LEVEL2_HISTORIAN_URL}/api/summary")
    if data:
        return data
    return {
        "total_alerts":     0,
        "alert_breakdown":  {},
        "latest_alert":     None,
        "physical_process": get_physics_metrics(),   # try direct physics API
        "ml_engine_ready":  False,
        "_bridge_error":    "Level 2 historian API unreachable",
    }


def push_event_to_l2(
    event_type: str,
    source: str,
    detail: str,
    severity: str = "MEDIUM",
) -> bool:
    """
    Push a Level 3 security event into the Level 2 historian (InfluxDB).

    This creates a cross-layer audit trail: L3 workstation detects something
    suspicious and records it into the shared historian so the ML engine
    can correlate across layers.

    Parameters
    ----------
    event_type : canonical event type string (e.g. ``"L3_INTRUSION_DETECTED"``)
    source     : originating L3 service (e.g. ``"historian-workstation"``)
    detail     : human-readable description
    severity   : ``"LOW"`` / ``"MEDIUM"`` / ``"HIGH"`` / ``"CRITICAL"``

    Returns True if the historian accepted the event.
    """
    resp = _post(
        f"{LEVEL2_HISTORIAN_URL}/api/external-event",
        body={
            "event_type": event_type,
            "source":     source,
            "detail":     detail,
            "severity":   severity,
        },
    )
    return resp is not None and resp.get("status") == "ok"


def send_control_command(pump_rpm: float | None = None, valve_pos: float | None = None) -> dict:
    """
    Send an actuator control command to the Level 2 physics API.

    !! NOTE — this is intentionally unauthenticated on the L2 side (honeynet design). !!
    This function is here so that a compromised Level 3 workstation can demonstrate
    the full cross-layer attack path:

      L3 Workstation (compromised) → POST /api/physics/control → L2 Physics Engine
      ATT&CK: T0855 — Unauthorized Command Message

    Parameters
    ----------
    pump_rpm  : new pump speed in RPM (0–3000); None to leave unchanged
    valve_pos : new valve position (0.0–1.0); None to leave unchanged

    Returns the response dict from the physics API.
    """
    body: dict = {}
    if pump_rpm is not None:
        body["pump_rpm"] = pump_rpm
    if valve_pos is not None:
        body["valve_pos"] = valve_pos

    resp = _post(f"{LEVEL2_PHYSICS_URL}/api/physics/control", body=body)
    return resp or {"error": "Level 2 physics API unreachable or rejected command"}
