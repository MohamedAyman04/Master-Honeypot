"""
DMZ Secure OT Access Gateway - Configuration
"""
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dmz_secure_gateway_master_key_2026")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 8088))

# Dual-World Target Endpoints
# ── Normal Telemetry (4 Workstations: 2 Engineers, 2 Operators) ─────────────
REAL_ENG_WORKSTATION_1_URL = os.getenv("REAL_ENG_WORKSTATION_1_URL", "http://ws_eng_01:5001")
REAL_ENG_WORKSTATION_2_URL = os.getenv("REAL_ENG_WORKSTATION_2_URL", "http://ws_eng_02:5001")
REAL_OPS_WORKSTATION_1_URL = os.getenv("REAL_OPS_WORKSTATION_1_URL", "http://ws_ops_01:5001")
REAL_OPS_WORKSTATION_2_URL = os.getenv("REAL_OPS_WORKSTATION_2_URL", "http://ws_ops_02:5001")

REAL_WORKSTATION_URL = os.getenv("REAL_WORKSTATION_URL", REAL_ENG_WORKSTATION_1_URL)
REAL_OPS_WORKSTATION_URL = os.getenv("REAL_OPS_WORKSTATION_URL", REAL_OPS_WORKSTATION_1_URL)
REAL_HISTORIAN_URL = os.getenv("REAL_HISTORIAN_URL", "http://ics_historian_l3:5000")

# ── Honeypot Deception Zone (5 Workstations: 2 Engineers, 2 Operators, 1 Main) ──
DECOY_ENG_WORKSTATION_1_URL = os.getenv("DECOY_ENG_WORKSTATION_1_URL", "http://ws_decoy_eng:5001")
DECOY_ENG_WORKSTATION_2_URL = os.getenv("DECOY_ENG_WORKSTATION_2_URL", "http://ws_decoy_eng_02:5001")
DECOY_OPS_WORKSTATION_1_URL = os.getenv("DECOY_OPS_WORKSTATION_1_URL", "http://ws_decoy_ops:5001")
DECOY_OPS_WORKSTATION_2_URL = os.getenv("DECOY_OPS_WORKSTATION_2_URL", "http://ws_decoy_ops_02:5001")
DECOY_MAIN_WORKSTATION_URL  = os.getenv("DECOY_MAIN_WORKSTATION_URL",  "http://ws_decoy_main:5001")

DECOY_WORKSTATION_URL = os.getenv("DECOY_WORKSTATION_URL", DECOY_ENG_WORKSTATION_1_URL)
DECOY_OPS_WORKSTATION_URL = os.getenv("DECOY_OPS_WORKSTATION_URL", DECOY_OPS_WORKSTATION_1_URL)
DECOY_HISTORIAN_URL = os.getenv("DECOY_HISTORIAN_URL", "http://honeypot_historian_api:5000")

# Telemetry and Narrative Logging
STORY_LOGGER_URL = os.getenv("STORY_LOGGER_URL", "http://story_logger:8600")
INFLUX_URL = os.getenv("INFLUX_URL", "http://historian:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "supersecrettoken")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my_refinery")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "sensor_logs")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3005/d/dmz-gateway-telemetry/dmz-access-gateway-and-dual-world-telemetry")

# Security and Rate Limiting
BRUTE_FORCE_WINDOW = int(os.getenv("BRUTE_FORCE_WINDOW", 30)) # seconds
BRUTE_FORCE_THRESHOLD = int(os.getenv("BRUTE_FORCE_THRESHOLD", 3)) # attempts

# Corporate Oil Refinery Branding (ARABCO)
COMPANY_NAME = os.getenv("COMPANY_NAME", "ARABCO")
SECURITY_DIVISION = os.getenv("SECURITY_DIVISION", "ARABCO Operations")
GATEWAY_BRANDING = os.getenv("GATEWAY_BRANDING", "ARABCO")

# SMTP / Email MFA Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "ARABCO <noreply@arabco-refinery.com>")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Authorized Corporate User Accounts (Real Industrial Zone Access)
VALID_USERS = {
    # Lead OT Process Automation Engineer
    "mohamed-ayman": {
        "passwords": ["youssefEssam2009$"],
        "password": "youssefEssam2009$",
        "role": "engineer",
        "name": "Mohamed Ayman",
        "email": "mohikel6@gmail.com",
        "security_questions": {
            "dog_name": "Roy",
            "birth_place": "Egypt",
            "siblings_count": "2"
        }
    }
}

# Known Honeypot Trap Wordlists (Attempts instantly flagged for deception routing)
HONEYPOT_WORDLIST = {
    "password", "123456", "root", "toor", "admin123",
    "scada", "codesys", "operator123", "engineer456", "plc", "siemens",
    "guest", "test",
    # Legacy default roles now trapped as honeypot decoys
    "operator", "engineer", "admin", "Operator2026!", "Engineer2026!"
}

# RockYou Dictionary & Pre-indexed Database Configuration
ROCKYOU_PATH = os.getenv("ROCKYOU_PATH", os.path.join(os.path.dirname(__file__), "rockyou.txt"))
ROCKYOU_DB_PATH = os.getenv("ROCKYOU_DB_PATH", os.path.join(os.path.dirname(__file__), "rockyou.db"))
ROCKYOU_URL = os.getenv(
    "ROCKYOU_URL",
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz"
)

