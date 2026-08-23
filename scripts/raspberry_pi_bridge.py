#!/usr/bin/env python3
"""
Master-Honeypot Raspberry Pi Hardware Integration Bridge
=========================================================
Connects the Master-Honeypot monitoring & physics stack to the
physical Raspberry Pi 4B running CODESYS SoftPLC (192.168.1.8).

Responsibilities:
1. Polls Modbus TCP registers from Raspberry Pi (192.168.1.8:502) at 1 Hz.
2. Ingests live telemetry into InfluxDB (bucket: sensor_logs, measurement: plc_telemetry).
3. Updates Redis state store (ics_state_store) for ML Anomaly Engine & HMI.
4. Enables cross-layer Honeypot detection of real physical attacks against hardware PLCs.
"""

import os
import sys
import time
import json
import logging
import redis
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration
PI_HOST = os.getenv("RPI_HOST", "172.20.10.8")
PI_MODBUS_PORT = int(os.getenv("RPI_MODBUS_PORT", 502))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "supersecrettoken")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my_refinery")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "sensor_logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] (RaspberryPiBridge) %(message)s'
)
logger = logging.getLogger("RaspberryPiBridge")

def connect_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        logger.info(f"Connected to Redis state store at {REDIS_HOST}:{REDIS_PORT}")
        return r
    except Exception as e:
        logger.warning(f"Redis not reachable at {REDIS_HOST}:{REDIS_PORT} ({e}). Running in standalone mode.")
        return None

def connect_influx():
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=3000)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        logger.info(f"Connected to InfluxDB Historian at {INFLUX_URL} (bucket: {INFLUX_BUCKET})")
        return client, write_api
    except Exception as e:
        logger.warning(f"InfluxDB not reachable at {INFLUX_URL} ({e}). Telemetry persistence disabled.")
        return None, None

def main():
    logger.info("==========================================================")
    logger.info(f"Starting Master-Honeypot Raspberry Pi Hardware Bridge")
    logger.info(f"Target Hardware PLC: {PI_HOST}:{PI_MODBUS_PORT}")
    logger.info("==========================================================")

    r_client = connect_redis()
    influx_client, write_api = connect_influx()
    modbus_client = ModbusTcpClient(PI_HOST, port=PI_MODBUS_PORT, timeout=2.0)

    reconnect_delay = 3
    sample_count = 0

    while True:
        if not modbus_client.is_socket_open():
            logger.info(f"Connecting to Raspberry Pi Modbus TCP at {PI_HOST}:{PI_MODBUS_PORT}...")
            if not modbus_client.connect():
                logger.warning(f"Failed to connect to {PI_HOST}:{PI_MODBUS_PORT}. Retrying in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                continue
            logger.info(f"Successfully connected to Raspberry Pi CODESYS SoftPLC at {PI_HOST}:{PI_MODBUS_PORT}")

        try:
            # Read 10 Holding Registers starting at address 1
            rr = modbus_client.read_holding_registers(address=1, count=10)
            if rr.isError():
                logger.warning(f"Modbus read error from Pi: {rr}")
                time.sleep(1)
                continue

            regs = rr.registers
            pump_rpm = float(regs[0])
            valve_pos = float(regs[1]) / 1000.0
            pressure = float(regs[2]) / 10.0
            flow_rate = float(regs[3]) / 10.0
            temperature = float(regs[4]) / 10.0
            emergency_stop = int(regs[5])
            control_mode = int(regs[6])
            alarm_mask = int(regs[7])
            scan_count = int(regs[8])
            uptime_s = int(regs[9])

            sample_count += 1
            if sample_count % 10 == 0:
                logger.info(
                    f"[Telemetry #{sample_count}] "
                    f"Pressure: {pressure:5.1f} PSI | "
                    f"Flow: {flow_rate:5.1f} L/s | "
                    f"Temp: {temperature:4.1f} °C | "
                    f"RPM: {pump_rpm:4.0f} | "
                    f"Valve: {valve_pos*100:3.0f}% | "
                    f"Alarms: {alarm_mask:#04x}"
                )

            # Update Redis State Store
            if r_client:
                try:
                    state_dict = {
                        "pump_rpm": pump_rpm,
                        "valve_pos": valve_pos,
                        "pressure": pressure,
                        "flow_rate": flow_rate,
                        "temperature": temperature,
                        "emergency_stop": emergency_stop,
                        "source": "raspberry_pi_codesys",
                        "timestamp": time.time()
                    }
                    r_client.set("rpi_plc_state", json.dumps(state_dict))
                except Exception as ex:
                    logger.debug(f"Redis write error: {ex}")

            # Write to InfluxDB Historian
            if write_api:
                try:
                    point = Point("plc_telemetry") \
                        .tag("device", "raspberry_pi_4b") \
                        .tag("plc_type", "codesys_softplc") \
                        .tag("host", PI_HOST) \
                        .field("pressure", pressure) \
                        .field("flow_rate", flow_rate) \
                        .field("temperature", temperature) \
                        .field("pump_rpm", pump_rpm) \
                        .field("valve_position", valve_pos) \
                        .field("emergency_stop", emergency_stop) \
                        .field("alarm_high_pressure", 1 if (alarm_mask & 1) else 0) \
                        .time(datetime.utcnow(), WritePrecision.NS)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                except Exception as ex:
                    logger.debug(f"Influx write error: {ex}")

        except Exception as e:
            logger.error(f"Bridge loop exception: {e}")
            modbus_client.close()
            time.sleep(2)

        time.sleep(1.0)

if __name__ == "__main__":
    main()
