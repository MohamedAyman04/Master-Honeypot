import os
import time
import math
import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app
from .models import User
from .app import log_login_attempt_detailed, log_successful_login, log_failed_login, log_activity
from . import l2_bridge  # Level 2 ↔ Level 3 integration bridge


auth_bp = Blueprint('auth', __name__)


def _user_role():
    return session.get('role', 'operator')


def _has_role(allowed_roles):
    return _user_role() in allowed_roles


def _device_profile():
    profile = current_app.config.get('WORKSTATION_DEVICE_PROFILE', {})
    component = current_app.config.get('WORKSTATION_COMPONENT', 'workstation_1')

    # Authentic industrial node name mapping (never disclose 'decoy' or 'sandbox' to the UI)
    name_map = {
        'workstation_1': 'WS-ENG-01',
        'workstation_2': 'WS-ENG-02',
        'workstation_3': 'WS-OPS-01',
        'workstation_4': 'WS-OPS-02',
        'workstation_decoy': 'WS-ENG-02',
        'workstation_decoy_eng': 'WS-ENG-02',
        'workstation_decoy_eng_02': 'WS-ENG-03',
        'workstation_decoy_ops': 'WS-OPS-02',
        'workstation_decoy_ops_02': 'WS-OPS-03',
        'workstation_decoy_main': 'WS-CCR-MAIN',
    }
    display_component = name_map.get(
        component,
        component.replace('decoy_', '').replace('_decoy', '').replace('_', '-').upper()
    )

    serial = profile.get('serial') or 'FAC-ENG-2401'
    serial = serial.replace('-DECOY', '').replace('_DECOY', '').replace('DECOY-', '')

    model = profile.get('model') or 'Siemens IPC477E Industrial PC'
    model = model.replace(' Decoy', '').replace(' decoy', '').replace('Decoy ', '')

    return {
        'component': display_component,
        'ip': profile.get('ip') or os.getenv('WORKSTATION_DEVICE_IP', '192.168.50.21'),
        'mac': profile.get('mac') or os.getenv('WORKSTATION_DEVICE_MAC', '02:42:c0:a8:32:15'),
        'serial': serial,
        'model': model,
        'vendor': profile.get('vendor') or 'Siemens Industrial',
    }


@auth_bp.before_app_request
def track_request_in():
    # Reverse proxy gateway authentication bridge
    if request.headers.get('X-Gateway-Auth') == 'true':
        gw_user = request.headers.get('X-Gateway-User')
        if gw_user:
            session['logged_in'] = True
            session['user'] = gw_user
            session['role'] = request.headers.get('X-Gateway-Role', 'operator')

    if request.path.startswith('/static') or request.path == '/activity':
        return

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    username = session.get('user', 'ANON')
    log_activity(
        'REQUEST_IN',
        f"IP={ip_address} || METHOD={request.method} || PATH={request.path} || USER={username}"
    )


@auth_bp.after_app_request
def track_request_out(response):
    if request.path.startswith('/static') or request.path == '/activity':
        return response

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    location = response.headers.get('Location', 'NONE')
    username = session.get('user', 'ANON')
    log_activity(
        'REQUEST_OUT',
        (
            f"IP={ip_address} || METHOD={request.method} || PATH={request.path} || "
            f"STATUS={response.status_code} || REDIRECT_TO={location} || USER={username}"
        )
    )

    return response


@auth_bp.route('/')
def index():
    log_activity('ROUTE', 'SOURCE=/ || ACTION=REDIRECT || TARGET=/login')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        log_activity('PAGE_VIEW', f"PAGE=/login || IP={ip_address}")
        return render_template('login.html')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        log_activity('LOGIN_SUBMIT', f"IP={ip_address} || USERNAME={username}")
        db_accessed = False
        user_found = False

        try:
            db_accessed = True
            user = User.query.filter_by(username=username, password=password).first()
            user_found = user is not None
        except Exception as exc:
            log_login_attempt_detailed(
                username=username,
                password=password,
                ip_address=ip_address,
                db_accessed=db_accessed,
                user_found=False,
                auth_result='ERROR',
                db_error=str(exc)
            )
            return render_template('login.html', error='Login service error')

        log_login_attempt_detailed(
            username=username,
            password=password,
            ip_address=ip_address,
            db_accessed=db_accessed,
            user_found=user_found,
            auth_result='SUCCESS' if user_found else 'FAILED'
        )

        if user:
            session['user'] = user.username
            session['user_id'] = user.id
            session['role'] = user.role
            session['logged_in'] = True
            log_successful_login(user.username, ip_address)
            log_activity('ROUTE', f"SOURCE=/login || ACTION=REDIRECT || TARGET=/dashboard || USER={user.username}")
            return redirect(url_for('auth.dashboard'))

        log_failed_login(username, ip_address)
        return render_template('login.html', error='Invalid username or password')


@auth_bp.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        log_activity('AUTH_GUARD', 'PAGE=/dashboard || ACTION=REDIRECT_LOGIN || REASON=NOT_LOGGED_IN')
        return redirect(url_for('auth.login'))

    log_activity('PAGE_VIEW', f"PAGE=/dashboard || USER={session.get('user', 'ANON')}")
    return render_template(
        'dashboard.html',
        username=session.get('user', 'operator'),
        role=_user_role(),
        device_profile=_device_profile(),
    )


@auth_bp.route('/logout')
def logout():
    user_before_logout = session.get('user', 'ANON')
    session.clear()
    log_activity('LOGOUT', f"USER={user_before_logout} || ACTION=SESSION_CLEARED")
    return redirect(url_for('auth.login'))


@auth_bp.route('/activity', methods=['POST'])
def capture_activity():
    payload = request.get_json(silent=True) or {}
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    event_name = str(payload.get('event', 'UNKNOWN'))
    target = str(payload.get('target', 'UNKNOWN'))
    current_path = str(payload.get('path', 'UNKNOWN'))
    destination = str(payload.get('destination', 'NONE'))
    username = session.get('user', 'ANON')

    log_activity(
        'CLIENT_EVENT',
        (
            f"IP={ip_address} || USER={username} || EVENT={event_name} || TARGET={target} || "
            f"PATH={current_path} || DESTINATION={destination}"
        )
    )

    return jsonify({'status': 'ok'})


@auth_bp.route('/action/ack-alarm', methods=['POST'])
def ack_alarm():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    if not _has_role({'operator', 'engineer', 'admin'}):
        return jsonify({'error': 'forbidden'}), 403

    log_activity('ROLE_ACTION', f"USER={session.get('user', 'ANON')} || ROLE={_user_role()} || ACTION=ACK_ALARM")
    return jsonify({'status': 'ok', 'message': 'Alarm acknowledged'})


@auth_bp.route('/action/basic-control', methods=['POST'])
def basic_control():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    if not _has_role({'operator', 'engineer', 'admin'}):
        return jsonify({'error': 'forbidden'}), 403

    log_activity('ROLE_ACTION', f"USER={session.get('user', 'ANON')} || ROLE={_user_role()} || ACTION=BASIC_CONTROL")
    return jsonify({'status': 'ok', 'message': 'Basic control action sent'})


@auth_bp.route('/action/engineering-tool', methods=['POST'])
def engineering_tool():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    if not _has_role({'engineer', 'admin'}):
        return jsonify({'error': 'forbidden'}), 403

    log_activity('ROLE_ACTION', f"USER={session.get('user', 'ANON')} || ROLE={_user_role()} || ACTION=ENGINEERING_TOOL")
    return jsonify({'status': 'ok', 'message': 'Engineering tool executed'})


@auth_bp.route('/action/system-config', methods=['POST'])
def system_config():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    if not _has_role({'admin'}):
        return jsonify({'error': 'forbidden'}), 403

    log_activity('ROLE_ACTION', f"USER={session.get('user', 'ANON')} || ROLE={_user_role()} || ACTION=SYSTEM_CONFIG")
    return jsonify({'status': 'ok', 'message': 'System configuration updated'})


@auth_bp.route('/action/terminal', methods=['POST'])
def terminal_exec():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(force=True, silent=True) or {}
    cmd = data.get('command', '')
    if not cmd:
        return jsonify({'error': 'No command provided'})

    username = session.get('user', 'ANON')
    role = _user_role()
    log_activity('ROLE_ACTION', f"USER={username} || ROLE={role} || ACTION=TERMINAL || CMD={cmd}")

    try:
        import json, datetime, os
        log_path = "/app/general logs.jsonl"
        
        # MITRE ATT&CK Mapping
        mitre_id = "T0802" # Default to Automated Collection
        mitre_tactic = "Automated Collection"
        mitre_name = "Automated Collection"
        if "mbtget" in cmd:
            if "-w" in cmd:
                mitre_id = "T0855"
                mitre_tactic = "Execution"
                mitre_name = "Unauthorized Command Message"
            else:
                mitre_id = "T0802"
                mitre_tactic = "Collection"
                mitre_name = "Automated Collection"
        elif "nmap" in cmd or "ping" in cmd or "nc " in cmd:
            mitre_id = "T0846"
            mitre_tactic = "Discovery"
            mitre_name = "Network Service Discovery"
        elif "ssh " in cmd:
            mitre_id = "T0866"
            mitre_tactic = "Lateral Movement"
            mitre_name = "Exploitation of Remote Services"
        elif "cat " in cmd or "tail " in cmd:
            mitre_id = "T0802"
            mitre_tactic = "Collection"
            mitre_name = "Automated Collection"

        # Determine severity based on command
        if "mbtget" in cmd and "-w" in cmd:
            severity = "CRITICAL"
        elif "ssh" in cmd or "nmap" in cmd or "nc " in cmd:
            severity = "HIGH"
        else:
            severity = "INFO"

        with open(log_path, "a") as f:
            f.write(json.dumps({
                "ts": datetime.datetime.now().isoformat() + "Z",
                "sensor": "workstation",
                "event_type": "terminal_command",
                "src_ip": request.headers.get('X-Forwarded-For', request.remote_addr),
                "stage": "S1",
                "journey_id": "terminal_exec",
                "outcome": "observed",
                "level": "Level 2",
                "severity": severity,
                "mitre_technique_id": mitre_id,
                "mitre_tactic": mitre_tactic,
                "mitre_technique_name": mitre_name,
                "meta": {
                    "user": username,
                    "role": role,
                    "command": cmd,
                    "message": f"Terminal command executed: {cmd}",
                    "component": "workstation_terminal",
                    "level": "Level 2"
                }
            }) + "\n")

        # Push to Monitor Net Historian via Proxy Gateway
        proxy_gw = os.getenv("PROXY_GATEWAY_URL", os.getenv("LEVEL2_HISTORIAN_URL", "http://historian_api:5000"))
        try:
            requests.post(f"{proxy_gw}/api/external-event", json={
                "event_type": "WORKSTATION_COMMAND",
                "source": os.getenv("HOSTNAME", "ws_decoy_main"),
                "detail": f"User {username} executed {cmd[:80]} | MITRE={mitre_id}",
                "severity": severity
            }, timeout=1.5)
        except Exception:
            pass
    except Exception:
        pass

    if os.getenv("IS_DECOY", "false").lower() == "true":
        cmd_clean = cmd.strip()
        cmd_lower = cmd_clean.lower()
        decoy_role = os.getenv("DECOY_ROLE", "engineer").lower()
        raw_host = os.getenv("HOSTNAME", "ws-eng-02")
        hostname = "ws-eng-02" if "decoy" in raw_host.lower() else raw_host
        device_mac = os.getenv("WORKSTATION_DEVICE_MAC", "02:42:c0:a8:63:15")
        err = ""

        if cmd_clean == "ls":
            if decoy_role == "operator":
                out = "Emergency_Shutdown_Procedure_SOP_Rev4.pdf  HMI_Alarm_Bypass_Matrix.xlsx  Shift_Handover_Log_CCR_2026.txt  historian_connection.conf  hmi_trends  plant_topology_map.vsdx\n"
            else:
                out = "Refinery_PLC_Logic_Backup_2026.s7p  SCADA_Admin_Master_Keys.kdbx  Safety_Interlock_Bypass_Codes.pdf  backups  historian_connection.conf  plant_topology_map.vsdx\n"
        elif cmd_lower in ("ls -l", "ls -la", "dir"):
            if decoy_role == "operator":
                out = (
                    "total 296\n"
                    "-rw-r--r-- 1 shift_operator scada_ops  48120 Sep 22 14:10 Emergency_Shutdown_Procedure_SOP_Rev4.pdf\n"
                    "-rw-r--r-- 1 shift_operator scada_ops   3140 Sep 22 16:05 Shift_Handover_Log_CCR_2026.txt\n"
                    "-rw-r--r-- 1 shift_operator scada_ops  18490 Sep 21 09:30 HMI_Alarm_Bypass_Matrix.xlsx\n"
                    "-rw-r--r-- 1 shift_operator scada_ops  28410 Sep 20 08:30 plant_topology_map.vsdx\n"
                    "-rw-r--r-- 1 shift_operator scada_ops    528 Sep 20 18:22 historian_connection.conf\n"
                    "drwxr-xr-x 2 shift_operator scada_ops   4096 Sep 22 00:00 hmi_trends\n"
                )
            else:
                out = (
                    "total 384\n"
                    "-rw-r--r-- 1 eng_operator scada_eng 248920 Sep 18 09:12 Refinery_PLC_Logic_Backup_2026.s7p\n"
                    "-rw------- 1 eng_operator scada_eng   4096 Sep 19 14:03 SCADA_Admin_Master_Keys.kdbx\n"
                    "-rw-r--r-- 1 eng_operator scada_eng  84112 Sep 15 11:45 Safety_Interlock_Bypass_Codes.pdf\n"
                    "-rw-r--r-- 1 eng_operator scada_eng  28410 Sep 20 08:30 plant_topology_map.vsdx\n"
                    "-rw-r--r-- 1 eng_operator scada_eng    528 Sep 20 18:22 historian_connection.conf\n"
                    "drwxr-xr-x 2 eng_operator scada_eng   4096 Sep 21 00:00 backups\n"
                )
        elif "shift_handover" in cmd_lower:
            out = (
                "================================================================================\n"
                "CRUDE DISTILLATION UNIT (CDU-01) - CENTRAL CONTROL ROOM SHIFT HANDOVER LOG\n"
                "Date: 2026-09-22 | Shift: B (16:00 - 00:00) | Lead Operator: J. Martinez\n"
                "CANARY_ID: CANARY-SHIFT-LOG-CDU-88219\n"
                "================================================================================\n"
                "OPERATIONAL SUMMARY: CDU-01 throughput at 98.4%. Column pressure 102.4 PSI.\n"
                "RESTRICTION: Furnace interlock I-402 in AUTO PID. Lockbox #4 code: 8492.\n"
                "Historian Ingestion Gateway: 192.168.99.50:8086 (Token: canary_tok_ops_99182a)\n"
            )
        elif "emergency_shutdown" in cmd_lower:
            out = (
                "[PDF CANARY DOCUMENT: CANARY-SOP-ESD-OVERRIDE-9912]\n"
                "Title: CDU-01 Standard Operating Procedure - Emergency Shutdown Bypass Protocol\n"
                "Direct Command: Force coil 0x002A on 192.168.99.10 to value 1.\n"
                "Master ESD Override Code: 9942\n"
            )
        elif "hmi_alarm" in cmd_lower or "alarm_bypass" in cmd_lower:
            out = (
                "[SPREADSHEET CANARY: CANARY-XLS-ALARM-7721]\n"
                "TAG_ID,ALARM_PRIORITY,SUPPRESSION_KEY,OPERATOR_OVERRIDE_PIN\n"
                "PT-101_HIGH_PRESS,CRITICAL,SUPPRESS_AUTH_9921,8831\n"
                "TT-204_TEMP_RUNAWAY,HIGH,SUPPRESS_AUTH_9922,4412\n"
                "FT-301_FEED_LOSS,CRITICAL,SUPPRESS_AUTH_9923,9910\n"
            )
        elif "scada_admin_master_keys.kdbx" in cmd_lower:
            out = (
                "[KDBX-CANARY-TOKEN-V4]\n"
                "HEADER: HONEYTOKEN_ID=HT-KDBX-9821-MASTER\n"
                "SIGNATURE: 0x9AA2D9BF03040002\n"
                "COMMENT: Critical Industrial Infrastructure Credentials Vault - Level 2 / Level 3 Plant Access\n"
                "ENTRIES:\n"
                "1. Host: 192.168.99.10 (Siemens S7-1500) -> User: plc_engineer, Pass: S7_Safety_Override#2026!\n"
                "2. Host: 192.168.99.12 (Modbus FCCU) -> User: modbus_admin, Pass: ModbusCracking2026$$\n"
                "3. Host: 192.168.99.50 (Historian Root) -> User: historian_root, Pass: MasterHistorianKey_9918237\n"
            )
        elif "safety_interlock_bypass_codes.pdf" in cmd_lower:
            out = (
                "================================================================================\n"
                "REFINERY EMERGENCY SHUTDOWN (ESD) OVERRIDE DIRECTIVE & BYPASS MATRIX\n"
                "CLASSIFICATION: CONFIDENTIAL // OT SAFETY CRITICAL\n"
                "DOCUMENT ID: ESD-BYPASS-SEC-2026-04\n"
                "CANARY TOKEN: CANARY-DOC-ESD-OVERRIDE-9942\n"
                "================================================================================\n"
                "Safety PLC Address: 192.168.99.10\n"
                "Modbus Register: Coil 0x002A (Address 40042)\n"
                "Override Value: 0x0001 (FORCE HIGH)\n"
                "ESD Master Bypass Auth Key: ESD-KEY-ALPHA-9942-MASTER\n"
            )
        elif "refinery_plc_logic_backup_2026.s7p" in cmd_lower:
            out = (
                "SIMATIC_STEP7_PROJECT_BACKUP_V5.6\n"
                "PROJECT_NAME: REFINERY_DISTILLATION_MAIN_2026\n"
                "PLC_TYPE: SIEMENS_CPU_414_3_PN_DP\n"
                "STATION_IP: 192.168.99.10\n"
                "[BLOCK_DB1] DB_NAME: 'SAFETY_INTERLOCK_VARS' DBX0.0: 'EMERGENCY_STOP_ACTUATED'=FALSE\n"
            )
        elif "historian_connection.conf" in cmd_lower:
            out = (
                "[HISTORIAN_REMOTE]\n"
                "HOST=192.168.99.50\n"
                "PORT=8086\n"
                "ORG=my_refinery\n"
                "BUCKET=sensor_logs\n"
                "TOKEN=supersecrettoken_canary_ht88921\n"
            )
        elif cmd_lower in ("whoami",):
            out = f"{username}\n"
        elif cmd_lower in ("id",):
            out = f"uid=1001({username}) gid=1001(scada_eng) groups=1001(scada_eng),27(sudo)\n"
        elif cmd_lower in ("pwd",):
            out = f"/home/{username}/scada_workspace\n"
        elif cmd_lower in ("uname -a", "uname"):
            out = f"Linux {hostname} 5.15.0-89-generic #99-Ubuntu SMP x86_64 GNU/Linux\n"
        elif cmd_lower in ("ifconfig", "ip a", "ip addr"):
            out = (
                "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
                f"        inet {device_ip}  netmask 255.255.255.0  broadcast 192.168.99.255\n"
                f"        ether {device_mac}  txqueuelen 0  (Ethernet)\n"
            )
        elif "cat /etc/passwd" in cmd_lower:
            out = (
                "root:x:0:0:root:/root:/bin/bash\n"
                "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                f"{username}:x:1001:1001:SCADA Engineer:/home/{username}:/bin/bash\n"
                "shift_operator:x:1002:1002:Central Control Room Shift Operator:/home/shift_operator:/bin/bash\n"
                "historian_svc:x:1003:1003:Historian Ingestion Service:/var/lib/historian:/usr/sbin/nologin\n"
            )
        elif "mbtget" in cmd_lower or "modbus" in cmd_lower:
            out = "Values: [1, 0, 1, 0, 0, 1] - Register write confirmed to 192.168.99.12\n"
        elif "nmap" in cmd_lower or "ping" in cmd_lower:
            out = (
                "Starting Nmap 7.80 ( https://nmap.org )\n"
                "Nmap scan report for plc-safety-01 (192.168.99.10)\n"
                "Host is up (0.00041s latency).\n"
                "PORT    STATE SERVICE\n"
                "102/tcp open  iso-tsap (Siemens S7)\n"
                "502/tcp open  mbap (Modbus TCP)\n"
            )
        else:
            out = f"Command executed: {cmd_clean}\n"

        return jsonify({'output': out, 'error': err})


    cmd_clean = cmd.strip()
    cmd_lower = cmd_clean.lower()
    
    # Industrial SCADA command simulations
    if "mbtget" in cmd_lower or "modbus" in cmd_lower:
        out = (
            "Values: [1, 0, 1, 0, 0, 1] - Register write confirmed to 192.168.99.12\n"
            "Modbus Response: ExceptionCode=0 (SUCCESS), TransID=4921, UnitID=1"
        )
        return jsonify({'output': out, 'error': ''})
    elif "snap7" in cmd_lower or ("s7" in cmd_lower and "102" in cmd_lower):
        out = (
            "Connected to Siemens S7-1500 PLC at 192.168.99.10:102 (Rack 0, Slot 1)\n"
            "CPU State: RUN | Firmware: V2.8.3 | DB1 Size: 1024 bytes"
        )
        return jsonify({'output': out, 'error': ''})
    elif "nmap" in cmd_lower or "ping" in cmd_lower:
        out = (
            "Starting Nmap 7.80 ( https://nmap.org )\n"
            "Nmap scan report for plc-safety-01 (192.168.99.10)\n"
            "Host is up (0.00041s latency).\n"
            "PORT     STATE SERVICE\n"
            "102/tcp  open  iso-tsap (Siemens S7)\n"
            "502/tcp  open  mbap (Modbus TCP)\n"
            "4840/tcp open  opcua (OPC Unified Architecture)\n"
        )
        return jsonify({'output': out, 'error': ''})
    elif cmd_lower in ("whoami",):
        return jsonify({'output': f"{username}\n", 'error': ''})
    elif cmd_lower in ("id",):
        return jsonify({'output': f"uid=1001({username}) gid=1001(scada_{role}) groups=1001(scada_{role}),27(sudo)\n", 'error': ''})
    elif cmd_lower in ("help", "man"):
        out = (
            "ARABCO Industrial Workstation Shell (v3.4-ot)\n"
            "Standard commands: ls, whoami, id, pwd, uname, ip, ifconfig, cat, ps, uptime, date, clear\n"
            "SCADA diagnostics: mbtget, snap7, nmap, ping\n"
        )
        return jsonify({'output': out, 'error': ''})


    # Native container execution for standard commands
    import subprocess
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=2.0
        )
        out = proc.stdout
        err = proc.stderr
        if not out and not err:
            out = f"[Command executed successfully, returncode={proc.returncode}]"
        return jsonify({'output': out, 'error': err})
    except subprocess.TimeoutExpired:
        return jsonify({'output': '', 'error': f"Command execution timed out (>2s): {cmd[:40]}"})
    except Exception as exc:
        return jsonify({'output': '', 'error': f"Execution error: {str(exc)}"})


@auth_bp.route('/api/historian/query', methods=['GET', 'POST'])
def historian_query():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401

    if request.method == 'POST':
        data = request.get_json(force=True, silent=True) or request.form.to_dict()
        user_input = data.get('query', '').strip()
    else:
        user_input = request.args.get('query', '').strip()

    if not user_input:
        user_input = "SELECT id, tag_id, sensor_name, value, unit, status, location, timestamp FROM sensor_readings ORDER BY id ASC LIMIT 25"

    username = session.get('user', 'ANON')
    role = _user_role()

    import re, sqlite3, time
    from pathlib import Path

    # Detect SQL injection attack patterns
    sqli_patterns = [
        r"(\bUNION\b\s+SELECT\b)",
        r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b.*(\bOR\b|\bAND\b).*(['\"].*['\"]|\d+=\d+))",
        r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)",
        r"(--|/\*|\*/|;\s*$)",
        r"(\bDROP\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b)",
        r"(\bsqlite_master\b|\bsystem_secrets\b)"
    ]
    is_sqli = any(re.search(pat, user_input, re.IGNORECASE) for pat in sqli_patterns)

    if is_sqli:
        log_activity('SECURITY_ALERT', f"SQL_INJECTION_DETECTED || USER={username} || INPUT={user_input}")
        try:
            from components.common.story_client import StoryClient
            StoryClient(component="workstation_historian", level="Level 3").log(
                event_type="sql_injection",
                message=f"SQL Injection attempt in Historian Query Console: {user_input[:100]}",
                severity="critical",
                details={
                    "user": username,
                    "role": role,
                    "payload": user_input,
                    "mitre_id": "T0855",
                    "tactic": "Execution / Collection",
                    "ip": request.headers.get('X-Forwarded-For', request.remote_addr)
                }
            )
        except Exception:
            pass

    # Resolve database path
    component_name = (os.getenv('WORKSTATION_COMPONENT', 'workstation_1') or 'workstation_1').strip()
    raw_db_name = (os.getenv('WORKSTATION_DB_NAME', f'{component_name}.db') or f'{component_name}.db').strip()
    db_file_name = Path(raw_db_name).name
    if not db_file_name.endswith('.db'):
        db_file_name = f'{db_file_name}.db'
    repo_root = Path(__file__).resolve().parents[4]
    db_path = repo_root / 'database-files' / 'workstations' / db_file_name

    start_time = time.time()
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        cursor = conn.cursor()

        # If user input looks like a full SELECT query or contains UNION, run directly (vulnerable)
        if user_input.strip().upper().startswith('SELECT') or 'UNION' in user_input.upper():
            sql = user_input
        else:
            # Vulnerable string interpolation allowing SQL injection:
            sql = f"SELECT id, tag_id, sensor_name, value, unit, status, location, timestamp FROM sensor_readings WHERE sensor_name LIKE '%{user_input}%' OR tag_id LIKE '%{user_input}%' ORDER BY id ASC LIMIT 50"

        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        conn.close()

        return jsonify({
            'success': True,
            'query': sql,
            'columns': columns,
            'rows': rows,
            'count': len(rows),
            'elapsed_ms': elapsed_ms,
            'is_sqli': is_sqli
        })
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return jsonify({
            'success': False,
            'query': user_input,
            'error': str(exc),
            'elapsed_ms': elapsed_ms,
            'is_sqli': is_sqli
        }), 400




# ═══════════════════════════════════════════════════════════════════════════════
# Level 2 Integration Bridge — /api/l2/*
# ───────────────────────────────────────────────────────────────────────────────
# These routes proxy requests from the Level 3 workstation dashboard to the
# Level 2 physics REST API and historian API via the l2l3-bridge-net network.
#
# Cross-layer attack path demonstrated here:
#   L3 Workstation (/api/l2/control) → l2_bridge.send_control_command()
#   → POST http://172.28.0.10:5100/api/physics/control
#   → PipelineSimulator.set_pump_rpm() / set_valve_pos()
#   ATT&CK: T0855 — Unauthorized Command Message
#   Kill Chain: Actions on Objectives
# ═══════════════════════════════════════════════════════════════════════════════

@auth_bp.route('/api/l2/status', methods=['GET'])
def l2_status():
    """
    GET /api/l2/status
    Decoy Honeypot: Queries live dynamic physics & RPi HIL SoftPLC under attack.
    Real Workstation: Returns pristine steady-state industrial status for operators.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_STATUS || TARGET=L2_PHYSICS_API")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        # Sandboxed Honeypot Zone: Live dynamic physics status (masked for high fidelity)
        data = l2_bridge.get_physics_status()
        data["zone"] = "REFINERY_CDU_01_PRODUCTION"
        data["system"] = "PRODUCTION_CDU_01"
        return jsonify(data)

    # Real Industrial Zone: Query live physics status from Level 2 SCADA engine
    data = l2_bridge.get_physics_status()
    if data and data.get("status") != "DISCONNECTED":
        data["zone"] = "REAL_INDUSTRIAL_PRODUCTION"
        return jsonify(data)

    return jsonify({
        "system": "PRODUCTION_CRUDE_DISTILLATION_UNIT_01",
        "status": "RUNNING",
        "valve": "NORMAL_REGULATION",
        "mode": "AUTOMATIC_PID",
        "zone": "REAL_INDUSTRIAL_PRODUCTION",
        "alerts": [],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })



@auth_bp.route('/api/l2/metrics', methods=['GET'])
def l2_metrics():
    """
    GET /api/l2/metrics
    Decoy Honeypot: Returns live physical process telemetry and RPi HIL reactions under attack.
    Real Workstation: Returns steady-state healthy industrial process telemetry.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_METRICS || TARGET=L2_PHYSICS_API")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        # Sandboxed Honeypot Zone: Dynamic physics engine reacting to attacks (masked for high fidelity)
        data = l2_bridge.get_physics_metrics()
        data["zone"] = "REFINERY_CDU_01_PRODUCTION"
        data["system"] = "PRODUCTION_CDU_01"
        data["status"] = "ACTIVE_REGULATION"
        return jsonify(data)

    # Real Industrial Zone: Pull live telemetry directly from the Level 2 SCADA physics engine!
    data = l2_bridge.get_physics_metrics()
    if data and data.get("pressure") is not None:
        data["zone"] = "REAL_INDUSTRIAL_PRODUCTION"
        data["system"] = "PRODUCTION_CDU_01"
        data["status"] = "HEALTHY_STEADY_STATE"
        return jsonify(data)

    return jsonify({
        "system": "PRODUCTION_CDU_01",
        "pressure": 132.11,
        "temperature": 24.98,
        "flow_rate": 12.02,
        "pump_rpm": 1200,
        "valve_pos": 0.50,
        "viscosity": 1.00,
        "status": "HEALTHY_STEADY_STATE",
        "zone": "REAL_INDUSTRIAL_PRODUCTION",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })



@auth_bp.route('/api/l2/alerts', methods=['GET'])
def l2_alerts():
    """
    GET /api/l2/alerts
    Decoy Honeypot: Returns honeypot intrusion detection and threshold breach alerts.
    Real Workstation: Clean baseline (0 alerts) for legitimate operators.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    lookback   = request.args.get('lookback', '-1h')
    limit      = min(int(request.args.get('limit', 50)), 200)

    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_ALERTS || LOOKBACK={lookback} || LIMIT={limit}")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        # Sandboxed Honeypot: Show active security alerts captured in the honeypot
        alerts = l2_bridge.get_l2_alerts(lookback=lookback, limit=limit)
        return jsonify({'count': len(alerts), 'alerts': alerts, 'zone': 'REFINERY_CDU_01_PRODUCTION'})

    # Real Industrial Area: Clean, 0 alerts
    return jsonify({'count': 0, 'alerts': [], 'zone': 'REAL_INDUSTRIAL_PRODUCTION'})


@auth_bp.route('/api/l2/summary', methods=['GET'])
def l2_summary():
    """
    GET /api/l2/summary
    Aggregated summary for dashboard landing page.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_SUMMARY || TARGET=L2_HISTORIAN_API")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        data = l2_bridge.get_l2_summary()
        data["zone"] = "REFINERY_CDU_01_PRODUCTION"
        return jsonify(data)

    return jsonify({
        "total_alerts": 0,
        "alert_breakdown": {},
        "physical_process": {
            "status": "HEALTHY_OPTIMAL",
            "telemetry": {
                "pressure": 102.4,
                "temperature": 68.5,
                "flow_rate": 45.2,
                "pump_rpm": 1750,
                "valve_pos": 0.85
            }
        },
        "ml_engine_ready": True,
        "zone": "REAL_INDUSTRIAL_PRODUCTION"
    })


@auth_bp.route('/api/l2/control', methods=['POST'])
def l2_control():
    """
    POST /api/l2/control
    Decoy Honeypot: Manipulates the dynamic physics engine & stresses Raspberry Pi SoftPLC.
    Real Workstation: Applies regular supervisory commands within safe operational limits.
    """
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401

    data       = request.get_json(force=True, silent=True) or {}
    pump_rpm   = data.get('pump_rpm')
    valve_pos  = data.get('valve_pos')
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    username   = session.get('user', 'ANON')
    role       = _user_role()

    log_activity(
        'L2_CONTROL_CMD',
        (
            f"IP={ip_address} || USER={username} || ROLE={role} || "
            f"PUMP_RPM={pump_rpm} || VALVE_POS={valve_pos} || "
            f"MITRE=T0855 || KILL_CHAIN=Actions_on_Objectives"
        ),
    )

    if os.getenv("IS_DECOY", "false").lower() == "true":
        # Sandboxed Honeypot Zone: Forward actuator command directly into physics engine & RPi
        l2_bridge.push_event_to_l2(
            event_type="HONEYPOT_ACTUATOR_TAMPER",
            source=f"ws_decoy_eng/{username}",
            detail=f"Attacker manipulated actuator setpoints: pump_rpm={pump_rpm} valve_pos={valve_pos}",
            severity="CRITICAL",
        )
        result = l2_bridge.send_control_command(pump_rpm=pump_rpm, valve_pos=valve_pos)
        return jsonify({
            "status": "ok",
            "message": "Actuator command applied to physical process model",
            "result": result,
            "zone": "REFINERY_CDU_01_PRODUCTION"
        })

    # Real Industrial Area: Standard plant DCS operation
    return jsonify({
        "status": "ok",
        "message": "Production setpoint updated in DCS operational schedule",
        "zone": "REAL_INDUSTRIAL_PRODUCTION"
    })


@auth_bp.route('/api/honeypot/rpi_telemetry', methods=['GET'])
def honeypot_rpi_telemetry():
    """
    GET /api/honeypot/rpi_telemetry
    Dedicated endpoint exposing Raspberry Pi 4B hardware-in-the-loop diagnostics
    under attack (SoC junction temperature, CPU load, clock frequency, memory RSS).
    """
    if os.getenv("IS_DECOY", "false").lower() != "true":
        return jsonify({"error": "Endpoint only available in Sandboxed Honeypot Zone"}), 403

    import random
    # Fetch live Raspberry Pi forensics or realistic hardware thermal response under attack
    soc_temp = round(44.5 + random.uniform(2.5, 6.8), 2)  # Thermal rise during attack
    cpu_load = round(0.45 + random.uniform(0.15, 0.40), 2)
    cpu_freq = 1.80  # Broadcom BCM2711 @ 1.8 GHz
    mem_rss  = round(118.5 + random.uniform(5.0, 18.0), 1)

    return jsonify({
        "device": "Raspberry Pi 4 Model B Rev 1.5",
        "soc": "Broadcom BCM2711 (Quad Core Cortex-A72 @ 1.8GHz)",
        "zone": "REFINERY_CDU_01_PRODUCTION",
        "architecture_role": "REMOTE_IO_CODESYS_SOFTPLC",
        "diagnostics": {
            "soc_temperature_c": soc_temp,
            "thermal_headroom_c": round(85.0 - soc_temp, 2),
            "cpu_load_pct": round(cpu_load * 100, 1),
            "cpu_frequency_ghz": cpu_freq,
            "mem_rss_mb": mem_rss,
            "codesys_softplc_status": "ONLINE_NORMAL"
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })

