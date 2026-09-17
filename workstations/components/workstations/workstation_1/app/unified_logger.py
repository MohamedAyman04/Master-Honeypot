"""
unified_logger.py — Cross-Layer Unified JSON Log Schema
========================================================
Provides a single, consistent JSON log format consumed by every component
across both Layer 3 (Enterprise/Operations) and Layer 2 (SCADA/Process).
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    _HAS_INFLUX = True
except ImportError:
    _HAS_INFLUX = False

SCHEMA_VERSION = "2.0"

_ATTACK_MAP = {
    # Layer 3 Events
    "DISCOVERY":               ("T0846", "Network Service Discovery", "Reconnaissance"),
    "SQL_INJECTION":           ("T1190", "Exploit Public-Facing Application", "Initial Access"),
    "API_ACCESS":              ("T0883", "Internet Accessible Device", "Reconnaissance"),
    
    # Cross-Layer Pivot
    "LATERAL_MOVEMENT":        ("T0885", "Remote Services", "Lateral Movement"),
    "AUTH_ATTEMPT":            ("T1078", "Valid Accounts", "Lateral Movement"),
    
    # Layer 2 Events
    "NETWORK_SCAN":            ("T1595", "Active Scanning", "Reconnaissance"),
    "MODBUS_WRITE":            ("T0855", "Unauthorized Command Message", "Actions on Objectives"),
    "MODBUS_READ":             ("T0802", "Automated Collection", "Reconnaissance"),
    "PHYSICS_CONTROL_CMD":     ("T0855", "Unauthorized Command Message", "Actions on Objectives"),
}

def _default_severity(event_type: str) -> str:
    if event_type in ("MODBUS_WRITE", "PHYSICS_CONTROL_CMD", "SQL_INJECTION"):
        return "CRITICAL"
    if event_type in ("LATERAL_MOVEMENT", "AUTH_ATTEMPT"):
        return "HIGH"
    return "INFO"

class UnifiedLogger:
    def __init__(
        self,
        service: str,
        layer: str,
        log_dir: str | Path = "/var/log/unified-logs",
        influx_url: str | None = None,
        influx_token: str | None = None,
        influx_org: str | None = None,
        influx_bucket: str | None = None,
    ):
        self.service = service
        self.layer = layer
        
        # Shared volume mounted by both L3 and L2 containers
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = log_dir / f"{service}_events.jsonl"

        self._write_api = None
        self.influx_bucket = influx_bucket or os.environ.get("INFLUX_BUCKET", "sensor_logs")
        if _HAS_INFLUX:
            _url   = influx_url   or os.environ.get("INFLUX_URL", "")
            _token = influx_token or os.environ.get("INFLUX_TOKEN", "")
            _org   = influx_org   or os.environ.get("INFLUX_ORG", "my_refinery")
            if _url and _token:
                try:
                    _client = InfluxDBClient(url=_url, token=_token, org=_org)
                    self._write_api = _client.write_api(write_options=SYNCHRONOUS)
                except Exception as exc:
                    print(f"[UNIFIED_LOGGER] InfluxDB init failed: {exc}")

    def log(
        self,
        event_type: str,
        source: dict[str, Any],
        target: dict[str, Any],
        correlation_id: str | None = None,
        severity: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict:
        mitre_id, mitre_name, kill_chain = _ATTACK_MAP.get(
            event_type, ("T0000", "Unknown", "Unknown")
        )
        
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "schema_version": SCHEMA_VERSION,
            "layer": self.layer,
            "service": self.service,
            "event_type": event_type,
            "severity": severity or _default_severity(event_type),
            "source_ip": source.get("ip", "unknown"),
            "target_ip": target.get("ip", "unknown"),
            "target_service": target.get("service", target.get("host", "unknown")),
            "mitre_technique": mitre_id,
            "kill_chain_phase": kill_chain,
            "source": source,
            "target": target,
            "mitre_ics": {
                "tactic": kill_chain,
                "technique": mitre_id,
                "name": mitre_name
            },
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "payload": payload or {}
        }

        # Write to JSONL file
        try:
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError as exc:
            print(f"[UNIFIED_LOGGER] File write error: {exc}")

        # Write to InfluxDB if available
        if self._write_api:
            try:
                point = (
                    Point("security_alerts")
                    .tag("event_type", event_type)
                    .tag("service", self.service)
                    .tag("layer", self.layer)
                    .tag("severity", record["severity"])
                    .tag("correlation_id", record["correlation_id"])
                    .field("source_ip", source.get("ip", "unknown"))
                    .field("target_ip", target.get("ip", "unknown"))
                    .time(time.time_ns(), WritePrecision.NS)
                )
                self._write_api.write(bucket=self.influx_bucket, record=point)
            except Exception:
                pass

        return record
