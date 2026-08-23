# CODESYS Development System V3.5 — Raspberry Pi 4B Setup & Connection Guide

This guide explains how to connect to the physical **Raspberry Pi 4B (172.20.10.8)** from the **CODESYS Development System (V3.5)** running on Windows/PC, deploy IEC 61131-3 logic (Ladder Logic / Structured Text / FBD), and integrate with the Master-Honeypot.

---

## 1. Raspberry Pi 4B Device Credentials

| Parameter | Value |
|---|---|
| **IP Address** | `172.20.10.8` |
| **SSH User** | `mohamed-ayman` |
| **SSH Password** | `mohamed2004` |
| **Modbus TCP Port** | `502` |
| **OPC UA Server** | `opc.tcp://172.20.10.8:4840/codesys/server/` |
| **WebVisu HMI** | `http://172.20.10.8:8080` |
| **Operating System** | Debian 13 (trixie, aarch64 64-bit) |
| **RAM / Hardware** | 4GB RAM, Cortex-A72 Quad-Core |

---

## 2. Standalone SoftPLC vs. CODESYS IDE Modes

The Raspberry Pi is configured with two flexible operation modes:

### Mode A: Standalone Industrial SoftPLC (Active by Default)
- Managed via `codesys-plc.service` on the Pi (`sudo systemctl status codesys-plc`).
- Automatically simulates the hydraulic pipeline physics, exposes Modbus TCP on port `502`, OPC UA on port `4840`, and WebVisu on port `8080`.
- Requires zero extra software on your PC; fully integrated with Master-Honeypot out-of-the-box.

### Mode B: Official CODESYS Control for Raspberry Pi Runtime
To deploy your own custom IEC 61131-3 programs directly from CODESYS IDE:
1. Open **CODESYS V3.5 SP19 / SP20** on Windows.
2. In the top menu, navigate to **Tools** → **Update Raspberry Pi** (or **CODESYS Control for Linux ARM64 SL**).
3. Enter:
   - **IP address:** `172.20.10.8`
   - **User:** `mohamed-ayman`
   - **Password:** `mohamed2004`
4. Click **Install / Update**. CODESYS IDE will deploy the native Linux ARM64 runtime package (`codesyscontrol_arm64.deb`) over SSH.
5. In your CODESYS Project:
   - Device: Select `CODESYS Control for Linux ARM64 SL` (or `CODESYS Control for Raspberry Pi 64 SL`).
   - Double-click `Device (CODESYS Control...)` → **Communication Settings**.
   - Click **Scan Network...** → Select `172.20.10.8 [0001]`.
   - Click **Online** → **Login** (Alt+F8) → **Run** (F5).

---

## 3. Register Map for Master-Honeypot Synchronization

| Modbus Address | Data Type | Engineering Unit | Parameter | Description |
|---|---|---|---|---|
| `40001` (Reg 0) | `UINT` | RPM (0–3000) | `pump_rpm` | Oil pipeline main pump motor speed |
| `40002` (Reg 1) | `UINT` | 0.1% (0–1000) | `valve_pos` | Primary outlet control valve position |
| `40003` (Reg 2) | `UINT` | 0.1 PSI | `pressure` | Pipeline head pressure telemetry |
| `40004` (Reg 3) | `UINT` | 0.1 L/s | `flow_rate` | Volumetric flow rate telemetry |
| `40005` (Reg 4) | `UINT` | 0.1 °C | `temperature` | Process fluid temperature |
| `40006` (Reg 5) | `UINT` | Boolean (0/1) | `emergency_stop` | E-Stop interlock trip |
| `40007` (Reg 6) | `UINT` | Enum (0/1/2) | `control_mode` | 0: Auto, 1: Manual, 2: Remote SCADA |
| `40008` (Reg 7) | `UINT` | Bitmask | `alarm_status` | Bit 0: Overpressure, Bit 1: Overheat |

---

## 4. WebVisu Operator Dashboard

Open your browser to:
```
http://172.20.10.8:8080
```
This displays the real-time SCADA operator screen with live dials, pressure/flow telemetry, interactive sliders for manual pump/valve control, E-Stop button, and live Modbus/OPC UA access logs.

---

## 5. Master-Honeypot Integration Commands

To run the Master-Honeypot with the Raspberry Pi hardware PLC:

```bash
# 1. Run the hardware integration bridge
python scripts/raspberry_pi_bridge.py

# 2. Run automated test suite
python scripts/test_raspberry_pi_integration.py --host 172.20.10.8
```
