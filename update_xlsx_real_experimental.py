#!/usr/bin/env python3
"""
Update Comparative-OT-Security-Landscape.xlsx so that Theme 3 explicitly features
the 5 physical experimental papers that bought actual industrial PLCs (Schneider, Siemens,
Allen-Bradley, BACnet) and tested real physical process rigs (water loops, power plant,
substation relays, chillers, marine switchboards).
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FILE_PATH = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/Comparative-OT-Security-Landscape.xlsx"

def update_workbook():
    wb = openpyxl.load_workbook(FILE_PATH)

    # ── Styling Definitions ───────────────────────────────────────────────────
    FONT_TITLE = Font(name="Calibri", size=14, bold=True, color="000000")
    FONT_SUBTITLE = Font(name="Calibri", size=10, italic=True, color="444444")
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

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SHEET 1: Executive Summary & Scorecard
    # ─────────────────────────────────────────────────────────────────────────
    ws_exec = wb['Executive Summary & Scorecard']
    for rng in list(ws_exec.merged_cells.ranges):
        ws_exec.unmerge_cells(str(rng))

    for r in range(1, ws_exec.max_row + 1):
        for c in range(1, ws_exec.max_column + 1):
            ws_exec.cell(r, c).value = None

    ws_exec.views.sheetView[0].showGridLines = True
    ws_exec.cell(2, 2, "Literature Comparison Matrix & Feature Scorecard").font = FONT_TITLE
    ws_exec.cell(3, 2, "Authentic evaluation: Sim Only vs Hybrid vs Real Industrial PLCs/Rigs vs Proposed System").font = FONT_SUBTITLE

    scorecard_headers = [
        "Evaluation Dimension",
        "Simulation Only (18)",
        "Hybrid Co-Sim (24)",
        "Real PLCs & Physical Rigs (5)",
        "Proposed System (This Work)"
    ]

    scorecard_data = [
        ["Physical Hardware Node", "❌", "✔️", "✔️ (Schneider, Siemens, AB)", "✔️ (Raspberry Pi 4B)"],
        ["Hardware-in-the-Loop (HIL)", "❌", "✔️", "✔️ (Real process HIL)", "✔️ (Real-time closed-loop)"],
        ["Certified Industrial PLC Hardware", "❌", "Partial (OpenPLC/VM)", "✔️ (Schneider M580, Siemens, AB)", "❌ (Raspberry Pi SoftPLC)"],
        ["Real Physical Process / Fluid Rigs", "❌ (Synthetic/CSV)", "Partial (Simulink)", "✔️ (Water loops, chillers, steam)", "❌ (Hydraulic ODE approximation)"],
        ["Commercial SCADA Engineering Suite", "❌ (Generic scripts)", "Partial", "✔️ (Control Expert, CITECT, SCC)", "✔️ (CODESYS IDE + WebVisu)"],
        ["Hardware Mechanical Safety (PRV)", "❌", "Partial", "✔️ (Physical breakers & relief valves)", "❌ (Software logic check only)"],
        ["Fieldbus Protocol Diversity", "1 (Modbus/BACnet)", "1–2 protocols", "Modbus, IEC 61850, BACnet, OPC", "✔️ 4 Protocols (MB, OPC-UA, S7, DNP3)"],
        ["Cyber Deception Honeynet", "Partial (Fake)", "Partial", "❌ Impractical on production rigs", "✔️ Dynamic feedback honeynet"],
        ["Destructive Attack Safety", "✔️ Safe", "✔️ Safe", "❌ HIGH HAZARD (Physical damage)", "✔️ 100% Safe (Software ODE)"],
        ["SCADA Host & Volatile Memory Security", "❌", "❌", "❌ (Focus on fieldbus/process)", "✔️ (SSH + In-memory artifacts)"],
        ["Edge Embedded Profiling (Thermals)", "❌", "❌", "❌ (Unmeasured in PLC cabinets)", "✔️ (44.3°C, CPU, RAM)"],
        ["Scalability (Node Count)", "✔️ High (100+ virtual)", "Moderate", "❌ Very Rigid (Physical plumbing)", "❌ 1 Physical edge node"],
        ["Execution Speed (Faster than RT)", "✔️ Accelerated", "❌ Real-time bound", "❌ Real-time bound", "❌ (1x Real-time wall-clock)"],
        ["Capital Equipment Cost", "Near-zero", "$5K–$50K", "$50K–$500K+ (Commercial rigs)", "~$50 (Raspberry Pi 4B)"]
    ]

    for c_idx, h_text in enumerate(scorecard_headers, 2):
        cell = ws_exec.cell(5, c_idx, h_text)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN

    for r_idx, r_data in enumerate(scorecard_data, 6):
        is_alt = (r_idx % 2 == 1)
        row_fill = FILL_ALT_ROW if is_alt else FILL_WHITE
        for c_idx, val in enumerate(r_data, 2):
            cell = ws_exec.cell(r_idx, c_idx, val)
            cell.border = BORDER_THIN
            if c_idx == 2:
                cell.font = Font(name="Calibri", size=9.5, bold=True, color="000000")
                cell.alignment = ALIGN_LEFT
                cell.fill = row_fill
            elif c_idx == 6:
                cell.font = FONT_PROPOSED
                cell.alignment = ALIGN_LEFT
                cell.fill = FILL_PROPOSED_ROW
                cell.border = BORDER_PROPOSED
            else:
                cell.font = FONT_DATA
                cell.alignment = ALIGN_CENTER if val in ["✔️", "❌"] else ALIGN_LEFT
                cell.fill = row_fill

    ws_exec.column_dimensions['B'].width = 38
    ws_exec.column_dimensions['C'].width = 24
    ws_exec.column_dimensions['D'].width = 26
    ws_exec.column_dimensions['E'].width = 34
    ws_exec.column_dimensions['F'].width = 34

    # ─────────────────────────────────────────────────────────────────────────
    # 2. SHEET 4: Theme 3 - Real PLCs & Physical Testbeds (5 Papers)
    # ─────────────────────────────────────────────────────────────────────────
    sheet4_name = "Theme 3 - Hard Only (5 P)"
    if sheet4_name in wb.sheetnames:
        old_ws4 = wb[sheet4_name]
        s4_idx = wb.sheetnames.index(sheet4_name)
        wb.remove(old_ws4)
    else:
        s4_idx = len(wb.sheetnames)

    ws4 = wb.create_sheet(title="Theme 3 - Real PLCs & Rigs (5 P)", index=s4_idx)
    ws4.views.sheetView[0].showGridLines = True

    THEME3_HEADERS = [
        ("Paper / System Name", 26, ALIGN_LEFT),
        ("Target Domain", 18, ALIGN_CENTER),
        ("Physical PLC Hardware Bought", 24, ALIGN_LEFT),
        ("Physical Process Rig / Piping", 26, ALIGN_LEFT),
        ("SCADA Engineering Software", 22, ALIGN_LEFT),
        ("Fieldbus Protocols", 18, ALIGN_CENTER),
        ("Mechanical Safety Interlocks", 20, ALIGN_LEFT),
        ("Cyber Deception Support", 15, ALIGN_CENTER),
        ("Host / Memory Forensics", 15, ALIGN_CENTER),
        ("Edge CPU / Thermals Evaluated", 16, ALIGN_CENTER),
        ("Paper Strength (vs Proposed)", 32, ALIGN_LEFT),
        ("Proposed System Focus", 32, ALIGN_LEFT),
    ]

    PROPOSED_THEME3_ROW = [
        "Proposed System (This Work)",
        "Water / Pipeline",
        "❌ (Raspberry Pi 4B SoftPLC)",
        "❌ (Hydraulic ODE, no pipes)",
        "✔️ CODESYS IDE + WebVisu",
        "4 Protocols (MB, OPC-UA, S7, DNP3)",
        "❌ (Software logic check only)",
        "✔️ Dynamic Feedback Honeynet",
        "✔️ SCADA SSH + Memory Artifacts",
        "✔️ Continuous (44.3°C, CPU, RAM)",
        "— [BENCHMARK BASELINE] —",
        "Low-cost edge deception honeynet with safe overpressure exploration"
    ]

    REAL_PLC_PAPERS_DATA = [
        [
            "ares-etacs.pdf (WonderICS / G-ICS)",
            "Water Circulation & Treatment",
            "✔️ Schneider Modicon M580 & M340",
            "✔️ Real water loop (pumps, tanks, dosing)",
            "Schneider Control Expert & PcVue",
            "Modbus TCP / RTU, OPC UA",
            "✔️ Physical circuit breakers & relays",
            "❌ (Training lab only)",
            "❌",
            "❌",
            "Real Schneider PLCs & physical water plumbing",
            "Post-compromise cyber deception & memory forensics"
        ],
        [
            "1-s2.0-S1874548224000167-main.pdf",
            "Thermal Power Generation",
            "✔️ Schneider Modicon M580 PLC",
            "✔️ Real thermal steam plant (22 sensors)",
            "CITECT SCADA (OWS, EWS, Server)",
            "Modbus TCP/IP",
            "✔️ Industrial PID loop trip protection",
            "❌ (Threat modeling only)",
            "❌",
            "❌",
            "Physical M580 PID closed-loop steam plant",
            "Multi-protocol deception on accessible edge SBC"
        ],
        [
            "3524489.3527299.pdf (EnCyCris)",
            "Digital Power Substation",
            "✔️ Siemens SICAM A8000 & SIPROTEC 5",
            "✔️ Substation bus with Omicron CMC injection",
            "Siemens SICAM SCC on SIMATIC IPC",
            "IEC 61850 GOOSE/SV, 104, MMS",
            "✔️ Hardware protection trip (<4 ms)",
            "❌ (Substation defense only)",
            "❌",
            "❌",
            "Microsecond Siemens protection relays & Omicron",
            "Low-cost ($50) edge platform with SCADA SSH capture"
        ],
        [
            "2210.11234v3.pdf (TAMU BAS Lab)",
            "Building Automation (HVAC)",
            "✔️ Physical BACnet DDC Controllers",
            "✔️ Real physical water chillers & boilers",
            "Central BAS Server & ControlDesk",
            "BACnet/IP, ARCNET",
            "✔️ Hardware chiller overpressure safety",
            "❌ (Fault detection only)",
            "❌",
            "❌",
            "Physical industrial water chillers and boilers",
            "Cross-layer host memory forensics + fieldbus deception"
        ],
        [
            "jmse-12-01236.pdf (Marine PMS)",
            "Marine LNG Vessel Power",
            "✔️ Allen-Bradley PLC & KTE PMS2500",
            "✔️ Physical Main Switchboard (MSBD)",
            "Simulation Control Console (SCC)",
            "Modbus TCP, OPC Ethernet",
            "✔️ Physical generator breaker trips",
            "❌ (Safety & fault testing only)",
            "❌",
            "❌",
            "Physical Allen-Bradley PLC & marine switchboard",
            "Safe destructive testing without equipment damage risk"
        ]
    ]

    ws4.cell(1, 1, "Theme 3: Real Industrial PLCs & Physical Testbeds").font = FONT_TITLE
    ws4.cell(2, 1, "Published Research Utilizing Commercial Industrial PLCs (Schneider, Siemens, Allen-Bradley, BACnet) and Physical Process Rigs").font = FONT_SUBTITLE

    for c_idx, (h_name, width, align) in enumerate(THEME3_HEADERS, 1):
        cell = ws4.cell(4, c_idx, h_name)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN
        ws4.column_dimensions[get_column_letter(c_idx)].width = width

    for c_idx, val in enumerate(PROPOSED_THEME3_ROW, 1):
        cell = ws4.cell(5, c_idx, val)
        cell.font = FONT_PROPOSED
        cell.fill = FILL_PROPOSED_ROW
        cell.alignment = THEME3_HEADERS[c_idx - 1][2]
        cell.border = BORDER_PROPOSED

    for r_idx, r_data in enumerate(REAL_PLC_PAPERS_DATA, 6):
        is_alt = (r_idx % 2 == 1)
        row_fill = FILL_ALT_ROW if is_alt else FILL_WHITE
        for c_idx, val in enumerate(r_data, 1):
            cell = ws4.cell(r_idx, c_idx, str(val))
            cell.border = BORDER_THIN
            cell.alignment = THEME3_HEADERS[c_idx - 1][2]
            cell.fill = row_fill
            cell.font = FONT_TICK if val in ["✔️", "❌"] else FONT_DATA

    ws4.freeze_panes = "B6"

    wb.save(FILE_PATH)
    print(f"Successfully updated {FILE_PATH} with real PLC experimental testbeds!")

if __name__ == "__main__":
    update_workbook()
