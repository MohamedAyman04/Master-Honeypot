#!/usr/bin/env python3
"""
CODESYS SoftPLC Runtime for Raspberry Pi 4B (Master-Honeypot Integration)
========================================================================
Implements:
1. Modbus TCP Server (Port 502) - Standard industrial fieldbus protocol
2. OPC UA Server (Port 4840) - Standard industrial SCADA / enterprise protocol
3. WebVisu Web Interface (Port 8080) - Real-time SCADA operator display
4. IEC 61131-3 Scan Cycle Engine (100ms) - Physics-aware industrial pipeline control & safety logic
"""

import sys
import time
import math
import random
import threading
import logging
import asyncio
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request

# Modbus Libraries
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.device import ModbusDeviceIdentification

# OPC UA Libraries
try:
    from asyncua import Server, ua
    OPCUA_AVAILABLE = True
except ImportError:
    OPCUA_AVAILABLE = False

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] (%(name)s) %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/codesys_softplc.log', mode='a')
    ]
)
logger = logging.getLogger("CODESYS_SoftPLC")

# Global PLC State
class PLCState:
    def __init__(self):
        self.lock = threading.RLock()
        # Control Variables
        self.pump_rpm = 1200.0          # Range: 0 - 3000
        self.valve_pos = 0.60           # Range: 0.0 - 1.0 (60%)
        self.emergency_stop = 0         # 0: Normal, 1: Tripped
        self.control_mode = 0           # 0: Auto, 1: Manual, 2: Remote SCADA
        
        # Process State (Hydraulic Model)
        self.pressure = 96.0            # PSI (Normal: ~96 PSI)
        self.flow_rate = 14.4           # L/s
        self.temperature = 34.4         # °C
        
        # Diagnostics
        self.alarm_high_pressure = False
        self.alarm_overheat = False
        self.scan_count = 0
        self.start_time = time.time()
        self.last_modbus_client = "None"
        self.modbus_write_count = 0
        self.event_log = []
        self._syncing = False

    def log_event(self, event_type, details):
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        entry = {"time": ts, "type": event_type, "details": details}
        with self.lock:
            self.event_log.insert(0, entry)
            if len(self.event_log) > 50:
                self.event_log.pop()
        logger.info(f"[{event_type}] {details}")

plc = PLCState()

# ── IEC 61131-3 Cyclic Execution Logic (100ms Scan Cycle) ────────────────────
def iec_scan_cycle():
    """Simulates IEC 61131-3 PLC scan loop: Read Inputs -> Execute Logic -> Update Outputs"""
    dt = 0.1  # 100ms scan cycle
    kappa_p = 0.05
    kappa_q = 0.05
    gamma_t = 0.012
    delta_t = 0.010
    lambda_t = 0.02
    t_ambient = 22.0

    while True:
        cycle_start = time.time()
        with plc.lock:
            plc.scan_count += 1
            
            # 1. Check Safety Interlocks (IEC Safety Function Block)
            if plc.emergency_stop == 1:
                plc.pump_rpm = max(0.0, plc.pump_rpm - 100.0)
            
            # 2. Physics Equilibrium Dynamics
            p_star = (plc.pump_rpm / 10.0) * (1.5 - plc.valve_pos * 0.8)
            q_star = (plc.pump_rpm / 50.0) * plc.valve_pos
            
            # Apply Hard Constraints (Valve Closed clamping)
            if plc.valve_pos <= 0.01:
                q_star = 0.0
                p_star = (plc.pump_rpm / 10.0) * 1.5
            
            # Differential State Evolution
            noise_p = random.gauss(0, 0.2)
            noise_q = random.gauss(0, 0.05)
            noise_t = random.gauss(0, 0.05)
            
            plc.pressure += kappa_p * (p_star - plc.pressure) + noise_p
            plc.pressure = max(0.0, plc.pressure)
            
            plc.flow_rate += kappa_q * (q_star - plc.flow_rate) + noise_q
            if plc.valve_pos <= 0.01:
                plc.flow_rate = 0.0
            else:
                plc.flow_rate = max(0.0, plc.flow_rate)
                
            temp_target = gamma_t * plc.pump_rpm - delta_t * plc.flow_rate - lambda_t * (plc.temperature - t_ambient)
            plc.temperature += temp_target * dt + noise_t
            
            # 3. Alarm Logic & Safety Limits
            plc.alarm_high_pressure = (plc.pressure > 150.0)
            plc.alarm_overheat = (plc.temperature > 85.0)
            
            # Auto-trip in Safety Mode if pressure exceeds critical threshold (200 PSI)
            if plc.pressure > 200.0 and plc.control_mode == 0:
                plc.emergency_stop = 1
                plc.log_event("SAFETY_INTERLOCK", f"Overpressure trip activated: Pressure={plc.pressure:.1f} PSI")

        elapsed = time.time() - cycle_start
        sleep_time = max(0.005, dt - elapsed)
        time.sleep(sleep_time)

# ── Modbus Data Store Synchronization ─────────────────────────────────────────
class CustomModbusDataBlock(ModbusSequentialDataBlock):
    def setValues(self, address, values):
        super().setValues(address, values)
        # Only process external writes
        if getattr(plc, "_syncing", False):
            return
        
        with plc.lock:
            plc.modbus_write_count += len(values)
            for offset, val in enumerate(values):
                reg = address + offset
                if reg == 1:  # Register 0: Pump RPM
                    plc.pump_rpm = float(max(0, min(3000, val)))
                    plc.log_event("MODBUS_WRITE", f"Pump RPM set to {plc.pump_rpm}")
                elif reg == 2:  # Register 1: Valve Position (0 - 1000 = 0.0 - 1.0)
                    plc.valve_pos = float(max(0, min(1000, val))) / 1000.0
                    plc.log_event("MODBUS_WRITE", f"Valve Position set to {plc.valve_pos*100:.1f}%")
                elif reg == 6:  # Register 5: Emergency Stop
                    plc.emergency_stop = 1 if val != 0 else 0
                    plc.log_event("MODBUS_WRITE", f"Emergency Stop set to {plc.emergency_stop}")
                elif reg == 7:  # Register 6: Control Mode
                    plc.control_mode = int(val)
                    plc.log_event("MODBUS_WRITE", f"Control Mode set to {plc.control_mode}")

def sync_modbus_registers(store):
    """Continuously mirrors internal PLC state into Modbus Holding & Input registers"""
    while True:
        with plc.lock:
            plc._syncing = True
            alarm_mask = (1 if plc.alarm_high_pressure else 0) | (2 if plc.alarm_overheat else 0) | (4 if plc.emergency_stop else 0)
            uptime_s = int(time.time() - plc.start_time) % 65535
            
            holding_vals = [
                int(plc.pump_rpm),
                int(plc.valve_pos * 1000),
                int(plc.pressure * 10),
                int(plc.flow_rate * 10),
                int(plc.temperature * 10),
                int(plc.emergency_stop),
                int(plc.control_mode),
                int(alarm_mask),
                int(plc.scan_count % 65535),
                int(uptime_s)
            ]
            
            coils_vals = [
                1 if plc.pump_rpm > 10 else 0,
                1 if plc.valve_pos > 0.05 else 0,
                1 if plc.alarm_high_pressure else 0,
                1 if plc.alarm_overheat else 0,
                1 if plc.emergency_stop == 1 else 0
            ]
            
            try:
                store.setValues(3, 1, holding_vals)  # Holding Registers (FC3/FC6/FC16)
                store.setValues(4, 1, holding_vals[:5]) # Input Registers (FC4)
                store.setValues(1, 1, coils_vals)    # Coils (FC1/FC5)
                store.setValues(2, 1, coils_vals)    # Discrete Inputs (FC2)
            finally:
                plc._syncing = False
        time.sleep(0.1)

async def run_modbus_server():
    di_block = ModbusSequentialDataBlock(1, [0]*100)
    co_block = ModbusSequentialDataBlock(1, [0]*100)
    hr_block = CustomModbusDataBlock(1, [0]*100)
    ir_block = ModbusSequentialDataBlock(1, [0]*100)
    
    store = ModbusSlaveContext(di=di_block, co=co_block, hr=hr_block, ir=ir_block)
    context = ModbusServerContext(slaves=store, single=True)
    
    # Start background synchronization
    threading.Thread(target=sync_modbus_registers, args=(store,), daemon=True).start()
    
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'CODESYS GmbH / CODESYS Control for Raspberry Pi'
    identity.ProductCode = 'CODESYS-RPI4-SL'
    identity.VendorUrl = 'https://www.codesys.com'
    identity.ProductName = 'CODESYS Control for Raspberry Pi SL (Master-Honeypot)'
    identity.ModelName = 'Raspberry Pi 4B Industrial SoftPLC'
    identity.MajorMinorRevision = '3.5.19.0'
    
    logger.info("Starting CODESYS Modbus TCP Server on 0.0.0.0:502...")
    await StartAsyncTcpServer(context=context, identity=identity, address=("0.0.0.0", 502))

# ── OPC UA Server (Port 4840) ────────────────────────────────────────────────
async def run_opcua_server():
    if not OPCUA_AVAILABLE:
        logger.warning("asyncua not available; skipping OPC UA server.")
        return

    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/codesys/server/")
    server.set_server_name("CODESYS SoftPLC OPC UA Server")
    
    uri = "http://codesys.raspberrypi.honeypot"
    idx = await server.register_namespace(uri)
    
    # Create Objects and Variables
    objects = server.nodes.objects
    plc_obj = await objects.add_object(idx, "CODESYS_RaspberryPi_PLC")
    
    var_pump = await plc_obj.add_variable(idx, "PumpRPM", float(plc.pump_rpm))
    var_valve = await plc_obj.add_variable(idx, "ValvePosition", float(plc.valve_pos))
    var_pressure = await plc_obj.add_variable(idx, "Pressure", float(plc.pressure))
    var_flow = await plc_obj.add_variable(idx, "FlowRate", float(plc.flow_rate))
    var_temp = await plc_obj.add_variable(idx, "Temperature", float(plc.temperature))
    var_estop = await plc_obj.add_variable(idx, "EmergencyStop", int(plc.emergency_stop))
    var_alarm = await plc_obj.add_variable(idx, "HighPressureAlarm", bool(plc.alarm_high_pressure))
    
    await var_pump.set_writable()
    await var_valve.set_writable()
    await var_estop.set_writable()
    
    logger.info("Starting CODESYS OPC UA Server on opc.tcp://0.0.0.0:4840/codesys/server/...")
    async with server:
        while True:
            with plc.lock:
                p_rpm = float(plc.pump_rpm)
                v_pos = float(plc.valve_pos)
                press = float(plc.pressure)
                flow = float(plc.flow_rate)
                temp = float(plc.temperature)
                estop = int(plc.emergency_stop)
                alarm = bool(plc.alarm_high_pressure)
                
            await var_pump.write_value(p_rpm)
            await var_valve.write_value(v_pos)
            await var_pressure.write_value(press)
            await var_flow.write_value(flow)
            await var_temp.write_value(temp)
            await var_estop.write_value(estop)
            await var_alarm.write_value(alarm)
            await asyncio.sleep(0.5)

# ── WebVisu Web Interface (Port 8080) ─────────────────────────────────────────
app = Flask("CODESYS_WebVisu")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CODESYS Control for Raspberry Pi — WebVisu HMI</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: #0f172a; color: #f8fafc; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 2px solid #334155; }
        .logo { font-size: 24px; font-weight: bold; color: #38bdf8; display: flex; align-items: center; gap: 10px; }
        .badge { background: #0284c7; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .badge-live { background: #16a34a; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .card-title { font-size: 14px; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; margin-bottom: 10px; }
        .value { font-size: 36px; font-weight: bold; color: #38bdf8; }
        .unit { font-size: 16px; color: #64748b; font-weight: normal; }
        .alarm { color: #ef4444 !important; }
        .controls { margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-size: 14px; color: #cbd5e1; margin-bottom: 5px; }
        input[type="range"] { width: 100%; height: 8px; border-radius: 4px; background: #334155; }
        button { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.2s; }
        button:hover { background: #1d4ed8; }
        .btn-danger { background: #dc2626; }
        .btn-danger:hover { background: #b91c1c; }
        .logs-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        .logs-table th, .logs-table td { padding: 10px; text-align: left; border-bottom: 1px solid #334155; }
        .logs-table th { color: #94a3b8; background: #0f172a; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <span>⚙️ CODESYS Control V3.5</span>
            <span class="badge">Raspberry Pi 4B (4GB)</span>
            <span class="badge badge-live">RUNTIME RUNNING</span>
        </div>
        <div>
            <span style="color: #94a3b8;">IP: 192.168.1.8 | Modbus: 502 | OPC UA: 4840</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">Pipeline Pressure</div>
            <div class="value" id="pressure">-- <span class="unit">PSI</span></div>
        </div>
        <div class="card">
            <div class="card-title">Volumetric Flow Rate</div>
            <div class="value" id="flow_rate">-- <span class="unit">L/s</span></div>
        </div>
        <div class="card">
            <div class="card-title">Fluid Temperature</div>
            <div class="value" id="temperature">-- <span class="unit">°C</span></div>
        </div>
        <div class="card">
            <div class="card-title">Pump Speed</div>
            <div class="value" id="pump_rpm">-- <span class="unit">RPM</span></div>
        </div>
        <div class="card">
            <div class="card-title">Valve Position</div>
            <div class="value" id="valve_pos">-- <span class="unit">%</span></div>
        </div>
        <div class="card">
            <div class="card-title">PLC Scan Diagnostics</div>
            <div style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                <div>Cycles: <strong id="scan_count">0</strong></div>
                <div>Modbus Writes: <strong id="write_count">0</strong></div>
                <div>Status: <span id="alarm_status" style="color: #22c55e; font-weight: bold;">NORMAL</span></div>
            </div>
        </div>
    </div>

    <div class="controls">
        <div class="card">
            <div class="card-title">Manual Process Setpoints (WebVisu)</div>
            <div class="form-group">
                <label>Pump RPM Setpoint: <span id="rpm_val">1200</span> RPM</label>
                <input type="range" id="rpm_slider" min="0" max="3000" step="50" value="1200" oninput="document.getElementById('rpm_val').innerText = this.value">
                <button onclick="setRPM()" style="margin-top: 10px;">Apply RPM</button>
            </div>
            <div class="form-group">
                <label>Valve Position Setpoint: <span id="valve_val">60</span>%</label>
                <input type="range" id="valve_slider" min="0" max="100" step="1" value="60" oninput="document.getElementById('valve_val').innerText = this.value">
                <button onclick="setValve()" style="margin-top: 10px;">Apply Valve</button>
            </div>
        </div>

        <div class="card">
            <div class="card-title">Safety & Interlock Control</div>
            <p style="color: #94a3b8; font-size: 14px; margin-bottom: 15px;">
                Emergency Stop shuts down the pump immediately and triggers an alarm broadcast over Modbus and OPC UA.
            </p>
            <button class="btn-danger" style="width: 100%; padding: 15px; font-size: 16px;" onclick="toggleEstop()">🚨 EMERGENCY STOP / RESET</button>
        </div>
    </div>

    <div class="card" style="margin-top: 20px;">
        <div class="card-title">Live PLC Command & Event Log</div>
        <table class="logs-table">
            <thead>
                <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Event Type</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody id="logs_body">
                <tr><td colspan="3">Loading events...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('pressure').innerHTML = data.pressure.toFixed(1) + ' <span class="unit">PSI</span>';
                if (data.pressure > 150) document.getElementById('pressure').classList.add('alarm');
                else document.getElementById('pressure').classList.remove('alarm');

                document.getElementById('flow_rate').innerHTML = data.flow_rate.toFixed(1) + ' <span class="unit">L/s</span>';
                document.getElementById('temperature').innerHTML = data.temperature.toFixed(1) + ' <span class="unit">°C</span>';
                document.getElementById('pump_rpm').innerHTML = Math.round(data.pump_rpm) + ' <span class="unit">RPM</span>';
                document.getElementById('valve_pos').innerHTML = (data.valve_pos * 100).toFixed(0) + ' <span class="unit">%</span>';
                document.getElementById('scan_count').innerText = data.scan_count;
                document.getElementById('write_count').innerText = data.modbus_write_count;

                const alarmEl = document.getElementById('alarm_status');
                if (data.emergency_stop === 1) {
                    alarmEl.innerText = '🚨 EMERGENCY TRIP';
                    alarmEl.style.color = '#ef4444';
                } else if (data.alarm_high_pressure) {
                    alarmEl.innerText = '⚠️ HIGH PRESSURE ALARM';
                    alarmEl.style.color = '#f59e0b';
                } else {
                    alarmEl.innerText = '✅ NORMAL OPERATION';
                    alarmEl.style.color = '#22c55e';
                }

                // Update logs
                let html = '';
                data.event_log.slice(0, 10).forEach(e => {
                    html += `<tr><td>${e.time}</td><td><strong>${e.type}</strong></td><td>${e.details}</td></tr>`;
                });
                document.getElementById('logs_body').innerHTML = html;
            } catch(e) {
                console.error(e);
            }
        }

        async function setRPM() {
            const val = document.getElementById('rpm_slider').value;
            await fetch('/api/set_rpm', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({rpm: parseFloat(val)}) });
            fetchStatus();
        }

        async function setValve() {
            const val = document.getElementById('valve_slider').value;
            await fetch('/api/set_valve', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({valve: parseFloat(val)/100.0}) });
            fetchStatus();
        }

        async function toggleEstop() {
            await fetch('/api/toggle_estop', { method: 'POST' });
            fetchStatus();
        }

        setInterval(fetchStatus, 500);
        fetchStatus();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def get_status():
    with plc.lock:
        return jsonify({
            "pump_rpm": plc.pump_rpm,
            "valve_pos": plc.valve_pos,
            "pressure": plc.pressure,
            "flow_rate": plc.flow_rate,
            "temperature": plc.temperature,
            "emergency_stop": plc.emergency_stop,
            "control_mode": plc.control_mode,
            "alarm_high_pressure": plc.alarm_high_pressure,
            "alarm_overheat": plc.alarm_overheat,
            "scan_count": plc.scan_count,
            "modbus_write_count": plc.modbus_write_count,
            "event_log": list(plc.event_log)
        })

@app.route("/api/set_rpm", methods=["POST"])
def set_rpm():
    data = request.get_json(force=True)
    with plc.lock:
        plc.pump_rpm = max(0.0, min(3000.0, float(data.get("rpm", 1200.0))))
        plc.log_event("WEBVISU_COMMAND", f"Pump RPM setpoint changed to {plc.pump_rpm}")
    return jsonify({"status": "ok", "pump_rpm": plc.pump_rpm})

@app.route("/api/set_valve", methods=["POST"])
def set_valve():
    data = request.get_json(force=True)
    with plc.lock:
        plc.valve_pos = max(0.0, min(1.0, float(data.get("valve", 0.6))))
        plc.log_event("WEBVISU_COMMAND", f"Valve Position setpoint changed to {plc.valve_pos*100:.1f}%")
    return jsonify({"status": "ok", "valve_pos": plc.valve_pos})

@app.route("/api/toggle_estop", methods=["POST"])
def toggle_estop():
    with plc.lock:
        plc.emergency_stop = 0 if plc.emergency_stop == 1 else 1
        plc.log_event("WEBVISU_COMMAND", f"Emergency Stop toggled: {plc.emergency_stop}")
    return jsonify({"status": "ok", "emergency_stop": plc.emergency_stop})

def run_webvisu():
    logger.info("Starting CODESYS WebVisu HMI on http://0.0.0.0:8080...")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False, threaded=True)

# ── Main Entrypoint ──────────────────────────────────────────────────────────
def main():
    logger.info("Initializing CODESYS SoftPLC Engine for Raspberry Pi 4B...")
    
    # Start IEC Scan Cycle in background thread
    threading.Thread(target=iec_scan_cycle, daemon=True).start()
    
    # Start WebVisu HMI in background thread
    threading.Thread(target=run_webvisu, daemon=True).start()
    
    # Start Async Event Loop for Modbus and OPC UA
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tasks = [
        loop.create_task(run_modbus_server())
    ]
    if OPCUA_AVAILABLE:
        tasks.append(loop.create_task(run_opcua_server()))
        
    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        logger.info("Shutting down CODESYS SoftPLC...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
