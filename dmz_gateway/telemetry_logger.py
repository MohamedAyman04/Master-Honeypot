"""
DMZ Secure OT Access Gateway - Telemetry & Narrative Logger Integration
"""
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

def log_event_to_story(event_type, message, severity="info", details=None):
    """Submits a narrative event to story_logger for general logs.jsonl and Grafana correlation."""
    dt = details or {}
    src_ip = dt.get("ip", "0.0.0.0")
    payload = {
        "sensor": "dmz_gateway",
        "level": "Level 3.5",
        "event_type": event_type,
        "src_ip": src_ip,
        "stage": "S1",
        "outcome": "blocked" if severity.lower() in ("warning", "critical", "failed") else "observed",
        "severity": severity.upper(),
        "meta": {
            "component": "dmz_gateway",
            "message": message,
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
    Logs structured security telemetry to InfluxDB measurement: honeypot_attacker_telemetry.
    Directly powers unsupervised LSTM-Autoencoder anomaly profiling and behavioral clustering.
    """
    is_anomaly = 1 if actor_type == "attacker" else 0
    clean_tactic = str(tactic).replace(" ", "_").replace(",", "_")

    # Method 1: Client library if available
    write_api = get_influx_api()
    if write_api:
        try:
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
                .time(time.time_ns(), WritePrecision.NS)
            )
            write_api.write(bucket=config.INFLUX_BUCKET, record=point)
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
