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

    Returns:
      { "system": "PUMP_STATION_01", "status": "RUNNING", "valve": "OPEN",
        "alerts": [], "timestamp": "..." }
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_STATUS || TARGET=L2_PHYSICS_API")

    data = l2_bridge.get_physics_status()
    return jsonify(data)


@auth_bp.route('/api/l2/metrics', methods=['GET'])
def l2_metrics():
    """
    GET /api/l2/metrics
    Returns live physical process telemetry pulled from the L2 physics API:
      pressure (PSI), temperature (°C), flow_rate (L/s), pump_rpm, valve_pos, viscosity

    This is the primary data source for the real-time dashboard chart.
    ATT&CK: T0802 — Automated Collection
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_METRICS || TARGET=L2_PHYSICS_API")

    data = l2_bridge.get_physics_metrics()
    return jsonify(data)


@auth_bp.route('/api/l2/alerts', methods=['GET'])
def l2_alerts():
    """
    GET /api/l2/alerts
    Returns recent security alerts from the Level 2 historian (InfluxDB).
    Optional query params:
      - lookback : InfluxDB range string (default: -1h)
      - limit    : max records (default: 50)
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    lookback   = request.args.get('lookback', '-1h')
    limit      = min(int(request.args.get('limit', 50)), 200)

    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_ALERTS || LOOKBACK={lookback} || LIMIT={limit}")

    alerts = l2_bridge.get_l2_alerts(lookback=lookback, limit=limit)
    return jsonify({'count': len(alerts), 'alerts': alerts})


@auth_bp.route('/api/l2/summary', methods=['GET'])
def l2_summary():
    """
    GET /api/l2/summary
    Aggregated cross-layer summary for the L3 dashboard landing page:
      - total_alerts, alert_breakdown
      - physical_process (live telemetry from L2)
      - ml_engine_ready status
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_activity('L2_BRIDGE', f"IP={ip_address} || ACTION=GET_SUMMARY || TARGET=L2_HISTORIAN_API")

    data = l2_bridge.get_l2_summary()
    return jsonify(data)


@auth_bp.route('/api/l2/control', methods=['POST'])
def l2_control():
    """
    POST /api/l2/control
    !! INTENTIONALLY WEAK ACCESS CONTROL — any logged-in user can call this !!

    Sends an actuator control command to the Level 2 physics engine.
    Demonstrates the full cross-layer attack path from a compromised
    Level 3 workstation down to the OT process layer.

    Body (JSON):
      { "pump_rpm": 3000, "valve_pos": 0.0 }

    ATT&CK: T0855 — Unauthorized Command Message
    Kill Chain: Actions on Objectives
    """
    # Only require a session — intentionally NOT restricting to operator/admin.
    # This simulates a privilege misconfiguration in the L3 application.
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

    # Also push a cross-layer event into L2's historian so the ML engine sees it
    l2_bridge.push_event_to_l2(
        event_type="L3_CONTROL_COMMAND",
        source=f"l3-workstation/{username}",
        detail=f"Cross-layer control command from L3: pump_rpm={pump_rpm} valve_pos={valve_pos}",
        severity="HIGH",
    )

    result = l2_bridge.send_control_command(pump_rpm=pump_rpm, valve_pos=valve_pos)
    return jsonify(result)

