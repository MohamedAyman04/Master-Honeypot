import os
import random
import socket
import sqlite3
import threading
import time
from datetime import datetime
import json
from urllib import request as urlrequest
from prometheus_client import Counter, Gauge, start_http_server


DB_PATH = '/app/database-files/historians/sensor_readings_historian.db'
PUSH_INTERVAL_SECONDS = int(os.getenv('OPCUA_PUSH_SECONDS', '600'))
OPCUA_METRICS_PORT = int(os.getenv('OPCUA_METRICS_PORT', '9108'))
LEVEL2_HOST = os.getenv('LEVEL2_HOST', '').strip()
LEVEL2_MODBUS_PORT = int(os.getenv('LEVEL2_MODBUS_PORT', '502'))
LEVEL2_DNP3_PORT = int(os.getenv('LEVEL2_DNP3_PORT', '20000'))
LEVEL2_S7_PORT = int(os.getenv('LEVEL2_S7_PORT', '102'))
LEVEL2_TIMEOUT_SECONDS = float(os.getenv('LEVEL2_TIMEOUT_SECONDS', '2.0'))
LEVEL2_PULL_URL = os.getenv('LEVEL2_PULL_URL', '').strip()
LEVEL2_SHARED_TOKEN = os.getenv('LEVEL2_SHARED_TOKEN', '').strip()

PUSH_TOTAL = Counter('opcua_push_total', 'Total number of OPC UA publish batches')
PUSH_FAILURE_TOTAL = Counter('opcua_push_failure_total', 'Total number of OPC UA publish failures')
LAST_PUSH_EPOCH = Gauge('opcua_last_push_epoch', 'Unix epoch of latest successful OPC UA publish')
LISTENER_CONNECTION_TOTAL = Counter('opcua_listener_connection_total', 'Total number of OPC UA TCP listener connections')

SENSOR_PROFILES = [
    {'name': 'Temperature_Reactor_A', 'unit': 'C', 'min': 132.0, 'max': 178.0},
    {'name': 'Pressure_Tank_B', 'unit': 'Bar', 'min': 18.0, 'max': 31.0},
    {'name': 'Flow_Rate_Main', 'unit': 'L/min', 'min': 95.0, 'max': 155.0},
    {'name': 'Vibration_Pump_2', 'unit': 'mm/s', 'min': 0.6, 'max': 5.8},
]


def ensure_table_exists():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
        conn.commit()


def build_status(sensor_name, value):
    if sensor_name == 'Temperature_Reactor_A' and value >= 172.0:
        return 'Warning'
    if sensor_name == 'Pressure_Tank_B' and value >= 28.5:
        return 'Warning'
    if sensor_name == 'Vibration_Pump_2' and value >= 5.0:
        return 'Warning'
    return 'Normal'


def _tcp_reachable(host, port, timeout_seconds):
    try:
        with socket.create_connection((host, int(port)), timeout=float(timeout_seconds)):
            return True
    except OSError:
        return False


def _level2_protocol_rows(now):
    if not LEVEL2_HOST:
        return []

    rows = []
    checks = [
        ('MODBUS', LEVEL2_MODBUS_PORT),
        ('DNP3', LEVEL2_DNP3_PORT),
        ('S7', LEVEL2_S7_PORT),
    ]

    for protocol_name, port in checks:
        is_online = _tcp_reachable(LEVEL2_HOST, port, LEVEL2_TIMEOUT_SECONDS)
        rows.append(
            (
                f'L2_{protocol_name}_Link',
                1.0 if is_online else 0.0,
                'state',
                'Normal' if is_online else 'Warning',
                'L2_GATEWAY',
                now,
            )
        )

    return rows


def _adapt_metrics_response(payload: dict, now: str) -> list:
    """Convert historian_api /api/metrics → sensor_readings row tuples.

    The Level 2 historian_api returns:
      {"physical_process": {"pressure": .., "flow_rate": .., "temperature": .., "pump_rpm": ..}}

    This adapter maps those fields to named sensor rows compatible with
    the sensor_readings SQLite schema used by write_readings_batch().
    """
    phys = payload.get('physical_process', {})
    mapping = [
        ('Pressure_Pipeline',   phys.get('pressure'),    'PSI',  'pipeline'),
        ('Flow_Rate_Main',      phys.get('flow_rate'),   'L/s',  'pipeline'),
        ('Temperature_Process', phys.get('temperature'), 'C',    'pipeline'),
        ('Pump_RPM',            phys.get('pump_rpm'),    'RPM',  'pipeline'),
    ]
    rows = []
    for name, value, unit, source in mapping:
        if value is None:
            continue
        try:
            fval = float(value)
        except (TypeError, ValueError):
            continue
        status = 'Warning' if (name == 'Pressure_Pipeline' and fval > 280) else 'Normal'
        rows.append((name, fval, unit, status, source, now))
    return rows


def _level2_http_rows(now):
    if not LEVEL2_PULL_URL:
        return []

    request = urlrequest.Request(LEVEL2_PULL_URL, method='GET')
    if LEVEL2_SHARED_TOKEN:
        request.add_header('X-Bridge-Token', LEVEL2_SHARED_TOKEN)

    with urlrequest.urlopen(request, timeout=LEVEL2_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode('utf-8'))

    # If source provides the generic readings[] schema, use it directly.
    if 'readings' in payload:
        rows = []
        for item in payload.get('readings', []):
            sensor_name = str(item.get('sensor_name', '')).strip()
            if not sensor_name:
                continue
            try:
                value = float(item.get('value'))
            except (TypeError, ValueError):
                continue
            unit = str(item.get('unit', 'raw')).strip() or 'raw'
            status = str(item.get('status', 'Normal')).strip() or 'Normal'
            source = str(item.get('source', 'L2_HTTP')).strip() or 'L2_HTTP'
            rows.append((sensor_name, value, unit, status, source, now))
        return rows

    # Fall back to the historian_api /api/metrics schema (Level 2 bridge).
    return _adapt_metrics_response(payload, now)


def write_readings_batch():
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rows = []

    # Removed fake data generation to ensure only Level 2 physics data is used.
    rows.extend(_level2_protocol_rows(now))

    if LEVEL2_PULL_URL:
        try:
            rows.extend(_level2_http_rows(now))
        except Exception as error:
            print(f"[!] Level 2 HTTP pull error: {error}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            """
            INSERT INTO sensor_readings (sensor_name, value, unit, status, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()

    PUSH_TOTAL.inc()
    LAST_PUSH_EPOCH.set(time.time())
    print(f"[*] OPC UA pushed {len(rows)} readings at {now} UTC")


def publisher_loop():
    ensure_table_exists()
    print(f"[*] OPC UA publisher started. Target DB: {DB_PATH}")
    print(f"[*] Publish interval: {PUSH_INTERVAL_SECONDS} seconds")
    if LEVEL2_HOST:
        print(
            f"[*] Level 2 protocol polling enabled: host={LEVEL2_HOST} "
            f"modbus={LEVEL2_MODBUS_PORT} dnp3={LEVEL2_DNP3_PORT} s7={LEVEL2_S7_PORT}"
        )
    if LEVEL2_PULL_URL:
        print(f"[*] Level 2 HTTP pull enabled: {LEVEL2_PULL_URL}")

    while True:
        try:
            write_readings_batch()
        except Exception as error:
            PUSH_FAILURE_TOTAL.inc()
            print(f"[!] OPC UA publish error: {error}")

        time.sleep(PUSH_INTERVAL_SECONDS)


def tcp_listener():
    host = '0.0.0.0'
    port = 4840

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)

    print(f"[*] OPC UA listener running on {host}:{port}")

    while True:
        try:
            conn, addr = server.accept()
            LISTENER_CONNECTION_TOTAL.inc()
            conn.sendall(b'OPC UA simulator online\n')
            conn.close()
            print(f"[*] OPC UA client connected: {addr[0]}:{addr[1]}")
        except Exception as error:
            print(f"[!] OPC UA listener error: {error}")
            time.sleep(1)


def main():
    start_http_server(OPCUA_METRICS_PORT)
    print(f"[*] OPC UA metrics endpoint running on 0.0.0.0:{OPCUA_METRICS_PORT}")

    publisher = threading.Thread(target=publisher_loop, daemon=True)
    publisher.start()

    tcp_listener()


if __name__ == "__main__":
    main()
