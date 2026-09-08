#!/usr/bin/env python3
"""
Apply user refinements to Comparative-OT-Security-Landscape.xlsx:
1. Revise Columns 15 and 16 across all theme sheets to eliminate ambiguity:
   - Col 15: "Paper Primary Focus & Strength" (What the published paper actually proposed & tested)
   - Col 16: "Our Differentiator (Why We Differ)" (Why our thesis differs / takes an alternative approach)
2. In the "50+ Node Scale" column, update Proposed System from "❌ (1 Node)" to "❌ (2 Nodes / 16 Containers)"
   to accurately reflect 2 physical machines (Raspberry Pi 4B + Laptop) orchestrating 16 Docker containers.
3. In the "Fieldbus Protocols" column, replace generic "1 Protocol" with specific protocol names (e.g. "Modbus TCP only", "BACnet only").
4. Update Sheet 1 (Executive Summary & Scorecard) to reflect these exact refinements.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FILE_PATH = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/Comparative-OT-Security-Landscape.xlsx"

def apply_refinements():
    wb = openpyxl.load_workbook(FILE_PATH)

    FONT_HEADER = Font(name="Calibri", size=9.5, bold=True, color="FFFFFF")
    FONT_PROPOSED = Font(name="Calibri", size=9.5, bold=True, color="000000")
    FONT_DATA = Font(name="Calibri", size=9.5, color="000000")
    FONT_TICK = Font(name="Calibri", size=10, bold=True, color="000000")

    FILL_BLACK_HEADER = PatternFill(start_color="1A1A1A", end_color="1A1A1A", fill_type="solid")
    FILL_PROPOSED_ROW = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid")
    FILL_ALT_ROW = PatternFill(start_color="F7F7F7", end_color="F7F7F7", fill_type="solid")
    FILL_WHITE = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    BORDER_THIN = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    BORDER_PROPOSED = Border(
        left=Side(style='medium', color='333333'),
        right=Side(style='medium', color='333333'),
        top=Side(style='medium', color='333333'),
        bottom=Side(style='medium', color='333333')
    )

    ALIGN_CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
    ALIGN_HEADER = Alignment(horizontal='center', vertical='center', wrap_text=True)

    REVISED_HEADERS = [
        ("Paper", 26, ALIGN_LEFT),
        ("Domain", 18, ALIGN_CENTER),
        ("Hardware Node", 12, ALIGN_CENTER),
        ("HIL Closed-Loop", 12, ALIGN_CENTER),
        ("Industrial PLC", 13, ALIGN_CENTER),
        ("Multi-Stage Plant", 14, ALIGN_CENTER),
        ("Real Fluid / Pipes", 14, ALIGN_CENTER),
        ("Mechanical PRV", 13, ALIGN_CENTER),
        ("50+ Node Scale", 14, ALIGN_CENTER),
        ("Microsecond RT", 13, ALIGN_CENTER),
        ("Fieldbus Protocols", 18, ALIGN_CENTER),
        ("Deception Honeynet", 15, ALIGN_CENTER),
        ("Host / Memory Forensics", 16, ALIGN_CENTER),
        ("Edge CPU / Thermals", 15, ALIGN_CENTER),
        ("Paper Primary Focus & Strength", 32, ALIGN_LEFT),
        ("Our Differentiator (Why We Differ)", 34, ALIGN_LEFT),
    ]

    PROPOSED_UNIFIED_ROW = [
        "Proposed System (This Work)",
        "Water / Pipeline",
        "✔️",
        "✔️",
        "❌ (Raspberry Pi)",
        "❌ (Single-Stage)",
        "❌ (Simulated ODE)",
        "❌ (Software only)",
        "❌ (2 Nodes / 16 Cont.)",
        "❌ (100ms Linux)",
        "4 Protocols",
        "✔️",
        "✔️",
        "✔️",
        "— [Benchmark Baseline] —",
        "Accessible edge HIL SoftPLC with host forensics & safe overpressure testing"
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Update Sheet 1: Executive Summary & Scorecard
    # ─────────────────────────────────────────────────────────────────────────
    ws_exec = wb['Executive Summary & Scorecard']
    for r in range(5, ws_exec.max_row + 1):
        metric = ws_exec.cell(r, 2).value
        if metric and 'Scalability' in str(metric):
            ws_exec.cell(r, 6).value = "❌ (2 Nodes / 16 Containers)"
        if metric and 'Fieldbus Protocol' in str(metric):
            ws_exec.cell(r, 3).value = "Modbus TCP only (mostly)"
            ws_exec.cell(r, 4).value = "1–2 protocols (Modbus/BACnet)"

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Update Theme 1: Simulation Only
    # ─────────────────────────────────────────────────────────────────────────
    ws1 = wb["Theme 1 - Sim Only (18 P)"]
    # Headers
    for c_idx, (h_name, width, align) in enumerate(REVISED_HEADERS, 1):
        cell = ws1.cell(4, c_idx, h_name)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN
        ws1.column_dimensions[get_column_letter(c_idx)].width = width

    # Row 5 Proposed System
    for c_idx, val in enumerate(PROPOSED_UNIFIED_ROW, 1):
        cell = ws1.cell(5, c_idx, val)
        cell.font = FONT_PROPOSED
        cell.fill = FILL_PROPOSED_ROW
        cell.alignment = REVISED_HEADERS[c_idx - 1][2]
        cell.border = BORDER_PROPOSED

    # Data Rows
    for r in range(6, ws1.max_row + 1):
        p_str = str(ws1.cell(r, 1).value)
        # Protocols: be specific!
        if '01403664' in p_str or '10848045' in p_str or 'tesi' in p_str or 's10844' in p_str:
            ws1.cell(r, 11).value = "Modbus TCP only"
        elif '09252312' in p_str:
            ws1.cell(r, 11).value = "DNP3 only"
        else:
            ws1.cell(r, 11).value = "Modbus TCP only"

        # Col 15 & 16
        if '01403664' in p_str or '09252312' in p_str or '10848045' in p_str or 's10844' in p_str:
            ws1.cell(r, 15).value = "Offline 6-stage physical SWaT dataset playback"
            ws1.cell(r, 16).value = "Provides live closed-loop reactive physics to attacker writes"
        elif 'Two-Level' in p_str:
            ws1.cell(r, 15).value = "Multi-tank simulated network scaling"
            ws1.cell(r, 16).value = "Deploys onto physical ARM64 SoftPLC with network jitter"
        elif 'electronics-11-01659' in p_str:
            ws1.cell(r, 15).value = "Large multi-bus power grid flow equations"
            ws1.cell(r, 16).value = "Integrates 4 industrial fieldbus protocols with SoC thermals"
        else:
            ws1.cell(r, 15).value = "Massive virtual container scalability (100+ nodes)"
            ws1.cell(r, 16).value = "Employs continuous differential equations to defeat fingerprinting"

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Update Theme 2: Hybrid & HIL
    # ─────────────────────────────────────────────────────────────────────────
    ws2 = wb["Theme 2 - Hybrid & HIL (24 P)"]
    for c_idx, (h_name, width, align) in enumerate(REVISED_HEADERS, 1):
        cell = ws2.cell(4, c_idx, h_name)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN
        ws2.column_dimensions[get_column_letter(c_idx)].width = width

    for c_idx, val in enumerate(PROPOSED_UNIFIED_ROW, 1):
        cell = ws2.cell(5, c_idx, val)
        cell.font = FONT_PROPOSED
        cell.fill = FILL_PROPOSED_ROW
        cell.alignment = REVISED_HEADERS[c_idx - 1][2]
        cell.border = BORDER_PROPOSED

    for r in range(6, ws2.max_row + 1):
        p_str = str(ws2.cell(r, 1).value)
        # Protocols
        if '03787788' in p_str or '2210' in p_str:
            ws2.cell(r, 11).value = "BACnet/IP only"
        elif '3524489' in p_str or 'Impact' in p_str:
            ws2.cell(r, 11).value = "IEC 61850 only"
        elif '01674048' in p_str:
            ws2.cell(r, 11).value = "Modbus / S7comm"
        else:
            ws2.cell(r, 11).value = "Modbus TCP only"

        # Col 15 & 16
        if '03787788' in p_str or '2210' in p_str:
            ws2.cell(r, 15).value = "Building HVAC multi-zone thermal loops"
            ws2.cell(r, 16).value = "Reconfigurable multi-protocol edge testbed with SCADA SSH"
        elif '1874548224' in p_str:
            ws2.cell(r, 15).value = "Industrial thermal power plant turbine simulation"
            ws2.cell(r, 16).value = "Accessible low-cost ($50) edge hardware feasibility"
        elif '3524489' in p_str or 'Impact' in p_str:
            ws2.cell(r, 15).value = "Microsecond RTDS power grid substation simulation"
            ws2.cell(r, 16).value = "Low-cost pipeline deception with host memory forensics"
        elif 'ares-etacs' in p_str:
            ws2.cell(r, 15).value = "Physical Schneider PLC hardware training rig"
            ws2.cell(r, 16).value = "Automated post-compromise cyber deception & memory dumps"
        elif 'jmse' in p_str:
            ws2.cell(r, 15).value = "Marine LNG vessel switchboard fault testing"
            ws2.cell(r, 16).value = "Safe destructive overpressure testing without hardware damage"
        else:
            ws2.cell(r, 15).value = "Mature academic Simulink co-simulation blocksets"
            ws2.cell(r, 16).value = "Deterministic CODESYS SoftPLC on ARM64 with thermals"

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Update Theme 3: Real PLCs & Physical Testbeds
    # ─────────────────────────────────────────────────────────────────────────
    ws3 = wb["Theme 3 - Real PLCs & Rigs"]
    for c_idx, (h_name, width, align) in enumerate(REVISED_HEADERS, 1):
        cell = ws3.cell(4, c_idx, h_name)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN
        ws3.column_dimensions[get_column_letter(c_idx)].width = width

    for c_idx, val in enumerate(PROPOSED_UNIFIED_ROW, 1):
        cell = ws3.cell(5, c_idx, val)
        cell.font = FONT_PROPOSED
        cell.fill = FILL_PROPOSED_ROW
        cell.alignment = REVISED_HEADERS[c_idx - 1][2]
        cell.border = BORDER_PROPOSED

    THEME3_REFINED = [
        [
            "ares-etacs.pdf (WonderICS / G-ICS)",
            "Water & Chemical Loop",
            "✔️",
            "✔️",
            "✔️ (Schneider M580)",
            "✔️ (Water & Dosing)",
            "✔️ (Pumps & Tanks)",
            "✔️ (Physical Breakers)",
            "❌ (Rig Scale)",
            "❌ (Scan Cycle)",
            "Modbus TCP, OPC UA",
            "❌ (Training Lab)",
            "❌",
            "❌",
            "Hands-on training rig with physical Schneider M580 & water loops",
            "Replaces rigid $50K water plumbing with safe software ODEs"
        ],
        [
            "1-s2.0-S1874548224000167-main.pdf",
            "Thermal Power Generation",
            "✔️",
            "✔️",
            "✔️ (Schneider M580)",
            "✔️ (Multi-Stage Steam)",
            "✔️ (22 Sensor Stream)",
            "✔️ (Industrial PID Trip)",
            "❌ (Single Plant)",
            "❌ (PID Loop)",
            "Modbus TCP/IP",
            "❌ (Threat Analysis)",
            "❌",
            "❌",
            "Physical M580 PID closed-loop steam turbine stability",
            "Evaluates low-cost $50 SBC feasibility instead of industrial PLC racks"
        ],
        [
            "3524489.3527299.pdf (EnCyCris)",
            "Digital Power Substation",
            "✔️",
            "✔️",
            "✔️ (Siemens SIPROTEC)",
            "✔️ (Process & Station)",
            "❌ (Electrical Grid)",
            "✔️ (Hardware Trip <4ms)",
            "❌ (Bay Scale)",
            "✔️ (Microsecond RTDS)",
            "IEC 61850 GOOSE/SV",
            "❌ (Substation Defense)",
            "❌",
            "❌",
            "Microsecond Siemens protection relays & Omicron injection",
            "Extends beyond grid relays to multi-protocol SCADA host forensics"
        ],
        [
            "2210.11234v3.pdf (TAMU BAS Lab)",
            "Building Automation (HVAC)",
            "✔️",
            "✔️",
            "✔️ (BACnet DDC)",
            "✔️ (Chillers & Boilers)",
            "✔️ (Physical Chillers)",
            "✔️ (Physical PRVs)",
            "❌ (Campus Lab)",
            "❌ (Thermal Lag)",
            "BACnet/IP only",
            "❌ (Fault Detection)",
            "❌",
            "❌",
            "Physical industrial water chillers & boiler fault detection",
            "Couples fieldbus commands with interactive SCADA shell monitoring"
        ],
        [
            "jmse-12-01236.pdf (Marine PMS)",
            "Marine LNG Vessel Power",
            "✔️",
            "✔️",
            "✔️ (Allen-Bradley PLC)",
            "✔️ (Generator Balance)",
            "❌ (Marine Switchboard)",
            "✔️ (Generator Breakers)",
            "❌ (Vessel Board)",
            "✔️ (100 µs Cycle)",
            "Modbus TCP, OPC",
            "❌ (Safety/Faults)",
            "❌",
            "❌",
            "Full-scale marine switchboard & blackout recovery testing",
            "Enables safe destructive overpressure tests without equipment damage"
        ]
    ]

    for r_idx, r_data in enumerate(THEME3_REFINED, 6):
        is_alt = (r_idx % 2 == 1)
        row_fill = FILL_ALT_ROW if is_alt else FILL_WHITE
        for c_idx, val in enumerate(r_data, 1):
            cell = ws3.cell(r_idx, c_idx, str(val))
            cell.border = BORDER_THIN
            cell.alignment = REVISED_HEADERS[c_idx - 1][2]
            cell.fill = row_fill
            cell.font = FONT_TICK if val in ["✔️", "❌"] else FONT_DATA

    wb.save(FILE_PATH)
    print("Successfully applied user refinements across all sheets!")

if __name__ == "__main__":
    apply_refinements()
