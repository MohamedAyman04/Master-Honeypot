"""
Workstation logging configuration.

Detailed login attempt logging is enabled for research.
"""

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

from components.common.story_client import StoryClient


COMPONENT_NAME = os.getenv("WORKSTATION_COMPONENT", "workstation_1")
DEVICE_IP = os.getenv("WORKSTATION_DEVICE_IP", "")
DEVICE_MAC = os.getenv("WORKSTATION_DEVICE_MAC", "")
DEVICE_SERIAL = os.getenv("WORKSTATION_SERIAL", "")
DEVICE_MODEL = os.getenv("WORKSTATION_MODEL", "")
DEVICE_VENDOR = os.getenv("WORKSTATION_VENDOR", "")

_story_client = StoryClient(component=COMPONENT_NAME, level="Level 3")


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


def _parse_kv_message(message):
    parsed = {}
    for segment in str(message).split("||"):
        item = segment.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            parsed[key.strip().lower()] = value.strip()
        else:
            parsed.setdefault("message", item)
    return parsed


def workstation_identity():
    return {
        "component": COMPONENT_NAME,
        "device_ip": DEVICE_IP,
        "device_mac": DEVICE_MAC,
        "device_serial": DEVICE_SERIAL,
        "device_model": DEVICE_MODEL,
        "device_vendor": DEVICE_VENDOR,
    }


def _identity_fields():
    base = workstation_identity()
    return {key: value for key, value in base.items() if value}


def _emit_json(logger, payload, level="INFO"):
    enriched = dict(payload)
    enriched.update(_identity_fields())
    line = json.dumps(enriched, ensure_ascii=True)
    if level == "WARNING":
        logger.warning(line)
    elif level == "ERROR":
        logger.error(line)
    else:
        logger.info(line)


def log_event(event_type, message, level="INFO"):
    """Structured event logger used by workstation auth flow."""
    payload = {
        "timestamp": _utc_timestamp(),
        "component": COMPONENT_NAME,
        "event": str(event_type).lower(),
    }
    payload.update(_parse_kv_message(message))
    _emit_json(_activity_logger, payload, level=level)


def _build_creds_logger():
    logs_dir = Path(__file__).resolve().parents[4] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("workstation_creds")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(str(logs_dir / "details.log"), maxBytes=5 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


_creds_logger = _build_creds_logger()


def _build_activity_logger():
    logs_dir = Path(__file__).resolve().parents[4] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("workstation_activity")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(str(logs_dir / "simplified.log"), maxBytes=5 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


_activity_logger = _build_activity_logger()


def log_activity(activity_type, message, level="INFO"):
    """Structured activity logger for UI movement and redirections."""
    payload = {
        "timestamp": _utc_timestamp(),
        "component": COMPONENT_NAME,
        "event": "activity",
        "activity_type": str(activity_type).lower(),
    }
    payload.update(_parse_kv_message(message))
    _emit_json(_activity_logger, payload, level=level)

    if str(activity_type).upper() in {"L2_BRIDGE", "ROLE_ACTION"}:
        _story_client.log(
            event_type="activity",
            message=message,
            severity="info",
            details={"activity_type": str(activity_type).upper()},
        )


def log_login_attempt(username, password, ip_address):
    """Backward-compatible login attempt logger."""
    log_login_attempt_detailed(
        username=username,
        password=password,
        ip_address=ip_address,
        db_accessed=False,
        user_found=False,
        auth_result="ATTEMPT"
    )


def log_login_attempt_detailed(username, password, ip_address, db_accessed, user_found, auth_result, db_error=""):
    """Detailed credential logging for thesis analysis."""
    payload = {
        "timestamp": _utc_timestamp(),
        "component": COMPONENT_NAME,
        "event": "login_attempt",
        "ip": ip_address,
        "username": username,
        "password": password,
        "db_accessed": bool(db_accessed),
        "user_found": bool(user_found),
        "status": str(auth_result).lower(),
        "db_error": db_error or "NONE",
    }
    _emit_json(_creds_logger, payload)

    _story_client.log(
        event_type="login_attempt",
        message=f"Login {str(auth_result).lower()} for {username}",
        severity="warning" if str(auth_result).lower() != "success" else "info",
        details={
            "ip": ip_address,
            "username": username,
            "db_accessed": bool(db_accessed),
            "user_found": bool(user_found),
            "status": str(auth_result).lower(),
            "db_error": db_error or "NONE",
        },
    )


def log_successful_login(username, ip_address):
    """Log successful login event with concise context."""
    payload = {
        "timestamp": _utc_timestamp(),
        "component": COMPONENT_NAME,
        "event": "login_success",
        "ip": ip_address,
        "username": username,
        "status": "success",
    }
    _emit_json(_creds_logger, payload)


def log_failed_login(username, ip_address):
    """Log failed login event with concise context."""
    payload = {
        "timestamp": _utc_timestamp(),
        "component": COMPONENT_NAME,
        "event": "login_failed",
        "ip": ip_address,
        "username": username,
        "status": "failed",
    }
    _emit_json(_creds_logger, payload, level="WARNING")