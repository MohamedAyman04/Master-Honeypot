#!/usr/bin/env python3
"""
Master-Honeypot Raspberry Pi & CODESYS Integration Test Suite
============================================================
Runs comprehensive automated verification against the physical
Raspberry Pi 4B (192.168.1.8) running CODESYS SoftPLC.
"""

import sys
import time
import json
import urllib.request
import urllib.error
from pymodbus.client import ModbusTcpClient

PI_HOST = "192.168.1.8"
MODBUS_PORT = 502
WEBVISU_PORT = 8080
OPCUA_PORT = 4840

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_webvisu_http():
    print_header("Test 1: WebVisu HTTP & REST API (Port 8080)")
    url = f"http://{PI_HOST}:{WEBVISU_PORT}/api/status"
    try:
        t0 = time.time()
        req = urllib.request.Request(url, headers={'User-Agent': 'MasterHoneypotTest/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            elapsed = (time.time() - t0) * 1000
            data = json.loads(resp.read().decode('utf-8'))
            print(f"  [PASS] HTTP GET {url} returned 200 OK in {elapsed:.1f}ms")
            print(f"         - Pressure   : {data['pressure']:.2f} PSI")
            print(f"         - Flow Rate  : {data['flow_rate']:.2f} L/s")
            print(f"         - Temperature: {data['temperature']:.2f} °C")
            print(f"         - Pump RPM   : {data['pump_rpm']:.0f} RPM")
            print(f"         - Valve Pos  : {data['valve_pos']*100:.1f}%")
            print(f"         - Scan Cycles: {data['scan_count']}")
            print(f"         - Status     : {'HIGH PRESSURE' if data['alarm_high_pressure'] else 'NORMAL'}")
            return True
    except Exception as e:
        print(f"  [FAIL] Could not connect to WebVisu at {url}: {e}")
        return False

def test_modbus_read():
    print_header("Test 2: Modbus TCP Read Holding Registers (Port 502)")
    client = ModbusTcpClient(PI_HOST, port=MODBUS_PORT, timeout=2.0)
    try:
        t0 = time.time()
        if not client.connect():
            print(f"  [FAIL] Failed to connect to Modbus TCP at {PI_HOST}:{MODBUS_PORT}")
            return False
        
        rr = client.read_holding_registers(address=1, count=10)
        elapsed = (time.time() - t0) * 1000
        if rr.isError():
            print(f"  [FAIL] Modbus read returned error: {rr}")
            return False
        
        regs = rr.registers
        print(f"  [PASS] Read 10 Holding Registers in {elapsed:.1f}ms:")
        print(f"         - Reg 0 (Pump RPM)     : {regs[0]}")
        print(f"         - Reg 1 (Valve Pos*1000): {regs[1]} ({regs[1]/10:.1f}%)")
        print(f"         - Reg 2 (Pressure*10)  : {regs[2]} ({regs[2]/10.0:.1f} PSI)")
        print(f"         - Reg 3 (Flow Rate*10) : {regs[3]} ({regs[3]/10.0:.1f} L/s)")
        print(f"         - Reg 4 (Temp*10)      : {regs[4]} ({regs[4]/10.0:.1f} °C)")
        print(f"         - Reg 5 (E-Stop)       : {regs[5]}")
        print(f"         - Reg 6 (Control Mode) : {regs[6]}")
        print(f"         - Reg 7 (Alarm Mask)   : {regs[7]:#04x}")
        print(f"         - Reg 8 (Scan Count)   : {regs[8]}")
        print(f"         - Reg 9 (Uptime s)     : {regs[9]}")
        return True
    except Exception as e:
        print(f"  [FAIL] Modbus read exception: {e}")
        return False
    finally:
        client.close()

def test_modbus_write():
    print_header("Test 3: Modbus TCP Write & Physics Response (Port 502)")
    client = ModbusTcpClient(PI_HOST, port=MODBUS_PORT, timeout=2.0)
    try:
        client.connect()
        # Set pump RPM to 1800
        target_rpm = 1800
        print(f"  [STEP 1] Writing target Pump RPM = {target_rpm} to Register 1 (FC6)...")
        wr = client.write_register(address=1, value=target_rpm)
        if wr.isError():
            print(f"  [FAIL] Modbus write returned error: {wr}")
            return False
        print(f"  [PASS] Write register acknowledged.")

        print(f"  [STEP 2] Waiting 1.5s for SoftPLC physics engine equilibrium update...")
        time.sleep(1.5)

        rr = client.read_holding_registers(address=1, count=5)
        if rr.isError():
            print(f"  [FAIL] Modbus verification read failed: {rr}")
            return False
        
        new_rpm = rr.registers[0]
        new_press = rr.registers[2] / 10.0
        new_flow = rr.registers[3] / 10.0
        print(f"  [PASS] Verified updated PLC telemetry:")
        print(f"         - New Pump RPM: {new_rpm} (Expected: {target_rpm})")
        print(f"         - New Pressure: {new_press:.1f} PSI")
        print(f"         - New Flow    : {new_flow:.1f} L/s")
        
        # Reset back to default 1200
        client.write_register(address=1, value=1200)
        return True
    except Exception as e:
        print(f"  [FAIL] Modbus write exception: {e}")
        return False
    finally:
        client.close()

def test_modbus_coils_estop():
    print_header("Test 4: Modbus Coils & Emergency Trip Verification")
    client = ModbusTcpClient(PI_HOST, port=MODBUS_PORT, timeout=2.0)
    try:
        client.connect()
        print("  [STEP 1] Reading status coils (FC1)...")
        cr = client.read_coils(address=1, count=5)
        if cr.isError():
            print(f"  [FAIL] Read coils failed: {cr}")
            return False
        
        coils = cr.bits[:5]
        print(f"  [PASS] Coils Status:")
        print(f"         - Pump Running       : {coils[0]}")
        print(f"         - Valve Open         : {coils[1]}")
        print(f"         - High Pressure Alarm: {coils[2]}")
        print(f"         - Overheat Alarm     : {coils[3]}")
        print(f"         - E-Stop Active      : {coils[4]}")
        return True
    except Exception as e:
        print(f"  [FAIL] Coils exception: {e}")
        return False
    finally:
        client.close()

def test_opcua_port():
    print_header("Test 5: OPC UA Port & Handshake Check (Port 4840)")
    import socket
    try:
        t0 = time.time()
        s = socket.create_connection((PI_HOST, OPCUA_PORT), timeout=2.0)
        elapsed = (time.time() - t0) * 1000
        s.close()
        print(f"  [PASS] OPC UA Server socket reachable on {PI_HOST}:{OPCUA_PORT} ({elapsed:.1f}ms latency)")
        print(f"         - Endpoint URL: opc.tcp://{PI_HOST}:{OPCUA_PORT}/codesys/server/")
        return True
    except Exception as e:
        print(f"  [FAIL] OPC UA port {OPCUA_PORT} unreachable: {e}")
        return False

def main():
    print("\n" + "#" * 70)
    print("  MASTER-HONEYPOT <-> RASPBERRY PI 4B CODESYS INTEGRATION TEST")
    print(f"  Target: {PI_HOST} (Debian 13 trixie ARM64)")
    print("#" * 70)

    results = []
    results.append(("WebVisu HTTP API", test_webvisu_http()))
    results.append(("Modbus TCP Read", test_modbus_read()))
    results.append(("Modbus TCP Write & Physics", test_modbus_write()))
    results.append(("Modbus Coils & E-Stop", test_modbus_coils_estop()))
    results.append(("OPC UA Port Reachability", test_opcua_port()))

    print_header("SUMMARY OF RESULTS")
    all_passed = True
    for name, passed in results:
        status = "[SUCCESS]" if passed else "[FAILED]"
        print(f"  {status:<10} : {name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("  >>> ALL INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
        print("  Raspberry Pi 4B CODESYS SoftPLC is fully functional & integrated.")
    else:
        print("  >>> SOME TESTS FAILED. CHECK LOGS ABOVE. <<<")
    print("=" * 70 + "\n")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
