"""
DMZ Secure OT Access Gateway - Anomaly & Attack Inspection Engine
"""
import time
import re
from collections import defaultdict, deque
try:
    from . import config
except (ImportError, ValueError):
    import config

# IP -> deque of failure timestamps
_failed_attempts = defaultdict(deque)
# IP -> quarantine status & reason
_quarantined_ips = {}

SQLI_PATTERNS = [
    r"(\%27|\')\s*(\-\-|\#|\%23|\/\*)",
    r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
    r"\w*((\%27)|(\'))(\s)*((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
    r"((\%27)|(\'))\s*union",
    r"union(\s)+select",
    r"sleep\((\s)*\d+(\s)*\)",
    r"exec(\s)+(master|xp_)"
]

TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"/etc/passwd",
    r"win\.ini",
    r"/proc/self"
]

SCANNER_AGENTS = [
    "sqlmap", "nikto", "hydra", "nmap", "gobuster",
    "dirbuster", "wfuzz", "zgrab", "masscan", "metasploit"
]

def clean_old_attempts(ip):
    now = time.time()
    while _failed_attempts[ip] and (now - _failed_attempts[ip][0]) > config.BRUTE_FORCE_WINDOW:
        _failed_attempts[ip].popleft()

def record_failed_attempt(ip):
    clean_old_attempts(ip)
    _failed_attempts[ip].append(time.time())
    if len(_failed_attempts[ip]) >= config.BRUTE_FORCE_THRESHOLD:
        _quarantined_ips[ip] = {
            "reason": f"Brute force detected ({len(_failed_attempts[ip])} failures in {config.BRUTE_FORCE_WINDOW}s)",
            "tactic": "T1110 (Brute Force)",
            "timestamp": time.time()
        }
        return True
    return False

def record_successful_auth(ip):
    clean_old_attempts(ip)
    if ip in _failed_attempts:
        _failed_attempts[ip].clear()
    if ip in _quarantined_ips:
        del _quarantined_ips[ip]

def clear_quarantine(ip=None):
    if ip:
        _quarantined_ips.pop(ip, None)
        if ip in _failed_attempts:
            _failed_attempts[ip].clear()
    else:
        _quarantined_ips.clear()
        _failed_attempts.clear()

def is_ip_quarantined(ip):
    clean_old_attempts(ip)
    if ip in _quarantined_ips:
        # Check quarantine expiration (e.g. 10 minutes)
        if time.time() - _quarantined_ips[ip]["timestamp"] < 600:
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]
        else:
            del _quarantined_ips[ip]
    return False, None, None

def inspect_request(ip, user_agent, username, password=None):
    """
    Analyzes request metadata, user agent, and payload for anomalies.
    Returns (is_anomalous: bool, reason: str, tactic: str)
    """
    u_str = (username or "").strip()
    p_str = (password or "").strip()

    # Pre-check: If user provides legitimate authorized corporate credentials, never quarantine!
    user_record = config.VALID_USERS.get(u_str)
    if user_record:
        valid_passwords = user_record.get('passwords', [user_record.get('password')])
        if p_str in valid_passwords:
            clear_quarantine(ip)
            return False, "Authorized corporate credentials", "None"

    # 1. Check IP Quarantine State
    is_q, q_reason, q_tactic = is_ip_quarantined(ip)
    if is_q:
        return True, q_reason, q_tactic

    # 2. Scanner / Automated User-Agent Inspection
    ua_lower = (user_agent or "").lower()
    for scanner in SCANNER_AGENTS:
        if scanner in ua_lower:
            _quarantined_ips[ip] = {
                "reason": f"Automated reconnaissance tool detected: '{scanner}' in User-Agent",
                "tactic": "T1595 (Active Scanning)",
                "timestamp": time.time()
            }
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

    # 3. Payload Injection Signatures (SQLi & Path Traversal on username)
    for pattern in SQLI_PATTERNS:
        if re.search(pattern, u_str, re.IGNORECASE):
            _quarantined_ips[ip] = {
                "reason": "SQL injection attempt detected in authentication username",
                "tactic": "T1190 (Exploit Public-Facing Application)",
                "timestamp": time.time()
            }
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

    for pattern in TRAVERSAL_PATTERNS:
        if re.search(pattern, u_str, re.IGNORECASE):
            _quarantined_ips[ip] = {
                "reason": "Path traversal pattern detected in username",
                "tactic": "T1190 (Exploit Public-Facing Application)",
                "timestamp": time.time()
            }
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

    # 4. Honeypot Wordlist / Default Credential Trapping
    u_lower = u_str.lower()
    p_lower = p_str.lower()
    if u_lower in config.HONEYPOT_WORDLIST or p_lower in config.HONEYPOT_WORDLIST:
        # Attacker is spraying default wordlists
        _quarantined_ips[ip] = {
            "reason": f"Attacker matched default ICS honeypot wordlist: '{u_lower or p_lower}'",
            "tactic": "T1110.003 (Password Spraying)",
            "timestamp": time.time()
        }
        return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

    return False, "Normal", "None"
