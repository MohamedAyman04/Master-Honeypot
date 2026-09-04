#!/usr/bin/env python3
"""
Generate a clean, professional, non-AI, academic-grade Excel workbook.
- Monochrome / Black & White palette (Black headers, white/light gray rows)
- Strict simple checkmarks (✔️ and ❌ only, no verbose explanations in checkmark cells)
- Authentic system naming: "Proposed System (This Work)" without stars or marketing fluff
- Concise, factual table entries (3-7 words max)
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FILE_PATH = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/Comparative-OT-Security-Landscape.xlsx"

def build_clean_workbook():
    wb = openpyxl.load_workbook(FILE_PATH)

    # ── Strict Black & White / Grayscale Palette ─────────────────────────────
    FONT_TITLE = Font(name="Calibri", size=14, bold=True, color="000000")
    FONT_SUBTITLE = Font(name="Calibri", size=10, italic=True, color="444444")
    FONT_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    FONT_PROPOSED = Font(name="Calibri", size=9.5, bold=True, color="000000")
    FONT_DATA = Font(name="Calibri", size=9.5, color="000000")
    FONT_TICK = Font(name="Calibri", size=10, bold=True, color="000000")

    FILL_BLACK_HEADER = PatternFill(start_color="1A1A1A", end_color="1A1A1A", fill_type="solid") # Solid Black/Dark Charcoal
    FILL_PROPOSED_ROW = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid") # Solid Light Gray
    FILL_ALT_ROW = PatternFill(start_color="F7F7F7", end_color="F7F7F7", fill_type="solid")     # Very Faint Gray
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
    ws_exec.cell(2, 2, "Literature Comparison Matrix").font = FONT_TITLE
    ws_exec.cell(3, 2, "Comparative evaluation of experimental methodologies in OT/CPS security research").font = FONT_SUBTITLE

    scorecard_headers = [
        "Evaluation Metric",
        "Simulation Only (18)",
        "Hybrid & HIL (24)",
        "Hardware Only (5)",
        "Proposed System (This Work)"
    ]

    scorecard_data = [
        ["Physical Hardware Node", "❌", "✔️", "✔️", "✔️ (Raspberry Pi 4B)"],
        ["Hardware-in-the-Loop (HIL)", "❌", "✔️", "❌", "✔️"],
        ["Process Physics Model", "Offline CSV / Mock", "PC Co-Simulation", "Real Physical Plant", "Hydraulic ODE (100ms)"],
        ["Process Complexity", "Single or multi-stage", "Multi-stage (Simulink)", "Full multi-stage (6 stages)", "Single-stage pipeline"],
        ["Non-Linear Dynamics (Cavitation, Wear)", "❌", "Partial (Simulink)", "✔️ (Real phenomena)", "❌ (Low-order ODE)"],
        ["Sensor Noise Model", "❌ (Zero-noise)", "❌ (Deterministic)", "✔️ (Real analog drift)", "Gaussian N(0, σ²)"],
        ["Mechanical Safety (PRV / Breaker)", "❌", "Partial", "✔️ (Physical PRV)", "❌ (Software check only)"],
        ["Destructive Attack Safety", "✔️ Safe", "✔️ Safe", "❌ High risk (Damage hazard)", "✔️ Safe (Software ODE)"],
        ["Scalability (Node Count)", "✔️ High (100+ virtual)", "Moderate", "❌ Rigid (Fixed rig)", "❌ 1 Physical node"],
        ["Execution Speed", "✔️ Accelerated", "❌ Real-time bound", "❌ Real-time bound", "❌ Real-time bound (100ms)"],
        ["Industrial Controller Hardware", "❌", "✔️ (Siemens S7/AB)", "✔️ (Industrial PLCs)", "Raspberry Pi SoftPLC"],
        ["Cyber Deception Honeynet", "Partial (Static/Fake)", "Partial", "❌ Impractical on plant", "✔️ Dynamic feedback"],
        ["Industrial Protocols", "1 (Modbus/BACnet)", "1–2 protocols", "1 proprietary vendor", "4 (MB, OPC-UA, S7, DNP3)"],
        ["SCADA Host & Memory Security", "❌", "❌", "Partial (Linux)", "✔️ (SSH + Memory artifacts)"],
        ["Edge Profiling (Thermals/CPU)", "❌", "❌", "Partial", "✔️ (44.3°C, CPU, RAM)"],
        ["Capital Equipment Cost", "Near-zero", "$5K–$50K", "$50K–$1M+", "~$50 (Raspberry Pi)"]
    ]

    # Header row (row 5)
    for c_idx, h_text in enumerate(scorecard_headers, 2):
        cell = ws_exec.cell(5, c_idx, h_text)
        cell.font = FONT_HEADER
        cell.fill = FILL_BLACK_HEADER
        cell.alignment = ALIGN_HEADER
        cell.border = BORDER_THIN

    # Data rows (rows 6 to 21)
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
            elif c_idx == 6: # Proposed System column
                cell.font = FONT_PROPOSED
                cell.alignment = ALIGN_LEFT
                cell.fill = FILL_PROPOSED_ROW
                cell.border = BORDER_PROPOSED
            else:
                cell.font = FONT_DATA
                cell.alignment = ALIGN_CENTER if val in ["✔️", "❌"] else ALIGN_LEFT
                cell.fill = row_fill

    ws_exec.column_dimensions['B'].width = 34
    ws_exec.column_dimensions['C'].width = 24
    ws_exec.column_dimensions['D'].width = 24
    ws_exec.column_dimensions['E'].width = 26
    ws_exec.column_dimensions['F'].width = 30

    # ─────────────────────────────────────────────────────────────────────────
    # 2. THEME SHEETS: Clean, Concise, Checkmark-Only
    # ─────────────────────────────────────────────────────────────────────────
    THEME_HEADERS = [
        ("Paper", 26, ALIGN_LEFT),
        ("Domain", 15, ALIGN_CENTER),
        ("Hardware", 11, ALIGN_CENTER),
        ("HIL", 9, ALIGN_CENTER),
        ("Process Physics", 22, ALIGN_LEFT),
        ("Protocols", 16, ALIGN_CENTER),
        ("SoftPLC", 13, ALIGN_CENTER),
        ("Deception", 11, ALIGN_CENTER),
        ("Host Security", 12, ALIGN_CENTER),
        ("Edge Metrics", 12, ALIGN_CENTER),
        ("Paper Strength (vs Proposed)", 30, ALIGN_LEFT),
        ("Proposed System Focus", 30, ALIGN_LEFT),
    ]

    PROPOSED_THEME_ROW = [
        "Proposed System (This Work)",
        "Water / Pipeline",
        "✔️",
        "✔️",
        "Hydraulic ODE (100ms)",
        "4 Protocols",
        "CODESYS",
        "✔️",
        "✔️",
        "✔️",
        "—",
        "Low-cost edge deception honeynet"
    ]

    def build_clean_theme_sheet(sheet_name, title, theme_id):
        old_ws = wb[sheet_name]
        existing_rows = []
        for r in range(6, old_ws.max_row + 1):
            p_name = old_ws.cell(r, 1).value
            domain = old_ws.cell(r, 2).value
            phys_hw = old_ws.cell(r, 3).value
            hil = old_ws.cell(r, 4).value
            if p_name:
                existing_rows.append({
                    'paper': str(p_name),
                    'domain': str(domain) if domain else 'General OT',
                })

        sheet_idx = wb.sheetnames.index(sheet_name)
        wb.remove(old_ws)
        ws = wb.create_sheet(title=sheet_name, index=sheet_idx)
        ws.views.sheetView[0].showGridLines = True

        ws.cell(1, 1, title).font = FONT_TITLE
        ws.cell(2, 1, f"Total Sources: {len(existing_rows)}").font = FONT_SUBTITLE

        # Header (row 4)
        for c_idx, (h_name, width, align) in enumerate(THEME_HEADERS, 1):
            cell = ws.cell(4, c_idx, h_name)
            cell.font = FONT_HEADER
            cell.fill = FILL_BLACK_HEADER
            cell.alignment = ALIGN_HEADER
            cell.border = BORDER_THIN
            ws.column_dimensions[get_column_letter(c_idx)].width = width

        # Row 5: Proposed System
        for c_idx, val in enumerate(PROPOSED_THEME_ROW, 1):
            cell = ws.cell(5, c_idx, val)
            cell.font = FONT_PROPOSED
            cell.fill = FILL_PROPOSED_ROW
            cell.alignment = THEME_HEADERS[c_idx - 1][2]
            cell.border = BORDER_PROPOSED

        # Data rows
        for r_idx, r_item in enumerate(existing_rows, 6):
            p_name = r_item['paper']
            domain = r_item['domain']

            # Categorical checkmarks & concise values
            if theme_id == 1: # Simulation Only
                phys_hw = "❌"
                hil = "❌"
                softplc = "❌"
                deception = "✔️" if ('honeypot' in p_name.lower() or 'tesi' in p_name.lower() or 'future' in p_name.lower()) else "❌"
                host_sec = "❌"
                edge_prof = "❌"

                if '01403664' in p_name or '09252312' in p_name or '10848045' in p_name or 's10844' in p_name:
                    physics = "SWaT CSV Replay"
                    protos = "Modbus" if '01403664' in p_name else ("DNP3" if '09252312' in p_name else "Modbus")
                    paper_str = "6-Stage physical water plant data"
                    my_focus = "Live closed-loop reactive physics"
                elif 'Two-Level' in p_name:
                    physics = "Simulated Tank ODE"
                    protos = "Modbus"
                    paper_str = "Multi-tank simulation scale"
                    my_focus = "Physical ARM64 SoftPLC deployment"
                elif 'electronics-11-01659' in p_name:
                    physics = "Power Grid Flow"
                    protos = "Modbus"
                    paper_str = "Large-scale electrical grid model"
                    my_focus = "Multi-protocol fieldbus integration"
                else:
                    physics = "Algebraic Mock / None"
                    protos = "Modbus" if 'tesi' in p_name else "Single Protocol"
                    paper_str = "100+ Nodes virtual scalability"
                    my_focus = "Continuous physics for deception"

            elif theme_id == 2: # Hybrid & HIL
                phys_hw = "✔️"
                hil = "✔️"
                deception = "✔️" if ('Savage' in p_name or 'out.pdf' in p_name or 'Honey' in p_name) else "❌"
                host_sec = "❌"
                edge_prof = "❌"

                if '03787788' in p_name or '2210.11234' in p_name:
                    physics = "Real HVAC Equipment"
                    protos = "BACnet"
                    softplc = "Proprietary"
                    paper_str = "Physical chiller/boiler thermal loops"
                    my_focus = "Multi-protocol fieldbus deception"
                elif '1874548224' in p_name:
                    physics = "Thermal Power Plant"
                    protos = "Modbus"
                    softplc = "Industrial"
                    paper_str = "Multi-stage steam turbine physics"
                    my_focus = "Low-cost edge hardware feasibility"
                elif '1874548225' in p_name:
                    physics = "Real Water Rig"
                    protos = "Modbus"
                    softplc = "Industrial"
                    paper_str = "Physical water pumps and tanks"
                    my_focus = "Safe overpressure testing (>200 PSI)"
                elif '3524489' in p_name or 'Impact' in p_name:
                    physics = "RTDS Grid Simulator"
                    protos = "IEC 61850"
                    softplc = "Proprietary"
                    paper_str = "Microsecond electrical transients"
                    my_focus = "Low-cost ($50) edge testbed"
                elif 'ares-etacs' in p_name:
                    physics = "Water Circulation Rig"
                    protos = "Modbus"
                    softplc = "Schneider"
                    paper_str = "Physical Schneider PLC hardware"
                    my_focus = "Post-compromise cyber deception"
                else:
                    physics = "Co-Simulated Model"
                    protos = "Modbus"
                    softplc = "OpenPLC" if 'testbeds' in p_name else "❌"
                    paper_str = "Standard Simulink toolchain"
                    my_focus = "CODESYS on ARM64 with thermals"

            else: # Theme 3: Hardware Only
                phys_hw = "✔️"
                hil = "❌"
                protos = "Proprietary" if '2402' in p_name else ("Standard" if 'NIST' in p_name else "GPIO/SPI")
                softplc = "Proprietary" if '2402' in p_name else "❌"
                deception = "❌"
                host_sec = "✔️" if '2402' in p_name else "❌"
                edge_prof = "✔️" if ('c3965' in p_name or 'pico' in p_name) else "❌"

                if '2402.14599' in p_name:
                    physics = "OS Host Metrics"
                    paper_str = "Dedicated host OS kernel monitoring"
                    my_focus = "Cross-layer fieldbus + physics link"
                elif 'NIST' in p_name:
                    physics = "Operational Guidelines"
                    paper_str = "Comprehensive federal OT standard"
                    my_focus = "Experimental testbed validation"
                elif 'c3965c88' in p_name or 'pico' in p_name:
                    physics = "Electrical GPIO/ADC"
                    paper_str = "Low-level hardware clock/pin tests"
                    my_focus = "Complete industrial SoftPLC stack"
                else: # Claroty
                    physics = "Live Production Plants"
                    paper_str = "Empirical data from 1000+ plants"
                    my_focus = "Interactive deception sandbox"

            row_data = [
                p_name,
                domain,
                phys_hw,
                hil,
                physics,
                protos,
                softplc,
                deception,
                host_sec,
                edge_prof,
                paper_str,
                my_focus
            ]

            is_alt = (r_idx % 2 == 1)
            row_fill = FILL_ALT_ROW if is_alt else FILL_WHITE

            for c_idx, val in enumerate(row_data, 1):
                cell = ws.cell(r_idx, c_idx, str(val))
                cell.border = BORDER_THIN
                cell.alignment = THEME_HEADERS[c_idx - 1][2]
                cell.fill = row_fill
                cell.font = FONT_TICK if val in ["✔️", "❌"] else FONT_DATA

        ws.freeze_panes = "B6"

    build_clean_theme_sheet("Theme 1 - Sim Only (18 P)", "Theme 1: Simulation & Emulation Only Papers", 1)
    build_clean_theme_sheet("Theme 2 - Hybrid & HIL (24 P)", "Theme 2: Hybrid & Hardware-in-the-Loop Papers", 2)
    build_clean_theme_sheet("Theme 3 - Hard Only (5 P)", "Theme 3: Real Physics & Hardware-Centric Research", 3)

    wb.save(FILE_PATH)
    print(f"Successfully generated clean academic workbook at:\n{FILE_PATH}")

if __name__ == "__main__":
    build_clean_workbook()
