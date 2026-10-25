#!/usr/bin/env python3
"""
4-Stage Active Deception Attack Chain Verification Suite
========================================================
Tests and validates the complete adaptive deception lifecycle across:
  Stage 1: Reconnaissance               -> NETWORK_TOPOLOGY_SCOUT (persona_code=1)
  Stage 2: Credential Theft             -> CREDENTIAL_VAULT_HUNTER (persona_code=2)
  Stage 3: Process Sabotage (Multi-OT)  -> PROCESS_SABOTEUR (persona_code=3)
           [Modbus TCP (RPi HIL & Fake PLC Tarpit), S7comm, DNP3, OPC-UA]
  Stage 4: PLC Logic Firmware Exploit   -> PLC_FIRMWARE_EXPLOITER (persona_code=4)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import http.cookiejar

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://dmz_gateway:8088")
INFLUX_URL = os.getenv("INFLUX_URL", "http://historian:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "supersecrettoken")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my_refinery")

def banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

class DeceptionChainTester:
    def __init__(self, username: str):
        self.username = username
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Kali-Linux; Deception-Chain-Auditor/2.0)",
            "X-Forwarded-For": "10.240.10.99"
        }

    def authenticate_into_sandbox(self) -> bool:
        banner(f"INITIAL ACCESS: Quarantining Attacker Session ({self.username}) via DMZ Gateway")
        payload = urllib.parse.urlencode({
            "username": self.username,
            "password": "password123"  # RockYou dictionary credential -> triggers silent sandbox routing
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{GATEWAY_URL}/login",
            data=payload,
            headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded"}
        )
        resp = self.opener.open(req, timeout=5.0)
        final_url = resp.geturl()
        print(f"  [+] Login HTTP Status : {resp.status}")
        print(f"  [+] Redirect Target   : {final_url}")
        assert "/dashboard" in final_url, f"Expected redirect to /dashboard, got {final_url}"
        print("  [✓] Attacker silently quarantined into Deception Sandbox!")
        return True

    def exec_cmd(self, cmd: str) -> str:
        payload = json.dumps({"command": cmd}).encode("utf-8")
        req = urllib.request.Request(
            f"{GATEWAY_URL}/action/terminal",
            data=payload,
            headers={**self.headers, "Content-Type": "application/json"}
        )
        resp = self.opener.open(req, timeout=6.0)
        data = json.loads(resp.read().decode("utf-8"))
        out = data.get("output", "") or data.get("error", "")
        return out.strip()

    def get_profile(self) -> dict:
        req = urllib.request.Request(
            f"{GATEWAY_URL}/api/deception/profile/{self.username}",
            headers=self.headers
        )
        resp = self.opener.open(req, timeout=5.0)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("profile", {})

    def run_stage(self, stage_num: int, stage_name: str, commands: list, expected_persona: str, expected_lure_keyword: str):
        banner(f"STAGE {stage_num}: {stage_name} (Expected Persona: {expected_persona})")
        for cmd in commands:
            out = self.exec_cmd(cmd)
            first_line = out.splitlines()[0] if out else "(no output)"
            print(f"  [$] {cmd}")
            print(f"      -> {first_line[:95]}")
            time.sleep(0.25)

        profile = self.get_profile()
        persona = profile.get("dominant_persona")
        scores = profile.get("normalized_scores", {})
        counts = profile.get("counts", {})
        sabo_breakdown = profile.get("sabo_breakdown", {})
        dwell = profile.get("dwell_time_s", 0.0)

        print("\n  [*] Active Deception Profile Telemetry:")
        print(f"      - Dominant Persona  : {persona}")
        print(f"      - Normalized Scores : {json.dumps(scores)}")
        print(f"      - Cumulative Counts : {json.dumps(counts)}")
        if stage_num == 3:
            print(f"      - Sabotage Protocols: {json.dumps(sabo_breakdown)}")
        print(f"      - Dwell Time        : {dwell}s (Total Commands: {profile.get('command_count')})")

        # Inspect morphed directory lures via ls -la
        ls_out = self.exec_cmd("ls -la")
        print("\n  [*] Morphed Decoy Directory Listing (ls -la):")
        for line in ls_out.splitlines():
            print(f"      {line}")

        assert persona == expected_persona, f"Stage {stage_num} failed: expected {expected_persona}, got {persona}"
        assert expected_lure_keyword in ls_out, f"Stage {stage_num} lure check failed: '{expected_lure_keyword}' not in ls -la"
        print(f"\n  [✓] STAGE {stage_num} VERIFIED: Persona={persona} | Lure='{expected_lure_keyword}' active!")
        return profile


def verify_influxdb_chain():
    banner("TELEMETRY VERIFICATION: InfluxDB 'attacker_intent' Time-Series Audit")
    flux = f'''from(bucket: "sensor_logs")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "attacker_intent")
  |> filter(fn: (r) => r["_field"] == "persona_code")
  |> keep(columns: ["_time", "persona", "_value", "attacker_ip"])
  |> group()
  |> sort(columns: ["_time"], desc: false)'''
    req = urllib.request.Request(
        f"{INFLUX_URL}/api/v2/query?org={INFLUX_ORG}",
        data=flux.encode("utf-8"),
        headers={
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Content-Type": "application/vnd.flux"
        }
    )
    resp = urllib.request.urlopen(req, timeout=5.0)
    csv_text = resp.read().decode("utf-8")
    seen_personas = []
    for expected in ["NETWORK_TOPOLOGY_SCOUT", "CREDENTIAL_VAULT_HUNTER", "PROCESS_SABOTEUR", "PLC_FIRMWARE_EXPLOITER"]:
        if expected in csv_text:
            seen_personas.append(expected)
    print(f"  [+] Distinct Persona Transitions Recorded in InfluxDB: {seen_personas}")
    for expected in ["NETWORK_TOPOLOGY_SCOUT", "CREDENTIAL_VAULT_HUNTER", "PROCESS_SABOTEUR", "PLC_FIRMWARE_EXPLOITER"]:
        assert expected in seen_personas, f"Missing persona {expected} in InfluxDB telemetry!"
    print("  [✓] All 4 Active Deception Stages confirmed in InfluxDB historian!")


def main():
    session_user = f"apt_chain_{int(time.time()) % 10000}"
    tester = DeceptionChainTester(username=session_user)
    tester.authenticate_into_sandbox()

    # STAGE 1: Reconnaissance
    tester.run_stage(
        stage_num=1,
        stage_name="Reconnaissance & OT Topology Discovery",
        commands=[
            "nmap -sT 192.168.1.16",
            "arp -a",
            "ip route",
            "netstat -tuln",
            "cat /etc/hosts",
        ],
        expected_persona="NETWORK_TOPOLOGY_SCOUT",
        expected_lure_keyword="plant_topology_map.vsdx"
    )

    # STAGE 2: Credential Theft
    tester.run_stage(
        stage_num=2,
        stage_name="Credential Harvesting & Vault Extraction",
        commands=[
            "cat /etc/passwd",
            "cat SCADA_Admin_Vault_2026.kdbx",
            "cat rpi_codesys_access.conf",
            "cat historian_connection.conf",
            "grep -i pass historian_connection.conf",
        ],
        expected_persona="CREDENTIAL_VAULT_HUNTER",
        expected_lure_keyword="id_rsa_cdu_gateway"
    )

    # STAGE 3: Process Sabotage (Modbus TCP on RPi & Fake PLC, S7comm, DNP3, OPC-UA)
    p3 = tester.run_stage(
        stage_num=3,
        stage_name="Multi-Protocol Industrial Process Sabotage",
        commands=[
            "mbtget -w6 192.168.1.16 0 1850",
            "mbtget -w6 192.168.99.15 0 2200",
            "snap7 192.168.1.16 102 write DB1.DBD0 1",
            "dnp3 192.168.1.16 20000 crob trip",
            "opcua opc.tcp://192.168.1.16:4840 write PumpRPM=1900",
            "mbtget -w6 192.168.1.16 0 1200",
        ],
        expected_persona="PROCESS_SABOTEUR",
        expected_lure_keyword="Safety_Interlock_Override_Codes.csv"
    )
    sabo = p3.get("sabo_breakdown", {})
    assert sabo.get("modbus", 0) >= 2, f"Expected modbus sabotage >= 2, got {sabo}"
    assert sabo.get("s7comm", 0) >= 1, f"Expected s7comm sabotage >= 1, got {sabo}"
    assert sabo.get("dnp3", 0) >= 1, f"Expected dnp3 sabotage >= 1, got {sabo}"
    assert sabo.get("opcua", 0) >= 1, f"Expected opcua sabotage >= 1, got {sabo}"
    print("  [✓] Multi-protocol sabotage counters verified (Modbus, S7comm, DNP3, OPC-UA)!")

    # STAGE 4: PLC Logic & Firmware Exploitation
    tester.run_stage(
        stage_num=4,
        stage_name="PLC Logic & Firmware Exploitation",
        commands=[
            "cat Refinery_PLC_Logic_Backup_2026.project",
            "cat Siemens_CPU414_Safety_OB1.s7p",
            "codesys_cli upload OB1_Main_Cycle.st --target=192.168.1.16",
            "plc_flash --firmware=codesys_rt_v3.5.19_patched.bin --target=192.168.1.16",
            "st_compile --inject=ladder_interlock_bypass.st --out=BootProject.app",
            "objdump -d BootProject.app",
        ],
        expected_persona="PLC_FIRMWARE_EXPLOITER",
        expected_lure_keyword="CODESYS_V35_Runtime_Diagnostics.log"
    )

    # Verify InfluxDB Telemetry
    time.sleep(1.0)
    verify_influxdb_chain()

    banner("ALL 4 ACTIVE DECEPTION STAGES PASSED END-TO-END VERIFICATION!")

if __name__ == "__main__":
    main()
