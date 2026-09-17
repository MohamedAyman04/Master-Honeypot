from io import StringIO
import csv
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import sqlite3

from flask import Blueprint, Response, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import text

from .models import db, SensorReading, User
from components.common.story_client import StoryClient


sensor_bp = Blueprint('sensor', __name__)

_story_client = StoryClient(component="sensor_readings_historian", level="Level 3")


REPO_ROOT = Path(__file__).resolve().parents[4]

DATABASES = {
    'sensor_readings_historian': {
        'label': 'Sensor Readings Historian',
        'path': REPO_ROOT / 'database-files' / 'historians' / 'sensor_readings_historian.db',
        'permission': {
            'admin': '1=1',
            'engineer': "timestamp >= datetime('now', '-1 month')",
            'operator': "timestamp >= datetime('now', '-2 day')",
        },
        'predefined': {
            'default': {
                'label': 'Run Predefined: Last 24h',
                'sql': "SELECT id, sensor_name, value, unit, status, source, timestamp FROM sensor_readings WHERE timestamp >= datetime('now', '-1 day') ORDER BY timestamp DESC LIMIT 500",
            },
            'recent': {
                'label': 'Run Predefined: Latest 100',
                'sql': "SELECT id, sensor_name, value, unit, status, source, timestamp FROM sensor_readings ORDER BY timestamp DESC LIMIT 100",
            },
            'focus': {
                'label': 'Run Predefined: Warnings',
                'sql': "SELECT id, sensor_name, value, unit, status, source, timestamp FROM sensor_readings WHERE status != 'Normal' ORDER BY timestamp DESC LIMIT 200",
            },
        },
    },
    'maintenance_times_historian': {
        'label': 'Maintenance Times Historian',
        'path': REPO_ROOT / 'database-files' / 'historians' / 'maintenance_times_historian.db',
        'permission': {
            'admin': '1=1',
            'engineer': "window_start >= datetime('now', '-3 month')",
            'operator': '1=0',
        },
        'predefined': {
            'default': {
                'label': 'Run Predefined: Scheduled Windows',
                'sql': "SELECT id, component_name, window_start, window_end, status, notes FROM maintenance_windows ORDER BY window_start DESC LIMIT 200",
            },
            'recent': {
                'label': 'Run Predefined: Last 3 Months',
                'sql': "SELECT id, component_name, window_start, window_end, status, notes FROM maintenance_windows WHERE window_start >= datetime('now', '-3 month') ORDER BY window_start DESC LIMIT 200",
            },
            'focus': {
                'label': 'Run Predefined: Non-Completed',
                'sql': "SELECT id, component_name, window_start, window_end, status, notes FROM maintenance_windows WHERE status != 'Completed' ORDER BY window_start DESC LIMIT 200",
            },
        },
    },
    'components_historian': {
        'label': 'Components Historian',
        'path': REPO_ROOT / 'database-files' / 'historians' / 'components_historian.db',
        'permission': {
            'admin': '1=1',
            'engineer': '1=1',
            'operator': '1=0',
        },
        'predefined': {
            'default': {
                'label': 'Run Predefined: Component Inventory',
                'sql': "SELECT id, component_name, component_type, level, status, location FROM factory_components ORDER BY id DESC LIMIT 200",
            },
            'recent': {
                'label': 'Run Predefined: Level 2 Assets',
                'sql': "SELECT id, component_name, component_type, level, status, location FROM factory_components WHERE level = 2 ORDER BY component_name ASC LIMIT 200",
            },
            'focus': {
                'label': 'Run Predefined: Non-Active',
                'sql': "SELECT id, component_name, component_type, level, status, location FROM factory_components WHERE status != 'Active' ORDER BY component_name ASC LIMIT 200",
            },
        },
    },
    'user_historian': {
        'label': 'User Historian',
        'path': REPO_ROOT / 'database-files' / 'historians' / 'user_historian.db',
        'permission': {
            'admin': '1=1',
            'engineer': '1=0',
            'operator': '1=0',
        },
        'predefined': {
            'default': {
                'label': 'Run Predefined: User Accounts',
                'sql': "SELECT id, username, password, role, created_at FROM users ORDER BY id DESC LIMIT 200",
            },
            'recent': {
                'label': 'Run Predefined: Created Last 3 Months',
                'sql': "SELECT id, username, password, role, created_at FROM users WHERE created_at >= datetime('now', '-3 month') ORDER BY created_at DESC LIMIT 200",
            },
            'focus': {
                'label': 'Run Predefined: Elevated Roles',
                'sql': "SELECT id, username, password, role, created_at FROM users WHERE role IN ('admin', 'engineer') ORDER BY id DESC LIMIT 200",
            },
        },
    },
}


CRUD_ACTION_ORDER = ('add', 'edit', 'delete')

CRUD_ACTION_LABELS = {
    'add': 'Add Record',
    'edit': 'Edit Record',
    'delete': 'Delete Record',
}

CRUD_POLICY = {
    'admin': {
        'sensor_readings_historian': {'add', 'edit', 'delete'},
        'maintenance_times_historian': {'add', 'edit', 'delete'},
        'components_historian': {'add', 'edit', 'delete'},
        'user_historian': {'add', 'edit', 'delete'},
    },
    'engineer': {
        'sensor_readings_historian': {'add', 'edit'},
        'maintenance_times_historian': {'add', 'edit', 'delete'},
        'components_historian': {'add', 'edit', 'delete'},
        'user_historian': set(),
    },
    'operator': {
        'sensor_readings_historian': {'add'},
        'maintenance_times_historian': set(),
        'components_historian': set(),
        'user_historian': set(),
    },
}

CRUD_SCHEMAS = {
    'sensor_readings_historian': {
        'table': 'sensor_readings',
        'pk': 'id',
        'fields': [
            {'name': 'sensor_name', 'label': 'Sensor Name', 'type': 'text', 'required_add': True, 'placeholder': 'Temperature_Reactor_A'},
            {'name': 'value', 'label': 'Value', 'type': 'float', 'required_add': True, 'placeholder': '145.2'},
            {'name': 'unit', 'label': 'Unit', 'type': 'text', 'required_add': True, 'placeholder': 'C'},
            {'name': 'status', 'label': 'Status', 'type': 'text', 'required_add': False, 'placeholder': 'Normal'},
            {'name': 'source', 'label': 'Source', 'type': 'text', 'required_add': False, 'placeholder': 'OPCUA'},
            {'name': 'timestamp', 'label': 'Timestamp', 'type': 'text', 'required_add': False, 'placeholder': 'YYYY-MM-DD HH:MM:SS'},
        ],
    },
    'maintenance_times_historian': {
        'table': 'maintenance_windows',
        'pk': 'id',
        'fields': [
            {'name': 'component_name', 'label': 'Component Name', 'type': 'text', 'required_add': True, 'placeholder': 'Pump_1'},
            {'name': 'window_start', 'label': 'Window Start', 'type': 'text', 'required_add': True, 'placeholder': 'YYYY-MM-DD HH:MM:SS'},
            {'name': 'window_end', 'label': 'Window End', 'type': 'text', 'required_add': True, 'placeholder': 'YYYY-MM-DD HH:MM:SS'},
            {'name': 'status', 'label': 'Status', 'type': 'text', 'required_add': False, 'placeholder': 'Scheduled'},
            {'name': 'notes', 'label': 'Notes', 'type': 'text', 'required_add': False, 'placeholder': 'Seal check'},
        ],
    },
    'components_historian': {
        'table': 'factory_components',
        'pk': 'id',
        'fields': [
            {'name': 'component_name', 'label': 'Component Name', 'type': 'text', 'required_add': True, 'placeholder': 'Gateway_Node_1'},
            {'name': 'component_type', 'label': 'Component Type', 'type': 'text', 'required_add': True, 'placeholder': 'Gateway'},
            {'name': 'level', 'label': 'Level', 'type': 'int', 'required_add': True, 'placeholder': '2'},
            {'name': 'status', 'label': 'Status', 'type': 'text', 'required_add': False, 'placeholder': 'Active'},
            {'name': 'location', 'label': 'Location', 'type': 'text', 'required_add': False, 'placeholder': 'Control Room'},
        ],
    },
    'user_historian': {
        'table': 'users',
        'pk': 'id',
        'fields': [
            {'name': 'username', 'label': 'Username', 'type': 'text', 'required_add': True, 'placeholder': 'new_user'},
            {'name': 'password', 'label': 'Password', 'type': 'text', 'required_add': True, 'placeholder': 'change_me'},
            {'name': 'role', 'label': 'Role', 'type': 'text', 'required_add': False, 'placeholder': 'operator'},
            {'name': 'created_at', 'label': 'Created At', 'type': 'text', 'required_add': False, 'placeholder': 'YYYY-MM-DD HH:MM:SS'},
        ],
    },
}


def _crud_actions(role, selected_db):
    allowed = CRUD_POLICY.get(role, {}).get(selected_db, set())
    return [action for action in CRUD_ACTION_ORDER if action in allowed]


def _manageable_databases(role):
    manageable = {}
    for db_key, db_meta in DATABASES.items():
        if _crud_actions(role, db_key):
            manageable[db_key] = db_meta
    return manageable


def _parse_record_id(raw_value):
    try:
        record_id = int((raw_value or '').strip())
    except (TypeError, ValueError) as exc:
        raise ValueError('Record ID must be a positive integer.') from exc

    if record_id <= 0:
        raise ValueError('Record ID must be a positive integer.')
    return record_id


def _parse_field_value(raw_value, field_type):
    value = (raw_value or '').strip()
    if value == '':
        return None

    if field_type == 'int':
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError('Expected integer value.') from exc

    if field_type == 'float':
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError('Expected numeric value.') from exc

    return value


def _collect_crud_values(selected_db, action, form_data):
    schema = CRUD_SCHEMAS[selected_db]
    values = {}

    for field in schema['fields']:
        form_key = f"field_{field['name']}"
        raw_value = form_data.get(form_key, '')

        try:
            parsed = _parse_field_value(raw_value, field.get('type', 'text'))
        except ValueError as exc:
            raise ValueError(f"{field['label']}: {exc}") from exc

        if parsed is None:
            if action == 'add' and field.get('required_add'):
                raise ValueError(f"{field['label']} is required for add action.")
            continue

        values[field['name']] = parsed

    if action == 'add' and selected_db == 'sensor_readings_historian' and 'timestamp' not in values:
        values['timestamp'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    if action == 'edit' and not values:
        raise ValueError('Provide at least one field value to update.')

    return values


def _execute_secure_crud_action(selected_db, action, form_data):
    schema = CRUD_SCHEMAS[selected_db]
    table_name = schema['table']
    primary_key = schema['pk']
    db_path = DATABASES[selected_db]['path']

    with sqlite3.connect(str(db_path)) as connection:
        cursor = connection.cursor()

        if action == 'add':
            values = _collect_crud_values(selected_db, action, form_data)
            columns = list(values.keys())
            placeholders = ', '.join('?' for _ in columns)
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, [values[column] for column in columns])
            connection.commit()
            return f"Added record id={cursor.lastrowid} in {DATABASES[selected_db]['label']}.", 1

        if action == 'edit':
            record_id = _parse_record_id(form_data.get('record_id', ''))
            values = _collect_crud_values(selected_db, action, form_data)
            assignments = ', '.join(f"{column} = ?" for column in values.keys())
            sql = f"UPDATE {table_name} SET {assignments} WHERE {primary_key} = ?"
            params = [values[column] for column in values.keys()] + [record_id]
            cursor.execute(sql, params)
            connection.commit()

            if cursor.rowcount == 0:
                raise ValueError(f"No record found with id={record_id}.")

            return f"Updated record id={record_id} in {DATABASES[selected_db]['label']}.", cursor.rowcount

        if action == 'delete':
            record_id = _parse_record_id(form_data.get('record_id', ''))
            sql = f"DELETE FROM {table_name} WHERE {primary_key} = ?"
            cursor.execute(sql, (record_id,))
            connection.commit()

            if cursor.rowcount == 0:
                raise ValueError(f"No record found with id={record_id}.")

            return f"Deleted record id={record_id} from {DATABASES[selected_db]['label']}.", cursor.rowcount

    raise ValueError('Unsupported management action.')


def _log_manage_event(username, role, selected_db, action, status, row_count=0, error=''):
    payload = {
        'timestamp': _utc_timestamp(),
        'component': 'sensor_readings_historian',
        'event': 'data_manage',
        'action': str(action).lower(),
        'username': username,
        'role': role,
        'db': selected_db,
        'status': str(status).lower(),
        'rows': int(row_count),
        'error': (error or 'NONE').replace('\n', ' ').strip(),
    }
    line = json.dumps(payload, ensure_ascii=True)

    if str(status).upper() in ('ERROR', 'FORBIDDEN'):
        QUERY_LOGGER.error(line)
    else:
        QUERY_LOGGER.info(line)


def _build_query_logger():
    logs_dir = REPO_ROOT / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger('historian_sql_queries')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(str(logs_dir / 'sql_queries.log'), maxBytes=5 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


QUERY_LOGGER = _build_query_logger()


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


def _log_query_event(event_name, username, role, selected_db, original_sql, filtered_sql, status, row_count=0, error=''):
    payload = {
        'timestamp': _utc_timestamp(),
        'component': 'sensor_readings_historian',
        'event': str(event_name).lower(),
        'username': username,
        'role': role,
        'db': selected_db,
        'status': str(status).lower(),
        'rows': int(row_count),
        'original_sql': (original_sql or '').replace('\n', ' ').strip(),
        'filtered_sql': (filtered_sql or '').replace('\n', ' ').strip(),
        'error': (error or 'NONE').replace('\n', ' ').strip(),
    }
    line = json.dumps(payload, ensure_ascii=True)

    if str(status).upper() == 'ERROR':
        QUERY_LOGGER.error(line)
    else:
        QUERY_LOGGER.info(line)

    _story_client.log(
        event_type="query_event",
        message=f"{event_name} on {selected_db}",
        severity="warning" if str(status).upper() == "ERROR" else "info",
        details={
            "username": username,
            "role": role,
            "db": selected_db,
            "status": str(status).lower(),
            "rows": int(row_count),
            "original_sql": (original_sql or '').replace('\n', ' ').strip(),
            "filtered_sql": (filtered_sql or '').replace('\n', ' ').strip(),
            "error": (error or 'NONE').replace('\n', ' ').strip(),
        },
    )


def _valid_database(db_name):
    return db_name in DATABASES


def _permission_clause(role, selected_db):
    permission_map = DATABASES[selected_db]['permission']
    return permission_map.get(role, '1=0')


def _permission_summary(role, selected_db):
    summary = {
        'admin': {
            'sensor_readings_historian': 'full access',
            'maintenance_times_historian': 'full access',
            'components_historian': 'full access',
            'user_historian': 'full access',
        },
        'engineer': {
            'sensor_readings_historian': 'last month only',
            'maintenance_times_historian': 'last 3 months only',
            'components_historian': 'full access',
            'user_historian': 'no access (filtered unless bypassed)',
        },
        'operator': {
            'sensor_readings_historian': 'last 48 hours only',
            'maintenance_times_historian': 'no access (filtered unless bypassed)',
            'components_historian': 'no access (filtered unless bypassed)',
            'user_historian': 'no access (filtered unless bypassed)',
        },
    }
    return summary.get(role, {}).get(selected_db, 'no access')


def _apply_vulnerable_permission_filter(original_sql, permission_clause):
    sql = (original_sql or '').strip().rstrip(';')
    if not sql:
        return ''

    # Intentionally vulnerable by direct SQL string concatenation.
    if permission_clause == '1=1':
        return sql

    boundary = re.search(r'\b(order\s+by|group\s+by|limit)\b', sql, re.IGNORECASE)
    if boundary:
        head = sql[:boundary.start()].rstrip()
        tail = ' ' + sql[boundary.start():].lstrip()
    else:
        head = sql
        tail = ''

    if re.search(r'\bwhere\b', head, re.IGNORECASE):
        return f"{head} AND {permission_clause}{tail}"
    return f"{head} WHERE {permission_clause}{tail}"


def _execute_sql_on_database(selected_db, final_sql):
    db_path = DATABASES[selected_db]['path']
    with sqlite3.connect(str(db_path)) as connection:
        cursor = connection.cursor()
        cursor.execute(final_sql)

        if cursor.description is None:
            connection.commit()
            return [], []

        headers = [desc[0] for desc in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
        return headers, rows


def _ensure_multi_db_seed_data():
    for config in DATABASES.values():
        config['path'].parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(DATABASES['sensor_readings_historian']['path'])) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_name VARCHAR(100) NOT NULL,
                value FLOAT NOT NULL,
                unit VARCHAR(30) NOT NULL,
                status VARCHAR(30) DEFAULT 'Normal',
                source VARCHAR(80) DEFAULT 'OPCUA',
                timestamp DATETIME
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO sensor_readings (sensor_name, value, unit, status, source, timestamp) VALUES (?, ?, ?, ?, ?, datetime('now', ?))",
                [
                    ('Temperature_Reactor_A', 146.2, 'C', 'Normal', 'OPCUA', '-30 minutes'),
                    ('Pressure_Tank_B', 23.4, 'Bar', 'Normal', 'OPCUA', '-20 minutes'),
                    ('Flow_Rate_Main', 127.1, 'L/min', 'Normal', 'OPCUA', '-10 minutes'),
                ],
            )
            conn.commit()

    with sqlite3.connect(str(DATABASES['maintenance_times_historian']['path'])) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_name VARCHAR(100) NOT NULL,
                window_start DATETIME NOT NULL,
                window_end DATETIME NOT NULL,
                status VARCHAR(30) DEFAULT 'Scheduled',
                notes VARCHAR(255) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM maintenance_windows").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO maintenance_windows (component_name, window_start, window_end, status, notes) VALUES (?, datetime('now', ?), datetime('now', ?), ?, ?)",
                [
                    ('Pump_1', '+1 day', '+1 day', 'Scheduled', 'Seal check'),
                    ('Valve_A', '+2 day', '+2 day', 'Scheduled', 'Actuator calibration'),
                    ('Compressor_3', '+4 day', '+4 day', 'Planned', 'Vibration inspection'),
                ],
            )
            conn.commit()

    with sqlite3.connect(str(DATABASES['components_historian']['path'])) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factory_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_name VARCHAR(120) NOT NULL,
                component_type VARCHAR(60) NOT NULL,
                level INTEGER NOT NULL,
                status VARCHAR(30) DEFAULT 'Active',
                location VARCHAR(120) DEFAULT 'Unknown'
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM factory_components").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO factory_components (component_name, component_type, level, status, location) VALUES (?, ?, ?, ?, ?)",
                [
                    ('Plant_Network_Switch_A', 'Network', 2, 'Active', 'Control Room'),
                    ('Gateway_Node_1', 'Gateway', 2, 'Active', 'Cell/Area Boundary'),
                    ('Backup_Switch_B', 'Network', 2, 'Inactive', 'Panel Room'),
                ],
            )
            conn.commit()

    with sqlite3.connect(str(DATABASES['user_historian']['path'])) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'operator',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                [
                    ('admin', 'admin', 'admin'),
                    ('operator', 'operator123', 'operator'),
                    ('engineer', 'engineer456', 'engineer'),
                ],
            )
            conn.commit()


def _valid_role(role):
    return role in ('operator', 'engineer', 'admin')


@sensor_bp.route('/')
def index():
    if session.get('historian_logged_in'):
        return redirect(url_for('sensor.query_console'))
    return redirect(url_for('sensor.login'))


@sensor_bp.route('/handoff')
def handoff():
    username = request.args.get('username', '').strip()
    role = request.args.get('role', 'operator').strip().lower()
    selected_db = request.args.get('selected_db', 'sensor_readings_historian').strip()

    if not username or not _valid_role(role):
        return redirect(url_for('sensor.login'))

    if not _valid_database(selected_db):
        selected_db = 'sensor_readings_historian'

    session['historian_user'] = username
    session['historian_role'] = role
    session['historian_logged_in'] = True
    session['selected_db'] = selected_db
    return redirect(url_for('sensor.query_console'))


@sensor_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and session.get('historian_logged_in'):
        return redirect(url_for('sensor.query_console'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username, password=password).first()
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

        if user:
            session['historian_user'] = user.username
            session['historian_role'] = user.role
            session['historian_logged_in'] = True
            session['selected_db'] = 'sensor_readings_historian'

            _story_client.log(
                event_type="login_success",
                message=f"Historian login success for {username}",
                severity="info",
                details={"ip": ip_address, "username": username, "role": user.role},
            )
            return redirect(url_for('sensor.query_console'))

        _story_client.log(
            event_type="login_failed",
            message=f"Historian login failed for {username}",
            severity="warning",
            details={"ip": ip_address, "username": username},
        )
        return render_template('historian_login.html', error='Invalid credentials')

    return render_template('historian_login.html')


@sensor_bp.route('/logout')
def logout():
    session.pop('historian_user', None)
    session.pop('historian_role', None)
    session.pop('historian_logged_in', None)
    return redirect(url_for('sensor.login'))


@sensor_bp.route('/dashboard')
def dashboard():
    if not session.get('historian_logged_in'):
        return redirect(url_for('sensor.login'))

    count = SensorReading.query.count()
    role = session.get('historian_role', 'operator')
    return render_template('historian_dashboard.html', records_count=count, role=role, username=session.get('historian_user', 'anon'))


@sensor_bp.route('/api/readings')
def api_readings():
    if not session.get('historian_logged_in'):
        return jsonify({'error': 'unauthorized'}), 401

    rows = SensorReading.query.order_by(SensorReading.timestamp.desc()).all()
    return jsonify([row.to_dict() for row in rows])


@sensor_bp.route('/api/predefined/last24h')
def predefined_last24h():
    if not session.get('historian_logged_in'):
        return jsonify({'error': 'unauthorized'}), 401

    _ensure_multi_db_seed_data()
    rows = db.session.execute(
        text(DATABASES['sensor_readings_historian']['predefined']['default']['sql'])
    ).mappings().all()
    return jsonify([dict(row) for row in rows])


@sensor_bp.route('/manage', methods=['POST'])
def manage_dataset():
    if not session.get('historian_logged_in'):
        return redirect(url_for('sensor.login'))

    _ensure_multi_db_seed_data()

    username = session.get('historian_user', 'anon')
    role = session.get('historian_role', 'operator')
    selected_db = request.form.get('manage_db', session.get('manage_db', 'sensor_readings_historian')).strip()
    action = request.form.get('manage_action', '').strip().lower()

    if not _valid_database(selected_db):
        session['manage_error'] = 'Invalid target database.'
        _log_manage_event(username, role, selected_db, action, 'ERROR', row_count=0, error='INVALID_DATABASE')
        return redirect(url_for('sensor.query_console'))

    allowed_actions = _crud_actions(role, selected_db)
    if action not in allowed_actions:
        session['manage_error'] = 'You are not allowed to perform this action on the selected database.'
        _log_manage_event(username, role, selected_db, action, 'FORBIDDEN', row_count=0, error='ROLE_NOT_ALLOWED')
        return redirect(url_for('sensor.query_console', manage_db=selected_db))

    try:
        message, changed_rows = _execute_secure_crud_action(selected_db, action, request.form)
        session['manage_success'] = message
        _log_manage_event(username, role, selected_db, action, 'SUCCESS', row_count=changed_rows)
    except Exception as exc:
        session['manage_error'] = str(exc)
        _log_manage_event(username, role, selected_db, action, 'ERROR', row_count=0, error=str(exc))

    return redirect(url_for('sensor.query_console', manage_db=selected_db))


@sensor_bp.route('/query', methods=['GET', 'POST'])
def query_console():
    if not session.get('historian_logged_in'):
        return redirect(url_for('sensor.login'))

    _ensure_multi_db_seed_data()

    username = session.get('historian_user', 'anon')
    role = session.get('historian_role', 'operator')
    selected_db = request.form.get('selected_db', session.get('selected_db', 'sensor_readings_historian')).strip()
    if not _valid_database(selected_db):
        selected_db = 'sensor_readings_historian'

    session['selected_db'] = selected_db

    manageable_db_options = _manageable_databases(role)
    manage_db = request.args.get('manage_db', request.form.get('manage_db', session.get('manage_db', selected_db))).strip()
    if manage_db not in manageable_db_options:
        manage_db = next(iter(manageable_db_options), '')
    session['manage_db'] = manage_db

    manage_actions = _crud_actions(role, manage_db) if manage_db else []
    manage_fields = CRUD_SCHEMAS.get(manage_db, {}).get('fields', []) if manage_db else []
    manage_success = session.pop('manage_success', None)
    manage_error = session.pop('manage_error', None)

    db_config = DATABASES[selected_db]
    active_predefined = db_config['predefined']

    query_text = ''
    filtered_query_text = ''
    headers = []
    rows = []
    error = None

    if request.method == 'POST':
        selected_predefined = request.form.get('predefined_query', '').strip()
        custom_sql = request.form.get('custom_sql', '').strip()

        if selected_predefined in active_predefined:
            query_text = active_predefined[selected_predefined]['sql']
        else:
            query_text = custom_sql or active_predefined['default']['sql']

        permission_clause = _permission_clause(role, selected_db)
        filtered_query_text = _apply_vulnerable_permission_filter(query_text, permission_clause)

        try:
            headers, rows = _execute_sql_on_database(selected_db, filtered_query_text)
            _log_query_event(
                event_name='QUERY_EXECUTE',
                username=username,
                role=role,
                selected_db=selected_db,
                original_sql=query_text,
                filtered_sql=filtered_query_text,
                status='SUCCESS',
                row_count=len(rows),
            )
        except Exception as exc:
            error = str(exc)
            _log_query_event(
                event_name='QUERY_EXECUTE',
                username=username,
                role=role,
                selected_db=selected_db,
                original_sql=query_text,
                filtered_sql=filtered_query_text,
                status='ERROR',
                row_count=0,
                error=error,
            )

    return render_template(
        'historian_query.html',
        username=username,
        role=role,
        selected_db=selected_db,
        database_options=DATABASES,
        permission_summary=_permission_summary(role, selected_db),
        active_predefined=active_predefined,
        manageable_db_options=manageable_db_options,
        manage_db=manage_db,
        manage_actions=manage_actions,
        manage_fields=manage_fields,
        manage_action_labels=CRUD_ACTION_LABELS,
        manage_success=manage_success,
        manage_error=manage_error,
        query_text=query_text,
        filtered_query_text=filtered_query_text,
        headers=headers,
        rows=rows,
        error=error,
    )


@sensor_bp.route('/export', methods=['POST'])
def export_dataset():
    if not session.get('historian_logged_in'):
        return jsonify({'error': 'unauthorized'}), 401

    _ensure_multi_db_seed_data()

    username = session.get('historian_user', 'anon')
    role = session.get('historian_role', 'operator')
    selected_db = request.form.get('selected_db', session.get('selected_db', 'sensor_readings_historian')).strip()
    if not _valid_database(selected_db):
        selected_db = 'sensor_readings_historian'

    db_config = DATABASES[selected_db]
    query_text = request.form.get('custom_sql', '').strip() or db_config['predefined']['default']['sql']
    permission_clause = _permission_clause(role, selected_db)
    filtered_query_text = _apply_vulnerable_permission_filter(query_text, permission_clause)

    try:
        headers, rows = _execute_sql_on_database(selected_db, filtered_query_text)
        _log_query_event(
            event_name='EXPORT_EXECUTE',
            username=username,
            role=role,
            selected_db=selected_db,
            original_sql=query_text,
            filtered_sql=filtered_query_text,
            status='SUCCESS',
            row_count=len(rows),
        )
    except Exception as exc:
        _log_query_event(
            event_name='EXPORT_EXECUTE',
            username=username,
            role=role,
            selected_db=selected_db,
            original_sql=query_text,
            filtered_sql=filtered_query_text,
            status='ERROR',
            row_count=0,
            error=str(exc),
        )
        return jsonify({'error': str(exc)}), 400

    output = StringIO()
    writer = csv.writer(output)
    if headers:
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={selected_db}_export.csv'}
    )
