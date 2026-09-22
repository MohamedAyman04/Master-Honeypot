"""
DMZ Secure OT Access Gateway - Configuration
"""
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dmz_secure_gateway_master_key_2026")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 8088))

# Dual-World Target Endpoints
REAL_WORKSTATION_URL = os.getenv("REAL_WORKSTATION_URL", "http://ws_eng_01:5001")
REAL_OPS_WORKSTATION_URL = os.getenv("REAL_OPS_WORKSTATION_URL", "http://ws_ops_01:5001")
REAL_HISTORIAN_URL = os.getenv("REAL_HISTORIAN_URL", "http://ics_historian_l3:5000")

DECOY_WORKSTATION_URL = os.getenv("DECOY_WORKSTATION_URL", "http://ws_decoy_eng:5001")
DECOY_OPS_WORKSTATION_URL = os.getenv("DECOY_OPS_WORKSTATION_URL", "http://ws_decoy_ops:5001")
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

# TOTP MFA Secret (Base32 encoded)
OTP_BASE32_SECRET = os.getenv("OTP_BASE32_SECRET", "JBSWY3DPEHPK3PXP")

# Authorized Corporate User Accounts (Real Industrial Zone Access)
VALID_USERS = {
    # Primary Shift Operator
    "operator": {
        "password": "Cdu#Op2026!9xVm",
        "role": "operator",
        "name": "Central Control Room Shift Operator"
    },
    "op_cdu_shift1": {
        "password": "Cdu#Op2026!9xVm",
        "role": "operator",
        "name": "CDU-01 Senior Unit Operator"
    },
    # Process Automation Engineer
    "engineer": {
        "password": "Eng#Sys2026!8wQz",
        "role": "engineer",
        "name": "Lead Process Automation Engineer"
    },
    "eng_process_lead": {
        "password": "Eng#Sys2026!8wQz",
        "role": "engineer",
        "name": "Lead Process Automation Engineer"
    },
    # OT Cybersecurity Systems Auditor
    "admin": {
        "password": "Sec#Audit2026!5vKp",
        "role": "admin",
        "name": "OT Systems Compliance Auditor"
    }
}

# Known Honeypot Trap Wordlists (Attempts instantly flagged for deception routing)
HONEYPOT_WORDLIST = {
    "password", "123456", "root", "toor", "admin123",
    "scada", "codesys", "operator123", "engineer456", "plc", "siemens",
    "operator2026!", "engineer2026!"
}
