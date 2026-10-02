"""
DMZ Secure OT Access Gateway - Anomaly & Attack Inspection Engine
==================================================================
Inspects all incoming gateway traffic for:
1. Command Injection (OS command execution & shell expansion)
2. SQL Injection (tautologies, UNION, stacked queries, time-based blind SQLi)
3. Path Traversal / LFI
4. Automated Security Scanners & Reconnaissance User-Agents
5. Wordlist & Dictionary Attacks using RockYou.txt (14+ million passwords)
6. Dynamic Rate-Limiting & Credential Brute-Forcing
"""
import os
import time
import re
import sqlite3
import urllib.parse
from collections import defaultdict, deque
from functools import lru_cache

try:
    from . import config
except (ImportError, ValueError):
    import config

# IP -> deque of failure timestamps
_failed_attempts = defaultdict(deque)
# IP -> quarantine status & reason
_quarantined_ips = {}

# ── SQL INJECTION SIGNATURES ──────────────────────────────────────────────────
SQLI_PATTERNS = [
    # Classic quote + comment: ' --, ' #, '/*, " --, etc.
    re.compile(r"(\%27|\'|\%22|\")\s*(\-\-|\#|\%23|\/\*)", re.IGNORECASE),
    # Classic boolean tautologies: ' or 1=1, ' or 'a'='a, " or ""=", ' or true
    re.compile(r"(\%27|\'|\%22|\")\s*(or|and)\s+[\'\"]?\w+[\'\"]?\s*=\s*[\'\"]?\w+[\'\"]?", re.IGNORECASE),
    re.compile(r"\b(or|and)\s+\d+\s*=\s*\d+", re.IGNORECASE),
    re.compile(r"(\%27|\'|\%22|\")\s*(or|and)\s+(true|false|null)", re.IGNORECASE),
    re.compile(r"\w*((\%27)|(\'))(\s)*((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.IGNORECASE),
    # Union-based SQLi: UNION SELECT, UNION ALL SELECT
    re.compile(r"\bunion\s+(all\s+)?select\b", re.IGNORECASE),
    re.compile(r"(\%27|\'|\%22|\")\s*union\b", re.IGNORECASE),
    # Stacked queries / DDL / DML: ; drop table, ; insert, ; update, ; delete
    re.compile(r";\s*(drop|insert|update|delete|create|alter|truncate|grant|revoke)\b", re.IGNORECASE),
    # Time-based blind SQLi: sleep(..), waitfor delay, pg_sleep(..), benchmark(..)
    re.compile(r"\b(sleep|pg_sleep)\s*\(\s*\d+\s*\)", re.IGNORECASE),
    re.compile(r"\bwaitfor\s+delay\s+[\'\"]\d+", re.IGNORECASE),
    re.compile(r"\bbenchmark\s*\(\s*\d+", re.IGNORECASE),
    # Stored procedures / dangerous DB execution functions
    re.compile(r"\bexec(\s+xp_|\s+sp_|\s+master|\s*\()", re.IGNORECASE),
    # DB meta extraction
    re.compile(r"\binformation_schema\b", re.IGNORECASE),
    re.compile(r"\binto\s+(outfile|dumpfile)\b", re.IGNORECASE)
]

# ── COMMAND INJECTION SIGNATURES ──────────────────────────────────────────────
CMD_INJECTION_PATTERNS = [
    # Shell chaining followed by standard UNIX / Windows utilities
    re.compile(
        r"(?:;|&&|\|\||\||&|\n|\r)\s*(?:cat|ls|id|whoami|uname|pwd|hostname|ping|curl|wget|nc|ncat|netcat|"
        r"bash|sh|zsh|python|python3|perl|ruby|php|echo|rm|touch|cp|mv|chmod|chown|kill|ps|top|env|export|"
        r"dir|type|ipconfig|ifconfig|netstat|find|grep|awk|sed|sudo|su|sleep)\b",
        re.IGNORECASE
    ),
    # Command substitution: $(cmd), `cmd`
    re.compile(r"\$\([^\)]+\)", re.IGNORECASE),
    re.compile(r"`[^`]+`", re.IGNORECASE),
    re.compile(r"\$\{IFS\}", re.IGNORECASE),
    # Pipes directly to a shell interpreter: | bash, | sh
    re.compile(r"\|\s*(?:bash|sh|zsh|dash|python|perl)\b", re.IGNORECASE),
    # Direct shell execution paths
    re.compile(r"/(?:bin|usr/bin)/(?:ba)?sh\b", re.IGNORECASE),
    re.compile(r"/(?:bin|usr/bin)/zsh\b", re.IGNORECASE),
    re.compile(r"\b(?:cmd(?:\.exe)?\s*/c|powershell(?:\.exe)?\s*-(?:enc|command|c))\b", re.IGNORECASE),
    # Reverse shells / socket syntax
    re.compile(r"\bnc\s+-[ecl]\b", re.IGNORECASE),
    re.compile(r"/dev/tcp/\d+\.\d+\.\d+\.\d+/\d+", re.IGNORECASE)
]

# ── PATH TRAVERSAL SIGNATURES ─────────────────────────────────────────────────
TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./", re.IGNORECASE),
    re.compile(r"\.\.\\", re.IGNORECASE),
    re.compile(r"/etc/passwd", re.IGNORECASE),
    re.compile(r"win\.ini", re.IGNORECASE),
    re.compile(r"/proc/self", re.IGNORECASE)
]

# ── SCANNER USER-AGENTS ───────────────────────────────────────────────────────
SCANNER_AGENTS = [
    "sqlmap", "nikto", "hydra", "nmap", "gobuster",
    "dirbuster", "wfuzz", "zgrab", "masscan", "metasploit"
]

# ── ROCKYOU WORDLIST ENGINE ───────────────────────────────────────────────────
_sqlite_conn = None
_rockyou_checked_count = 0
_rockyou_hits_count = 0

def get_rockyou_db_connection():
    """Returns a thread-safe / read-only SQLite connection to rockyou.db."""
    global _sqlite_conn
    db_path = getattr(config, "ROCKYOU_DB_PATH", os.path.join(os.path.dirname(__file__), "rockyou.db"))
    if _sqlite_conn is None:
        if os.path.exists(db_path):
            try:
                _sqlite_conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
            except Exception:
                try:
                    _sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
                except Exception:
                    _sqlite_conn = None
    return _sqlite_conn

@lru_cache(maxsize=100000)
def check_rockyou(term: str) -> bool:
    """
    Checks if a given credential term exists in the RockYou dictionary or ICS honeypot wordlist.
    Uses LRU cache + SQLite indexed database for microsecond lookups.
    """
    global _rockyou_checked_count, _rockyou_hits_count
    if not term:
        return False

    w = term.strip().lower()
    _rockyou_checked_count += 1

    # 1. Fast path: check known honeypot traps
    if w in getattr(config, "HONEYPOT_WORDLIST", set()):
        _rockyou_hits_count += 1
        return True

    # 2. SQLite Database path (rockyou.db with 14M indexed entries)
    conn = get_rockyou_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM rockyou WHERE password = ? LIMIT 1", (w,))
            hit = cursor.fetchone() is not None
            if hit:
                _rockyou_hits_count += 1
            return hit
        except Exception:
            pass

    # 3. Text file fallback if DB not yet created
    txt_path = getattr(config, "ROCKYOU_PATH", os.path.join(os.path.dirname(__file__), "rockyou.txt"))
    if os.path.exists(txt_path):
        try:
            with open(txt_path, "r", encoding="latin-1", errors="ignore") as f:
                # Scan top 50,000 passwords in file
                for i, line in enumerate(f):
                    if i > 50000:
                        break
                    if line.strip().lower() == w:
                        _rockyou_hits_count += 1
                        return True
        except Exception:
            pass

    return False

# ── INJECTION INSPECTION HELPERS ──────────────────────────────────────────────
def check_injection_patterns(text: str):
    """
    Checks text (both raw and URL-decoded) for Command Injection, SQLi, and Traversal.
    Returns (detected_type: str, matched_pattern: str, sample: str) or (None, None, None).
    """
    if not text:
        return None, None, None

    decoded = urllib.parse.unquote(text)
    candidates = [text, decoded]
    # Handle double URL encoding
    if "%" in decoded:
        try:
            candidates.append(urllib.parse.unquote(decoded))
        except Exception:
            pass

    for candidate in candidates:
        # Check Command Injection
        for pattern in CMD_INJECTION_PATTERNS:
            m = pattern.search(candidate)
            if m:
                return "CMD_INJECTION", pattern.pattern, m.group(0)

        # Check SQL Injection
        for pattern in SQLI_PATTERNS:
            m = pattern.search(candidate)
            if m:
                return "SQL_INJECTION", pattern.pattern, m.group(0)

        # Check Path Traversal
        for pattern in TRAVERSAL_PATTERNS:
            m = pattern.search(candidate)
            if m:
                return "PATH_TRAVERSAL", pattern.pattern, m.group(0)

    return None, None, None

# ── RATE LIMITING & QUARANTINE ────────────────────────────────────────────────
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
        # Check quarantine expiration (10 minutes)
        if time.time() - _quarantined_ips[ip]["timestamp"] < 600:
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]
        else:
            del _quarantined_ips[ip]
    return False, None, None

# ── MASTER REQUEST INSPECTOR ──────────────────────────────────────────────────
def inspect_request(ip, user_agent, username, password=None):
    """
    Analyzes request metadata, user agent, and payload for anomalies and exploits.
    Returns (is_anomalous: bool, reason: str, tactic: str)
    """
    u_str = (username or "").strip()
    p_str = (password or "").strip()

    # Pre-check: Legitimate authorized corporate credentials are NEVER quarantined
    user_record = config.VALID_USERS.get(u_str)
    if user_record:
        valid_passwords = user_record.get('passwords', [user_record.get('password')])
        if p_str in valid_passwords:
            clear_quarantine(ip)
            return False, "Authorized corporate credentials", "None"

    # 1. Command Injection, SQL Injection, and Path Traversal Inspection
    for field_name, field_val in [("username", u_str), ("password", p_str)]:
        inj_type, _, sample = check_injection_patterns(field_val)
        if inj_type == "CMD_INJECTION":
            _quarantined_ips[ip] = {
                "reason": f"Command injection detected in {field_name}: '{sample}'",
                "tactic": "T1059 (Command and Scripting Interpreter)",
                "timestamp": time.time()
            }
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

        if inj_type == "SQL_INJECTION":
            _quarantined_ips[ip] = {
                "reason": f"SQL injection detected in {field_name}: '{sample}'",
                "tactic": "T1190 (Exploit Public-Facing Application)",
                "timestamp": time.time()
            }
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

        if inj_type == "PATH_TRAVERSAL":
            _quarantined_ips[ip] = {
                "reason": f"Path traversal pattern detected in {field_name}: '{sample}'",
                "tactic": "T1190 (Exploit Public-Facing Application)",
                "timestamp": time.time()
            }
            return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

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

    # 3. RockYou Wordlist & Password Dictionary Trapping
    if p_str and check_rockyou(p_str):
        _quarantined_ips[ip] = {
            "reason": f"Attacker used credentials from RockYou wordlist: '{p_str[:30]}'",
            "tactic": "T1110.001 (Password Guessing via RockYou Wordlist)",
            "timestamp": time.time()
        }
        return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

    if u_str and check_rockyou(u_str):
        _quarantined_ips[ip] = {
            "reason": f"Attacker sprayed username from RockYou dictionary: '{u_str[:30]}'",
            "tactic": "T1110.003 (Password Spraying)",
            "timestamp": time.time()
        }
        return True, _quarantined_ips[ip]["reason"], _quarantined_ips[ip]["tactic"]

    # 4. Check Prior IP Quarantine State (if no specific new attack signature triggered)
    is_q, q_reason, q_tactic = is_ip_quarantined(ip)
    if is_q:
        return True, q_reason, q_tactic

    return False, "Normal", "None"

def inspect_generic_payload(payload_str):
    """
    Examines arbitrary query parameters, URL paths, or request body payloads for exploits.
    Returns (is_exploit: bool, reason: str, tactic: str)
    """
    if not payload_str:
        return False, None, None

    inj_type, _, sample = check_injection_patterns(payload_str)
    if inj_type == "CMD_INJECTION":
        return True, f"Command injection detected in HTTP payload: '{sample}'", "T1059 (Command and Scripting Interpreter)"
    elif inj_type == "SQL_INJECTION":
        return True, f"SQL injection detected in HTTP payload: '{sample}'", "T1190 (Exploit Public-Facing Application)"
    elif inj_type == "PATH_TRAVERSAL":
        return True, f"Path traversal detected in HTTP payload: '{sample}'", "T1190 (Exploit Public-Facing Application)"

    return False, None, None

def get_stats():
    """Returns anomaly detector and RockYou engine telemetry stats."""
    db_ok = os.path.exists(getattr(config, "ROCKYOU_DB_PATH", ""))
    txt_ok = os.path.exists(getattr(config, "ROCKYOU_PATH", ""))
    return {
        "quarantined_ips_count": len(_quarantined_ips),
        "rockyou_db_available": db_ok,
        "rockyou_txt_available": txt_ok,
        "rockyou_lookups": _rockyou_checked_count,
        "rockyou_hits": _rockyou_hits_count
    }
