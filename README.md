# ICS Honeypot — Physics-Aware Industrial Control System Deception & Cross-Layer Intrusion Detection Environment

A high-interaction, physics-grounded Industrial Cyber-Physical System (\ac{icps}) honeypot and cross-layer intrusion detection research environment. Designed to emulate realistic Operational Technology (\ac{ot}) infrastructure across 5 segmented Docker networks, continuous hydraulic physics simulation, Modbus/TCP, Siemens S7comm, DNP3, and OPC UA services, hardware-in-the-loop (HIL) Raspberry Pi 4B controller integration, automated 9-phase cyber-attack campaigns (including stealth drift, un-commanded telemetry replay, and authorized SCADA insider setpoint manipulation), and a 6-layer cross-layer detection architecture.

---

## 1. System Snapshot & Purdue Model Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4 / EXTERNAL THREAT SIMULATION                                                            │
│  • attacker_node        : Kali Linux Node (nmap, pymodbus, snap7, dnp3_probe, attack_suite)     │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 3 — Enterprise & Remote Access (enterprise-net: 192.168.50.0/24)                         │
│  • ics_historian_api    :5001  ← Authenticated Level-3 REST API                                  │
│  • ics_scada_ssh        :2222  ← Engineer/Operator SSH Pivot (static IP: 192.168.50.10)          │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 3.5 — Industrial DMZ (dmz-net: externally reachable)                                      │
│  • plc_simulator        :502   ← Modbus TCP Honeypot                                             │
│  • ics_s7_plc           :102   ← Siemens S7comm Honeypot (S7-300 DB1)                            │
│  • ics_dnp3             :20000 ← DNP3 Utility Protocol Honeypot                                  │
│  • fake_plc_sim         :503   ← Low-Interaction Deception Tarpit                                │
│  • honeypot_historian_api:5002 ← Decoy Unauthenticated REST API                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 2 — SCADA & Monitoring (monitor-net)                                                      │
│  • ics_ml_engine        :8001  ← 6-Layer Detection Engine (Isolation Forest, LSTM, CUSUM, NMG)  │
│  • ics_historian        :8086  ← InfluxDB v2.7 Time-Series Store                                 │
│  • ics_grafana          :3005  ← SCADA Process & Security Dashboards                             │
│  • ics_hmi              :8060  ← SCADA Operator Web Console                                      │
│  • story_logger         :8600  ← JSONL Event Narrative Bus                                       │
│  • ics_log_dashboard    :8502  ← Streamlit Kill-Chain Log Browser                                │
│  • ics_sniffer/correlator      ← Deep Packet Inspection & Command-Consequence Correlator        │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  LEVEL 1 / 0 — Field Process & Physical Devices (ot-net)                                         │
│  • ics_physics_engine          ← Continuous Hydraulic Pipeline Simulator (100ms ODE solver)     │
│  • ics_state_store             ← Redis Shared In-Memory Process Bus                              │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  PHYSICAL HARDWARE PLC — Hardware-in-the-Loop Node (172.20.10.8 / 192.168.1.8)                   │
│  • Raspberry Pi 4B (Debian 13 ARM64) running CODESYS SoftPLC Engine                             │
│    - Modbus TCP (:502)       - Siemens S7comm (:102 DB1)   - DNP3 (:20000)                       │
│    - OPC UA (:4840)          - WebVisu HMI (:8080)         - IEC 61131-3 100ms Scan Cycle        │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Authoritative Benchmark Results Across 3 Multi-Hour Campaigns

All numbers produced by `python scripts/canonical_evaluation.py` (`val_frac=0.45`, `SEED=42`, validation-only threshold calibration, recovery masking):

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

## 3. Six-Layer Cross-Layer Detection Architecture

```
[Layer 1: Protocol Semantic Verification] ──► Modbus deep packet inspection & forced-write rules
[Layer 2: Expert Safety Rules]            ──► Physical Boundary Gate (P > 150 PSI safety limit)
[Layer 3: Statistical Drift Monitor]       ──► EWMA & CUSUM on pressure dynamics (K=0.5, H=6.0)
[Layer 4: Cross-Layer Correlator]         ──► Command-to-consequence temporal verification
[Layer 5: Domain-Separated ML Ensemble]   ──► ML_net (5 network features) & ML_proc (5 process features)
[Layer 6: Decision Fusion & NMG]          ──► Narrow Mechanism Gate & Dual-Gated Physical Defense
```

* **Domain Feature Separation:** $\mathbf{x}_{\text{net}}$ (protocol timing, write frequency, FC, length) for $\text{ML}_{\text{net}}$ ($0.982$--$0.989$ Precision) vs. $\mathbf{x}_{\text{proc}}$ (pressure, flow rate, temperature, $\Delta P$, mean dev) for $\text{ML}_{\text{proc}}$.
* **Narrow Mechanism Gate (NMG — Stealth Replay Gate):**
  $$A_{\text{NMG}} = A_{\text{net}} \lor \left( |\delta_P| > \tau_{\text{NMG}} \land f_{\text{write\_10s}} == 0 \right)$$
  Admitting process alerts *only* when network detection is silent AND physical mean deviations occur without Modbus write traffic.
* **Dual-Gated Physical Mechanism Defense:** Pairing NMG's *Stealth Replay Gate* (Phase 8 replay, $87.6\%$ recall) with Layer 2's deterministic *Physical Boundary Gate* ($P > 150\text{ PSI}$, Phase 9 insider setpoint attack, $100.0\%$ recall).

---

## 4. Physical Process Dynamics & Mathematical Formulation

The physics engine (`physics/physics_engine.py`) models a continuous hydraulic pipeline transport loop:
$$P^*(t) = \left(\frac{R(t)}{10.0}\right) \times \left(1.5 - 0.8 \cdot V(t)\right)$$
$$Q^*(t) = \left(\frac{R(t)}{50.0}\right) \times V(t)$$

Continuous relaxation dynamics:
$$\dot{P}(t) = \kappa_p \left( P^*(t) - P(t) \right) + \eta_p(t)$$
$$\dot{Q}(t) = \kappa_q \left( Q^*(t) - Q(t) \right) + \eta_q(t)$$
$$\dot{T}(t) = \gamma_t R(t) - \delta_t Q(t) - \lambda_t (T(t) - T_{\text{ambient}}) + \eta_t(t)$$

---

## 5. Automated 9-Phase Cyber-Attack Campaigns

| Phase | Scenario / Attack Tactic | ATT&CK Tactic | Technique | Detection Gate |
|---|---|---|---|---|
| 1 | Network Reconnaissance | Discovery (`TA0007`) | `T1046` Network Service Scanning | Layer 1 Network Semantics |
| 2 | Service Fingerprinting | Discovery (`TA0007`) | `T1082` System Information Discovery | Layer 1 Network Semantics |
| 3 | Vulnerability Scanning | Discovery (`TA0007`) | `T1018` Remote System Discovery | Layer 1 Protocol Rules |
| 4 | Semantic Injection | Impact (`TA0040`) | `T0855` Unauthorized Command Message | Layer 1 Network Semantics |
| 5 | Stealth Pressure Drift | Evasion / Impact | `T0836` Parameter Drift (+2 PSI/step) | Layer 3 EWMA / CUSUM (100% Recall) |
| 6 | Lateral Movement | Lateral Move (`TA0008`) | `T1021` Remote Services (SCADA SSH) | Layer 1 Auth Monitor |
| 7 | Actuator Hijacking | Impact (`TA0040`) | `T0831` Manipulation of Control | Layer 1 $\text{ML}_{\text{net}}$ + Layer 4 |
| 8 | Telemetry Replay Attack | Defense Evasion | `T0853` Spoofed Sensor Telemetry | Layer 6 NMG Stealth Replay Gate |
| 9 | SCADA Insider Setpoint | Impact (`TA0040`) | `T0855` Authorized SSH/HMI Tampering | Layer 2 Physical Boundary Gate ($P>150$) |

---

## 6. Quickstart & Testing Commands

### Automated Multi-Protocol Verification (Raspberry Pi & Docker)
```bash
# Run complete 5-protocol test suite against Raspberry Pi
python3 scripts/test_raspberry_pi_integration.py --host 172.20.10.8

# Inspect OPC UA Address Space & Live Nodes
python3 scripts/inspect_opcua.py
python3 scripts/inspect_opcua.py --watch
```

### Run Authoritative Benchmark Evaluation
```bash
python3 scripts/canonical_evaluation.py
```

### Start Docker Stack
```bash
docker compose up --build -d
```
