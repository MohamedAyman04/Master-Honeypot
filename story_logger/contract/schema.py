from __future__ import annotations

REQUIRED_FIELDS = (
    "ts",
    "sensor",
    "event_type",
    "src_ip",
    "stage",
    "journey_id",
    "outcome",
    "meta",
)

ALLOWED_SENSORS = (
    "portal",
    "cowrie",
    "mssql",
    "conpot",
    "synthetic",
    "workstation",
    "historian",
    "opcua",
    "attacker_script",
    "attacker_node",
    "ml-engine",
)

ALLOWED_STAGES = (
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
)

ALLOWED_OUTCOMES = (
    "allowed",
    "blocked",
    "failed",
    "success",
    "observed",
    "unknown",
)

EXPECTED_TYPES = {
    "ts": str,
    "sensor": str,
    "event_type": str,
    "src_ip": str,
    "stage": str,
    "journey_id": str,
    "outcome": str,
    "meta": dict,
}
