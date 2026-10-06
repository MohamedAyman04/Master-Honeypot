"""
shared/mitre_mapping.py
=======================
Central MITRE ATT\u0026CK for ICS technique mapping table.

Consumed by:
  - logger/correlator.py   (network-layer events)
  - ml-engine/trainer.py   (ML anomaly events)

Each entry maps an internal event_type string to:
  mitre_tactic          – ATT\u0026CK for ICS tactic name
  mitre_technique_id    – Txxxx ID
  mitre_technique_name  – Human-readable technique name
  kill_chain_stage      – ICS Kill Chain stage
  purdue_level          – Purdue/ISA-95 level string
  protocol              – Network protocol involved (for dashboard filtering)

References:
  https://attack.mitre.org/matrices/ics/
  Assante \u0026 Lee, "The Industrial Control System Cyber Kill Chain" (SANS, 2015)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Master mapping table
# Key: internal event_type  (must match tags written by correlator / ml_engine)
# ---------------------------------------------------------------------------
TECHNIQUE_MAP: dict[str, dict[str, str]] = {

    # ── Modbus TCP (Level 1/2) ──────────────────────────────────────────────
    "write_command": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "modbus_write": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "modbus_read": {
        "mitre_tactic":         "Collection",
        "mitre_technique_id":   "T0802",
        "mitre_technique_name": "Automated Collection",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "credential_discovery": {
        "mitre_tactic":         "Credential Access",
        "mitre_technique_id":   "T1005",
        "mitre_technique_name": "Data from Local System",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },
    "lateral_movement": {
        "mitre_tactic":         "Lateral Movement",
        "mitre_technique_id":   "T0867",
        "mitre_technique_name": "Lateral Tool Transfer",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },
    "network_scan": {
        "mitre_tactic":         "Reconnaissance",
        "mitre_technique_id":   "T1595",
        "mitre_technique_name": "Active Scanning",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 4",
    },
    "terminal_cmd": {
        "mitre_tactic":         "Execution",
        "mitre_technique_id":   "T0807",
        "mitre_technique_name": "Command-Line Interface",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },
    "forced_write": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "replay_attack": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0856",
        "mitre_technique_name": "Spoof Reporting Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },

    # ── S7comm / Siemens (Level 2) ──────────────────────────────────────────
    "s7_connect": {
        "mitre_tactic":         "Initial Access",
        "mitre_technique_id":   "T0886",
        "mitre_technique_name": "Remote Services",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "S7comm",
        "detection_layer":      "Layer 1",
    },
    "s7_read": {
        "mitre_tactic":         "Collection",
        "mitre_technique_id":   "T0802",
        "mitre_technique_name": "Automated Collection",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "S7comm",
        "detection_layer":      "Layer 1",
    },
    "s7_write": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "S7comm",
        "detection_layer":      "Layer 1",
    },
    "s7_stop_cpu": {
        "mitre_tactic":         "Inhibit Response Function",
        "mitre_technique_id":   "T0816",
        "mitre_technique_name": "Device Restart/Shutdown",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "S7comm",
        "detection_layer":      "Layer 1",
    },

    # ── DNP3 (Level 1) ──────────────────────────────────────────────────────
    "dnp3_read": {
        "mitre_tactic":         "Collection",
        "mitre_technique_id":   "T0802",
        "mitre_technique_name": "Automated Collection",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "DNP3",
        "detection_layer":      "Layer 1",
    },
    "dnp3_write": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "DNP3",
        "detection_layer":      "Layer 1",
    },
    "dnp3_direct_operate": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "DNP3",
        "detection_layer":      "Layer 1",
    },
    "dnp3_unsolicited": {
        "mitre_tactic":         "Collection",
        "mitre_technique_id":   "T0802",
        "mitre_technique_name": "Automated Collection",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "DNP3",
        "detection_layer":      "Layer 1",
    },
    "S7COMM_PROBE": {
        "mitre_tactic":         "Discovery",
        "mitre_technique_id":   "T0846",
        "mitre_technique_name": "Network Service Discovery",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "S7comm",
        "detection_layer":      "Layer 1",
    },
    "DNP3_PROBE": {
        "mitre_tactic":         "Discovery",
        "mitre_technique_id":   "T0846",
        "mitre_technique_name": "Network Service Discovery",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "DNP3",
        "detection_layer":      "Layer 1",
    },

    # ── SSH / SCADA Workstation (Level 3) ───────────────────────────────────
    "ssh_login": {
        "mitre_tactic":         "Lateral Movement",
        "mitre_technique_id":   "T0812",
        "mitre_technique_name": "Default Credentials",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },
    "ssh_bruteforce": {
        "mitre_tactic":         "Lateral Movement",
        "mitre_technique_id":   "T0812",
        "mitre_technique_name": "Default Credentials",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },
    "ssh_command": {
        "mitre_tactic":         "Execution",
        "mitre_technique_id":   "T0807",
        "mitre_technique_name": "Command-Line Interface",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },
    "ssh_recon": {
        "mitre_tactic":         "Discovery",
        "mitre_technique_id":   "T0842",
        "mitre_technique_name": "Network Sniffing",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SSH",
        "detection_layer":      "Layer 2",
    },

    # ── ML-engine anomaly types ──────────────────────────────────────────────
    "ISOLATION_FOREST": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0806",
        "mitre_technique_name": "Brute Force I/O",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "LSTM_AUTOENCODER": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0856",
        "mitre_technique_name": "Spoof Reporting Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "REPLAY_LSTM": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0856",
        "mitre_technique_name": "Spoof Reporting Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },
    "SEMANTIC_INJECTION": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 1",
    },
    "CROSS_LAYER_ANOMALY": {
        "mitre_tactic":         "Evasion",
        "mitre_technique_id":   "T0820",
        "mitre_technique_name": "Exploitation for Evasion",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 2",
    },
    "STEALTH_DRIFT": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0836",
        "mitre_technique_name": "Modify Parameter",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },
    "OVER_PRESSURE": {
        "mitre_tactic":         "Damage to Property",
        "mitre_technique_id":   "T0828",
        "mitre_technique_name": "Loss of Safety",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 0",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },
    "DRIFT_ATTACK": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0836",
        "mitre_technique_name": "Modify Parameter",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },
    "ZERO_VARIANCE": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0856",
        "mitre_technique_name": "Spoof Reporting Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },
    "REPLAY_FINGERPRINT": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0856",
        "mitre_technique_name": "Spoof Reporting Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 2",
        "protocol":             "Modbus",
        "detection_layer":      "Layer 0",
    },

    # ── Multi-Layered Monitor Zone Detections ─────────────────────────────
    "lstm_ae_proc": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0831",
        "mitre_technique_name": "Manipulation of Control",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 0",
        "protocol":             "Process Dynamics",
        "detection_layer":      "Layer 0",
    },
    "lstm_ae_net": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 1",
        "protocol":             "Fieldbus Telemetry",
        "detection_layer":      "Layer 1",
    },
    "if_proc": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0836",
        "mitre_technique_name": "Modify Parameter",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 0",
        "protocol":             "Process Dynamics",
        "detection_layer":      "Layer 0",
    },
    "if_net": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0806",
        "mitre_technique_name": "Brute Force I/O",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 1",
        "protocol":             "Fieldbus Telemetry",
        "detection_layer":      "Layer 1",
    },
    "layer_0_detection": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0831",
        "mitre_technique_name": "Manipulation of Control",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 0",
        "protocol":             "Process Dynamics",
        "detection_layer":      "Layer 0",
    },
    "layer_1_detection": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Unauthorized Command Message",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Level 1",
        "protocol":             "Fieldbus Protocols",
        "detection_layer":      "Layer 1",
    },
    "layer_2_detection": {
        "mitre_tactic":         "Lateral Movement",
        "mitre_technique_id":   "T0886",
        "mitre_technique_name": "Remote Services",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 2",
        "protocol":             "SCADA / SSH",
        "detection_layer":      "Layer 2",
    },
    "layer_3_detection": {
        "mitre_tactic":         "Collection",
        "mitre_technique_id":   "T0809",
        "mitre_technique_name": "Data from Information Repositories",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 3",
        "protocol":             "Workstation API",
        "detection_layer":      "Layer 3",
    },
    "layer_4_detection": {
        "mitre_tactic":         "Initial Access",
        "mitre_technique_id":   "T0817",
        "mitre_technique_name": "Exploit Public-Facing Application",
        "kill_chain_stage":     "Stage 1 - IT Intrusion",
        "purdue_level":         "Level 3.5",
        "protocol":             "HTTP/S",
        "detection_layer":      "Layer 4",
    },
    "alert_fused": {
        "mitre_tactic":         "Impair Process Control",
        "mitre_technique_id":   "T0855",
        "mitre_technique_name": "Fused Multi-Layer Cyber-Physical Anomaly",
        "kill_chain_stage":     "Stage 2 - ICS Impact",
        "purdue_level":         "Cross-Layer",
        "protocol":             "Multi-Protocol",
        "detection_layer":      "Alert Fused",
    },
}

# Fallback for unknown event types
_UNKNOWN: dict[str, str] = {
    "mitre_tactic":         "Unknown",
    "mitre_technique_id":   "T0000",
    "mitre_technique_name": "Unknown Technique",
    "kill_chain_stage":     "Unknown",
    "purdue_level":         "Unknown",
    "protocol":             "Unknown",
    "detection_layer":      "Unknown",
}


def lookup(event_type: str) -> dict[str, str]:
    """
    Return the ATT\u0026CK metadata dict for *event_type*.
    Falls back to _UNKNOWN if the key is not in the table.
    The returned dict is a shallow copy — safe to mutate.
    All events are tagged Purdue Level 2 for this honeypot deployment.
    """
    key = event_type.lower() if isinstance(event_type, str) else event_type
    result = dict(TECHNIQUE_MAP.get(key, TECHNIQUE_MAP.get(event_type, _UNKNOWN)))
    result["purdue_level"] = "Level 2"
    return result


def enrich_point(point, event_type: str):
    """
    Add MITRE ATT\u0026CK tags to an InfluxDB-client Point object in-place.
    All five fields are added as *tags* (indexed, filterable) except none
    are omitted so that existing field queries continue to work unchanged.

    Usage:
        from shared.mitre_mapping import enrich_point
        p = Point("correlation_logs").tag(...).field(...)
        enrich_point(p, "write_command")
        write_api.write(bucket=BUCKET, record=p)
    """
    meta = lookup(event_type)
    (point
     .tag("mitre_tactic",          meta["mitre_tactic"])
     .tag("mitre_technique_id",    meta["mitre_technique_id"])
     .tag("mitre_technique_name",  meta["mitre_technique_name"])
     .tag("kill_chain_stage",      meta["kill_chain_stage"])
     .tag("purdue_level",          meta["purdue_level"])
     .tag("protocol",              meta["protocol"])
     .tag("detection_layer",      meta.get("detection_layer", "Layer 1")))
    return point
