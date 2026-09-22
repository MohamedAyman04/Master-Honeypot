# Master-Honeypot — Physics-Aware ICS Deception & Cross-Layer Intrusion Detection Framework

A high-interaction, physics-grounded Industrial Cyber-Physical System (ICPS) honeypot and cross-layer intrusion detection research environment. Designed to emulate realistic Operational Technology (OT) infrastructure across 5 segmented Docker networks, continuous hydraulic physics simulation, multi-protocol industrial services (Modbus/TCP, Siemens S7comm, DNP3, and OPC UA), hardware-in-the-loop (HIL) Raspberry Pi 4B controller integration with live edge host diagnostics and volatile memory forensics, an enterprise Purdue Level 3 workstation tier, automated 9-phase cyber-attack campaigns, and a 6-layer cross-layer anomaly detection architecture.

---

## 1. System Architecture & Purdue Model Mapping

The architecture implements a full 5-tier Purdue Model decomposition combining simulated container services, physical hardware PLCs, and an enterprise network:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4 / EXTERNAL THREAT SIMULATION                                                            │
│  • attacker_node        : Kali Linux Node (nmap, pymodbus, snap7, dnp3_probe, attack_suite)     │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 3 — Enterprise & Multi-Workstation Tier (enterprise-net: 192.168.50.0/24)                 │
│  • ws_eng_01            :5021  ← Siemens Field PG M6 Engineering Workstation (192.168.50.21)    │
│  • ws_eng_02            :5022  ← Dell Precision 3660 Industrial Tower (192.168.50.22)            │
│  • ws_ops_01            :5023  ← Advantech PPC-3150S SCADA Operator Console (192.168.50.31)      │
│  • ws_ops_02            :5024  ← Advantech UNO-2484G Industrial Box PC (192.168.50.32)           │
│  • ws_maint_01          :5025  ← Panasonic Toughbook CF-33 Field Maintenance (192.168.50.41)     │
│  • ics_opcua_l3         :4841  ← Enterprise OPC UA Bridge Server (192.168.50.50)                 │
│  • ics_historian_l3     :5005  ← Enterprise SQL Historian Archive (192.168.50.60)                │
│  • ics_historian_api    :5001  ← Authenticated Level-3 REST Gateway                              │
│  • ics_scada_ssh        :2222  ← Engineer/Operator SSH Pivot Host (192.168.50.10)                │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 3.5 — Industrial DMZ & Honeypot Sandbox Deception (dmz-net / sandbox-net)                 │
│  • dmz_gateway          :8088  ← Secure OT Access Gateway (MFA/2FA + Dual-World Routing Engine)    │
│  • ws_decoy_eng         :5026  ← Sandboxed Decoy Workstation (Honeypot Zone, 192.168.99.21)       │
│  • ws_decoy_ops         :5027  ← Sandboxed Decoy Operator Console (Honeypot Zone, 192.168.99.31)  │
│  • plc_simulator        :502   ← High-Interaction Modbus TCP Honeypot                            │
│  • ics_s7_plc           :102   ← Siemens S7comm Honeypot (S7-300 DB1 Emulation)                  │
│  • ics_dnp3             :20000 ← DNP3 Outstation Honeypot (Water/Power Utility Protocol)         │
│  • fake_plc_sim         :503   ← Low-Interaction Deception Tarpit                                │
│  • honeypot_historian_api:5002 ← Decoy Unauthenticated REST API (Tarpit Honeypot)                │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 2 — SCADA Control & Detection Operations (monitor-net)                                   │
│  • ics_ml_engine        :8001  ← 6-Layer Cross-Layer ML Detection Engine (IF, LSTM, CUSUM, NMG) │
│  • ics_historian        :8086  ← InfluxDB v2.7 Time-Series Historian                             │
│  • ics_grafana          :3005  ← SCADA Process, Forensics & Security Dashboards                  │
│  • story_logger         :8600  ← Structured Event Narrative Bus & MITRE ATT&CK Correlator        │
│  • ics_log_dashboard    :8502  ← Streamlit Kill-Chain Log Browser & Analysis Console             │
│  • ics_rpi_bridge              ← Dynamic Hardware Bridge (Auto-Discovery & Fallback Standby)     │
│  • ics_sniffer/correlator      ← Deep Packet Inspection & Command-Consequence Correlator         │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 1 / 0 — Field Process & Actuation (ot-net)                                                │
│  • ics_physics_engine          ← Continuous Hydraulic Pipeline Simulator (100ms ODE Solver)      │
│  • ics_state_store             ← Redis Shared In-Memory Process Bus                              │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  PHYSICAL HARDWARE PLC — Hardware-in-the-Loop Node (172.20.10.8 / 192.168.1.8)                   │
│  • Raspberry Pi 4B (Broadcom BCM2711 Quad-core Cortex-A72 @ 1.8GHz, 4GB RAM, Debian 13 ARM64)   │
│    - CODESYS SoftPLC Engine  : IEC 61131-3 100ms Continuous Cyclic Process Task                  │
│    - Modbus TCP Server (:502): Holding Registers 0–9 (RPM, Valve, Pressure, Flow, Temp, Alarms) │
│    - OPC UA Server (:4840)   : opc.tcp://<PI_HOST>:4840/codesys/server/                          │
│    - WebVisu Console (:8080) : Real-Time HTML5 WebVisu + REST API (/api/status)                 │
│    - Edge Telemetry Host     : SoC Temperature, CPU Load, Clock Freq, Memory RSS Diagnostics     │
│    - Volatile Memory Forensics: Host Runtime Process Memory Inspection & Socket Mapping         │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Web Interfaces & Port Reference

| Service | Port | URL | Credentials / Notes |
|---|---|---|---|
| **DMZ OT Secure Gateway** | `8088` / `8443` | `http://localhost:8088` | `operator` / `Operator2026!` or `engineer` / `Engineer2026!` + TOTP (bypass: `999888`) |
| **Gateway Diagnostics** | `8088` | `http://localhost:8088/status` | Redirects to Grafana Telemetry Dashboard; JSON at `/api/status` |
| **Decoy Engineering WS** | `5026` | `http://localhost:5026` | Sandboxed Decoy Workstation (Siemens Field PG M6 Canary Honeytokens) |
| **Decoy Operator Console**| `5027` | `http://localhost:5027` | Sandboxed Decoy Operator Console (Rockwell ASEM 6300B Canary Honeytokens) |
| **Grafana Dashboards** | `3005` | `http://localhost:3005` | `admin` / `admin` (Level 2 SCADA, Forensics & DMZ Gateway Telemetry) |
| **SCADA Web HMI** | `8060` | `http://localhost:8060` | Interactive operator console & pump controls |
| **Raspberry Pi WebVisu** | `8080` | `http://172.20.10.8:8080` | Native CODESYS HTML5 HMI & `/api/status` |
| **Streamlit Log Browser**| `8502` | `http://localhost:8502` | Live kill-chain and forensic log viewer |
| **InfluxDB Historian** | `8086` | `http://localhost:8086` | `admin` / `password123` (org: `my_refinery`) |
| **ML Engine REST API** | `8001` | `http://localhost:8001` | Anomaly inference & model status endpoints |
| **Story Logger API** | `8600` | `http://localhost:8600` | Narrative event submission endpoint |
| **Engineering WS 01** | `5021` | `http://localhost:5021` | Siemens Field PG M6 management console |
| **Engineering WS 02** | `5022` | `http://localhost:5022` | Dell Precision 3660 workstation |
| **Operations WS 01** | `5023` | `http://localhost:5023` | Advantech PPC-3150S operator interface |
| **Operations WS 02** | `5024` | `http://localhost:5024` | Advantech UNO-2484G control interface |
| **Maintenance WS 01** | `5025` | `http://localhost:5025` | Panasonic Toughbook CF-33 field terminal |
| **Enterprise Historian**| `5005` | `http://localhost:5005` | Level 3 SQL sensor archive |
| **Enterprise OPC UA** | `4841` | `opc.tcp://localhost:4841` | Level 3 SCADA OPC UA data bridge |
| **SCADA SSH Bastion** | `2222` | `ssh operator@localhost -p 2222` | `operator123` / `engineer456` |
| **Modbus TCP Gateway** | `502` | `modbus://localhost:502` | Emulated Level 3.5 Modbus PLC |
| **Siemens S7comm** | `102` | `s7comm://localhost:102` | Emulated S7-300 PLC (Rack 0, Slot 2) |
| **DNP3 Outstation** | `20000`| `dnp3://localhost:20000` | DNP3 telemetry server |

---

## 3. DMZ Secure OT Access Gateway & Dual-World Deception Routing

The framework implements a dynamic dual-world routing engine at Purdue Level 3.5 to achieve active attacker deception while isolating production OT operations:

```
[Remote User / Ingress]
         │
         ▼
[DMZ Secure OT Access Gateway (:8088)]
   ├── 1. Deep Anomaly & Exploit Inspection (SQLi, Traversal, Scanner UA, Wordlists)
   ├── 2. Primary Credential Authentication (operator / engineer)
   └── 3. RFC 6238 TOTP Multi-Factor Authentication (MFA / 2FA / OTP)
         │
         ├──────────────────────────────────────────────┐
         ▼ (Valid Auth + OTP)                           ▼ (Attack / Anomaly / Brute Force)
[Real Industrial Area (Level 3 / Level 2)]   [Sandboxed Honeypot Zone (Level 3.5)]
  • ws_eng_01 (192.168.50.21:5001)             • ws_decoy_eng (192.168.99.21:5001, host :5026)
  • ws_ops_01 (192.168.50.31:5001)             • ws_decoy_ops (192.168.99.31:5001, host :5027)
  • Real InfluxDB Historian (:8086)            • Isolated network: sandbox-net
  • Real SCADA Actuators & Physics API         • Dynamic Raspberry Pi HIL / Physics Link
                                               • Decoy Canary Honeytokens (.pdf, .txt, .xlsx, .kdbx)
                                               • Decoy Historian API (:5002)
                                               • Simulated SCADA Shell & Telemetry
```

### Anomaly-Driven Deception Routing Policy
- **Legitimate Operator Path**: Users providing authorized corporate credentials (`operator`/`Operator2026!`, `engineer`/`Engineer2026!`, or complex passwords `Cdu#Op2026!9xVm`/`Eng#Sys2026!8wQz`) and verified 6-digit TOTP tokens are granted `REAL_INDUSTRIAL` access, seamlessly reverse-proxied to `ws_ops_01` (operators) or `ws_eng_01` (engineers) on `enterprise-net`.
- **Active Attacker Quarantine**: Requests triggering exploit patterns (SQL injection, path traversal), reconnaissance user-agents (`sqlmap`, `nikto`, `hydra`, `nmap`), default ICS dictionary spraying (`admin`, `codesys`, `siemens`, `password`), or $\ge 3$ failed logins within 30 seconds are silently trapped. The gateway presents a fake successful login and diverts the session to the decoy consoles on `sandbox-net`.
- **Targeted Canary Honeytokens**:
  - **Engineering Decoy (`ws_decoy_eng`, host :5026)**: Siemens Field PG M6 (`FAC-ENG-DECOY-9901`). Contains `SCADA_Admin_Master_Keys.kdbx`, `Safety_Interlock_Bypass_Codes.pdf`, and `Refinery_PLC_Logic_Backup_2026.s7p`.
  - **Operator Decoy (`ws_decoy_ops`, host :5027)**: Rockwell Automation ASEM 6300B (`FAC-OPS-DECOY-9902`). Contains `Emergency_Shutdown_Procedure_SOP_Rev4.pdf`, `Shift_Handover_Log_CCR_2026.txt`, and `HMI_Alarm_Bypass_Matrix.xlsx`.
- **Unsupervised ML Data Pipeline**: All attacker actions, dwell times, and command attempts in the decoy sandbox stream directly to InfluxDB (`honeypot_attacker_telemetry`) and `story_logger` (`logs/general logs.jsonl`), fueling the unsupervised **LSTM-Autoencoder** and Isolation Forest clustering models.

---

## 4. Physical Raspberry Pi 4B & CODESYS Integration

The system supports seamless hardware-in-the-loop (HIL) switching between pure container simulation and a physical hardware controller.

### Dynamic Multi-Host Auto-Discovery
The hardware bridge (`scripts/raspberry_pi_bridge.py`) continuously probes candidate IP addresses:
- **Mobile Hotspot Subnet**: `172.20.10.8`
- **Lab / Home Wi-Fi Subnet**: `192.168.1.8`

When switching networks on the fly, the bridge detects socket closure, auto-scans both candidate subnets with sub-second latency, reattaches to the active IP, and notifies the internal services.

### Automatic Standby Decoupling
- While the hardware PLC is active, `ics_rpi_bridge` publishes canonical Modbus telemetry to InfluxDB and maintains a heartbeat in Redis (`rpi_plc_state`).
- The internal container services (`ics_historian_bridge` and `ics_physics_engine`) detect `is_hil_active() == True` and automatically enter `[HIL ACTIVE]` / `[PHYSICS STANDBY]` monitoring mode, ensuring zero telemetry collision or inconsistency across WebVisu, Grafana, and the SCADA HMI.

### Edge Host Diagnostics & Volatile Memory Forensics
Directly queries the physical Broadcom BCM2711 SoC and the running SoftPLC Linux process context:
- **SoC Junction Temperature**: Real-time die thermals (`vcgencmd measure_temp`).
- **Dynamic Clock Frequency & Core Voltage**: Monitored for under-voltage or thermal throttling flags (`0x0` = optimal).
- **Process Memory Segments**: `VmSize`, `VmRSS`, `VmData`, `VmStk` tracking heap and stack integrity.
- **Dynamic Shared Library Mapping**: Cryptographic, protocol, and runtime `.so` shared objects in RAM.
- **Open Protocol Socket Descriptors**: Live file descriptors and socket inodes mapped to network threads.

---

## 5. Six-Layer Cross-Layer Detection Architecture

```
[Layer 1: Protocol Semantic Verification] ──► Modbus deep packet inspection & forced-write rules
[Layer 2: Expert Safety Rules]            ──► Physical Boundary Gate (P > 150 PSI safety limit)
[Layer 3: Statistical Drift Monitor]       ──► EWMA & CUSUM on pressure dynamics (K=0.5, H=6.0)
[Layer 4: Cross-Layer Correlator]         ──► Command-to-consequence temporal verification
[Layer 5: Domain-Separated ML Ensemble]   ──► ML_net (5 network features) & ML_proc (5 process features)
[Layer 6: Decision Fusion & NMG]          ──► Narrow Mechanism Gate & Dual-Gated Physical Defense
```

### Domain Feature Separation
- **Network Feature Space** ($\mathbf{x}_{\text{net}}$): Inter-arrival time, 10s write frequency, Modbus function code, frame length, write ratio. Evaluated by $\text{ML}_{\text{net}}$ (Isolation Forest / Random Forest), achieving $0.982$–$0.989$ Precision.
- **Process Feature Space** ($\mathbf{x}_{\text{proc}}$): Pressure, flow rate, temperature, pressure first-order difference ($\Delta P$), and mean deviation ($\delta_P$). Evaluated by $\text{ML}_{\text{proc}}$ (LSTM Autoencoder).

### Narrow Mechanism Gate (NMG) Formulation
Traditional OR-fusion suffers from severe false-positive inflation in noisy industrial environments. The Narrow Mechanism Gate (NMG) conditionally admits process-layer alerts *only* during silent network conditions:
$$A_{\text{NMG}} = A_{\text{net}} \lor \left( |\delta_P| > \tau_{\text{NMG}} \land f_{\text{write\_10s}} == 0 \right)$$

### Dual-Gated Physical Defense
- **Stealth Replay Gate (NMG)**: Detects un-commanded physical deviations during frozen or replayed network telemetry (Phase 8, $87.6\%$ Recall).
- **Physical Boundary Gate (Layer 2)**: Deterministic safety tripwire triggered when pressure exceeds critical design thresholds ($P > 150\text{ PSI}$), capturing authorized SCADA insider attacks (Phase 9, $100.0\%$ Recall).

---

## 6. Benchmark Performance Across Multi-Hour Campaigns

Benchmark results evaluated via `python scripts/canonical_evaluation.py` (`val_frac=0.45`, `SEED=42`, strict validation threshold calibration, recovery masking):

| Dataset | Configuration | Precision | Recall | F1 Score | TP | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| **Dataset 1** (`20260724_014825`, 6.5h) | Network-only Baseline ($\text{L1} + \text{ML}_{\text{net}}$) | 0.866 | 0.378 | **0.527** | 123 | 19 | 202 |
| | Combined Architecture (OR Fusion) | 0.212 | 0.778 | **0.333** | 253 | 942 | 72 |
| | ★ **Narrow Mechanism Gate (NMG)** | **0.485** | **0.760** | **0.592** | **247** | **262** | **78** |
| | | | | | | | |
| **Dataset 2** (`20260725_055634`, 6.5h) | Network-only Baseline ($\text{L1} + \text{ML}_{\text{net}}$) | 0.982 | 0.538 | **0.695** | 267 | 5 | 229 |
| | Combined Architecture (OR Fusion) | 0.173 | 0.829 | **0.286** | 411 | 1965 | 85 |
| | ★ **Narrow Mechanism Gate (NMG)** | **0.600** | **0.972** | **0.742** | **482** | **321** | **14** |
| | | | | | | | |
| **Dataset 3** (`20260801_052308`, 7.8h) | Network-only Baseline ($\text{L1} + \text{ML}_{\text{net}}$) | 0.989 | 0.601 | **0.748** | 366 | 4 | 243 |
| | Combined Architecture (OR Fusion) | 0.167 | 0.700 | **0.270** | 426 | 2124 | 183 |
| | ★ **Narrow Mechanism Gate (NMG)** | **0.881** | **0.901** | **0.891** | **549** | **74** | **60** |

---

## 7. Continuous Physical Process Dynamics

The pipeline transport loop (`physics/physics_engine.py`) models continuous fluid mechanics via coupled ordinary differential equations solved at 100ms intervals:

$$P^*(t) = \left(\frac{R(t)}{10.0}\right) \times \left(1.5 - 0.8 \cdot V(t)\right)$$
$$Q^*(t) = \left(\frac{R(t)}{50.0}\right) \times V(t)$$

Dynamic state relaxation with process noise:
$$\dot{P}(t) = \kappa_p \left( P^*(t) - P(t) \right) + \eta_p(t)$$
$$\dot{Q}(t) = \kappa_q \left( Q^*(t) - Q(t) \right) + \eta_q(t)$$
$$\dot{T}(t) = \gamma_t R(t) - \delta_t Q(t) - \lambda_t (T(t) - T_{\text{ambient}}) + \eta_t(t)$$

Where $R(t)$ is pump motor RPM, $V(t) \in [0.0, 1.0]$ is control valve position, $P(t)$ is line pressure (PSI), $Q(t)$ is volumetric flow rate (L/s), and $T(t)$ is process temperature (°C).

---

## 8. Automated 9-Phase Cyber-Attack Campaigns

The attack suite (`attacker_node/attack_suite.py`) executes an end-to-end cyber kill chain mapped directly to the MITRE ATT&CK for ICS framework:

| Phase | Tactical Objective | MITRE ATT&CK Tactic | Technique ID & Name | Targeted Layer |
|---|---|---|---|---|
| **1** | Network Reconnaissance | Discovery (`TA0007`) | `T1046` Network Service Scanning | Level 3.5 DMZ |
| **2** | Service Fingerprinting | Discovery (`TA0007`) | `T1082` System Information Discovery | Modbus / S7 / DNP3 |
| **3** | Vulnerability Probing | Discovery (`TA0007`) | `T1018` Remote System Discovery | Protocol Handshakes |
| **4** | Semantic Command Injection | Impact (`TA0040`) | `T0855` Unauthorized Command Message | Level 1 Modbus FC6 |
| **5** | Stealth Pressure Drift | Evasion / Impact | `T0836` Parameter Drift (+2 PSI increments) | Process Physics |
| **6** | Lateral Movement | Lateral Move (`TA0008`) | `T1021` Remote Services (SCADA SSH Pivot) | Level 3 → Level 2 |
| **7** | Actuator Hijacking | Impact (`TA0040`) | `T0831` Manipulation of Control | Pump / Valve State |
| **8** | Telemetry Replay Attack | Defense Evasion (`TA0037`) | `T0853` Spoofed Sensor Telemetry | InfluxDB Historian |
| **9** | SCADA Insider Tampering | Impact (`TA0040`) | `T0855` Authorized Operator Overpressure | SCADA HMI / SSH |

---

## 9. Repository Layout & Organization

The codebase is organized into dedicated functional parent directories:

```text
Master-Honeypot/
├── .env                       # Central environment variables (passwords, tokens, RPI_HOST)
├── .gitignore                 # Standard version control ignore rules
├── docker-compose.yml         # 30-container production orchestration file
├── README.md                  # Comprehensive framework documentation
├── requirements.txt           # Python package dependencies
├── general logs.jsonl -> logs # Backward compatibility symlink for container mounts
│
├── attacker_node/             # Kali Linux penetration node & MITRE attack suite
├── codesys_pi/                # CODESYS SoftPLC runtime files, systemd unit, deploy scripts
├── dmz_gateway/               # DMZ Secure OT Access Gateway, MFA/2FA, & Deception Router
├── fake_plc/                  # Low-interaction Modbus honeypot tarpit
├── grafana_dashboards/        # Production Grafana dashboard definitions (JSON)
├── grafana_provisioning/      # Automated Grafana datasource and dashboard provisioning
├── historian_api/             # Level 2 authenticated Historian REST API
├── hmi/                       # Dash SCADA operator web console & simulator
├── honeypot/                  # Honeypot core configuration
├── honeypot_historian_api/    # DMZ decoy unauthenticated Historian API
├── journal/                   # Research lab notes and experiment logs
├── log_dashboard/             # Streamlit kill-chain log browser (:8502)
├── logger/                    # Network sniffer, DPI logger, and event correlator
├── logs/                      # Central persistent log store (general logs.jsonl)
├── ml-engine/                 # 6-layer ML anomaly detection service & detector algorithms
├── physics/                   # Continuous ODE hydraulic simulation engine
├── plc/                       # Primary high-interaction Modbus, S7-300, and DNP3 PLCs
├── results/                   # Evaluation benchmark CSVs, ablation data & reports
│   └── figures/               # Thesis confusion matrices, PR curves, and timeline plots
├── scada_ssh/                 # SCADA SSH honeypot bastion & physics REST API
├── scripts/                   # Production scripts, hardware tools, and tests
│   ├── attacks/               # Standalone attack scripts (attack_simulation.py)
│   ├── evaluation/            # Benchmark scripts (evaluate.py, profile_normals.py)
│   ├── raspberry_pi_bridge.py # Dynamic HIL bridge with candidate host auto-discovery
│   ├── test_edge_forensics_and_thermals.py # Live SoC & volatile memory forensics suite
│   ├── test_raspberry_pi_integration.py    # 5-protocol automated hardware verification
│   └── canonical_evaluation.py             # Authoritative 6-layer benchmark evaluator
├── shared/                    # Shared data structures, MITRE mapping & StoryClient
├── story_logger/              # Structured story logger microservice
└── workstations/              # Purdue Level 3 enterprise & decoy workstation cluster
    └── database-files/honeytokens/ # High-value canary honeytokens (.kdbx, .pdf, .s7p)
```

---

## 10. Quickstart & Verification Commands

### 1. Launch the Full Honeypot Stack
```bash
# Clone the repository
git clone git@github.com:MohamedAyman04/Master-Honeypot.git
cd Master-Honeypot

# Start all 30 containers in background
docker compose up --build -d

# Verify container health
docker compose ps
```

### 2. Physical Raspberry Pi 4B Verification
```bash
# Run automated 5-protocol test suite (auto-discovers 172.20.10.8 / 192.168.1.8)
python3 scripts/test_raspberry_pi_integration.py

# Run live edge CPU/thermals and volatile memory forensics suite
python3 scripts/test_edge_forensics_and_thermals.py

# Inspect OPC UA Address Space on the Raspberry Pi
python3 scripts/inspect_opcua.py --watch
```

### 3. Run Benchmark Evaluation Pipeline
```bash
# Execute canonical 6-layer evaluation on multi-hour campaign data
python3 scripts/canonical_evaluation.py

# Run Phase 7 gate evaluation
python3 scripts/evaluate_phase7_gate.py
```

### 4. Execute Kill-Chain Attacks
```bash
# Launch full 9-phase attack suite inside the Kali attacker container
docker exec -it attacker_node python3 /app/attack_suite.py --phase 0

# Or test an individual attack phase (e.g. Phase 5 stealth drift)
docker exec -it attacker_node python3 /app/attack_suite.py --phase 5
```
