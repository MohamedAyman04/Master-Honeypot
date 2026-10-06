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

        error_msg = "Invalid credentials."
        if is_bf:
            error_msg = "Too many failed attempts. Please try again later."

        return render_template('gateway_login.html', error=error_msg)

    # Step 3: Password Correct -> Proceed to MFA Challenge (Email 2FA / OTP)
    anomaly_detector.record_successful_auth(ip)
    session['temp_user'] = username
    session['temp_role'] = user_record['role']
    session['temp_email'] = user_record.get('email', '')

    # Generate 6-digit OTP code and dispatch via corporate email
    otp_code = mfa_handler.generate_session_otp()
    session['expected_otp'] = otp_code
    session['otp_expiry'] = time.time() + 300  # 5 minutes
    session['security_questions_failed_attempts'] = 0

    _sent, _send_msg = mfa_handler.send_mfa_email(
        to_email=user_record.get('email', 'mohikel6@gmail.com'),
        otp_code=otp_code,
        user_name=user_record.get('name', username),
        ip_address=ip
    )

    telemetry_logger.log_event_to_story(
        event_type="mfa_challenge_issued",
        message=f"Email MFA challenge initiated for user '{username}' (dispatched to {user_record.get('email')})",
        severity="info",
        details={"ip": ip, "username": username, "email": user_record.get('email')}
    )
    _stats['mfa_challenges'] += 1
    return redirect(url_for('mfa_challenge'))

@app.route('/mfa', methods=['GET', 'POST'])
def mfa_challenge():
    if not session.get('temp_user'):
        return redirect(url_for('login'))

    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    if request.method == 'GET':
        return render_template(
            'gateway_mfa.html',
            username=session.get('temp_user'),
            email=session.get('temp_email', 'mohikel6@gmail.com'),
            error=None
        )

    otp_input = request.form.get('otp_code', '').strip()
    expected_otp = session.get('expected_otp', '')
    otp_expiry = session.get('otp_expiry', 0)

    # Verify 6-Digit Email OTP Token
    if mfa_handler.verify_email_otp(otp_input, expected_otp, otp_expiry):
        # ── SUCCESSFUL MFA: GRANT ACCESS TO REAL INDUSTRIAL ZONE ─────────────
        username = session.pop('temp_user')
        role = session.pop('temp_role', 'engineer')
        session.pop('expected_otp', None)
        session.pop('otp_expiry', None)
        session.pop('security_questions_failed_attempts', None)

        session['is_authenticated'] = True
        session['user'] = username
        session['role'] = role
        session['routing_world'] = 'REAL_INDUSTRIAL'
        session['actor_type'] = 'operator'
        _stats['real_sessions'] += 1

        telemetry_logger.log_event_to_story(
            event_type="mfa_authenticated_real_zone",
            message=f"User '{username}' completed Email 2FA. Access granted to Real Industrial Zone.",
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
            reason="Authenticated via Password + Email 2FA"
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
            username=session.get('temp_user'),
            email=session.get('temp_email', 'mohikel6@gmail.com'),
            error="Invalid or expired passcode. Please try again."
        )

@app.route('/mfa/security-questions', methods=['GET', 'POST'])
def security_questions_challenge():
    if not session.get('temp_user'):
        return redirect(url_for('login'))

    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    username = session.get('temp_user')
    failed_attempts = session.get('security_questions_failed_attempts', 0)
    remaining_attempts = max(0, 2 - failed_attempts)

    if request.method == 'GET':
        return render_template(
            'gateway_security_questions.html',
            username=username,
            remaining_attempts=remaining_attempts,
            error=None
        )

    dog_name = request.form.get('dog_name', '').strip()
    birth_place = request.form.get('birth_place', '').strip()
    siblings_count = request.form.get('siblings_count', '').strip()

    user_record = config.VALID_USERS.get(username, {})
    expected_questions = user_record.get('security_questions', {
        "dog_name": "Roy",
        "birth_place": "Egypt",
        "siblings_count": "2"
    })

    is_correct = mfa_handler.verify_security_questions(dog_name, birth_place, siblings_count, expected_questions)

    if is_correct:
        # ── SUCCESSFUL ANSWERS: NAVIGATE TO NORMAL TELEMETRY AND REAL INDUSTRIAL ZONE ──
        username = session.pop('temp_user')
        role = session.pop('temp_role', 'engineer')
        session.pop('expected_otp', None)
        session.pop('otp_expiry', None)
        session.pop('security_questions_failed_attempts', None)

        session['is_authenticated'] = True
        session['user'] = username
        session['role'] = role
        session['routing_world'] = 'REAL_INDUSTRIAL'
        session['actor_type'] = 'operator'
        _stats['real_sessions'] += 1

        telemetry_logger.log_event_to_story(
            event_type="security_questions_authenticated_real_zone",
            message=f"Operator '{username}' verified security questions fallback. Access granted to Real Industrial Zone.",
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
            reason="Authenticated via Security Questions Fallback"
        )

        return redirect('/dashboard')
    else:
        # FAILED ANSWERS
        failed_attempts += 1
        session['security_questions_failed_attempts'] = failed_attempts
        remaining_attempts = max(0, 2 - failed_attempts)

        telemetry_logger.log_event_to_story(
            event_type="security_questions_verification_failed",
            message=f"Security questions verification failed (attempt {failed_attempts}/2) for '{username}' from {ip}",
            severity="warning",
            details={"ip": ip, "username": username, "failed_attempts": failed_attempts}
        )

        if failed_attempts >= 2:
            # ── FAILED TWICE: IMMEDIATE QUARANTINE TO HONEYPOT DECEPTION SANDBOX ──
            target_role = session.get('temp_role', 'engineer')
            dest_node = "ws_decoy_ops" if target_role == "operator" else "ws_decoy_eng"
            user_quarantined = session.pop('temp_user', 'attacker')
            session.pop('expected_otp', None)
            session.pop('otp_expiry', None)
            session.pop('security_questions_failed_attempts', None)

            session['is_authenticated'] = True
            session['user'] = user_quarantined
            session['role'] = target_role
            session['routing_world'] = 'SANDBOX_DECEPTION'
            session['actor_type'] = 'attacker'
            session['quarantine_reason'] = "Security questions verification failed twice - suspected unauthorized account takeover"
            session['quarantine_tactic'] = "T1078 (Valid Accounts - Defense Evasion Quarantine)"
            _stats['quarantined_sessions'] += 1

            telemetry_logger.log_event_to_story(
                event_type="security_questions_honeypot_diverted",
                message=f"User failed security questions twice ({user_quarantined}). Threat diverted to Deception Honeypot Sandbox ({dest_node}).",
                severity="critical",
                details={
                    "ip": ip,
                    "user_agent": user_agent,
                    "username": user_quarantined,
                    "tactic": "T1078 (Valid Accounts)",
                    "destination": dest_node,
                    "role": target_role
                }
            )

            telemetry_logger.log_routing_telemetry(
                src_ip=ip,
                user_agent=user_agent,
                username=user_quarantined,
                routing_world="SANDBOX_DECEPTION",
                actor_type="attacker",
                tactic="T1078 (Valid Accounts)",
                reason=f"Security questions failed twice (Diverted to {dest_node})"
            )

            return redirect('/dashboard')

        return render_template(
            'gateway_security_questions.html',
            username=username,
            remaining_attempts=remaining_attempts,
            error="Incorrect answers. Please try again."
        )

@app.route('/dashboard', methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/proxy/', defaults={'subpath': 'dashboard'}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/proxy/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_root(subpath='dashboard'):
    if subpath in ('login', 'mfa', 'status', 'logout', 'mfa/security-questions', 'security-questions'):
        if subpath == 'login': return redirect(url_for('login'))
        if subpath == 'mfa': return redirect(url_for('mfa_challenge'))
        if subpath in ('mfa/security-questions', 'security-questions'): return redirect(url_for('security_questions_challenge'))
        if subpath == 'status': return redirect(url_for('gateway_status'))
        if subpath == 'logout': return redirect(url_for('logout'))

    if not session.get('is_authenticated'):
        return redirect(url_for('login'))

    routing_world = session.get('routing_world', 'SANDBOX_DECEPTION')
    actor_type = session.get('actor_type', 'attacker')
    ip = get_client_ip()

    # Deep Inspection of HTTP path, query string, and data for Command/SQL Injections
    # Note: Authenticated legitimate corporate users on REAL_INDUSTRIAL communicating with their
    # own engineering workstation terminal/tools must stay on the legitimate production workstation.
    if routing_world != 'REAL_INDUSTRIAL':
        qs = request.query_string.decode('utf-8', errors='ignore')
        payload_to_check = f"{subpath}?{qs}"
        try:
            raw_body = request.get_data(as_text=True)
            if raw_body:
                payload_to_check += f" {raw_body[:500]}"
        except Exception:
            pass

        is_exploit, exp_reason, exp_tactic = anomaly_detector.inspect_generic_payload(payload_to_check)
        if is_exploit:
            # Immediate active quarantine to Deception Sandbox
            session['routing_world'] = 'SANDBOX_DECEPTION'
            session['actor_type'] = 'attacker'
            session['quarantine_reason'] = exp_reason
            session['quarantine_tactic'] = exp_tactic
            routing_world = 'SANDBOX_DECEPTION'
            actor_type = 'attacker'
            _stats['quarantined_sessions'] += 1

            telemetry_logger.log_event_to_story(
                event_type="exploit_attempt_diverted_to_sandbox",
                message=f"Threat intercepted: {exp_reason}",
                severity="critical",
                details={
                    "ip": ip,
                    "user_agent": request.headers.get('User-Agent', ''),
                    "username": session.get('user', 'attacker'),
                    "tactic": exp_tactic,
                    "payload": payload_to_check[:100]
                }
            )

            telemetry_logger.log_routing_telemetry(
                src_ip=ip,
                user_agent=request.headers.get('User-Agent', ''),
                username=session.get('user', 'attacker'),
                routing_world="SANDBOX_DECEPTION",
                actor_type="attacker",
                tactic=exp_tactic,
                reason=exp_reason
            )


    if routing_world == 'REAL_INDUSTRIAL':
        if session.get('role') == 'operator':
            target_url = config.REAL_OPS_WORKSTATION_URL
        else:
            target_url = config.REAL_WORKSTATION_URL
    else:
        role = session.get('role', 'engineer')
        if role == 'operator':
            target_url = config.DECOY_OPS_WORKSTATION_URL
        elif role in ('main', 'supervisor', 'admin'):
            target_url = config.DECOY_MAIN_WORKSTATION_URL
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
        "detector_stats": anomaly_detector.get_stats(),
        "grafana_dashboard": config.GRAFANA_URL
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print(f"[*] Starting DMZ Secure OT Access Gateway on port {config.GATEWAY_PORT}")
    app.run(host='0.0.0.0', port=config.GATEWAY_PORT, debug=False)
