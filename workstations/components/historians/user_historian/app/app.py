"""
Historian logging configuration.

Logs are split into:
- activity stream: high-level query and security events
- query results stream: executed SQL with outcomes
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from components.common.story_client import StoryClient


COMPONENT_NAME = "user_historian"

_story_client = StoryClient(component=COMPONENT_NAME, level="Level 3")


def log_event(event_type, message, level="INFO"):
    """Write general activity/security events to historian activity stream."""
    entry = f"COMPONENT={COMPONENT_NAME} || EVENT={event_type} || {message}"
    if level == "WARNING":
        _activity_logger.warning(entry)
    elif level == "ERROR":
        _activity_logger.error(entry)
    else:
        _activity_logger.info(entry)

    _story_client.log(
        event_type="historian_event",
        message=entry,
        severity=level.lower(),
        details={"event_type": event_type},
    )


def log_login_attempt(username, password, ip_address):
    """Log historian login attempt details."""
    _details_logger.info(
        f"COMPONENT={COMPONENT_NAME} || EVENT=LOGIN_ATTEMPT || IP={ip_address} || USERNAME={username} || PASSWORD={password}"
    )

    _story_client.log(
        event_type="login_attempt",
        message=f"Login attempt for {username}",
        severity="info",
        details={"ip": ip_address, "username": username},
    )


def log_successful_login(username, ip_address):
    """Log historian successful login."""
    _details_logger.info(f"COMPONENT={COMPONENT_NAME} || EVENT=LOGIN_SUCCESS || IP={ip_address} || USERNAME={username}")

    _story_client.log(
        event_type="login_success",
        message=f"Login success for {username}",
        severity="info",
        details={"ip": ip_address, "username": username},
    )


def log_failed_login(username, ip_address):
    """Log historian failed login."""
    _details_logger.warning(f"COMPONENT={COMPONENT_NAME} || EVENT=LOGIN_FAILED || IP={ip_address} || USERNAME={username}")

    _story_client.log(
        event_type="login_failed",
        message=f"Login failed for {username}",
        severity="warning",
        details={"ip": ip_address, "username": username},
    )


def log_sql_injection(query, ip_address, payload):
    """Log potential SQL injection attempt in activity stream."""
    _activity_logger.warning(
        f"COMPONENT={COMPONENT_NAME} || EVENT=POTENTIAL_SQLI || IP={ip_address} || PAYLOAD={payload} || SQL={query}"
    )

    _story_client.log(
        event_type="sql_injection",
        message="Potential SQL injection detected",
        severity="high",
        details={"ip": ip_address, "payload": payload, "query": query},
    )


def _build_logger(logger_name, file_name):
    logs_dir = Path(__file__).resolve().parents[4] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(str(logs_dir / file_name), maxBytes=5 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s || %(levelname)s || %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


_activity_logger = _build_logger("historian_activity", "activity.log")
_details_logger = _build_logger("historian_details", "details.log")
_query_results_logger = _build_logger("historian_query_results", "sql_queries.log")


def log_query_result(actor, ip_address, payload, sql_text, status, rows_count, result_preview, error_message="NONE"):
    """Log query execution outcomes into dedicated query results stream."""
    preview_text = str(result_preview)
    if len(preview_text) > 600:
        preview_text = preview_text[:600] + "..."

    _query_results_logger.info(
        " || ".join([
            f"COMPONENT={COMPONENT_NAME}",
            f"HISTORIAN={COMPONENT_NAME}",
            f"ACTOR={actor}",
            f"IP={ip_address}",
            f"PAYLOAD={payload}",
            f"SQL={sql_text}",
            f"STATUS={status}",
            f"ROWS_COUNT={rows_count}",
            f"RESULT_PREVIEW={preview_text}",
            f"ERROR={error_message}",
        ])
    )