"""
Physical Process Simulator
==========================
Continuously models the pressure-regulated pipeline.
Stores shared state in Redis, which is read by Modbus and S7 servers.

Default operating point: 1200 RPM pump, valve 50% open (~12 L/s flow).
"""
import time
import os
import json
import redis
from physics.physics_engine import PipelineSimulator


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


def run_physics():
    sim = PipelineSimulator(use_redis=True)

    sim.set_pump_rpm(1200)
    sim.set_valve_pos(0.5)    # 50% open — nominal ~12 L/s per plant model

    state = sim.get_state()
    print("--- PHYSICAL PROCESS SIMULATOR STARTED ---")
    print(
        f"    Initial state: pump={state['pump_rpm']:.0f} RPM  "
        f"valve={state['valve_pos']:.0%}  "
        f"flow={state['flow_rate']:.1f} L/s"
    )
    print(f"    Update interval: 1s")

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
        print(
            f"[PHYSICS] P={state['pressure']:.1f} PSI  "
            f"F={state['flow_rate']:.2f} L/s  "
            f"T={state['temperature']:.1f}°C  "
            f"valve={state['valve_pos']:.2f}"
        )
        time.sleep(1)


if __name__ == "__main__":
    run_physics()
