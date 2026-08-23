from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .schema import (
    ALLOWED_OUTCOMES,
    ALLOWED_SENSORS,
    ALLOWED_STAGES,
    EXPECTED_TYPES,
    REQUIRED_FIELDS,
)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]


def _parse_iso_timestamp(value: str) -> None:
    """
    Accept ISO-8601 timestamps and support trailing Z for UTC.
    Raises ValueError if the timestamp is invalid.
    """
    ts = value
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    datetime.fromisoformat(ts)


def validate_event(event: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []

    if not isinstance(event, dict):
        return ValidationResult(valid=False, errors=["event must be a dictionary"])

    missing_fields = [field for field in REQUIRED_FIELDS if field not in event]
    if missing_fields:
        errors.append(f"missing required fields: {missing_fields}")

    for field_name, expected_type in EXPECTED_TYPES.items():
        if field_name in event and not isinstance(event[field_name], expected_type):
            errors.append(
                f"field '{field_name}' must be of type {expected_type.__name__}, "
                f"got {type(event[field_name]).__name__}"
            )

    sensor = event.get("sensor")
    if isinstance(sensor, str) and sensor not in ALLOWED_SENSORS:
        errors.append(
            f"field 'sensor' must be one of {list(ALLOWED_SENSORS)}, got '{sensor}'"
        )

    stage = event.get("stage")
    if isinstance(stage, str) and stage not in ALLOWED_STAGES:
        errors.append(
            f"field 'stage' must be one of {list(ALLOWED_STAGES)}, got '{stage}'"
        )

    outcome = event.get("outcome")
    if isinstance(outcome, str) and outcome not in ALLOWED_OUTCOMES:
        errors.append(
            f"field 'outcome' must be one of {list(ALLOWED_OUTCOMES)}, got '{outcome}'"
        )

    ts = event.get("ts")
    if isinstance(ts, str):
        try:
            _parse_iso_timestamp(ts)
        except ValueError:
            errors.append(f"field 'ts' must be a valid ISO-8601 timestamp, got '{ts}'")

    return ValidationResult(valid=(len(errors) == 0), errors=errors)


def ensure_valid_event(event: dict[str, Any]) -> dict[str, Any]:
    result = validate_event(event)
    if not result.valid:
        joined = "; ".join(result.errors)
        raise ValueError(f"event failed validation: {joined}")
    return event
