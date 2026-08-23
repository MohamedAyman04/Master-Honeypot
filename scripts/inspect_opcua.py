#!/usr/bin/env python3
"""
OPC UA Inspector & CLI Client for Raspberry Pi SoftPLC
======================================================
Usage:
  python3 scripts/inspect_opcua.py                         # Inspect & read all live PLC variables
  python3 scripts/inspect_opcua.py --watch                 # Live auto-refreshing monitor (1s interval)
  python3 scripts/inspect_opcua.py --write PumpRPM 1600    # Write setpoint to OPC UA variable
  python3 scripts/inspect_opcua.py --write ValvePosition 0.8
  python3 scripts/inspect_opcua.py --write EmergencyStop 1
  python3 scripts/inspect_opcua.py --host 172.20.10.8      # Specify custom host
"""

import sys
import time
import argparse
import asyncio

try:
    from asyncua import Client, ua
except ImportError:
    print("\n[!] 'asyncua' library is not installed.")
    print("    Install it via: pip3 install asyncua\n")
    sys.exit(1)

parser = argparse.ArgumentParser(description="Inspect & Interact with OPC UA Server on Raspberry Pi")
parser.add_argument("--host", default="172.20.10.8", help="OPC UA Server IP (default: 172.20.10.8)")
parser.add_argument("--port", type=int, default=4840, help="OPC UA Port (default: 4840)")
parser.add_argument("--endpoint", default="/codesys/server/", help="Endpoint path (default: /codesys/server/)")
parser.add_argument("--watch", action="store_true", help="Live continuous monitoring dashboard")
parser.add_argument("--write", nargs=2, metavar=("VAR_NAME", "VALUE"), help="Write value to variable (e.g. --write PumpRPM 1500)")
args = parser.parse_args()

URL = f"opc.tcp://{args.host}:{args.port}{args.endpoint}"

async def read_plc_nodes(client):
    """Retrieves all process variables under CODESYS_RaspberryPi_PLC node."""
    ns_idx = await client.get_namespace_index("http://codesys.raspberrypi.honeypot")
    objects = client.nodes.objects
    plc = await objects.get_child([f"{ns_idx}:CODESYS_RaspberryPi_PLC"])
    children = await plc.get_children()
    
    data = []
    for child in children:
        bname = await child.read_browse_name()
        val = await child.read_value()
        try:
            attr = await child.read_attribute(ua.AttributeIds.AccessLevel)
            al_val = attr.Value.Value if attr and attr.Value else 1
            is_writable = bool(al_val & 2)
        except Exception:
            is_writable = False

        data.append({
            "name": bname.Name,
            "value": val,
            "type": type(val).__name__,
            "node_id": child.nodeid.to_string(),
            "writable": is_writable,
            "node": child
        })
    return sorted(data, key=lambda x: x["name"])

async def run():
    print("=" * 78)
    print(f"  OPC UA INSPECTOR — Master-Honeypot")
    print(f"  Target Endpoint: {URL}")
    print("=" * 78)
    
    try:
        async with Client(url=URL, timeout=3) as client:
            namespaces = await client.get_namespace_array()
            ns_idx = await client.get_namespace_index("http://codesys.raspberrypi.honeypot")
            
            # ── 1. Write Mode ────────────────────────────────────────────────────────
            if args.write:
                var_name, val_raw = args.write
                objects = client.nodes.objects
                plc = await objects.get_child([f"{ns_idx}:CODESYS_RaspberryPi_PLC"])
                try:
                    target_node = await plc.get_child([f"{ns_idx}:{var_name}"])
                except Exception:
                    print(f"\n[!] Error: Variable '{var_name}' not found under CODESYS_RaspberryPi_PLC.")
                    return

                val_before = await target_node.read_value()
                print(f"\n[*] Target Node   : {target_node.nodeid.to_string()} ({var_name})")
                print(f"[*] Current Value : {val_before}")

                # Format Variant according to data type
                if isinstance(val_before, float):
                    dv = ua.DataValue(ua.Variant(float(val_raw), ua.VariantType.Double))
                elif isinstance(val_before, bool):
                    dv = ua.DataValue(ua.Variant(val_raw.lower() in ("1", "true", "yes"), ua.VariantType.Boolean))
                else:
                    dv = ua.DataValue(ua.Variant(int(val_raw), ua.VariantType.Int64))

                await target_node.write_value(dv)
                print(f"[+] Write operation sent successfully!")
                await asyncio.sleep(0.6)
                val_after = await target_node.read_value()
                print(f"[*] Verified Value: {val_after}\n")
                return

            # ── 2. Live Watch Mode ───────────────────────────────────────────────────
            if args.watch:
                print("\n[*] Entering live watch mode (Press Ctrl+C to exit)...")
                try:
                    while True:
                        rows = await read_plc_nodes(client)
                        sys.stdout.write("\033[H\033[J")
                        print("=" * 78)
                        print(f"  OPC UA LIVE MONITOR — {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  Server URL: {URL} | Namespace: {namespaces[ns_idx]} (ns={ns_idx})")
                        print("=" * 78)
                        print(f"  {'Variable Name':<22} | {'Data Type':<10} | {'Current Value':<16} | {'Access':<8} | {'NodeId'}")
                        print("-" * 78)
                        for r in rows:
                            val_str = f"{r['value']:.2f}" if isinstance(r['value'], float) else str(r['value'])
                            access_str = "R/W" if r["writable"] else "Read"
                            print(f"  {r['name']:<22} | {r['type']:<10} | {val_str:<16} | {access_str:<8} | {r['node_id']}")
                        print("=" * 78)
                        await asyncio.sleep(1.0)
                except KeyboardInterrupt:
                    print("\n[*] Exited watch mode.")
                    return

            # ── 3. Default Summary Mode ──────────────────────────────────────────────
            print(f"\n[+] Connected to OPC UA Server successfully!")
            print(f"    - Server Endpoint : {URL}")
            print(f"    - Registered Namespaces:")
            for idx, uri in enumerate(namespaces):
                marker = " ★ (Honeypot SoftPLC)" if idx == ns_idx else ""
                print(f"        ns={idx}: {uri}{marker}")
            
            print(f"\n── Live Process Nodes (CODESYS_RaspberryPi_PLC) ──────────────────────────────")
            rows = await read_plc_nodes(client)
            print(f"  {'Variable Name':<22} | {'Data Type':<10} | {'Current Value':<16} | {'Access':<8} | {'Node Identifier'}")
            print("  " + "-" * 74)
            for r in rows:
                val_str = f"{r['value']:.2f}" if isinstance(r['value'], float) else str(r['value'])
                access_str = "R/W" if r["writable"] else "Read"
                print(f"  {r['name']:<22} | {r['type']:<10} | {val_str:<16} | {access_str:<8} | {r['node_id']}")
            print("=" * 78 + "\n")

    except Exception as e:
        print(f"\n[!] OPC UA Connection Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(run())
