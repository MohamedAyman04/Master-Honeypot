"""
Attacker Intent Profiler & Adaptive Deception Classifier Engine
================================================================
Tracks and evaluates attacker behavior across 4 primary dimensions:
1. Reconnaissance (I_recon) - Network, host, and port scanning
2. Credential Harvesting (I_cred) - Searching for keys, tokens, vaults
3. Process Sabotage (I_sabo) - Write/disruption commands across:
   - Modbus TCP (FC6, FC16, register writes, coil forcing)
   - Siemens S7comm (DB write, CPU STOP, snap7, memory forcing)
   - DNP3 (direct operate, binary/analog output, trip/close)
   - OPC UA (setpoint injection, write_value, EmergencyStop)
4. PLC Logic & Firmware (I_logic) - Logic tampering, firmware inspection

Computes live intent vectors, dominant personas, dwell times, and writes
real-time metrics to InfluxDB (attacker_intent) and story_logger.
"""

import os
import re
import time
import json
import logging
from datetime import datetime

logger = logging.getLogger("AdaptiveDeceptionEngine")

# ── PATTERN CLASSIFIERS ────────────────────────────────────────────────────────

RECON_PATTERNS = [
    re.compile(r"\b(nmap|zenmap|masscan|zgrab)\b", re.IGNORECASE),
    re.compile(r"\b(ping|hping|hping3|traceroute|tracepath)\b", re.IGNORECASE),
    re.compile(r"\b(ifconfig|ip\s+a|ip\s+addr|ip\s+route|route\s+-n|netstat|ss\s+-tulpn|arp)\b", re.IGNORECASE),
    re.compile(r"\b(cat\s+/etc/hosts|cat\s+/etc/resolv\.conf|uname|hostname|whoami|id|pwd)\b", re.IGNORECASE),
    re.compile(r"\b(find\s+/|locate)\b", re.IGNORECASE),
    re.compile(r"\b(nc\s+-z|ncat\s+-z|curl\s+-s\s+http|wget)\b", re.IGNORECASE),
]

CRED_PATTERNS = [
    re.compile(r"\.(kdbx|key|pem|crt|p12|ovpn)\b", re.IGNORECASE),
    re.compile(r"\b(password|passwd|shadow|master_keys|credentials|secret|token|vault)\b", re.IGNORECASE),
    re.compile(r"\bcat\s+.*(shadow|passwd|\.bash_history|\.ssh|id_rsa|\.env|conf)\b", re.IGNORECASE),
    re.compile(r"\b(grep\s+(-[a-zA-Z]+\s+)*(pass|key|secret|token|auth)|sudo\s+-l)\b", re.IGNORECASE),
    re.compile(r"\b(sshpass|hydra|john|hashcat)\b", re.IGNORECASE),
]

# Process Sabotage across Modbus, S7comm, DNP3, and OPC-UA
SABO_PATTERNS = {
    "modbus": [
        re.compile(r"\bmbtget\s+(-w|-w6|-w16)\b", re.IGNORECASE),
        re.compile(r"\b(write_register|write_registers|write_coil|fc6|fc16)\b", re.IGNORECASE),
        re.compile(r"\bmodbus.*(write|force|inject|override)\b", re.IGNORECASE),
    ],
    "s7comm": [
        re.compile(r"\b(snap7|s7client|s7comm)\b.*(write|dbwrite|stop|force)", re.IGNORECASE),
        re.compile(r"\b(cpu\s+stop|plc_stop|stop_cpu|db1\.dbd|force_var)\b", re.IGNORECASE),
        re.compile(r"\bs7.*(write|override|kill|shut)\b", re.IGNORECASE),
    ],
    "dnp3": [
        re.compile(r"\bdnp3.*(control|direct_operate|operate|select|trip|close|crob)\b", re.IGNORECASE),
        re.compile(r"\b(binary_output|analog_output|crob|trip_close)\b", re.IGNORECASE),
        re.compile(r"\bdnp3_control\b", re.IGNORECASE),
    ],
    "opcua": [
        re.compile(r"\b(opcua|uawrite|asyncua|opc\.tcp).*(write|set|modify)\b", re.IGNORECASE),
        re.compile(r"\b(emergencystop|pumprpm|valveposition).*(write|set|=)\b", re.IGNORECASE),
        re.compile(r"\bwrite_value\s*\(", re.IGNORECASE),
    ]
}

LOGIC_PATTERNS = [
    re.compile(r"\.(project|projectarchive|s7p|pro|ap16|ap17|st|awl|app|bin|hex|elf)\b", re.IGNORECASE),
    re.compile(r"\b(codesys_cli|simatic|tia_portal|step7|micro_win|plc_flash|st_compile|objdump|fw_update)\b", re.IGNORECASE),
    re.compile(r"\b(ob1|ob35|fc1|fb1|ladder|plc_prog|bootproject|runtime_diagnostics)\b", re.IGNORECASE),
    re.compile(r"\b(hmi_app|firmware|plc_logic)\b", re.IGNORECASE),
]

# ── ATTACKER PROFILE DATA CLASS ────────────────────────────────────────────────

class AttackerProfile:
    def __init__(self, ip: str, session_id: str = None):
        self.ip = ip
        self.session_id = session_id or ip
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.command_count = 0
        
        # Raw cumulative intent counts
        self.counts = {
            "recon": 0,
            "cred": 0,
            "sabo": 0,
            "logic": 0
        }

        # Recency-weighted intent scores (tracks active kill-chain stage transitions)
        self.ewma_weights = {
            "recon": 0.0,
            "cred": 0.0,
            "sabo": 0.0,
            "logic": 0.0
        }
        
        # Protocol-specific sabotage counts
        self.sabo_protocol_counts = {
            "modbus": 0,
            "s7comm": 0,
            "dnp3": 0,
            "opcua": 0
        }
        
        self.command_history = []
        self.lures_presented = []
        self.lures_accessed = []

    @property
    def dwell_time_seconds(self) -> float:
        return max(0.0, time.time() - self.first_seen)

    @property
    def normalized_scores(self) -> dict:
        ewma_total = sum(self.ewma_weights.values())
        if ewma_total > 0:
            return {k: round(v / ewma_total, 3) for k, v in self.ewma_weights.items()}
        total = sum(self.counts.values())
        if total == 0:
            return {"recon": 0.25, "cred": 0.25, "sabo": 0.25, "logic": 0.25}
        return {k: round(v / total, 3) for k, v in self.counts.items()}

    @property
    def dominant_persona(self) -> str:
        if sum(self.counts.values()) == 0:
            return "UNCLASSIFIED_PROBE"
        ewma_total = sum(self.ewma_weights.values())
        if ewma_total > 0:
            top = max(self.ewma_weights, key=self.ewma_weights.get)
        else:
            top = max(self.counts, key=self.counts.get)
        mapping = {
            "recon": "NETWORK_TOPOLOGY_SCOUT",
            "cred": "CREDENTIAL_VAULT_HUNTER",
            "sabo": "PROCESS_SABOTEUR",
            "logic": "PLC_FIRMWARE_EXPLOITER"
        }
        return mapping.get(top, "MIXED_ADVERSARY")

    def inspect_command(self, cmd: str) -> dict:
        """Inspects command string, updates intent scores, and returns attribution."""
        self.last_seen = time.time()
        self.command_count += 1
        cmd_clean = cmd.strip()
        cmd_lower = cmd_clean.lower()
        matched = []

        # Passive directory listing (ls / dir): only count as initial recon if no prior activity
        is_passive_ls = cmd_lower in ("ls", "ls -l", "ls -la", "dir", "dir /w", "ll")
        if is_passive_ls:
            if sum(self.counts.values()) == 0:
                self.counts["recon"] += 1
                self.ewma_weights["recon"] += 1.0
                matched.append("recon")
            else:
                matched.append("lure_inspection")
        else:
            # 1. Process Sabotage across Modbus, S7comm, DNP3, and OPC-UA
            sabo_found = False
            for proto, patterns in SABO_PATTERNS.items():
                if any(p.search(cmd_clean) for p in patterns):
                    self.counts["sabo"] += 1
                    self.sabo_protocol_counts[proto] += 1
                    matched.append(f"sabo_{proto}")
                    sabo_found = True

            # General Modbus / write heuristics
            if not sabo_found and ("502" in cmd_clean or "mbtget" in cmd_clean) and ("-w" in cmd_clean or "write" in cmd_lower):
                self.counts["sabo"] += 1
                self.sabo_protocol_counts["modbus"] += 1
                matched.append("sabo_modbus")
                sabo_found = True

            # 2. PLC Logic & Firmware Exploitation
            logic_found = False
            if not sabo_found and any(p.search(cmd_clean) for p in LOGIC_PATTERNS):
                self.counts["logic"] += 1
                matched.append("logic")
                logic_found = True

            # 3. Credential Harvesting
            cred_found = False
            if not sabo_found and not logic_found and any(p.search(cmd_clean) for p in CRED_PATTERNS):
                self.counts["cred"] += 1
                matched.append("cred")
                cred_found = True

            # 4. Reconnaissance
            if not sabo_found and not logic_found and not cred_found and any(p.search(cmd_clean) for p in RECON_PATTERNS):
                self.counts["recon"] += 1
                matched.append("recon")

            # Default fallback: if command executed without specific signature
            if not matched:
                self.counts["recon"] += 1
                matched.append("recon_general")

            # Update recency-weighted EWMA scores so kill-chain stage transitions are responsive
            decay = 0.65
            for k in self.ewma_weights:
                self.ewma_weights[k] *= decay
            if sabo_found:
                self.ewma_weights["sabo"] += 1.2
            elif logic_found:
                self.ewma_weights["logic"] += 1.2
            elif cred_found:
                self.ewma_weights["cred"] += 1.2
            else:
                self.ewma_weights["recon"] += 1.0

        self.command_history.append({
            "ts": datetime.utcnow().isoformat() + "Z",
            "cmd": cmd_clean[:120],
            "matched": matched
        })

        return {
            "matched_vectors": matched,
            "persona": self.dominant_persona,
            "scores": self.normalized_scores,
            "dwell_time": round(self.dwell_time_seconds, 1)
        }

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "session_id": self.session_id,
            "dwell_time_s": round(self.dwell_time_seconds, 1),
            "command_count": self.command_count,
            "dominant_persona": self.dominant_persona,
            "counts": self.counts,
            "normalized_scores": self.normalized_scores,
            "sabo_breakdown": self.sabo_protocol_counts,
            "recent_commands": self.command_history[-8:],
            "lures_accessed": self.lures_accessed
        }

# ── PROFILER SINGLETON & PERSISTENCE ──────────────────────────────────────────

class AttackerIntentProfiler:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AttackerIntentProfiler, cls).__new__(cls)
            cls._instance._profiles = {}
            cls._instance._init_connections()
        return cls._instance

    def _init_connections(self):
        self.influx_url = os.getenv("INFLUX_URL", "http://historian:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN", "supersecrettoken")
        self.influx_org = os.getenv("INFLUX_ORG", "my_refinery")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "sensor_logs")
        self.story_url = os.getenv("STORY_LOGGER_URL", "http://story_logger:8600")

    def get_profile(self, ip: str, session_id: str = None) -> AttackerProfile:
        key = session_id or ip or "default_session"
        if key not in self._profiles:
            self._profiles[key] = AttackerProfile(ip=ip, session_id=key)
        return self._profiles[key]

    def record_command(self, ip: str, cmd: str, session_id: str = None) -> dict:
        profile = self.get_profile(ip, session_id)
        result = profile.inspect_command(cmd)
        
        # Publish live metrics to InfluxDB & story_logger for Grafana
        self._publish_influx_metrics(profile)
        self._publish_story_log(profile, cmd, result)
        
        return result

    def _publish_influx_metrics(self, profile: AttackerProfile):
        """Asynchronously writes attacker_intent points for Grafana dashboards using HTTP Line Protocol."""
        try:
            scores = profile.normalized_scores
            ip_tag = (profile.ip or "unknown").replace(" ", "_")
            persona_tag = profile.dominant_persona.replace(" ", "_")
            persona_code_map = {
                "PROCESS_SABOTEUR": 3,
                "CREDENTIAL_VAULT_HUNTER": 2,
                "NETWORK_TOPOLOGY_SCOUT": 1,
                "PLC_FIRMWARE_EXPLOITER": 4
            }
            p_code = persona_code_map.get(profile.dominant_persona, 1)

            line = (
                f"attacker_intent,attacker_ip={ip_tag},persona={persona_tag} "
                f"persona_code={p_code}i,"
                f"score_recon={float(scores['recon'])},"
                f"score_cred={float(scores['cred'])},"
                f"score_sabo={float(scores['sabo'])},"
                f"score_logic={float(scores['logic'])},"
                f"dwell_time_seconds={float(profile.dwell_time_seconds)},"
                f"command_count={int(profile.command_count)}i,"
                f"sabo_modbus={int(profile.sabo_protocol_counts['modbus'])}i,"
                f"sabo_s7comm={int(profile.sabo_protocol_counts['s7comm'])}i,"
                f"sabo_dnp3={int(profile.sabo_protocol_counts['dnp3'])}i,"
                f"sabo_opcua={int(profile.sabo_protocol_counts['opcua'])}i "
                f"{time.time_ns()}\n"
            )
            url = f"{self.influx_url}/api/v2/write?org={self.influx_org}&bucket={self.influx_bucket}&precision=ns"
            headers = {
                "Authorization": f"Token {self.influx_token}",
                "Content-Type": "text/plain; charset=utf-8"
            }
            import urllib.request
            req = urllib.request.Request(url, data=line.encode("utf-8"), headers=headers)
            urllib.request.urlopen(req, timeout=1.0)
        except Exception:
            pass

    def _publish_story_log(self, profile: AttackerProfile, cmd: str, result: dict):
        try:
            import urllib.request
            is_sabo = any("sabo" in m for m in result.get("matched_vectors", []))
            payload = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "sensor": "adaptive_deception",
                "event_type": "attacker_intent_update",
                "src_ip": profile.ip,
                "stage": "S3",
                "journey_id": "active_deception",
                "outcome": "analyzed",
                "severity": "HIGH" if is_sabo else "INFO",
                "mitre_technique_id": "T0855" if is_sabo else "T0802",
                "mitre_tactic": "Execution" if is_sabo else "Collection",
                "meta": {
                    "persona": profile.dominant_persona,
                    "command": cmd[:80],
                    "dwell_time_s": round(profile.dwell_time_seconds, 1),
                    "matched": result["matched_vectors"]
                }
            }
            req = urllib.request.Request(
                f"{self.story_url}/story/events",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=0.8)
        except Exception:
            pass

# Global Singleton Helper
profiler = AttackerIntentProfiler()
