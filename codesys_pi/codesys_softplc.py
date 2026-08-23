#!/usr/bin/env python3
"""
CODESYS SoftPLC Runtime for Raspberry Pi 4B (Master-Honeypot Integration)
========================================================================
Purdue Level 1/2 Industrial SoftPLC Controller
Implements:
1. Modbus TCP Server (Port 502)
2. OPC UA Server (Port 4840)
3. WebVisu Industrial Operator Interface (Port 8080)
4. IEC 61131-3 100ms Scan Cycle & Hydraulic Process Model
"""

import sys
import time
import math
import random
import threading
import logging
import asyncio
from datetime import datetime, timezone
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
        self.pump_rpm = 1200.0          # Range: 0 - 3000 RPM
        self.valve_pos = 0.60           # Range: 0.0 - 1.0 (60%)
        self.emergency_stop = 0         # 0: Normal, 1: Tripped
        self.control_mode = 0           # 0: AUTO, 1: MANUAL, 2: REMOTE_SCADA
        
        # Process State (Hydraulic Model)
        self.pressure = 96.0            # PSI
        self.flow_rate = 14.4           # L/s
        self.temperature = 34.4         # deg C
        
        # Diagnostics
        self.alarm_high_pressure = False
        self.alarm_overheat = False
        self.scan_count = 0
        self.start_time = time.time()
        self.modbus_write_count = 0
        self.event_log = []
        self._syncing = False

    def log_event(self, event_type, details):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
            
            # 1. Safety Interlocks
            if plc.emergency_stop == 1:
                plc.pump_rpm = max(0.0, plc.pump_rpm - 100.0)
            
            # 2. Physics Equilibrium Dynamics
            p_star = (plc.pump_rpm / 10.0) * (1.5 - plc.valve_pos * 0.8)
            q_star = (plc.pump_rpm / 50.0) * plc.valve_pos
            
            # Hard Constraints (Valve Closed Clamping)
            if plc.valve_pos <= 0.01:
                q_star = 0.0
                p_star = (plc.pump_rpm / 10.0) * 1.5
            
            # Differential State Evolution with Gaussian Noise
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
            
            # 3. Alarm Threshold Evaluation
            plc.alarm_high_pressure = (plc.pressure > 150.0)
            plc.alarm_overheat = (plc.temperature > 85.0)
            
            # Automatic Safety Trip (Pressure > 200 PSI in AUTO mode)
            if plc.pressure > 200.0 and plc.control_mode == 0:
                plc.emergency_stop = 1
                plc.log_event("SAFETY_TRIP", f"Overpressure Interlock: Pressure={plc.pressure:.1f} PSI")

        elapsed = time.time() - cycle_start
        sleep_time = max(0.005, dt - elapsed)
        time.sleep(sleep_time)

# ── Modbus Data Store Synchronization ─────────────────────────────────────────
class CustomModbusDataBlock(ModbusSequentialDataBlock):
    def setValues(self, address, values):
        super().setValues(address, values)
        if getattr(plc, "_syncing", False):
            return
        
        with plc.lock:
            plc.modbus_write_count += len(values)
            for offset, val in enumerate(values):
                reg = address + offset
                if reg == 1:  # Register 0: Pump RPM
                    plc.pump_rpm = float(max(0, min(3000, val)))
                    plc.log_event("MODBUS_WRITE", f"Pump RPM setpoint updated to {plc.pump_rpm:.0f} RPM")
                elif reg == 2:  # Register 1: Valve Position (0 - 1000)
                    plc.valve_pos = float(max(0, min(1000, val))) / 1000.0
                    plc.log_event("MODBUS_WRITE", f"Valve Position updated to {plc.valve_pos*100:.1f}%")
                elif reg == 6:  # Register 5: Emergency Stop
                    plc.emergency_stop = 1 if val != 0 else 0
                    plc.log_event("MODBUS_WRITE", f"Emergency Stop status updated: {plc.emergency_stop}")
                elif reg == 7:  # Register 6: Control Mode
                    plc.control_mode = int(val)
                    plc.log_event("MODBUS_WRITE", f"Control Mode updated to {plc.control_mode}")

def sync_modbus_registers(store):
    """Periodically mirrors internal PLC state into Modbus registers"""
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
                store.setValues(3, 1, holding_vals)      # Holding Registers (FC3/FC6/FC16)
                store.setValues(4, 1, holding_vals[:5])  # Input Registers (FC4)
                store.setValues(1, 1, coils_vals)        # Coils (FC1/FC5)
                store.setValues(2, 1, coils_vals)        # Discrete Inputs (FC2)
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

# ── Industrial WebVisu Monochrome Interface (Port 8080) ──────────────────────
app = Flask("CODESYS_WebVisu")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CODESYS WebVisu — Raspberry Pi 4B Industrial Node</title>
    <style>
        :root {
            --bg-primary: #0a0a0a;
            --bg-surface: #141414;
            --bg-elevated: #1e1e1e;
            --border-color: #2e2e2e;
            --text-primary: #f0f0f0;
            --text-secondary: #888888;
            --text-muted: #555555;
            --accent-border: #444444;
            --font-mono: 'Consolas', 'Monaco', 'Courier New', monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-sans);
            padding: 24px;
            line-height: 1.4;
        }

        /* Top System Bar */
        .system-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
        }
        .system-title {
            font-family: var(--font-mono);
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .system-meta {
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-secondary);
        }

        /* Section Layout */
        .grid-telemetry {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .telemetry-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            padding: 16px;
        }
        .tag-name {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }
        .tag-desc {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 10px;
        }
        .tag-value {
            font-family: var(--font-mono);
            font-size: 28px;
            font-weight: 700;
            color: var(--text-primary);
        }
        .tag-unit {
            font-size: 13px;
            font-weight: 400;
            color: var(--text-secondary);
            margin-left: 4px;
        }

        /* Control & Diagnostics Grid */
        .grid-control {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        @media (max-width: 800px) {
            .grid-control { grid-template-columns: 1fr; }
        }
        .panel {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            padding: 16px;
        }
        .panel-header {
            font-family: var(--font-mono);
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
            margin-bottom: 16px;
        }

        .form-row {
            margin-bottom: 16px;
        }
        .form-label {
            display: flex;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 12px;
            margin-bottom: 6px;
            color: var(--text-primary);
        }
        input[type="range"] {
            width: 100%;
            height: 4px;
            background: var(--border-color);
            outline: none;
            -webkit-appearance: none;
            margin-bottom: 8px;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 14px;
            height: 14px;
            background: #ffffff;
            cursor: pointer;
            border-radius: 0;
        }

        .btn {
            font-family: var(--font-mono);
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #ffffff;
            color: #000000;
            border: 1px solid #ffffff;
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 0;
            transition: all 0.1s;
        }
        .btn:hover {
            background: #cccccc;
            border-color: #cccccc;
        }
        .btn-outline {
            background: transparent;
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        .btn-outline:hover {
            background: var(--bg-elevated);
            border-color: #666666;
        }
        .btn-block { width: 100%; }

        /* Diagnostics Table */
        .diag-table {
            width: 100%;
            border-collapse: collapse;
            font-family: var(--font-mono);
            font-size: 12px;
        }
        .diag-table td {
            padding: 6px 0;
            border-bottom: 1px solid var(--border-color);
        }
        .diag-table td:last-child {
            text-align: right;
            color: var(--text-primary);
            font-weight: 600;
        }
        .diag-table tr:last-child td { border-bottom: none; }

        /* Event Log Table */
        .log-table {
            width: 100%;
            border-collapse: collapse;
            font-family: var(--font-mono);
            font-size: 12px;
            margin-top: 8px;
        }
        .log-table th {
            text-align: left;
            padding: 8px;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-surface);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
        }
        .log-table td {
            padding: 8px;
            border-bottom: 1px solid #1c1c1c;
            color: var(--text-primary);
        }
    </style>
</head>
<body>

    <div class="system-bar">
        <div class="system-title">
            CODESYS CONTROL V3.5 // RASPBERRY PI 4B NODE
        </div>
        <div class="system-meta">
            HOST: 192.168.1.8 | MODBUS: 502 | OPC-UA: 4840 | SCAN: 100ms
        </div>
    </div>

    <!-- Process Telemetry -->
    <div class="grid-telemetry">
        <div class="telemetry-card">
            <div class="tag-name">PT-101</div>
            <div class="tag-desc">Pipeline Pressure</div>
            <div class="tag-value"><span id="val_press">--</span><span class="tag-unit">PSI</span></div>
        </div>
        <div class="telemetry-card">
            <div class="tag-name">FT-101</div>
            <div class="tag-desc">Volumetric Flow Rate</div>
            <div class="tag-value"><span id="val_flow">--</span><span class="tag-unit">L/s</span></div>
        </div>
        <div class="telemetry-card">
            <div class="tag-name">TT-101</div>
            <div class="tag-desc">Fluid Temperature</div>
            <div class="tag-value"><span id="val_temp">--</span><span class="tag-unit">°C</span></div>
        </div>
        <div class="telemetry-card">
            <div class="tag-name">P-101</div>
            <div class="tag-desc">Main Pump Speed</div>
            <div class="tag-value"><span id="val_rpm">--</span><span class="tag-unit">RPM</span></div>
        </div>
        <div class="telemetry-card">
            <div class="tag-name">XV-101</div>
            <div class="tag-desc">Outlet Valve Position</div>
            <div class="tag-value"><span id="val_valve">--</span><span class="tag-unit">%</span></div>
        </div>
    </div>

    <!-- Controls and Diagnostics -->
    <div class="grid-control">
        <div class="panel">
            <div class="panel-header">Process Setpoint Manipulation (IEC 61131-3)</div>
            
            <div class="form-row">
                <div class="form-label">
                    <span>P-101 Speed Demand</span>
                    <span id="disp_rpm_slider">1200 RPM</span>
                </div>
                <input type="range" id="slider_rpm" min="0" max="3000" step="50" value="1200" oninput="document.getElementById('disp_rpm_slider').innerText = this.value + ' RPM'">
                <button class="btn btn-outline" onclick="applyRPM()">Apply RPM Setpoint</button>
            </div>

            <div class="form-row" style="margin-top: 20px;">
                <div class="form-label">
                    <span>XV-101 Valve Demand</span>
                    <span id="disp_valve_slider">60%</span>
                </div>
                <input type="range" id="slider_valve" min="0" max="100" step="1" value="60" oninput="document.getElementById('disp_valve_slider').innerText = this.value + '%'">
                <button class="btn btn-outline" onclick="applyValve()">Apply Valve Setpoint</button>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">PLC Controller Status</div>
            
            <table class="diag-table">
                <tr>
                    <td style="color: var(--text-secondary);">Operating State</td>
                    <td id="diag_state">RUNNING</td>
                </tr>
                <tr>
                    <td style="color: var(--text-secondary);">Interlock Alarm</td>
                    <td id="diag_alarm">NORMAL</td>
                </tr>
                <tr>
                    <td style="color: var(--text-secondary);">Scan Count</td>
                    <td id="diag_scans">0</td>
                </tr>
                <tr>
                    <td style="color: var(--text-secondary);">Modbus Write Operations</td>
                    <td id="diag_writes">0</td>
                </tr>
                <tr>
                    <td style="color: var(--text-secondary);">Emergency Stop Relay</td>
                    <td id="diag_estop">DE-ASSERTED</td>
                </tr>
            </table>

            <div style="margin-top: 24px;">
                <button class="btn btn-block" onclick="toggleEstop()" id="btn_estop">TOGGLE EMERGENCY STOP</button>
            </div>
        </div>
    </div>

    <!-- Event & Attack Log -->
    <div class="panel">
        <div class="panel-header">Command & Telemetry Audit Log</div>
        <table class="log-table">
            <thead>
                <tr>
                    <th style="width: 180px;">Timestamp (UTC)</th>
                    <th style="width: 180px;">Event Category</th>
                    <th>Parameters & Execution Details</th>
                </tr>
            </thead>
            <tbody id="log_body">
                <tr><td colspan="3" style="color: var(--text-muted);">Polling audit log...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                document.getElementById('val_press').innerText = data.pressure.toFixed(1);
                document.getElementById('val_flow').innerText = data.flow_rate.toFixed(1);
                document.getElementById('val_temp').innerText = data.temperature.toFixed(1);
                document.getElementById('val_rpm').innerText = Math.round(data.pump_rpm);
                document.getElementById('val_valve').innerText = Math.round(data.valve_pos * 100);

                document.getElementById('diag_scans').innerText = data.scan_count;
                document.getElementById('diag_writes').innerText = data.modbus_write_count;

                const alarmEl = document.getElementById('diag_alarm');
                if (data.emergency_stop === 1) {
                    alarmEl.innerText = 'TRIP (EMERGENCY STOP)';
                } else if (data.alarm_high_pressure) {
                    alarmEl.innerText = 'ALARM (HIGH PRESSURE)';
                } else if (data.alarm_overheat) {
                    alarmEl.innerText = 'ALARM (OVERHEAT)';
                } else {
                    alarmEl.innerText = 'NORMAL';
                }

                document.getElementById('diag_estop').innerText = (data.emergency_stop === 1) ? 'ASSERTED (ACTIVE)' : 'DE-ASSERTED';

                // Render Event Logs
                let rows = '';
                (data.event_log || []).slice(0, 10).forEach(entry => {
                    rows += `<tr>
                        <td style="font-family: var(--font-mono); color: var(--text-secondary);">${entry.time}</td>
                        <td style="font-family: var(--font-mono);">${entry.type}</td>
                        <td>${entry.details}</td>
                    </tr>`;
                });
                document.getElementById('log_body').innerHTML = rows || '<tr><td colspan="3">No events recorded.</td></tr>';

            } catch (err) {
                console.error(err);
            }
        }

        async function applyRPM() {
            const val = parseFloat(document.getElementById('slider_rpm').value);
            await fetch('/api/set_rpm', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({rpm: val})
            });
            updateStatus();
        }

        async function applyValve() {
            const val = parseFloat(document.getElementById('slider_valve').value) / 100.0;
            await fetch('/api/set_valve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({valve: val})
            });
            updateStatus();
        }

        async function toggleEstop() {
            await fetch('/api/toggle_estop', { method: 'POST' });
            updateStatus();
        }

        setInterval(updateStatus, 500);
        updateStatus();
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
        plc.log_event("OPERATOR_SETPOINT", f"P-101 speed demand set to {plc.pump_rpm:.0f} RPM")
    return jsonify({"status": "ok", "pump_rpm": plc.pump_rpm})

@app.route("/api/set_valve", methods=["POST"])
def set_valve():
    data = request.get_json(force=True)
    with plc.lock:
        plc.valve_pos = max(0.0, min(1.0, float(data.get("valve", 0.6))))
        plc.log_event("OPERATOR_SETPOINT", f"XV-101 position demand set to {plc.valve_pos*100:.1f}%")
    return jsonify({"status": "ok", "valve_pos": plc.valve_pos})

@app.route("/api/toggle_estop", methods=["POST"])
def toggle_estop():
    with plc.lock:
        plc.emergency_stop = 0 if plc.emergency_stop == 1 else 1
        state_str = "TRIPPED (ASSERTED)" if plc.emergency_stop == 1 else "RESET (DE-ASSERTED)"
        plc.log_event("SAFETY_INTERLOCK", f"Manual Emergency Stop {state_str}")
    return jsonify({"status": "ok", "emergency_stop": plc.emergency_stop})

def run_webvisu():
    logger.info("Starting CODESYS WebVisu HMI on http://0.0.0.0:8080...")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False, threaded=True)

# ── Main Entrypoint ──────────────────────────────────────────────────────────
def main():
    logger.info("Initializing CODESYS SoftPLC Engine for Raspberry Pi 4B...")
    
    # Start IEC Scan Cycle
    threading.Thread(target=iec_scan_cycle, daemon=True).start()
    
    # Start WebVisu HMI
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
