"""
DMZ Secure OT Access Gateway - Telemetry & Narrative Logger Integration
"""
import os
import time
import json
import requests
from datetime import datetime
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None
    Point = None
    WritePrecision = None
    SYNCHRONOUS = None

try:
    from . import config
except (ImportError, ValueError):
    import config

_influx_client = None
_write_api = None

def get_influx_api():
    global _influx_client, _write_api
    if _write_api is None:
        try:
            _influx_client = InfluxDBClient(
                url=config.INFLUX_URL,
                token=config.INFLUX_TOKEN,
                org=config.INFLUX_ORG,
                timeout=2000
            )
            _write_api = _influx_client.write_api(write_options=SYNCHRONOUS)
        except Exception:
            _write_api = None
    return _write_api

def _resolve_mitre_metadata(tactic_str: str, reason: str, subpath: str = "") -> dict:
    """Parse DMZ Gateway tactic string and reason into full MITRE ATT&CK for ICS tags."""
    raw = f"{tactic_str} {reason} {subpath}".lower()
    if "t0855" in raw or "mbtget" in raw or "modbus" in raw or "control" in raw:
        return {
            "event_type": "MODBUS_WRITE",
            "severity": "CRITICAL",
            "layer": "Level 2",
            "purdue_level": "Level 2",
            "kill_chain_stage": "Stage 2 - ICS Impact",
            "mitre_tactic": "Impair Process Control",
            "mitre_technique_id": "T0855",
            "mitre_technique_name": "Unauthorized Command Message",
            "protocol": "Modbus",
        }
    if "s7" in raw or "snap7" in raw or "102" in raw:
        return {
            "event_type": "S7COMM_PROBE",
            "severity": "HIGH",
            "layer": "Level 2",
            "purdue_level": "Level 2",
            "kill_chain_stage": "Stage 2 - ICS Impact",
            "mitre_tactic": "Discovery",
            "mitre_technique_id": "T0846",
            "mitre_technique_name": "Network Service Discovery",
            "protocol": "S7comm",
        }
    if "dnp3" in raw or "20000" in raw:
        return {
            "event_type": "DNP3_PROBE",
            "severity": "HIGH",
            "layer": "Level 1",
            "purdue_level": "Level 1",
            "kill_chain_stage": "Stage 2 - ICS Impact",
            "mitre_tactic": "Discovery",
            "mitre_technique_id": "T0846",
            "mitre_technique_name": "Network Service Discovery",
            "protocol": "DNP3",
        }
    if "t0866" in raw or "ssh" in raw or "scp" in raw:
        return {
            "event_type": "LATERAL_MOVEMENT",
            "severity": "HIGH",
            "layer": "Level 2",
            "purdue_level": "Level 2",
            "kill_chain_stage": "Stage 1 - IT Intrusion",
            "mitre_tactic": "Lateral Movement",
            "mitre_technique_id": "T0886",
            "mitre_technique_name": "Remote Services",
            "protocol": "SSH",
        }
    if "t0846" in raw or any(k in raw for k in ("nmap", "ping", "netstat", "arp")):
        return {
            "event_type": "NETWORK_SCAN",
            "severity": "MEDIUM",
            "layer": "Level 2",
            "purdue_level": "Level 2",
            "kill_chain_stage": "Stage 1 - IT Intrusion",
            "mitre_tactic": "Discovery",
            "mitre_technique_id": "T0846",
            "mitre_technique_name": "Network Service Discovery",
            "protocol": "TCP",
        }
    if "t0802" in raw or any(k in raw for k in ("cat ", "/etc/hosts", "/etc/passwd", ".kdbx", ".pdf")):
        return {
            "event_type": "CREDENTIAL_DISCOVERY",
            "severity": "HIGH",
            "layer": "Level 3",
            "purdue_level": "Level 3",
            "kill_chain_stage": "Stage 1 - IT Intrusion",
            "mitre_tactic": "Collection",
            "mitre_technique_id": "T0802",
            "mitre_technique_name": "Automated Collection",
            "protocol": "HTTP",
        }
    if "sql" in raw or "t1190" in raw or "injection" in raw:
        return {
            "event_type": "SQL_INJECTION",
            "severity": "CRITICAL",
            "layer": "Level 3.5",
            "purdue_level": "Level 3.5",
            "kill_chain_stage": "Stage 1 - IT Intrusion",
            "mitre_tactic": "Initial Access",
            "mitre_technique_id": "T1190",
            "mitre_technique_name": "Exploit Public-Facing Application",
            "protocol": "HTTP",
        }
    if "t1110" in raw or "rockyou" in raw or "password" in raw or "brute" in raw or "mfa" in raw:
        return {
            "event_type": "AUTH_ATTEMPT",
            "severity": "HIGH",
            "layer": "Level 3.5",
            "purdue_level": "Level 3.5",
            "kill_chain_stage": "Stage 1 - IT Intrusion",
            "mitre_tactic": "Credential Access",
            "mitre_technique_id": "T1110.001",
            "mitre_technique_name": "Password Guessing",
            "protocol": "HTTP",
        }
    if "t1059" in raw or "terminal" in raw or "cmd:" in raw:
        return {
            "event_type": "TERMINAL_CMD",
            "severity": "MEDIUM",
            "layer": "Level 3",
            "purdue_level": "Level 3",
            "kill_chain_stage": "Stage 1 - IT Intrusion",
            "mitre_tactic": "Execution",
            "mitre_technique_id": "T1059",
            "mitre_technique_name": "Command and Scripting Interpreter",
            "protocol": "HTTP",
        }
    return {
        "event_type": "DISCOVERY",
        "severity": "INFO",
        "layer": "Level 3",
        "purdue_level": "Level 3",
        "kill_chain_stage": "Stage 1 - IT Intrusion",
        "mitre_tactic": "Reconnaissance",
        "mitre_technique_id": "T1082",
        "mitre_technique_name": "System Information Discovery",
        "protocol": "HTTP",
    }

def log_event_to_story(event_type, message, severity="info", details=None):
    """Submits a narrative event to story_logger for general logs.jsonl and Grafana correlation."""
    dt = details or {}
    src_ip = dt.get("ip", "0.0.0.0")
    mitre = _resolve_mitre_metadata(dt.get("tactic", ""), message, dt.get("subpath", ""))
    sev = mitre["severity"] if severity.lower() in ("warning", "info") else severity.upper()
    if sev == "WARNING":
        sev = "HIGH"
    payload = {
        "sensor": "portal",
        "level": mitre["purdue_level"],
        "event_type": mitre["event_type"],
        "src_ip": src_ip,
        "stage": "S2" if "Stage 2" in mitre["kill_chain_stage"] else "S1",
        "journey_id": os.getenv("STORY_RUN_ID", "master_run_01"),
        "outcome": "blocked" if sev in ("HIGH", "CRITICAL") else "observed",
        "severity": sev,
        "meta": {
            "component": "dmz_gateway",
            "message": message,
            "mitre_tactic": mitre["mitre_tactic"],
            "mitre_technique_id": mitre["mitre_technique_id"],
            "mitre_technique_name": mitre["mitre_technique_name"],
            "kill_chain_stage": mitre["kill_chain_stage"],
            "purdue_level": mitre["purdue_level"],
            "protocol": mitre["protocol"],
            **dt
        }
    }
    try:
        requests.post(
            f"{config.STORY_LOGGER_URL}/story/events",
            json=payload,
            timeout=1.0
        )
    except Exception:
        pass

def log_routing_telemetry(src_ip, user_agent, username, routing_world, actor_type, tactic="None", reason="Normal"):
    """
    Logs structured security telemetry to InfluxDB measurements:
      1. honeypot_attacker_telemetry (DMZ Gateway dashboard)
      2. security_alerts (MITRE ATT&CK for ICS Attack Story dashboard)
    """
    is_anomaly = 1 if actor_type == "attacker" else 0
    clean_tactic = str(tactic).replace(" ", "_").replace(",", "_")
    mitre = _resolve_mitre_metadata(str(tactic), str(reason))
    session_id = os.getenv("STORY_RUN_ID", "master_run_01")

    # Method 1: Client library if available
    write_api = get_influx_api()
    if write_api:
        try:
            ts_now = time.time_ns()
            point = (
                Point("honeypot_attacker_telemetry")
                .tag("device", "dmz_gateway")
                .tag("src_ip", src_ip)
                .tag("actor_type", actor_type)
                .tag("routing_world", routing_world)
                .tag("tactic", clean_tactic)
                .tag("username", username or "anonymous")
                .field("is_anomaly", is_anomaly)
                .field("reason", reason)
                .field("user_agent", (user_agent or "")[:120])
                .field("dwell_count", 1)
                .time(ts_now, WritePrecision.NS)
            )
            records = [point]
            if is_anomaly == 1:
                alert_pt = (
                    Point("security_alerts")
                    .tag("event_type", mitre["event_type"])
                    .tag("alert_type", mitre["event_type"])
                    .tag("service", "dmz_gateway")
                    .tag("layer", mitre["layer"])
                    .tag("severity", mitre["severity"])
                    .tag("session_id", session_id)
                    .tag("source_ip", src_ip)
                    .tag("mitre_tactic", mitre["mitre_tactic"])
                    .tag("mitre_technique_id", mitre["mitre_technique_id"])
                    .tag("mitre_technique_name", mitre["mitre_technique_name"])
                    .tag("kill_chain_stage", mitre["kill_chain_stage"])
                    .tag("purdue_level", mitre["purdue_level"])
                    .tag("protocol", mitre["protocol"])
                    .field("source_ip", src_ip)
                    .field("narrative", f"[{mitre['layer']}] {reason} (User: {username or 'anon'}, IP: {src_ip})")
                    .field("detail", reason)
                    .field("value", 1.0)
                    .field("score", 1.0)
                    .time(ts_now, WritePrecision.NS)
                )
                records.append(alert_pt)
            write_api.write(bucket=config.INFLUX_BUCKET, record=records)
            return
        except Exception:
            pass

    # Method 2: Direct InfluxDB HTTP v2 Line Protocol
    try:
        line = f'honeypot_attacker_telemetry,device=dmz_gateway,src_ip={src_ip},actor_type={actor_type},routing_world={routing_world},tactic={clean_tactic} is_anomaly={is_anomaly}i,reason="{reason}",dwell_count=1i'
        requests.post(
            f"{config.INFLUX_URL}/api/v2/write?org={config.INFLUX_ORG}&bucket={config.INFLUX_BUCKET}&precision=s",
            headers={"Authorization": f"Token {config.INFLUX_TOKEN}"},
            data=line,
            timeout=1.0
        )
    except Exception:
        pass
    except Exception:
        pass
