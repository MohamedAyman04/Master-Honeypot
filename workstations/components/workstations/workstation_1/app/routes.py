import os
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
    return {
        'component': component,
        'ip': profile.get('ip') or 'N/A',
        'mac': profile.get('mac') or 'N/A',
        'serial': profile.get('serial') or 'N/A',
        'model': profile.get('model') or 'N/A',
        'vendor': profile.get('vendor') or 'N/A',
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
    except Exception:
        pass

    if os.getenv("IS_DECOY", "false").lower() == "true":
        cmd_clean = cmd.strip()
        cmd_lower = cmd_clean.lower()
        err = ""
        if cmd_lower in ("ls", "ls -l", "ls -la", "dir"):
            out = (
                "total 384\n"
                "-rw-r--r-- 1 eng_operator eng_operator 248920 Sep 18 09:12 Refinery_PLC_Logic_Backup_2026.s7p\n"
                "-rw------- 1 eng_operator eng_operator   4096 Sep 19 14:03 SCADA_Admin_Master_Keys.kdbx\n"
                "-rw-r--r-- 1 eng_operator eng_operator  84112 Sep 15 11:45 Safety_Interlock_Bypass_Codes.pdf\n"
                "-rw-r--r-- 1 eng_operator eng_operator  28410 Sep 20 08:30 plant_topology_map.vsdx\n"
                "-rw-r--r-- 1 eng_operator eng_operator    528 Sep 20 18:22 historian_connection.conf\n"
                "drwxr-xr-x 2 eng_operator eng_operator   4096 Sep 21 00:00 backups"
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
            out = "eng_operator"
        elif cmd_lower in ("id",):
            out = "uid=1001(eng_operator) gid=1001(scada_eng) groups=1001(scada_eng),27(sudo)"
        elif cmd_lower in ("pwd",):
            out = "/home/eng_operator/scada_workspace"
        elif cmd_lower in ("uname -a", "uname"):
            out = "Linux ws-eng-decoy-01 5.15.0-89-generic #99-Ubuntu SMP x86_64 GNU/Linux"
        elif cmd_lower in ("ifconfig", "ip a", "ip addr"):
            out = (
                "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
                "        inet 192.168.99.21  netmask 255.255.255.0  broadcast 192.168.99.255\n"
                "        ether 02:42:c0:a8:63:15  txqueuelen 0  (Ethernet)\n"
            )
        elif "cat /etc/passwd" in cmd_lower:
            out = (
                "root:x:0:0:root:/root:/bin/bash\n"
                "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                "scada_admin:x:1000:1000:SCADA Administrator:/home/scada_admin:/bin/bash\n"
                "eng_operator:x:1001:1001:Field Engineering Operator:/home/eng_operator:/bin/bash\n"
                "historian_svc:x:1002:1002:Historian Ingestion Service:/var/lib/historian:/usr/sbin/nologin\n"
            )
        elif "mbtget" in cmd_lower or "modbus" in cmd_lower:
            out = "Values: [1, 0, 1, 0, 0, 1] - Register write confirmed to 192.168.99.12"
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
            out = f"Command executed: {cmd_clean}"

        return jsonify({'output': out, 'error': err})

    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Use SCADA_SSH environment variables, defaulting to engineer
        scada_host = current_app.config.get('SCADA_SSH_HOST', '172.28.0.10')
        scada_port = int(current_app.config.get('SCADA_SSH_PORT', '2222'))
        # Determine SCADA user based on role or defaults
        scada_user = 'operator' if role == 'operator' else 'engineer'
        scada_pass = 'operator123' if role == 'operator' else 'engineer456'
        
        # Hardcode SCADA SSH fallback credentials for convenience 
        # (Level 2 scada_ssh container credentials)
        if scada_host == '172.28.0.10':
            pass # Keep defaults

        ssh.connect(hostname=scada_host, port=scada_port, username=scada_user, password=scada_pass, timeout=5)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        ssh.close()
        return jsonify({'output': out, 'error': err})
    except Exception as e:
        return jsonify({'error': f"SSH connection failed: {str(e)}"})



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
    Proxies the Level 2 physics system status to the L3 dashboard.
    No login required — reflects the unauthenticated nature of the L2 API.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_STATUS || TARGET=L2_PHYSICS_API")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        return jsonify({
            "system": "PUMP_STATION_DECOY_01",
            "status": "RUNNING",
            "valve": "OPEN",
            "alerts": [],
            "timestamp": "2026-09-21T00:00:00Z"
        })

    data = l2_bridge.get_physics_status()
    return jsonify(data)


@auth_bp.route('/api/l2/metrics', methods=['GET'])
def l2_metrics():
    """
    GET /api/l2/metrics
    Returns live physical process telemetry pulled from the L2 physics API.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_METRICS || TARGET=L2_PHYSICS_API")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        return jsonify({
            "pressure": 104.2,
            "temperature": 69.5,
            "flow_rate": 42.1,
            "pump_rpm": 1820,
            "valve_pos": 1.0,
            "viscosity": 2.4
        })

    data = l2_bridge.get_physics_metrics()
    return jsonify(data)


@auth_bp.route('/api/l2/alerts', methods=['GET'])
def l2_alerts():
    """
    GET /api/l2/alerts
    Returns recent security alerts from the Level 2 historian (InfluxDB).
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    lookback   = request.args.get('lookback', '-1h')
    limit      = min(int(request.args.get('limit', 50)), 200)

    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_ALERTS || LOOKBACK={lookback} || LIMIT={limit}")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        return jsonify({'count': 0, 'alerts': []})

    alerts = l2_bridge.get_l2_alerts(lookback=lookback, limit=limit)
    return jsonify({'count': len(alerts), 'alerts': alerts})


@auth_bp.route('/api/l2/summary', methods=['GET'])
def l2_summary():
    """
    GET /api/l2/summary
    Aggregated cross-layer summary for the L3 dashboard landing page.
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_SUMMARY || TARGET=L2_HISTORIAN_API")

    if os.getenv("IS_DECOY", "false").lower() == "true":
        return jsonify({
            "total_alerts": 0,
            "alert_breakdown": {},
            "physical_process": {"status": "NORMAL", "telemetry": {"pressure": 104.2}},
            "ml_engine_ready": True
        })

    data = l2_bridge.get_l2_summary()
    return jsonify(data)


@auth_bp.route('/api/l2/control', methods=['POST'])
def l2_control():
    """
    POST /api/l2/control
    Sends an actuator control command to the Level 2 physics engine.
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
        return jsonify({
            "status": "ok",
            "message": "Actuator setpoint applied to decoy safety controller"
        })

    # Also push a cross-layer event into L2's historian so the ML engine sees it
    l2_bridge.push_event_to_l2(
        event_type="L3_CONTROL_COMMAND",
        source=f"l3-workstation/{username}",
        detail=f"Cross-layer control command from L3: pump_rpm={pump_rpm} valve_pos={valve_pos}",
        severity="HIGH",
    )

    result = l2_bridge.send_control_command(pump_rpm=pump_rpm, valve_pos=valve_pos)
    return jsonify(result)

