#!/usr/bin/env python3
"""
Make all 3 theme sheets in Comparative-OT-Security-Landscape.xlsx 100% consistent:
Every theme sheet has precisely 16 columns (Col 1 is Paper, Cols 2-16 are the exact 15 points of comparison):
1. Paper
2. Domain
3. Hardware Node
4. HIL Closed-Loop
5. Industrial PLC
6. Multi-Stage Plant
7. Real Fluid / Pipes
8. Mechanical PRV
9. 50+ Node Scale
10. Microsecond RT
11. Fieldbus Protocols
12. Deception Honeynet
13. Host / Memory Forensics
14. Edge CPU / Thermals
15. Paper Strength (vs Proposed)
16. Proposed System Focus
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FILE_PATH = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/Comparative-OT-Security-Landscape.xlsx"

def align_workbook():
    wb = openpyxl.load_workbook(FILE_PATH)

    # ── Strict Black & White / Grayscale Palette ─────────────────────────────
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

    UNIFIED_HEADERS = [
        ("Paper", 26, ALIGN_LEFT),
        ("Domain", 18, ALIGN_CENTER),
        ("Hardware Node", 12, ALIGN_CENTER),
        ("HIL Closed-Loop", 12, ALIGN_CENTER),
        ("Industrial PLC", 13, ALIGN_CENTER),
        ("Multi-Stage Plant", 14, ALIGN_CENTER),
        ("Real Fluid / Pipes", 14, ALIGN_CENTER),
        ("Mechanical PRV", 13, ALIGN_CENTER),
        ("50+ Node Scale", 12, ALIGN_CENTER),
        ("Microsecond RT", 13, ALIGN_CENTER),
        ("Fieldbus Protocols", 16, ALIGN_CENTER),
        ("Deception Honeynet", 15, ALIGN_CENTER),
        ("Host / Memory Forensics", 16, ALIGN_CENTER),
        ("Edge CPU / Thermals", 15, ALIGN_CENTER),
        ("Paper Strength (vs Proposed)", 32, ALIGN_LEFT),
        ("Proposed System Focus", 32, ALIGN_LEFT),
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
        "❌ (1 Node)",
        "❌ (100ms Linux)",
        "4 Protocols",
        "✔️",
        "✔️",
        "✔️",
        "—",
        "Low-cost edge deception honeynet"
    ]

    # Rebuild Sheet 4 (Theme 3 - Real PLCs & Rigs) with the exact 16 columns!
    sheet4_name = "Theme 3 - Real PLCs & Rigs"
    if sheet4_name in wb.sheetnames:
        old_ws4 = wb[sheet4_name]
        s4_idx = wb.sheetnames.index(sheet4_name)
        wb.remove(old_ws4)
    else:
        s4_idx = len(wb.sheetnames)

    ws4 = wb.create_sheet(title=sheet4_name, index=s4_idx)
    ws4.views.sheetView[0].showGridLines = True

    ws4.cell(1, 1, "Theme 3: Real Industrial PLCs & Physical Testbeds").font = FONT_TITLE
    ws4.cell(2, 1, "Published Research Utilizing Commercial Industrial PLCs (Schneider, Siemens, Allen-Bradley, BACnet) and Physical Process Rigs").font = FONT_SUBTITLE

    # Header row
    for c_idx, (h_name, width, align) in enumerate(UNIFIED_HEADERS, 1):
        cell = ws4.cell(4, c_idx, h_name)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN
        ws4.column_dimensions[get_column_letter(c_idx)].width = width

    # Row 5: Proposed System
    for c_idx, val in enumerate(PROPOSED_UNIFIED_ROW, 1):
        cell = ws4.cell(5, c_idx, val)
        cell.font = FONT_PROPOSED
        cell.fill = FILL_PROPOSED_ROW
        cell.alignment = UNIFIED_HEADERS[c_idx - 1][2]
        cell.border = BORDER_PROPOSED

    # Real PLC Papers Data (16 columns each!)
    THEME3_DATA = [
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
            "Schneider M580 PLCs + physical water rig",
            "Post-compromise cyber deception & memory forensics"
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
            "Physical M580 PID closed-loop steam plant",
            "Multi-protocol deception on accessible edge SBC"
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
            "Microsecond Siemens protection relays & Omicron",
            "Low-cost ($50) edge platform with SCADA SSH capture"
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
            "BACnet/IP, ARCNET",
            "❌ (Fault Detection)",
            "❌",
            "❌",
            "Physical industrial water chillers and boilers",
            "Cross-layer host memory forensics + fieldbus deception"
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
            "Physical Allen-Bradley PLC & marine switchboard",
            "Safe destructive testing without equipment damage risk"
        ]
    ]

    for r_idx, r_data in enumerate(THEME3_DATA, 6):
        is_alt = (r_idx % 2 == 1)
        row_fill = FILL_ALT_ROW if is_alt else FILL_WHITE
        for c_idx, val in enumerate(r_data, 1):
            cell = ws4.cell(r_idx, c_idx, str(val))
            cell.border = BORDER_THIN
            cell.alignment = UNIFIED_HEADERS[c_idx - 1][2]
            cell.fill = row_fill
            cell.font = FONT_TICK if val in ["✔️", "❌"] else FONT_DATA

    ws4.freeze_panes = "B6"

    # Also verify Theme 1 and Theme 2 have the exact same unified headers!
    for sheet_name in ["Theme 1 - Sim Only (18 P)", "Theme 2 - Hybrid & HIL (24 P)"]:
        ws = wb[sheet_name]
        for c_idx, (h_name, width, align) in enumerate(UNIFIED_HEADERS, 1):
            cell = ws.cell(4, c_idx, h_name)
            cell.font = FONT_HEADER
            cell.fill = FILL_BLACK_HEADER
            cell.alignment = ALIGN_HEADER
            cell.border = BORDER_THIN
            ws.column_dimensions[get_column_letter(c_idx)].width = width
        
        # Verify Row 5 Proposed System
        for c_idx, val in enumerate(PROPOSED_UNIFIED_ROW, 1):
            cell = ws.cell(5, c_idx, val)
            cell.font = FONT_PROPOSED
            cell.fill = FILL_PROPOSED_ROW
            cell.alignment = UNIFIED_HEADERS[c_idx - 1][2]
            cell.border = BORDER_PROPOSED

    wb.save(FILE_PATH)
    print("Successfully aligned all 3 themes to have the EXACT SAME 15 COMPARISON POINTS (16 columns total)!")

if __name__ == "__main__":
    align_workbook()
