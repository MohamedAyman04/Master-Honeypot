"""
story_logger/app.py
====================
Central narrative log endpoint.  Every honeynet component posts events here.
Enrichment is applied automatically so that ALL entries in general logs.jsonl
have consistent severity + MITRE ATT&CK fields — whether the event came from
the attack_suite.py script or a student typing raw commands in the attacker
node terminal.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request
from contract.validate import ensure_valid_event

app = Flask(__name__)

# Default to story.jsonl as per combined_config.yaml
LOG_PATH = os.environ.get("STORY_LOG_PATH", "/repo/story.jsonl")


# ── MITRE ATT&CK + Severity enrichment table ──────────────────────────────────
# Maps event_type → (severity, mitre_technique_id, mitre_technique_name,
#                     mitre_tactic, kill_chain_stage, purdue_level, protocol)
_MITRE_TABLE: dict[str, tuple] = {
    # ── Attack-suite phase markers ────────────────────────────────────────────
    "kill_chain_started":   ("INFO",     "T0000", "Kill Chain Start",            "N/A",                   "Stage 0 - Initiation",      "External", "N/A"),
    "kill_chain_completed": ("INFO",     "T0000", "Kill Chain Complete",          "N/A",                   "Stage 0 - Initiation",      "External", "N/A"),
    "phase_started":        ("INFO",     "T0000", "Attack Phase Start",           "N/A",                   "Stage 0 - Initiation",      "External", "N/A"),
    "phase_completed":      ("INFO",     "T0000", "Attack Phase Complete",        "N/A",                   "Stage 0 - Initiation",      "External", "N/A"),
    "phase_failed":         ("MEDIUM",   "T0000", "Attack Phase Failed",          "N/A",                   "Stage 0 - Initiation",      "External", "N/A"),

    # ── Reconnaissance ────────────────────────────────────────────────────────
    "NETWORK_SCAN":         ("MEDIUM",   "T1595",  "Active Scanning",             "Reconnaissance",        "Stage 1 - IT Intrusion",    "Level 2",  "TCP"),
    "DISCOVERY":            ("MEDIUM",   "T0846",  "Remote System Discovery",     "Reconnaissance",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),
    "API_ACCESS":           ("MEDIUM",   "T0883",  "Internet Accessible Device",  "Reconnaissance",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),
    "S7COMM_PROBE":         ("HIGH",     "T0846",  "Network Service Discovery",   "Discovery",             "Stage 1 - IT Intrusion",    "Level 2",  "S7comm"),
    "DNP3_PROBE":           ("HIGH",     "T0846",  "Network Service Discovery",   "Discovery",             "Stage 1 - IT Intrusion",    "Level 1",  "DNP3"),
    "recon_scan":           ("MEDIUM",   "T1595",  "Active Scanning",             "Reconnaissance",        "Stage 1 - IT Intrusion",    "Level 2",  "TCP"),

    # ── Initial access / credential attacks ───────────────────────────────────
    "AUTH_ATTEMPT":         ("HIGH",     "T1078",  "Valid Accounts",              "Lateral Movement",      "Stage 1 - IT Intrusion",    "Level 3",  "SSH"),
    "ssh_login":            ("HIGH",     "T0886",  "Remote Services",             "Lateral Movement",      "Stage 1 - IT Intrusion",    "Level 3",  "SSH"),
    "ssh_brute_force":      ("HIGH",     "T1110",  "Brute Force",                 "Credential Access",     "Stage 1 - IT Intrusion",    "Level 3",  "SSH"),
    "sql_injection":        ("CRITICAL", "T1190",  "Exploit Public-Facing App",   "Initial Access",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),
    "SQL_INJECTION":        ("CRITICAL", "T1190",  "Exploit Public-Facing App",   "Initial Access",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),
    "API_EXPLOIT":          ("CRITICAL", "T1190",  "Exploit Public-Facing App",   "Initial Access",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),
    "web_recon":            ("MEDIUM",   "T1595",  "Active Scanning",             "Reconnaissance",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),
    "dir_brute_force":      ("MEDIUM",   "T1595",  "Active Scanning",             "Reconnaissance",        "Stage 1 - IT Intrusion",    "Level 3",  "HTTP"),

    # ── Lateral movement ──────────────────────────────────────────────────────
    "LATERAL_MOVEMENT":     ("CRITICAL", "T0885",  "Remote Services",             "Lateral Movement",      "Stage 1 - IT Intrusion",    "Level 3",  "SSH"),
    "lateral_movement":     ("CRITICAL", "T0885",  "Remote Services",             "Lateral Movement",      "Stage 1 - IT Intrusion",    "Level 3",  "SSH"),
    "pivot_ssh":            ("CRITICAL", "T0885",  "Remote Services",             "Lateral Movement",      "Stage 2 - ICS Impact",      "Level 2",  "SSH"),
    "privilege_escalation": ("CRITICAL", "T1078",  "Valid Accounts",              "Privilege Escalation",  "Stage 2 - ICS Impact",      "Level 2",  "SSH"),
    "cred_leak_exfil":      ("CRITICAL", "T0891",  "Credentials in Files",        "Credential Access",     "Stage 1 - IT Intrusion",    "Level 3",  "SSH"),

    # ── ICS / OT attacks ──────────────────────────────────────────────────────
    "MODBUS_WRITE":         ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "MODBUS_READ":          ("MEDIUM",   "T0802",  "Automated Collection",        "Collection",            "Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "modbus_write":         ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "modbus_read":          ("MEDIUM",   "T0802",  "Automated Collection",        "Collection",            "Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "forced_write":         ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "write_command":        ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "actuator_hijack":      ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    "valve_control":        ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),

    # ── ML-engine detections ──────────────────────────────────────────────────
    "detection_alert":      ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "SEMANTIC_INJECTION":   ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "REPLAY_ATTACK":        ("CRITICAL", "T0856",  "Spoof Reporting Message",     "Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    "STEALTH_DRIFT":        ("CRITICAL", "T0836",  "Modify Parameter",            "Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    "CROSS_LAYER_ANOMALY":  ("HIGH",     "T0820",  "Exploitation for Evasion",    "Evasion",               "Stage 2 - ICS Impact",      "Level 2",  "Modbus"),
    "OVER_PRESSURE":        ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    "replay_attack":        ("CRITICAL", "T0856",  "Spoof Reporting Message",     "Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    "stealth_drift":        ("CRITICAL", "T0836",  "Modify Parameter",            "Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),

    # ── Physics / process anomalies ───────────────────────────────────────────
    "PHYSICS_CONTROL_CMD":  ("CRITICAL", "T0855",  "Unauthorized Command Message","Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    "process_anomaly":      ("HIGH",     "T0836",  "Modify Parameter",            "Impair Process Control","Stage 2 - ICS Impact",      "Level 1",  "Modbus"),
    # ── Miscellaneous ─────────────────────────────────────────────────────────
    "MITRE_STEP":           ("INFO",     "T0000", "MITRE ATT&CK Step",           "Attack",                "Stage 1 - IT Intrusion",    "Level 2",  "N/A"),
    "kill_chain_phase":     ("INFO",     "T0000", "Kill Chain Phase",            "N/A",                   "Stage 0 - Initiation",      "External", "N/A"),
}

_UNKNOWN_SEVERITY = "INFO"
_UNKNOWN_MITRE = ("T0000", "Unknown Technique", "Unknown", "Unknown", "Unknown", "Unknown")


def _enrich(event: dict) -> dict:
    """
    Inject severity + MITRE ATT&CK fields into every event.
    If the event already has severity set (not None/missing), keep it.
    MITRE fields are always recomputed from the table unless explicitly provided in meta.
    """
    event_type = event.get("event_type", "")
    meta = event.get("meta", {})

    # Also check meta.alert_type as a secondary key (used by ML engine)
    lookup_key = event_type
    if lookup_key not in _MITRE_TABLE:
        alert_type = meta.get("alert_type", "")
        if alert_type in _MITRE_TABLE:
            lookup_key = alert_type

    entry = _MITRE_TABLE.get(lookup_key)
    if entry:
        sev, tid, tname, tactic, kc_stage, purdue, protocol = entry
    else:
        sev = _UNKNOWN_SEVERITY
        tid, tname, tactic, kc_stage, purdue, protocol = _UNKNOWN_MITRE

    # Allow meta to override table values (useful for generic MITRE_STEP)
    tid = meta.get("mitre_technique_id") or tid
    tname = meta.get("mitre_technique_name") or tname
    tactic = meta.get("mitre_tactic") or tactic
    kc_stage = meta.get("kill_chain_stage") or kc_stage
    purdue = meta.get("purdue_level") or purdue
    protocol = meta.get("protocol") or protocol

    # Only set severity if not already present (allow callers to override)
    if not event.get("severity"):
        event["severity"] = meta.get("severity") or sev

    # Always write MITRE fields for consistency
    event["mitre_technique_id"] = tid
    event["mitre_technique_name"] = tname
    event["mitre_tactic"] = tactic
    event["kill_chain_stage"] = kc_stage
    event["purdue_level"] = purdue
    event["protocol"] = protocol

    return event


# ── Helpers ───────────────────────────────────────────────────────────────────
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _generate_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nonce = uuid.uuid4().hex[:6]
    return f"{ts}_{nonce}"


def _ensure_log_dir() -> None:
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)


def _append_event(record: dict) -> None:
    _ensure_log_dir()
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + "\n")


def _map_to_new_schema(payload: dict) -> dict:
    """
    Maps old schema fields to the new contract defined in schema.py.
    Old: timestamp, component, event_type, level, run_id, message, severity, details
    New: ts, sensor, event_type, src_ip, stage, journey_id, outcome, meta
    """
    # If it's already using the new schema, pass through (minimal check)
    if "ts" in payload and "sensor" in payload and "journey_id" in payload:
        event = dict(payload)
    else:
        # Mapping from old schema
        event = {
            "ts":         payload.get("ts") or payload.get("timestamp") or _utc_now(),
            "sensor":     payload.get("sensor") or payload.get("component") or "unknown",
            "event_type": payload.get("event_type") or "unknown_event",
            "src_ip":     payload.get("src_ip") or payload.get("details", {}).get("src_ip") or "0.0.0.0",
            "stage":      payload.get("stage") or payload.get("details", {}).get("stage") or "S1",
            "journey_id": payload.get("journey_id") or payload.get("run_id") or _generate_run_id(),
            "outcome":    payload.get("outcome") or "observed",
            "meta":       payload.get("meta") or payload.get("details") or {},
        }
        # Add message to meta if it exists and isn't already there
        if "message" in payload and "message" not in event["meta"]:
            event["meta"]["message"] = payload["message"]

    # Promote `level` from meta to top-level for consistent filtering
    if "level" not in event and "level" in event.get("meta", {}):
        event["level"] = event["meta"]["level"]

    # Carry through severity if caller provided it at the top level
    if "severity" not in event and "severity" in payload:
        event["severity"] = payload["severity"]

    return event


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({"status": "ok", "log_path": LOG_PATH})


@app.post("/story/events")
def story_events():
    payload = request.get_json(silent=True) or {}

    try:
        # 1. Normalise to new schema (backward compat)
        mapped_event = _map_to_new_schema(payload)

        # 2. Validate against contract
        valid_event = ensure_valid_event(mapped_event)

        # 3. Enrich with severity + MITRE ATT&CK (always, for every event)
        enriched_event = _enrich(valid_event)

        # 4. Append to JSONL log
        _append_event(enriched_event)

        return jsonify({
            "status":     "ok",
            "journey_id": enriched_event["journey_id"],
            "ts":         enriched_event["ts"],
            "severity":   enriched_event.get("severity"),
        })

    except ValueError as e:
        print(f"Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        print(f"Internal error: {e}")
        return jsonify({"status": "error", "message": "internal error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8600"))
    app.run(host="0.0.0.0", port=port)
