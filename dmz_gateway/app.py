"""
DMZ Secure OT Access Gateway - Main Application
================================================
Implements dynamic two-factor authentication (MFA/OTP) and dual-world routing:
- Benign authenticated operators -> Real Industrial Zone (ws_eng_01)
- Brute-force / anomalous attackers -> Sandboxed Deception Zone (ws_decoy_eng)
"""
import time
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, Response
try:
    from . import config
    from . import anomaly_detector
    from . import mfa_handler
    from . import router
    from . import telemetry_logger
except (ImportError, ValueError):
    import config
    import anomaly_detector
    import mfa_handler
    import router
    import telemetry_logger

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = 'dmz_gateway_session'

# Statistics Counters for Status Dashboard
_stats = {
    "real_sessions": 0,
    "quarantined_sessions": 0,
    "mfa_challenges": 0
}

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

@app.route('/')
def index():
    if session.get('is_authenticated'):
        return redirect('/dashboard')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    if request.method == 'GET':
        return render_template('gateway_login.html', error=None)

    # Clear prior session state to ensure fresh evaluation
    session.clear()

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    # Step 1: Deep Anomaly & Exploit Inspection
    is_anomalous, reason, tactic = anomaly_detector.inspect_request(ip, user_agent, username, password)

    if is_anomalous:
        # ── ATTACKER DETECTED: ACTIVE DECEPTION QUARANTINE ──────────────────────
        # Determine persona: operator or engineer based on targeted account/action
        target_role = "operator" if any(k in username.lower() for k in ("op", "shift", "hmi", "scada", "user")) else "engineer"
        dest_node = "ws_decoy_ops" if target_role == "operator" else "ws_decoy_eng"

        # Fake successful authentication and seamlessly divert session into the Honeypot Sandbox!
        session['is_authenticated'] = True
        session['user'] = username or ("shift_operator" if target_role == "operator" else "eng_operator")
        session['role'] = target_role
        session['routing_world'] = 'SANDBOX_DECEPTION'
        session['actor_type'] = 'attacker'
        session['quarantine_reason'] = reason
        session['quarantine_tactic'] = tactic
        _stats['quarantined_sessions'] += 1

        telemetry_logger.log_event_to_story(
            event_type="attacker_quarantined_to_sandbox",
            message=f"Threat diverted to Deception Honeypot Sandbox ({dest_node}): {reason}",
            severity="warning",
            details={
                "ip": ip,
                "user_agent": user_agent,
                "username": username,
                "tactic": tactic,
                "destination": dest_node,
                "role": target_role
            }
        )

        telemetry_logger.log_routing_telemetry(
            src_ip=ip,
            user_agent=user_agent,
            username=username,
            routing_world="SANDBOX_DECEPTION",
            actor_type="attacker",
            tactic=tactic,
            reason=f"{reason} (Diverted to {dest_node})"
        )

        return redirect('/dashboard')

    # Step 2: Validate Corporate Credentials for Real Industrial Path
    user_record = config.VALID_USERS.get(username)
    valid_passwords = user_record.get('passwords', [user_record.get('password')]) if user_record else []
    if not user_record or password not in valid_passwords:
        is_bf = anomaly_detector.record_failed_attempt(ip)

        telemetry_logger.log_event_to_story(
            event_type="failed_login_attempt",
            message=f"Failed login attempt for user '{username}' from {ip}",
            severity="info",
            details={"ip": ip, "username": username}
        )

        telemetry_logger.log_routing_telemetry(
            src_ip=ip,
            user_agent=user_agent,
            username=username,
            routing_world="GATEWAY_REJECT",
            actor_type="unknown",
            tactic="T1110.001 (Password Guessing)",
            reason="Invalid credentials"
        )

        error_msg = "Invalid corporate credentials. Attempt has been recorded."
        if is_bf:
            error_msg = "Security threshold reached: Rate-limiting & behavioral inspection engaged."

        return render_template('gateway_login.html', error=error_msg)

    # Step 3: Password Correct -> Proceed to MFA Challenge (2FA / OTP)
    anomaly_detector.record_successful_auth(ip)
    session['temp_user'] = username
    session['temp_role'] = user_record['role']
    _stats['mfa_challenges'] += 1
    return redirect(url_for('mfa_challenge'))

@app.route('/mfa', methods=['GET', 'POST'])
def mfa_challenge():
    if not session.get('temp_user'):
        return redirect(url_for('login'))

    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    if request.method == 'GET':
        code, remaining = mfa_handler.get_current_otp()
        return render_template('gateway_mfa.html', current_otp=code, remaining_sec=remaining, error=None)

    otp_input = request.form.get('otp_code', '').strip()

    # Verify 6-Digit TOTP Token
    if mfa_handler.verify_otp(otp_input):
        # ── SUCCESSFUL MFA: GRANT ACCESS TO REAL INDUSTRIAL ZONE ─────────────
        username = session.pop('temp_user')
        role = session.pop('temp_role', 'operator')
        session['is_authenticated'] = True
        session['user'] = username
        session['role'] = role
        session['routing_world'] = 'REAL_INDUSTRIAL'
        session['actor_type'] = 'operator'
        _stats['real_sessions'] += 1

        telemetry_logger.log_event_to_story(
            event_type="mfa_authenticated_real_zone",
            message=f"Operator '{username}' completed 2FA. Access granted to Real Industrial Zone.",
            severity="info",
            details={"ip": ip, "username": username, "destination": "ws_eng_01"}
        )

        telemetry_logger.log_routing_telemetry(
            src_ip=ip,
            user_agent=user_agent,
            username=username,
            routing_world="REAL_INDUSTRIAL",
            actor_type="operator",
            tactic="None",
            reason="Authenticated via Password + 2FA"
        )

        return redirect('/dashboard')
    else:
        # Invalid OTP Code
        is_bf = anomaly_detector.record_failed_attempt(ip)
        if is_bf:
            # Attacker attempting OTP brute-force -> Quarantine to Sandbox
            session['is_authenticated'] = True
            session['user'] = session.pop('temp_user', 'attacker')
            session['role'] = 'operator'
            session['routing_world'] = 'SANDBOX_DECEPTION'
            session['actor_type'] = 'attacker'
            session['quarantine_reason'] = "OTP brute-force attack detected"
            session['quarantine_tactic'] = "T1110 (Brute Force MFA)"
            _stats['quarantined_sessions'] += 1
            return redirect('/dashboard')

        return render_template(
            'gateway_mfa.html',
            current_otp=mfa_handler.get_current_otp()[0],
            remaining_sec=mfa_handler.get_current_otp()[1],
            error="Invalid one-time passcode. Please check your authenticator token."
        )

@app.route('/dashboard', methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/proxy/', defaults={'subpath': 'dashboard'}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/proxy/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_root(subpath='dashboard'):
    if subpath in ('login', 'mfa', 'status', 'logout'):
        if subpath == 'login': return redirect(url_for('login'))
        if subpath == 'mfa': return redirect(url_for('mfa_challenge'))
        if subpath == 'status': return redirect(url_for('gateway_status'))
        if subpath == 'logout': return redirect(url_for('logout'))

    if not session.get('is_authenticated'):
        return redirect(url_for('login'))

    routing_world = session.get('routing_world', 'SANDBOX_DECEPTION')
    actor_type = session.get('actor_type', 'attacker')
    ip = get_client_ip()

    if routing_world == 'REAL_INDUSTRIAL':
        if session.get('role') == 'operator':
            target_url = config.REAL_OPS_WORKSTATION_URL
        else:
            target_url = config.REAL_WORKSTATION_URL
    else:
        if session.get('role') == 'operator':
            target_url = config.DECOY_OPS_WORKSTATION_URL
        else:
            target_url = config.DECOY_WORKSTATION_URL
        # Telemetry capture of attacker action in the sandbox
        telemetry_logger.log_routing_telemetry(
            src_ip=ip,
            user_agent=request.headers.get('User-Agent', ''),
            username=session.get('user', 'attacker'),
            routing_world="SANDBOX_DECEPTION",
            actor_type="attacker",
            tactic="T1082 (System Discovery in Honeypot)",
            reason=f"Action on {subpath}"
        )

    clean_subpath = subpath
    if clean_subpath.startswith('proxy/'):
        clean_subpath = clean_subpath[6:]

    return router.forward_request(
        target_base_url=target_url,
        subpath=clean_subpath,
        user=session.get('user', 'operator'),
        role=session.get('role', 'operator')
    )

@app.route('/status')
def gateway_status():
    """Security Operations & Telemetry: redirect to centralized Grafana dashboard."""
    return redirect(config.GRAFANA_URL)

@app.route('/api/status')
def gateway_status_api():
    """Security Operations & Telemetry Status endpoint (REST API)."""
    return jsonify({
        "status": "ONLINE",
        "gateway_id": "DMZ-GW-01A",
        "zone": "PURDUE_LEVEL_3.5_DMZ",
        "stats": _stats,
        "grafana_dashboard": config.GRAFANA_URL
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print(f"[*] Starting DMZ Secure OT Access Gateway on port {config.GATEWAY_PORT}")
    app.run(host='0.0.0.0', port=config.GATEWAY_PORT, debug=False)
