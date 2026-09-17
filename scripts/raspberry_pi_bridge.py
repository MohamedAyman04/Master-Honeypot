#!/usr/bin/env python3
"""
Master-Honeypot Raspberry Pi Hardware Integration Bridge (Dynamic Dual-Host)
=============================================================================
Connects the Master-Honeypot monitoring & physics stack to the physical
Raspberry Pi 4B running CODESYS SoftPLC.

Supports automatic discovery and seamless failover across networks:
- Hotspot / Mobile Subnet: 172.20.10.8
- Home / Lab Wi-Fi Subnet: 192.168.1.8
"""

import os
import sys
import time
import json
import socket
import logging
import urllib.request
import redis
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration
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

def parse_candidate_hosts():
    raw = os.getenv("RPI_HOST", "")
    candidates = []
    if raw:
        for item in raw.split(","):
            item = item.strip()
            if item and item not in candidates:
                candidates.append(item)
    for default_ip in ["172.20.10.8", "192.168.1.8"]:
        if default_ip not in candidates:
            candidates.append(default_ip)
    return candidates

def discover_active_host(candidates, port=502, timeout=0.8):
    """Probe candidate hosts sequentially to find which IP is reachable on Modbus TCP."""
    for host in candidates:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            s.close()
            if res == 0:
                return host
        except Exception:
            pass
    return None

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
    candidates = parse_candidate_hosts()
    logger.info("==========================================================")
    logger.info("Starting Master-Honeypot Raspberry Pi Dynamic Hardware Bridge")
    logger.info(f"Configured Candidates: {candidates} (Port: {PI_MODBUS_PORT})")
    logger.info("==========================================================")

    r_client = connect_redis()
    influx_client, write_api = connect_influx()

    current_host = None
    modbus_client = None
    reconnect_delay = 2
    sample_count = 0

    while True:
        if modbus_client is None or not modbus_client.is_socket_open():
            logger.info(f"Scanning candidate hosts {candidates} for reachable Raspberry Pi...")
            active_host = discover_active_host(candidates, port=PI_MODBUS_PORT, timeout=0.8)
            if not active_host:
                logger.warning(f"No Raspberry Pi reachable on {candidates}:{PI_MODBUS_PORT}. Retrying in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                continue

            if active_host != current_host:
                if modbus_client:
                    try:
                        modbus_client.close()
                    except Exception:
                        pass
                logger.info(f"Target selected / changed: {current_host} -> {active_host}")
                current_host = active_host
                modbus_client = ModbusTcpClient(current_host, port=PI_MODBUS_PORT, timeout=2.0)

            logger.info(f"Connecting to Raspberry Pi Modbus TCP at {current_host}:{PI_MODBUS_PORT}...")
            if not modbus_client.connect():
                logger.warning(f"Failed to connect to {current_host}:{PI_MODBUS_PORT}. Re-scanning...")
                modbus_client = None
                time.sleep(reconnect_delay)
                continue
            logger.info(f"Successfully connected to Raspberry Pi CODESYS SoftPLC at {current_host}:{PI_MODBUS_PORT}")

        try:
            # Read 10 Holding Registers starting at address 0 (CODESYS 0-indexed mapping)
            rr = modbus_client.read_holding_registers(address=0, count=10)
            if rr.isError():
                logger.warning(f"Modbus read error from Pi ({current_host}): {rr}")
                try:
                    modbus_client.close()
                except Exception:
                    pass
                modbus_client = None
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
                    f"[Telemetry #{sample_count} @ {current_host}] "
                    f"Pressure: {pressure:5.1f} PSI | "
                    f"Flow: {flow_rate:5.1f} L/s | "
                    f"Temp: {temperature:4.1f} °C | "
                    f"RPM: {pump_rpm:4.0f} | "
                    f"Valve: {valve_pos*100:3.0f}% | "
                    f"Alarms: {alarm_mask:#04x}"
                )

            # Update Redis State Store for cross-component HIL synchronization
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
                        "active_host": current_host,
                        "timestamp": time.time()
                    }
                    # Set with 10s TTL to signal to other containers that hardware HIL is active
                    r_client.set("rpi_plc_state", json.dumps(state_dict), ex=10)
                    # Also keep canonical pipeline_state in sync so Docker containers mirror hardware
                    r_client.set("pipeline_state", json.dumps(state_dict))
                except Exception as ex:
                    logger.debug(f"Redis write error: {ex}")

            # Poll Live Edge Hardware & Memory Forensics from Pi REST API
            soc_temp, cpu_load, cpu_freq_ghz, mem_rss_mb = 44.3, 0.15, 1.8, 113.0
            try:
                with urllib.request.urlopen(f"http://{current_host}:8080/api/status", timeout=1.0) as resp:
                    st_data = json.loads(resp.read().decode())
                    soc_temp = float(st_data.get("soc_temp", 44.3))
                    cpu_load = float(st_data.get("cpu_load", 0.15))
                    cpu_freq_ghz = float(st_data.get("cpu_freq_mhz", 1800)) / 1000.0
                    mem_rss_mb = float(st_data.get("mem_rss_mb", 113.0))
            except Exception:
                pass

            # Write to InfluxDB Historian
            if write_api:
                try:
                    now = datetime.utcnow()
                    point = Point("plc_telemetry") \
                        .tag("device", "raspberry_pi_4b") \
                        .tag("plc_type", "codesys_softplc") \
                        .tag("host", current_host) \
                        .field("pressure", pressure) \
                        .field("flow_rate", flow_rate) \
                        .field("temperature", temperature) \
                        .field("pump_rpm", pump_rpm) \
                        .field("valve_position", valve_pos) \
                        .field("emergency_stop", emergency_stop) \
                        .field("alarm_high_pressure", 1 if (alarm_mask & 1) else 0) \
                        .field("soc_temperature", soc_temp) \
                        .field("cpu_load", cpu_load) \
                        .field("cpu_frequency_ghz", cpu_freq_ghz) \
                        .field("mem_rss_mb", mem_rss_mb) \
                        .time(now, WritePrecision.NS)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

                    # Dedicated Edge Hardware & Forensics Measurement
                    hw_point = Point("edge_hardware_telemetry") \
                        .tag("device", "raspberry_pi_4b") \
                        .tag("soc", "broadcom_bcm2711") \
                        .tag("host", current_host) \
                        .field("soc_temperature", soc_temp) \
                        .field("cpu_load", cpu_load) \
                        .field("cpu_frequency_ghz", cpu_freq_ghz) \
                        .field("mem_rss_mb", mem_rss_mb) \
                        .field("emergency_stop", emergency_stop) \
                        .field("active_threads", 8) \
                        .time(now, WritePrecision.NS)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=hw_point)

                    # Canonical Pipeline Metrics Series
                    pipe_point = Point("pipeline_metrics") \
                        .tag("location", "pump_station_01") \
                        .tag("source", "historian_bridge") \
                        .field("pressure", pressure) \
                        .field("flow_rate", flow_rate) \
                        .field("temperature", temperature) \
                        .field("pump_rpm", pump_rpm) \
                        .time(now, WritePrecision.NS)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=pipe_point)

                    # Canonical Process State Series
                    pump_state = "running" if pump_rpm > 10 else "stopped"
                    proc_point = Point("process_state") \
                        .tag("location", "pump_station_01") \
                        .field("pressure", pressure) \
                        .field("flow_rate", flow_rate) \
                        .field("temperature", temperature) \
                        .field("pump_rpm", pump_rpm) \
                        .field("pump_state", pump_state) \
                        .field("setpoint", 200.0) \
                        .time(now, WritePrecision.NS)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=proc_point)
                except Exception as ex:
                    logger.debug(f"Influx write error: {ex}")

        except Exception as e:
            logger.error(f"Bridge loop exception on {current_host}: {e}")
            if modbus_client:
                try:
                    modbus_client.close()
                except Exception:
                    pass
                modbus_client = None
            time.sleep(1)

        time.sleep(1.0)

if __name__ == "__main__":
    main()
