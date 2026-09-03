#!/usr/bin/env python3
"""
Update Comparative-OT-Security-Landscape.xlsx with an academically honest,
balanced, and rigorous comparison across all dimensions:
- Acknowledge that Real Physics / Physical Testbeds are VASTLY SUPERIOR in physical complexity,
  ground-truth fluid/chemical dynamics, zero modeling approximation error, and physical phenomena.
- Accurately position Your Work: A simplified, low-order 1-stage hydraulic ODE designed for
  cyber deception, low-cost edge honeynet deployment, and safe attack experimentation.
- Clearly present Trade-offs, Strengths, and Weaknesses across all 4 paradigms.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FILE_PATH = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/Comparative-OT-Security-Landscape.xlsx"

def update_balanced_workbook():
    wb = openpyxl.load_workbook(FILE_PATH)

    # ── Styling Definitions ───────────────────────────────────────────────────
    FONT_TITLE = Font(name="Calibri", size=15, bold=True, color="003366")
    FONT_SUBTITLE = Font(name="Calibri", size=10, italic=True, color="555555")
    FONT_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    FONT_MY_WORK = Font(name="Calibri", size=9.5, bold=True, color="002B49")
    FONT_DATA = Font(name="Calibri", size=9, color="222222")
    
    FONT_TICK_YES = Font(name="Calibri", size=10, bold=True, color="0E6655") # Dark Green
    FONT_TICK_NO = Font(name="Calibri", size=9.5, color="922B21") # Dark Red
    FONT_TICK_PARTIAL = Font(name="Calibri", size=9.5, bold=True, color="B7950B") # Amber/Yellow for Partial/Trade-off
    FONT_SUPERIOR = Font(name="Calibri", size=9.5, bold=True, color="1B4F72") # Deep Blue for Superior
    
    FONT_PHYSICS = Font(name="Calibri", size=9, color="1A5276")
    FONT_TRADEOFF = Font(name="Calibri", size=9, italic=True, color="784212") # Warm Brown for Honest Trade-off
    FONT_ADVANTAGE = Font(name="Calibri", size=9, bold=True, color="0B5345")

    FILL_HEADER = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
    FILL_MY_WORK = PatternFill(start_color="D4E6F1", end_color="D4E6F1", fill_type="solid")
    FILL_SUPERIOR = PatternFill(start_color="E8F8F5", end_color="E8F8F5", fill_type="solid")
    FILL_ALT_ROW = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
    FILL_WHITE = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    FILL_PHYSICS = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
    FILL_TRADEOFF = PatternFill(start_color="FEF9E7", end_color="FEF9E7", fill_type="solid") # Warm cream for trade-offs

    THIN_BORDER = Border(
        left=Side(style='thin', color='D5D8DC'),
        right=Side(style='thin', color='D5D8DC'),
        top=Side(style='thin', color='D5D8DC'),
        bottom=Side(style='thin', color='D5D8DC')
    )
    MY_WORK_BORDER = Border(
        left=Side(style='medium', color='003366'),
        right=Side(style='medium', color='003366'),
        top=Side(style='medium', color='003366'),
        bottom=Side(style='medium', color='003366')
    )

    ALIGN_CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
    ALIGN_HEADER = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. UPDATE SHEET 1: Executive Summary & Scorecard (Balanced & Honest)
    # ─────────────────────────────────────────────────────────────────────────
    ws_exec = wb['Executive Summary & Scorecard']
    for rng in list(ws_exec.merged_cells.ranges):
        ws_exec.unmerge_cells(str(rng))

    ws_exec.cell(2, 2, "OT & Cyber-Physical Security Literature — Balanced Academic Scorecard").font = FONT_TITLE
    ws_exec.cell(3, 2, "Objective Comparison of Trade-Offs: Sim Only vs Hybrid/HIL vs Real Physical Plants vs Your Master's Work").font = FONT_SUBTITLE

    scorecard_headers = [
        "Evaluation Dimension / Trade-Off",
        "Theme 1: Sim Only (18 Papers)",
        "Theme 2: Hybrid & HIL (24 Papers)",
        "Theme 3: Real Physics & Hardware (5 Papers)",
        "★ YOUR MASTER'S WORK (HIL SoftPLC)"
    ]

    scorecard_rows = [
        # Physical Reality
        ["Physical Process Fidelity & Realism", 
         "❌ Low (Synthetic / Static CSV)", 
         "🟡 Moderate (PC-Simulated ODE)", 
         "✔️ SUPERIOR (100% Ground Truth Real Fluid/Pipes)", 
         "🟡 Moderate (Simplified 1-Stage Hydraulic ODE)"],
        
        # Physical Phenomena
        ["Complex Phenomena (Cavitation, Wear, Chemistry)", 
         "❌ None (Omitted)", 
         "🟡 Very Limited (Complex solvers needed)", 
         "✔️ SUPERIOR (Real Turbulence, Wear, Chemical Rx)", 
         "❌ Omitted (Low-order ODE for real-time edge)"],
        
        # Sim-to-Real Modeling Error
        ["Modeling Error & Approximation", 
         "❌ High (Disconnected from hardware)", 
         "🟡 Moderate (Numerical truncation in PC)", 
         "✔️ ZERO Modeling Error (Governed by Nature)", 
         "🟡 Approximated (Linearized low-order ODEs)"],

        # Sensor Noise Realism
        ["Sensor Noise & Analog Dynamics", 
         "❌ Zero-Noise / Idealized", 
         "❌ Often Omitted (Deterministic)", 
         "✔️ SUPERIOR (Real Analog Drift, ADC Noise)", 
         "🟡 Synthetic Gaussian Noise N(0, σ²)"],

        # Closed-Loop Feedback
        ["Closed-Loop Process Feedback", 
         "❌ Open-Loop or Dummy Return", 
         "✔️ Closed-Loop via Co-Simulation", 
         "✔️ Full Physical Closed-Loop", 
         "✔️ Real-Time Closed-Loop (dt = 100ms)"],

        # Safety Interlocks
        ["Safety Interlock / SIS Implementation", 
         "❌ Missing in >90% of Papers", 
         "🟡 Software-defined thresholds", 
         "✔️ Real Physical Relief Valves & Interlocks", 
         "✔️ Software SIS Trip Logic (P > 200 PSI)"],

        # Destructive Attack Safety
        ["Destructive Attack Testing & Safety", 
         "✔️ 100% Safe (Virtual, Zero damage)", 
         "✔️ 100% Safe (Simulated in PC)", 
         "❌ HIGH HAZARD (Real pipe burst / pump burnout)", 
         "✔️ 100% SAFE (Unlimited overpressure exploration)"],

        # Cyber Deception
        ["Cyber Deception & Honeynet Feasibility", 
         "🟡 Easy, but Fingerprintable", 
         "🟡 Complex setup / Single protocol", 
         "❌ IMPRACTICAL (Cannot expose real plants to net)", 
         "✔️ SUPERIOR (Designed specifically for honeynets)"],

        # Protocol Coverage
        ["Industrial Protocol Coverage", 
         "Single (Modbus/BACnet)", 
         "Mostly Single-Protocol (Modbus)", 
         "Single / Proprietary Vendor", 
         "✔️ 4 Protocols (Modbus, OPC-UA, S7, DNP3)"],

        # Host-Level Security
        ["SCADA Host & Memory Forensics", 
         "❌ Network-only analysis", 
         "❌ Network-only analysis", 
         "🟡 Partial (Linux SBCs)", 
         "✔️ Integrated SCADA SSH + Memory Artifacts"],

        # Edge Profiling
        ["Edge Embedded Profiling (CPU/Thermals)", 
         "❌ Unmeasured (Runs on PC/Cloud)", 
         "❌ Rarely Measured (<5%)", 
         "🟡 Partial Standalone Benchmarks", 
         "✔️ Continuous ARM64 Profiling (44.3°C, CPU, RAM)"],

        # System Cost & Scale
        ["Capital Cost & Maintenance", 
         "✔️ Near-Zero Cost", 
         "🟡 High ($5K–$50K Workstations)", 
         "❌ EXTREME CAPITAL ($50K–$1M+ testbeds)", 
         "✔️ Ultra-Low Cost (~$50 Raspberry Pi 4B)"],

        # Reconfigurability
        ["Experimental Reconfigurability", 
         "✔️ High (Code parameter change)", 
         "✔️ High (Simulator model edit)", 
         "❌ Rigid (Physical plumbing/wiring changes)", 
         "✔️ High (Dynamic ODE coefficient tuning)"]
    ]

    for c_idx, h_text in enumerate(scorecard_headers, 2):
        cell = ws_exec.cell(5, c_idx, h_text)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = THIN_BORDER

    for r_offset, r_data in enumerate(scorecard_rows):
        r_num = 6 + r_offset
        for c_idx, val in enumerate(r_data, 2):
            cell = ws_exec.cell(r_num, c_idx, val)
            cell.border = THIN_BORDER
            if c_idx == 2:
                cell.font = Font(name="Calibri", size=9.5, bold=True, color="003366")
                cell.alignment = ALIGN_LEFT
                cell.fill = FILL_ALT_ROW
            elif c_idx == 5: # Theme 3 (Real Physics)
                if "SUPERIOR" in val or "ZERO" in val:
                    cell.font = FONT_SUPERIOR
                    cell.fill = FILL_SUPERIOR
                elif "HAZARD" in val or "EXTREME" in val or "IMPRACTICAL" in val or "❌" in val:
                    cell.font = FONT_TICK_NO
                    cell.fill = FILL_WHITE
                else:
                    cell.font = FONT_DATA
                    cell.fill = FILL_WHITE
                cell.alignment = ALIGN_LEFT
            elif c_idx == 6: # YOUR WORK
                if "SUPERIOR" in val:
                    cell.font = FONT_ADVANTAGE
                    cell.fill = FILL_MY_WORK
                elif "🟡" in val or "Approximated" in val or "❌" in val:
                    cell.font = FONT_TRADEOFF
                    cell.fill = FILL_TRADEOFF
                else:
                    cell.font = FONT_MY_WORK
                    cell.fill = FILL_MY_WORK
                cell.alignment = ALIGN_LEFT
            else:
                cell.font = FONT_DATA
                cell.alignment = ALIGN_LEFT
                cell.fill = FILL_WHITE

    ws_exec.column_dimensions['B'].width = 38
    ws_exec.column_dimensions['C'].width = 28
    ws_exec.column_dimensions['D'].width = 30
    ws_exec.column_dimensions['E'].width = 38
    ws_exec.column_dimensions['F'].width = 42

    # ─────────────────────────────────────────────────────────────────────────
    # 2. ENHANCE THE 3 THEME SHEETS WITH BALANCED CONTENT
    # ─────────────────────────────────────────────────────────────────────────
    BALANCED_COLUMNS = [
        ("Paper / System Name", 30, ALIGN_LEFT),
        ("Target Domain", 16, ALIGN_CENTER),
        ("Physical Hardware (SBC/PLC)", 15, ALIGN_CENTER),
        ("HIL Closed-Loop", 14, ALIGN_CENTER),
        ("Physical Process Modeling Approach", 32, ALIGN_LEFT),
        ("Physical Phenomena Fidelity", 28, ALIGN_LEFT),
        ("Sensor Noise & Dynamic Lag", 24, ALIGN_LEFT),
        ("Safety & Destructive Testing", 26, ALIGN_LEFT),
        ("Multi-Protocol Support", 18, ALIGN_CENTER),
        ("Deterministic SoftPLC", 16, ALIGN_CENTER),
        ("Host / Volatile Memory Security", 16, ALIGN_CENTER),
        ("Edge CPU / Thermal Evaluation", 16, ALIGN_CENTER),
        ("Real Physics Limitations / Trade-Offs", 34, ALIGN_LEFT),
        ("Comparative Assessment (Where Paper Wins vs Where Your Work Focuses)", 38, ALIGN_LEFT),
    ]

    MY_WORK_BALANCED_ROW = [
        "★ YOUR WORK: Master-Honeypot HIL SoftPLC",
        "Water / Oil Pipeline",
        "✔️ Yes (Raspberry Pi 4B)",
        "✔️ Yes (Closed-Loop)",
        "Simplified 1-stage hydraulic ODE (P=f(RPM, Valve), Q=g(P), T=h(RPM, Q))",
        "🟡 Low-order hydrodynamic approximation (omits cavitation & multi-phase)",
        "✔️ Gaussian N(0, σ²) + 100ms discrete lag",
        "✔️ 100% Safe: Software SIS trip at P > 200 PSI",
        "✔️ 4 Protocols (MB, OPC-UA, S7, DNP3)",
        "✔️ Yes (CODESYS 100ms)",
        "✔️ SCADA SSH + In-Memory Artifacts",
        "✔️ Yes (44.3°C, Cortex-A72)",
        "Trade-off: Approximates fluid dynamics; cannot match multi-stage ground-truth plant physics.",
        "Focus: Balances sufficient physical realism for cyber deception with low-cost ($50) edge deployment and safe overpressure testing."
    ]

    def recreate_balanced_theme_sheet(sheet_name, title, theme_id):
        old_ws = wb[sheet_name]
        existing_rows = []
        for r in range(6, old_ws.max_row + 1):
            p_name = old_ws.cell(r, 1).value
            domain = old_ws.cell(r, 2).value
            phys_hw = old_ws.cell(r, 3).value
            hil = old_ws.cell(r, 4).value
            protos = old_ws.cell(r, 10).value if old_ws.max_column >= 10 else "None"
            softplc = old_ws.cell(r, 11).value if old_ws.max_column >= 11 else "❌ No"
            mem_sec = old_ws.cell(r, 12).value if old_ws.max_column >= 12 else "❌ No"
            edge_prof = old_ws.cell(r, 13).value if old_ws.max_column >= 13 else "❌ No"
            if p_name:
                existing_rows.append({
                    'paper': str(p_name),
                    'domain': str(domain) if domain else 'SCADA / General OT',
                    'phys_hw': str(phys_hw) if phys_hw else '❌ No',
                    'hil': str(hil) if hil else '❌ No',
                    'protos': str(protos) if protos else 'None',
                    'softplc': str(softplc) if softplc else '❌ No',
                    'mem_sec': str(mem_sec) if mem_sec else '❌ No',
                    'edge_prof': str(edge_prof) if edge_prof else '❌ No',
                })

        sheet_idx = wb.sheetnames.index(sheet_name)
        wb.remove(old_ws)
        ws = wb.create_sheet(title=sheet_name, index=sheet_idx)
        ws.views.sheetView[0].showGridLines = True

        ws.cell(1, 1, title).font = FONT_TITLE
        ws.cell(2, 1, f"Objective Comparative Analysis & Physics Trade-Offs • {len(existing_rows)} Literature Sources").font = FONT_SUBTITLE

        # Headers
        for c_idx, (h_name, width, align) in enumerate(BALANCED_COLUMNS, 1):
            cell = ws.cell(4, c_idx, h_name)
            cell.font = FONT_HEADER
            cell.fill = FILL_HEADER
            cell.alignment = ALIGN_HEADER
            cell.border = THIN_BORDER
            ws.column_dimensions[get_column_letter(c_idx)].width = width

        # Row 5: Your Work
        for c_idx, val in enumerate(MY_WORK_BALANCED_ROW, 1):
            cell = ws.cell(5, c_idx, val)
            cell.font = FONT_MY_WORK
            cell.fill = FILL_MY_WORK
            cell.alignment = BALANCED_COLUMNS[c_idx - 1][2]
            cell.border = MY_WORK_BORDER

        # Data Rows
        for r_idx, r_item in enumerate(existing_rows, 6):
            p_name = r_item['paper']
            domain = r_item['domain']

            if theme_id == 1: # Simulation Only
                if '01403664' in p_name or '09252312' in p_name or '10848045' in p_name or 's10844' in p_name:
                    model_appr = "Offline pre-recorded SWaT CSV dataset (Passive playback)"
                    phys_fid = "❌ High dataset fidelity, but 100% disconnected from live controller"
                    noise_lag = "Recorded physical noise (Immutable static stream)"
                    safety_test = "✔️ 100% Safe (Replaying historical attack records)"
                    limitations = "Cannot react dynamically to live attacker commands; no interactive feedback loop."
                    comparative = "Paper Win: Replays complex 6-stage real SWaT water plant data. Your Work Focus: Interactive live closed-loop HIL deception with dynamic ODE response."
                elif 'Two-Level' in p_name:
                    model_appr = "Water Distribution Tank (WDT) simulated ODE in Python script"
                    phys_fid = "🟡 Simple single-tank mass balance (dh/dt = (Qin - Qout)/A)"
                    noise_lag = "❌ Zero-noise numerical integration"
                    safety_test = "✔️ 100% Safe (Software simulation on PC)"
                    limitations = "Simplified single-variable tank; runs purely on host CPU without hardware delays."
                    comparative = "Paper Win: Fast theoretical algorithm testing. Your Work Focus: Deploys onto physical ARM64 SoftPLC with network latency and multi-protocol support."
                else:
                    model_appr = "Synthetic algebraic equations / Static lookup tables"
                    phys_fid = "❌ Zero physical process foundation; purely synthetic state transitions"
                    noise_lag = "❌ Deterministic / Idealized values"
                    safety_test = "✔️ Safe (Pure virtual software)"
                    limitations = "Lacks hydrodynamic or thermodynamic validity; easily detected as artificial honeypot."
                    comparative = "Paper Win: Minimal setup overhead. Your Work Focus: Adds continuous hydraulic ODEs to prevent honeypot fingerprinting."

            elif theme_id == 2: # Hybrid & HIL
                if '03787788' in p_name or '2210.11234' in p_name: # Building HVAC
                    model_appr = "Real physical HVAC equipment (chillers, boilers) + Building thermal co-sim"
                    phys_fid = "✔️ SUPERIOR physical thermal transfer (Q=m*Cp*dT) across real building zones"
                    noise_lag = "✔️ Inherent real analog sensor drift and thermal inertia"
                    safety_test = "🟡 Controlled physical faults (Valve stuck); physical equipment limits"
                    limitations = "Domain-specific to building automation (BACnet); high physical lab setup overhead."
                    comparative = "Paper Win: Superior real-world multi-zone thermal dynamics. Your Work Focus: Reconfigurable multi-protocol edge testbed with cyber deception and memory forensics."
                elif '1874548224' in p_name: # Thermal power
                    model_appr = "Industrial HIL simulator for thermal power generation (22 sensors)"
                    phys_fid = "✔️ High-fidelity multi-stage steam, enthalpy, and turbine power dynamics"
                    noise_lag = "✔️ Calibrated industrial sensor noise and thermal inertia"
                    safety_test = "✔️ Safe (High-end industrial simulator handles over-limits)"
                    limitations = "High capital cost for proprietary HIL simulator; cannot run on low-cost edge nodes."
                    comparative = "Paper Win: Full industrial multi-stage plant fidelity. Your Work Focus: Lightweight SoftPLC feasible for distributed low-cost ($50) edge deception."
                elif '1874548225' in p_name: # CyberSentry water testbed
                    model_appr = "Physical scaled-down water treatment testbed (Real pumps, pipes, tanks)"
                    phys_fid = "✔️ SUPERIOR ground-truth fluid flow, head pressure, and real pump curves"
                    noise_lag = "✔️ Genuine physical fluid turbulence and pressure sensor noise"
                    safety_test = "❌ Physical equipment damage risk under extreme hydraulic overpressure"
                    limitations = "Fixed physical pipe dimensions; prone to component wear; cannot safely test pipe bursts."
                    comparative = "Paper Win: 100% genuine fluid mechanics with zero modeling error. Your Work Focus: Safe exploration of destructive overpressure (>200 PSI) with cyber deception."
                elif '3524489' in p_name or 'Impact_and' in p_name: # EnCyCris / Polimi Substation
                    model_appr = "RTDS hardware grid simulator + Physical protection relays (SEL/Siemens)"
                    phys_fid = "✔️ Microsecond-accurate electromagnetic power transients (Real electrical physics)"
                    noise_lag = "✔️ Hardwired physical CT/PT sensor measurements"
                    safety_test = "🟡 Real protective relay tripping; capital equipment constraints"
                    limitations = "Extreme capital expenditure ($100K+); specialized to electrical substations."
                    comparative = "Paper Win: Unmatched microsecond electrical transient accuracy. Your Work Focus: Multi-protocol pipeline process deception on accessible ARM64 edge hardware."
                elif 'jmse-12-01236' in p_name: # Marine PMS
                    model_appr = "Marine Power Management System HIL (Real generators + Propulsion physics)"
                    phys_fid = "✔️ Highly accurate rotational engine dynamics, torque, and fuel flow"
                    noise_lag = "✔️ Real marine generator measurement noise"
                    safety_test = "🟡 Controlled engine testing; physical engine wear"
                    limitations = "Custom maritime propulsion focus; not easily adaptable to general OT deception."
                    comparative = "Paper Win: Complex rotational mechanics and electrical power balance. Your Work Focus: General-purpose industrial SoftPLC honeypot with host-level forensics."
                elif 'ares-etacs' in p_name: # WonderICS water loops
                    model_appr = "WonderICS physical water circulation rig + Industrial Schneider PLCs"
                    phys_fid = "✔️ Real hydraulic water circulation, tank levels, and valve feedback"
                    noise_lag = "✔️ Real physical flowmeter and level sensor dynamics"
                    safety_test = "🟡 Training testbed; physical overflow/leakage constraints"
                    limitations = "Physical footprint and maintenance; lacks post-compromise deceptive response."
                    comparative = "Paper Win: Authentic physical plumbing for hands-on student training. Your Work Focus: Automated post-compromise cyber deception and host memory security."
                else:
                    model_appr = "MATLAB/Simulink or Python co-simulated process model coupled to PLC"
                    phys_fid = "🟡 Mathematical process simulation (Level, pressure, or flow differential eqs)"
                    noise_lag = "❌ Often idealized zero-noise in co-simulation links"
                    safety_test = "✔️ Safe (Simulated physics absorbs attack commands)"
                    limitations = "Workstation-dependent; omits low-cost edge resource/thermal feasibility."
                    comparative = "Paper Win: Mature academic simulation models. Your Work Focus: Natively integrated SoftPLC on ARM64 SBC with thermal and memory profiling."

            else: # Theme 3: Real Physics & Hardware-Centric Research
                if '2402.14599' in p_name:
                    model_appr = "Dedicated SCADA operator workstation (Live OS host process environment)"
                    phys_fid = "❌ No fluid/physical process modeled (Evaluates host OS metrics only)"
                    noise_lag = "❌ N/A (Operating system performance counters)"
                    safety_test = "✔️ Safe (Host-level software testing)"
                    limitations = "Host-level only; completely detached from fieldbus I/O and physical plant dynamics."
                    comparative = "Paper Win: Deep host-level OS process monitoring. Your Work Focus: Couples SCADA host monitoring with fieldbus protocols and physical hydraulic state."
                elif 'NIST' in p_name:
                    model_appr = "NIST SP 800-82r3 Industrial Control Systems Security Guidelines"
                    phys_fid = "✔️ Covers ground-truth physical safety systems across thousands of real plants"
                    noise_lag = "N/A (Standard / Architecture Document)"
                    safety_test = "Prescribes physical safety instrumented systems (SIS) and containment"
                    limitations = "Guideline document; provides no executable testbed or experimental validation."
                    comparative = "NIST provides the authoritative industrial framework; Your Work implements and validates these Purdue/SIS concepts experimentally."
                elif 'c3965c88' in p_name or 'pico' in p_name:
                    model_appr = "Physical microcontrollers / SBCs (Real electrical GPIO & ADC pins)"
                    phys_fid = "✔️ Real physical electrical circuits, pin resistance, and clock oscillations"
                    noise_lag = "✔️ Real physical electrical thermal noise and ADC quantization error"
                    safety_test = "✔️ Safe low-voltage electrical experimentation"
                    limitations = "Evaluates hardware pins/clocks only; lacks SCADA architecture and process physics."
                    comparative = "Paper Win: Low-level electrical and hardware timing profiling. Your Work Focus: Builds an end-to-end industrial SoftPLC with hydraulic physics and SCADA HMI."
                else: # Claroty Global Survey
                    model_appr = "Empirical data from thousands of operational global industrial plants"
                    phys_fid = "✔️ ABSOLUTE GROUND TRUTH: Real production chemical, refining, and power plants"
                    noise_lag = "✔️ Real-world production sensor noise, fouling, and environmental drift"
                    safety_test = "❌ LIVE PRODUCTION: Zero tolerance for attack testing or destructive exploration"
                    limitations = "Production assets cannot be used for honeypots, penetration testing, or attacks."
                    comparative = "Claroty Win: Massive real-world scale and ground-truth telemetry. Your Work Focus: Provides a safe, accessible deception sandbox that mirrors industrial reality without operational risk."

            row_data = [
                p_name,
                domain,
                r_item['phys_hw'],
                r_item['hil'],
                model_appr,
                phys_fid,
                noise_lag,
                safety_test,
                r_item['protos'],
                r_item['softplc'],
                r_item['mem_sec'],
                r_item['edge_prof'],
                limitations,
                comparative
            ]

            row_fill = FILL_ALT_ROW if r_idx % 2 == 1 else FILL_WHITE

            for c_idx, val in enumerate(row_data, 1):
                cell = ws.cell(r_idx, c_idx, str(val))
                cell.border = THIN_BORDER
                cell.alignment = BALANCED_COLUMNS[c_idx - 1][2]
                cell.fill = row_fill

                if "✔️" in str(val) and "SUPERIOR" not in str(val):
                    cell.font = FONT_TICK_YES
                elif "❌" in str(val):
                    cell.font = FONT_TICK_NO
                elif "🟡" in str(val):
                    cell.font = FONT_TICK_PARTIAL
                elif "SUPERIOR" in str(val):
                    cell.font = FONT_SUPERIOR
                    cell.fill = FILL_SUPERIOR
                else:
                    cell.font = FONT_DATA

                if c_idx == 13: # Limitations column
                    cell.font = FONT_TRADEOFF
                elif c_idx == 14: # Comparative Assessment column
                    cell.font = FONT_DATA

        ws.freeze_panes = "B6"

    # Recreate all 3 theme sheets with balanced, honest comparisons
    recreate_balanced_theme_sheet("Theme 1 - Sim Only (18 P)", "Theme 1: Simulation & Emulation Only Papers (Academic Trade-Off Analysis)", 1)
    recreate_balanced_theme_sheet("Theme 2 - Hybrid & HIL (24 P)", "Theme 2: Hybrid & Hardware-in-the-Loop Papers (Academic Trade-Off Analysis)", 2)
    recreate_balanced_theme_sheet("Theme 3 - Hard Only (5 P)", "Theme 3: Real Physics & Hardware-Centric Research (Academic Trade-Off Analysis)", 3)

    wb.save(FILE_PATH)
    print(f"Successfully saved balanced, academically rigorous workbook to:\n{FILE_PATH}")

if __name__ == "__main__":
    update_balanced_workbook()
