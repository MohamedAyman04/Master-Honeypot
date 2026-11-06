"""
Physical Process Simulator (Saudi Aramco Reference Multi-Stage Refinery)
========================================================================
Continuously models the 4-Stage sequential petroleum refining process train:
  Stage 1: Crude Oil Ingestion & Electrostatic Desalting
  Stage 2: Atmospheric Distillation Unit (ADU) & Fractionation Column
  Stage 3: Hydrodesulfurization (HDS) Catalytic Reactor
  Stage 4: Finished Product In-Line Blending & Pipeline Custody Export

Persists state to Redis ('pipeline_state') for Modbus, S7, and SCADA servers.
Streams stage-by-stage process telemetry directly into InfluxDB Historian.
"""

import time
import os
import json
import redis
from datetime import datetime, timezone
from physics.physics_engine import PipelineSimulator

# ── InfluxDB Configuration ─────────────────────────────────────────────────────
INFLUX_URL    = os.environ.get("INFLUX_URL", "http://historian:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN", "supersecrettoken")
INFLUX_ORG    = os.environ.get("INFLUX_ORG", "my_refinery")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "sensor_logs")

_influx_client = None
_write_api = None

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    _influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=2000)
    _write_api = _influx_client.write_api(write_options=SYNCHRONOUS)
    print(f"[PHYSICS] Connected to InfluxDB at {INFLUX_URL} (bucket: {INFLUX_BUCKET})")
except Exception as e:
    print(f"[PHYSICS] InfluxDB client initialization note: {e}")


def is_hil_active(r_client) -> bool:
    if not r_client:
        return False
    try:
        raw = r_client.get("rpi_plc_state")
        if raw:
            st = json.loads(raw)
            if time.time() - float(st.get("timestamp", 0)) < 8.0:
                return True
    except Exception:
        pass
    return False


def publish_refinery_telemetry(state: dict):
    if not _write_api:
        return
    try:
        now = datetime.now(timezone.utc)
        p = Point("refinery_stages") \
            .tag("plant", "aramco_refinery_01") \
            .tag("facility", "hydrocarbon_processing") \
            .tag("zone", "level1_process") \
            .field("s1_desalter_pressure", float(state["stage1_desalter_pressure"])) \
            .field("s1_crude_flow",        float(state["stage1_crude_flow"])) \
            .field("s1_desalter_temp",     float(state["stage1_desalter_temp"])) \
            .field("s1_salt_content_ptb",  float(state["stage1_salt_content_ptb"])) \
            .field("s2_furnace_temp",      float(state["stage2_furnace_temp"])) \
            .field("s2_column_pressure",   float(state["stage2_column_pressure"])) \
            .field("s2_naphtha_flow",      float(state["stage2_naphtha_flow"])) \
            .field("s2_diesel_flow",       float(state["stage2_diesel_flow"])) \
            .field("s2_residue_flow",      float(state["stage2_residue_flow"])) \
            .field("s2_column_level",      float(state["stage2_column_level"])) \
            .field("s3_reactor_pressure",  float(state["stage3_reactor_pressure"])) \
            .field("s3_bed_temp",          float(state["stage3_bed_temp"])) \
            .field("s3_sulfur_ppm",        float(state["stage3_sulfur_ppm"])) \
            .field("s3_treated_diesel",    float(state["stage3_treated_diesel_flow"])) \
            .field("s4_export_pressure",   float(state["stage4_export_pressure"])) \
            .field("s4_export_flow",       float(state["stage4_export_flow"])) \
            .field("s4_diesel_cetane",     float(state["stage4_diesel_cetane"])) \
            .field("s4_tank_inventory",    float(state["stage4_tank_inventory_bbl"])) \
            .time(now, WritePrecision.NS)

        _write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception:
        pass


def run_physics():
    sim = PipelineSimulator(use_redis=True)

    sim.set_pump_rpm(1200)
    sim.set_valve_pos(0.5)    # 50% open — nominal ~12 L/s crude charge

    state = sim.get_state()
    print("==================================================================")
    print("  SAUDI ARAMCO REFERENCE REFINERY PROCESS SIMULATOR STARTED")
    print("  4-Stage Pipeline: Desalter -> ADU -> HDS -> Export Blending")
    print("==================================================================")
    print(f"  [S1] Crude Charge: {state['pump_rpm']:.0f} RPM | Valve: {state['valve_pos']:.0%} | Flow: {state['stage1_crude_flow']:.1f} L/s")
    print(f"  [S2] Furnace Temp: {state['stage2_furnace_temp']:.1f} °C | Column Top P: {state['stage2_column_pressure']:.2f} bar")
    print(f"  [S3] HDS Reactor P: {state['stage3_reactor_pressure']:.1f} PSI | Bed Temp: {state['stage3_bed_temp']:.1f} °C | Sulfur: {state['stage3_sulfur_ppm']:.1f} ppm")
    print(f"  [S4] Export Pressure: {state['pressure']:.1f} PSI | Flow: {state['flow_rate']:.1f} L/s")
    print("==================================================================")

    tick = 0
    while True:
        tick += 1
        if is_hil_active(sim.r):
            if tick % 15 == 0:
                print("[PHYSICS STANDBY] Physical Raspberry Pi HIL active; process state mirrored from hardware.")
            time.sleep(1)
            continue

        sim.update()
        state = sim.get_state()
        publish_refinery_telemetry(state)

        if tick % 5 == 0:
            print(
                f"[REFINERY TICK #{tick:04d}] "
                f"S1 Flow={state['stage1_crude_flow']:4.1f} L/s | "
                f"S2 FurnT={state['stage2_furnace_temp']:5.1f}°C | "
                f"S3 HDS_P={state['stage3_reactor_pressure']:5.1f} PSI | "
                f"S3 Sulf={state['stage3_sulfur_ppm']:4.1f} ppm | "
                f"S4 Export_P={state['pressure']:5.1f} PSI"
            )
        time.sleep(1)


if __name__ == "__main__":
    run_physics()
