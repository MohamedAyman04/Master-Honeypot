"""
Dynamic Lures & Adaptive Terminal Deception Engine
===================================================
Provides adaptive contextual lures and protocol execution for the Decoy Workstations.
Interacts with:
- Physical Raspberry Pi 4B (192.168.1.16:502, :4840, :8080)
- Modbus Deception Tarpit / Fake PLC (192.168.99.15:502 / fake_plc_sim)
- S7comm Honeypot (ics_s7_plc:102)
- DNP3 Honeypot (ics_dnp3:20000)
"""

import os
import re
import socket
import struct
import time
import subprocess
from datetime import datetime

PI_HOST = os.getenv("RPI_ACTIVE_HOST", "192.168.1.16")
PI_MODBUS_PORT = int(os.getenv("RPI_MODBUS_PORT", 502))
FAKE_PLC_HOST = os.getenv("FAKE_PLC_HOST", "192.168.99.15")

DECOY_DIRECTORY_DATA = {
    "CREDENTIAL_VAULT_HUNTER": {
        "total": 412,
        "files": [
            ("-rw-------", "1", "eng_operator", "scada_eng", "4096", "Sep 19 14:03", "SCADA_Admin_Vault_2026.kdbx"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "612", "Oct 02 08:15", "rpi_codesys_access.conf"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "528", "Sep 20 18:22", "historian_connection.conf"),
            ("-rw-------", "1", "eng_operator", "scada_eng", "1675", "Sep 15 10:20", "id_rsa_cdu_gateway"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "28410", "Sep 20 08:30", "plant_topology_map.vsdx"),
            ("drwxr-xr-x", "2", "eng_operator", "scada_eng", "4096", "Sep 21 00:00", "backups"),
        ],
        "hidden": [
            ("drwxr-xr-x", "5", "eng_operator", "scada_eng", "4096", "Oct 22 10:15", "."),
            ("drwxr-xr-x", "3", "root", "root", "4096", "Sep 15 09:00", ".."),
            ("-rw-------", "1", "eng_operator", "scada_eng", "842", "Oct 20 16:30", ".bash_history"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "220", "Sep 15 09:00", ".bash_logout"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "3771", "Sep 15 09:00", ".bashrc"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "807", "Sep 15 09:00", ".profile"),
        ]
    },
    "PROCESS_SABOTEUR": {
        "total": 388,
        "files": [
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "84112", "Sep 15 11:45", "Emergency_Shutdown_Matrix_CDU01.pdf"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "18490", "Sep 21 09:30", "HMI_Alarm_Bypass_Matrix.xlsx"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "4210", "Oct 01 11:20", "Safety_Interlock_Override_Codes.csv"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "3140", "Sep 22 16:05", "Shift_Handover_Log_CCR_2026.txt"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "528", "Sep 20 18:22", "historian_connection.conf"),
            ("drwxr-xr-x", "2", "eng_operator", "scada_eng", "4096", "Sep 22 00:00", "hmi_trends"),
        ],
        "hidden": [
            ("drwxr-xr-x", "5", "eng_operator", "scada_eng", "4096", "Oct 22 10:15", "."),
            ("drwxr-xr-x", "3", "root", "root", "4096", "Sep 15 09:00", ".."),
            ("-rw-------", "1", "eng_operator", "scada_eng", "842", "Oct 20 16:30", ".bash_history"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "220", "Sep 15 09:00", ".bash_logout"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "3771", "Sep 15 09:00", ".bashrc"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "807", "Sep 15 09:00", ".profile"),
        ]
    },
    "PLC_FIRMWARE_EXPLOITER": {
        "total": 520,
        "files": [
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "248920", "Sep 18 09:12", "Refinery_PLC_Logic_Backup_2026.project"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "98120", "Sep 18 10:45", "Siemens_CPU414_Safety_OB1.s7p"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "1024", "Sep 28 14:10", "CODESYS_V35_Runtime_Diagnostics.log"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "612", "Oct 02 08:15", "rpi_codesys_access.conf"),
            ("drwxr-xr-x", "2", "eng_operator", "scada_eng", "4096", "Sep 21 00:00", "backups"),
        ],
        "hidden": [
            ("drwxr-xr-x", "5", "eng_operator", "scada_eng", "4096", "Oct 22 10:15", "."),
            ("drwxr-xr-x", "3", "root", "root", "4096", "Sep 15 09:00", ".."),
            ("-rw-------", "1", "eng_operator", "scada_eng", "842", "Oct 20 16:30", ".bash_history"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "220", "Sep 15 09:00", ".bash_logout"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "3771", "Sep 15 09:00", ".bashrc"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "807", "Sep 15 09:00", ".profile"),
        ]
    },
    "NETWORK_TOPOLOGY_SCOUT": {
        "total": 384,
        "files": [
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "248920", "Sep 18 09:12", "Refinery_PLC_Logic_Backup_2026.project"),
            ("-rw-------", "1", "eng_operator", "scada_eng", "4096", "Sep 19 14:03", "SCADA_Admin_Vault_2026.kdbx"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "84112", "Sep 15 11:45", "Emergency_Shutdown_Matrix_CDU01.pdf"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "28410", "Sep 20 08:30", "plant_topology_map.vsdx"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "528", "Sep 20 18:22", "historian_connection.conf"),
            ("drwxr-xr-x", "2", "eng_operator", "scada_eng", "4096", "Sep 21 00:00", "backups"),
        ],
        "hidden": [
            ("drwxr-xr-x", "5", "eng_operator", "scada_eng", "4096", "Oct 22 10:15", "."),
            ("drwxr-xr-x", "3", "root", "root", "4096", "Sep 15 09:00", ".."),
            ("-rw-------", "1", "eng_operator", "scada_eng", "842", "Oct 20 16:30", ".bash_history"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "220", "Sep 15 09:00", ".bash_logout"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "3771", "Sep 15 09:00", ".bashrc"),
            ("-rw-r--r--", "1", "eng_operator", "scada_eng", "807", "Sep 15 09:00", ".profile"),
        ]
    }
}

def get_directory_listing(
    persona: str,
    role: str = "engineer",
    is_long: bool = False,
    show_all: bool = False,
    one_per_line: bool = False
) -> str:
    """Generates adaptive directory contents based on active attacker persona and command flags.
    
    - When is_long is False (plain 'ls' or 'dir'), outputs only file/dir names separated by spaces.
    - When is_long is True ('ls -l', 'ls -la', 'll'), outputs full permissions, owner, size, and date.
    - When show_all is True ('ls -a', 'ls -la'), includes hidden dotfiles (., .., .bash_history).
    """
    tmpl = DECOY_DIRECTORY_DATA.get(persona, DECOY_DIRECTORY_DATA["NETWORK_TOPOLOGY_SCOUT"])
    
    entries = []
    if show_all:
        entries.extend(tmpl["hidden"])
    entries.extend(tmpl["files"])

    if is_long:
        lines = [f"total {tmpl['total']}"]
        for perm, links, user, grp, size, dt, name in entries:
            lines.append(f"{perm} {links} {user} {grp} {size:>6} {dt} {name}")
        return "\n".join(lines) + "\n"
    elif one_per_line:
        names = [e[-1] for e in entries]
        return "\n".join(names) + "\n"
    else:
        names = [e[-1] for e in entries]
        return "  ".join(names) + "\n"

def get_file_content(filename: str, username: str = "eng_operator") -> str:
    """Returns adaptive realistic contents with canary tracking tokens."""
    fn = filename.lower()
    
    if "vault" in fn or "kdbx" in fn or "key" in fn:
        return (
            "[KDBX-CANARY-TOKEN-V4]\n"
            "HEADER: HONEYTOKEN_ID=HT-KDBX-9821-MASTER\n"
            "COMMENT: Refinery Control Vault — Critical Industrial Infrastructure\n"
            "ENTRIES:\n"
            "1. Primary SoftPLC: 192.168.1.16 (Raspberry Pi 4B CODESYS) -> User: mohamed-ayman, Pass: mohamed2004\n"
            "2. HMI Web Console: http://192.168.1.16:8080 (Industrial HMI Operator View)\n"
            "3. Secondary Modbus Gateway: 192.168.99.15:502 -> User: modbus_admin, Pass: ModbusCracking2026$$\n"
            "4. Historian Root: 192.168.99.50:8086 -> User: historian_root, Token: ht_canary_hist_9918237\n"
        )
    elif "rpi_codesys_access" in fn or "codesys" in fn and "conf" in fn:
        return (
            "# ARABCO Industrial Automation — CODESYS SoftPLC Node Configuration\n"
            "PLC_HARDWARE_TARGET=Raspberry Pi 4B Industrial Edge\n"
            "PLC_IP=192.168.1.16\n"
            "MODBUS_TCP_PORT=502\n"
            "OPCUA_TCP_PORT=4840\n"
            "HMI_WEB_PORT=8080\n"
            "SSH_ADMIN_USER=mohamed-ayman\n"
            "SSH_ADMIN_PASS=mohamed2004\n"
            "ACTIVE_TASK=Hydraulic_Pipeline_Simulation_Cycle_100ms\n"
            "CANARY_ID=CANARY-CONF-RPI-CODESYS-4412\n"
        )
    elif "emergency_shutdown" in fn or "esd" in fn:
        return (
            "================================================================================\n"
            "REFINERY EMERGENCY SHUTDOWN (ESD) OVERRIDE DIRECTIVE & BYPASS MATRIX\n"
            "CLASSIFICATION: CONFIDENTIAL // OT SAFETY CRITICAL\n"
            "CANARY TOKEN: CANARY-DOC-ESD-OVERRIDE-9942\n"
            "================================================================================\n"
            "Primary Physical PLC: 192.168.1.16\n"
            "Modbus Holding Register: Register 0 (Target Pump RPM, Baseline: 1200, Max: 3000)\n"
            "Modbus Digital Coil: Coil 0x0000 (Pump Run Interlock), Coil 0x0004 (E-Stop Active)\n"
            "Command Example: mbtget -w6 192.168.1.16 0 2500  (Force Overspeed)\n"
            "Emergency Stop Code: 9942 (Sets Coil 4 HIGH)\n"
        )
    elif "shift_handover" in fn:
        return (
            "================================================================================\n"
            "CRUDE DISTILLATION UNIT (CDU-01) - CENTRAL CONTROL ROOM SHIFT HANDOVER LOG\n"
            "Date: 2026-10-18 | Shift: B | Lead Operator: J. Martinez\n"
            "CANARY_ID: CANARY-SHIFT-LOG-CDU-88219\n"
            "================================================================================\n"
            "OPERATIONAL SUMMARY: CDU-01 throughput at 98.4%. Primary SoftPLC on 192.168.1.16.\n"
            "HMI Operator View: Available on http://192.168.1.16:8080\n"
            "Secondary Modbus Unit: 192.168.99.15 (Standby Tarpit Buffer)\n"
        )
    elif "project" in fn or "s7p" in fn:
        return (
            "CODESYS_V35_APPLICATION_BINARY_METADATA\n"
            "PROJECT_NAME: ARABCO_CDU01_HYDRAULIC_PIPELINE\n"
            "TARGET_DEVICE: Raspberry_Pi_4B_CODESYS_Control_for_Raspberry_Pi\n"
            "DEVICE_ENDPOINT: opc.tcp://192.168.1.16:4840/codesys/server/\n"
            "HMI_URL: http://192.168.1.16:8080\n"
            "CANARY_TOKEN: CANARY-PLC-PROJECT-9912\n"
        )
    elif "historian_connection" in fn:
        return (
            "[HISTORIAN_REMOTE]\n"
            "HOST=192.168.99.50\n"
            "PORT=8086\n"
            "ORG=my_refinery\n"
            "BUCKET=sensor_logs\n"
            "TOKEN=supersecrettoken_canary_ht88921\n"
        )
    elif "safety_interlock" in fn or "override_codes" in fn or "alarm_bypass" in fn:
        return (
            "[SAFETY INTERLOCK & ALARM BYPASS MATRIX — CANARY-XLS-ALARM-7721]\n"
            "TAG_ID,PROTOCOL,TARGET_HOST,REGISTER_OR_NODE,OVERRIDE_KEY\n"
            "PUMP_MAIN_SPEED,MODBUS_TCP,192.168.1.16:502,HR_0,ESD-KEY-ALPHA-9942\n"
            "VALVE_DISCHARGE,MODBUS_TCP,192.168.1.16:502,HR_1,ESD-KEY-BETA-8831\n"
            "SAFETY_DB1_LOCK,S7COMM,192.168.1.16:102,DB1.DBD0,S7-OVERRIDE-4412\n"
            "BREAKER_CROB_01,DNP3,192.168.1.16:20000,CROB_IDX_0,DNP3-TRIP-9910\n"
            "OPCUA_PUMP_NODE,OPC_UA,opc.tcp://192.168.1.16:4840,ns=2;s=PumpRPM,OPC-WRITE-7741\n"
        )
    elif "diagnostics" in fn or "runtime" in fn:
        return (
            "[CODESYS Control V3.5.19.0 Runtime Log — Raspberry Pi 4B Edge PLC]\n"
            "2026-10-22 18:00:01 [INFO]CmpApp: Application 'ARABCO_CDU01_HYDRAULIC_PIPELINE' loaded from BootProject.app\n"
            "2026-10-22 18:00:02 [INFO]CmpBlkDrvTcp: Listening on 192.168.1.16:11740 (CODESYS Gateway)\n"
            "2026-10-22 18:00:02 [INFO]CmpOPCUAServer: Endpoint opc.tcp://192.168.1.16:4840 active\n"
            "2026-10-22 18:00:03 [INFO]CmpWebServer: HMI service active on http://192.168.1.16:8080\n"
            "2026-10-22 18:00:03 [WARN]CmpSecurityManager: Unauthenticatedonline change permitted in engineering mode\n"
        )
    elif "id_rsa" in fn:
        return (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
            "QyNTUxOQAAACB8x9K2CANARY_KEY_HT_SSH_99182_ARABCO_CDU01_GATEWAY_KEYAA\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        )
    elif "hosts" in fn:
        return (
            "127.0.0.1       localhost\n"
            "192.168.1.16    plc-codesys-hil.arabco.local    # Raspberry Pi 4B CODESYS SoftPLC (Physical HIL - HMI :8080)\n"
            "192.168.99.15   plc-standby-tarpit.arabco.local # Standby Modbus TCP Controller (Deception Tarpit :502)\n"
            "192.168.99.10   plc-safety-01.arabco.local      # Siemens S7-1500 Safety Controller (:102)\n"
            "192.168.99.12   plc-fccu-modbus.arabco.local    # Modbus TCP Crude Refining Unit\n"
            "172.20.10.8     plc-codesys-alt.arabco.local    # Alternate RPi HIL Interface\n"
            "192.168.99.50   historian.arabco.local          # Plant Data Historian Repository\n"
        )
    elif "passwd" in fn:
        return (
            "root:x:0:0:root:/root:/bin/bash\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            f"{username}:x:1001:1001:SCADA Engineer:/home/{username}:/bin/bash\n"
            "mohamed-ayman:x:1002:1002:Lead Automation Engineer:/home/mohamed-ayman:/bin/bash\n"
            "shift_operator:x:1003:1003:Central Control Room Shift Operator:/home/shift_operator:/bin/bash\n"
            "historian_svc:x:1004:1004:Historian Ingestion Service:/var/lib/historian:/usr/sbin/nologin\n"
        )
    elif "bash_history" in fn or "history" in fn:
        return (
            "mbtget -r3 -a0 -c5 192.168.1.16\n"
            "mbtget -w6 192.168.1.16 0 1200\n"
            "curl -s http://192.168.1.16:8080/api/status\n"
            "ping 192.168.99.15\n"
            "cat /etc/hosts\n"
            "cat rpi_codesys_access.conf\n"
        )
    return f"File content for {filename} (empty or binary data)\n"

# ── DIRECT PROTOCOL EXECUTION FOR PIVOTING ATTACKERS ──────────────────────────

def execute_modbus_command(cmd: str) -> dict:
    """Executes live Modbus commands against Raspberry Pi (192.168.1.16) or Fake PLC (192.168.99.15)."""
    # Detect target IP in command or default to physical Raspberry Pi 4B
    ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", cmd)
    if ip_match:
        target_ip = ip_match.group(1)
    elif "fake" in cmd.lower() or "standby" in cmd.lower():
        target_ip = FAKE_PLC_HOST
    else:
        target_ip = PI_HOST

    # Extract numeric arguments excluding the target IP octets
    tokens = cmd.split()
    nums = []
    for t in tokens:
        if t == target_ip:
            continue
        if t.isdigit():
            nums.append(int(t))

    is_write = any(w in cmd.lower() for w in ["-w", "-w6", "-w16", "write", "fc6", "force"])
    is_fake = (target_ip == FAKE_PLC_HOST or "192.168.99.15" in target_ip)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.5)
        s.connect((target_ip, 502))

        if is_write:
            # Parse register and value
            reg = nums[0] if len(nums) >= 1 else 0
            val = nums[1] if len(nums) >= 2 else 1500

            # Modbus FC6: Write Single Register
            trans_id = 0x0001
            req_write = struct.pack(">HHHBBHH", trans_id, 0, 6, 1, 6, reg, val)
            s.sendall(req_write)
            resp_write = s.recv(1024)

            # Wait briefly for dynamic process physics solver on the Pi to compute reaction
            time.sleep(0.35)

            # Modbus FC3: Read back holding registers 0-4 for live verification
            trans_id = 0x0002
            req_read = struct.pack(">HHHBBHH", trans_id, 0, 6, 1, 3, 0, 5)
            s.sendall(req_read)
            resp_read = s.recv(1024)
            s.close()

            regs = [0, 0, 0, 0, 0]
            if len(resp_read) >= 9:
                byte_cnt = resp_read[8]
                if len(resp_read) >= 9 + byte_cnt:
                    regs = list(struct.unpack(f">{byte_cnt//2}H", resp_read[9:9+byte_cnt]))

            if is_fake:
                out = (
                    f"Values: [{val}] - Register write acknowledged by Standby Controller ({target_ip}:502)\n"
                    f"Modbus Response: ExceptionCode=0 (SUCCESS), TransID={trans_id}, UnitID=1\n"
                    f"[*] Note: Standby controller holding register {reg} status unchanged (Tarpit Active).\n"
                )
            else:
                out = (
                    f"[+] Modbus FC6 Write Confirmed on Physical Raspberry Pi ({target_ip}:502)!\n"
                    f"    Register [{reg}] successfully updated to value: {val}\n"
                    f"    Live Verification Readback: Reg 0 (Pump RPM)={regs[0]} | Reg 1 (Valve)={regs[1]/10.0:.1f}% | "
                    f"Reg 2 (Pressure)={regs[2]/10.0:.1f} PSI | Reg 3 (Flow)={regs[3]/10.0:.1f} L/s\n"
                    f"    CODESYS SoftPLC hydraulic ODE simulation state dynamically converged.\n"
                )
            return {"output": out, "error": ""}

        else:
            # Modbus FC3: Read Holding Registers
            start = nums[0] if len(nums) >= 1 else 0
            count = nums[1] if len(nums) >= 2 else 5
            count = min(max(count, 1), 20)

            trans_id = 0x0003
            req_read = struct.pack(">HHHBBHH", trans_id, 0, 6, 1, 3, start, count)
            s.sendall(req_read)
            resp_read = s.recv(1024)
            s.close()

            if len(resp_read) >= 9:
                byte_cnt = resp_read[8]
                regs = list(struct.unpack(f">{byte_cnt//2}H", resp_read[9:9+byte_cnt]))
                out = f"Modbus FC3 Read response from {target_ip}:502 (Holding Registers {start}-{start+len(regs)-1}):\n"
                for i, r in enumerate(regs):
                    addr = start + i
                    label = ""
                    if addr == 0: label = f" (Pump RPM: {r} RPM)"
                    elif addr == 1: label = f" (Valve Pos: {r/10.0:.1f}%)"
                    elif addr == 2: label = f" (Pressure: {r/10.0:.1f} PSI)"
                    elif addr == 3: label = f" (Flow Rate: {r/10.0:.1f} L/s)"
                    elif addr == 4: label = f" (Temperature: {r/10.0:.1f} °C)"
                    out += f"  Reg {addr:2d} : {r:5d}{label}\n"
                return {"output": out, "error": ""}
            else:
                return {"output": f"[-] Modbus response error from {target_ip}:502\n", "error": "InvalidPacket"}

    except Exception as e:
        if is_write:
            reg = nums[0] if len(nums) >= 1 else 0
            val = nums[1] if len(nums) >= 2 else 1500
            rpm = val if reg == 0 else 1200
            press = round(122.0 + (rpm - 1200) * 0.078, 1)
            flow = round(max(0.0, rpm * 0.01), 1)
            out = (
                f"[+] Modbus FC6 Write Confirmed on Physical Raspberry Pi ({target_ip}:502)!\n"
                f"    Register [{reg}] successfully updated to value: {val}\n"
                f"    Live Verification Readback: Reg 0 (Pump RPM)={rpm} | Reg 1 (Valve)=50.0% | "
                f"Reg 2 (Pressure)={press} PSI | Reg 3 (Flow)={flow} L/s\n"
                f"    CODESYS SoftPLC hydraulic ODE simulation state dynamically converged.\n"
            )
            return {"output": out, "error": ""}
        else:
            out = (
                f"Modbus FC3 Read response from {target_ip}:502 (Holding Registers 0-4):\n"
                f"  Reg  0 :  1200 (Pump RPM: 1200 RPM)\n"
                f"  Reg  1 :   500 (Valve Pos: 50.0%)\n"
                f"  Reg  2 :  1224 (Pressure: 122.4 PSI)\n"
                f"  Reg  3 :   120 (Flow Rate: 12.0 L/s)\n"
                f"  Reg  4 :   250 (Temperature: 25.0 °C)\n"
            )
            return {"output": out, "error": ""}

def execute_s7comm_command(cmd: str) -> dict:
    """Simulates S7comm interaction against Raspberry Pi or ics_s7_plc."""
    out = (
        f"[+] S7comm ISO-on-TCP Handshake with Siemens S7 Controller (192.168.1.16:102):\n"
        f"    COTP Connection: Confirmed (CC, TPDU size=1024)\n"
        f"    S7 Protocol Setup: Negotiated PDU Size = 480 bytes\n"
        f"    CPU Status: RUN | Module: CPU 414-3 PN/DP | Rack: 0 | Slot: 2\n"
    )
    if "write" in cmd.lower() or "stop" in cmd.lower() or "db" in cmd.lower():
        out += (
            f"    [!] S7comm Function 0x05 (Write Var) executed on DB1.DBD0.\n"
            f"    PLC Safety DB1 block override confirmed. Interlock bit force acknowledged.\n"
        )
    return {"output": out, "error": ""}

def execute_dnp3_command(cmd: str) -> dict:
    """Simulates DNP3 Outstation interaction against Raspberry Pi or ics_dnp3."""
    out = (
        f"[+] DNP3 Link-Layer Session Active (Target: 192.168.1.16:20000 | Outstation: 1):\n"
        f"    Function 0x00 (CONFIRM / ACK) received. Sequence: 4\n"
    )
    if "control" in cmd.lower() or "direct" in cmd.lower() or "trip" in cmd.lower():
        out += (
            f"    [!] DNP3 Function 0x05 (DIRECT_OPERATE) accepted by Outstation.\n"
            f"    CROB Status: Control Relay Output Block code 0x01 (TRIP) confirmed on Index 0.\n"
        )
    return {"output": out, "error": ""}

def execute_opcua_command(cmd: str) -> dict:
    """Interacts with OPC UA server on Raspberry Pi (192.168.1.16:4840)."""
    out = (
        f"[+] OPC UA Binary Session Connected to opc.tcp://192.168.1.16:4840/codesys/server/:\n"
        f"    Server: CODESYS Control for Raspberry Pi 4B (Version: 3.5.19)\n"
        f"    Namespace Index: http://codesys.raspberrypi.honeypot\n"
    )
    if "write" in cmd.lower() or "set" in cmd.lower() or "stop" in cmd.lower():
        out += (
            f"    [!] WriteAttribute (AccessLevel=CurrentWrite) confirmed for node ns=2;s=CODESYS_RaspberryPi_PLC.PumpRPM\n"
            f"    StatusCode: Good (0x00000000)\n"
        )
    else:
        out += (
            f"    Nodes Discovered: [PumpRPM, ValvePosition, Pressure_PSI, FlowRate_Ls, Temperature_C, EmergencyStop]\n"
        )
    return {"output": out, "error": ""}

def execute_firmware_command(cmd: str) -> dict:
    """Simulates PLC logic and firmware manipulation commands against CODESYS SoftPLC / S7-400."""
    out = (
        f"[+] CODESYS V3.5 / STEP7 Engineering Toolchain Connected (Target: 192.168.1.16:11740)\n"
        f"    Runtime Version: CODESYS Control V3.5.19.0 (ARM64 Linux / Raspberry Pi 4B)\n"
        f"    Active Application: ARABCO_CDU01_HYDRAULIC_PIPELINE (CRC32: 0x8F4A29E1)\n"
        f"    [!] Online Change / Logic Block Transfer staged in Deception Sandbox Buffer.\n"
        f"    Status: BootProject.app & OB1_Main_Cycle.st checksum verified (CANARY-FW-8821).\n"
    )
    return {"output": out, "error": ""}
