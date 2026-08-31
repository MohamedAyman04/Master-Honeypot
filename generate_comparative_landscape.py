#!/usr/bin/env python3
"""
Generate Comparative-OT-Security-Landscape.xlsx
Location: /run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd

SOURCE_FILE = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review/OT-Security-Research-Landscape.xlsx"
TARGET_DIR = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Literature Review"
TARGET_FILE = os.path.join(TARGET_DIR, "Comparative-OT-Security-Landscape.xlsx")

def build_comparative_workbook():
    # 1. Read source data
    wb_src = openpyxl.load_workbook(SOURCE_FILE, data_only=True)
    ws_src = wb_src['Research Comps']

    data = []
    headers = [cell.value for cell in ws_src[1] if cell.value is not None]

    for row in ws_src.iter_rows(min_row=2, values_only=True):
        if any(row):
            data.append(list(row)[:len(headers)])

    df = pd.DataFrame(data, columns=headers)
    print(f"Total source rows extracted: {len(df)}")

    # Classify into the 3 themes
    # Theme 1: Simulation/Emulation ONLY (No Physical Hardware & No HIL)
    df_sim_only = df[(df['Physical hardware used?'] == 'No') & (df['Hardware-in-the-loop used?'] == 'No')].copy()

    # Theme 2: Hybrid & HIL (Simulation + Hardware in the loop or physical PLCs)
    df_hybrid = df[(df['Hybrid physical/simulation architecture used?'] == 'Yes') | (df['Hardware-in-the-loop used?'] == 'Yes')].copy()

    # Theme 3: Hardware / Physical ONLY (Physical hardware used, Simulation is No)
    df_hard_only = df[(df['Physical hardware used?'] == 'Yes') & (df['Simulation used?'] == 'No')].copy()

    print(f"Theme 1 (Sim & Emul Only): {len(df_sim_only)} papers")
    print(f"Theme 2 (Hybrid & HIL): {len(df_hybrid)} papers")
    print(f"Theme 3 (Hardware Only): {len(df_hard_only)} papers")

    # 2. Create Target Workbook
    wb_tgt = openpyxl.Workbook()
    # remove default sheet
    wb_tgt.remove(wb_tgt.active)

    # Styles definition
    FONT_TITLE = Font(name="Calibri", size=16, bold=True, color="003366")
    FONT_SUBTITLE = Font(name="Calibri", size=11, italic=True, color="4A6572")
    FONT_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    FONT_MY_WORK = Font(name="Calibri", size=9.5, bold=True, color="002B49")
    FONT_DATA = Font(name="Calibri", size=9, color="212121")
    FONT_DIFF = Font(name="Calibri", size=9, bold=True, color="004D40")

    FILL_HEADER = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
    FILL_MY_WORK = PatternFill(start_color="D4E6F1", end_color="D4E6F1", fill_type="solid") # Distinct soft blue highlight
    FILL_ALT_ROW = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
    FILL_WHITE = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    FILL_DIFF = PatternFill(start_color="E8F8F5", end_color="E8F8F5", fill_type="solid")

    THIN_BORDER_GRAY = Border(
        left=Side(style='thin', color='D0D3D4'),
        right=Side(style='thin', color='D0D3D4'),
        top=Side(style='thin', color='D0D3D4'),
        bottom=Side(style='thin', color='D0D3D4')
    )
    MY_WORK_BORDER = Border(
        left=Side(style='medium', color='003366'),
        right=Side(style='medium', color='003366'),
        top=Side(style='medium', color='003366'),
        bottom=Side(style='medium', color='003366')
    )

    ALIGN_LEFT = Alignment(horizontal='left', vertical='top', wrap_text=True)
    ALIGN_CENTER = Alignment(horizontal='center', vertical='top', wrap_text=True)
    ALIGN_HEADER = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # ─────────────────────────────────────────────────────────────────────────────
    # SHEET 1: Table of Contents & Executive Overview
    # ─────────────────────────────────────────────────────────────────────────────
    ws_toc = wb_tgt.create_sheet(title="Executive Overview & TOC")
    ws_toc.views.sheetView[0].showGridLines = True

    ws_toc.cell(2, 2, "OT & CPS Security Research Landscape — 3-Thematic Comparative Analysis").font = FONT_TITLE
    ws_toc.cell(3, 2, "Author: Mohamed Ayman | Institution: German University in Cairo (GUC) | Date: August 2026").font = FONT_SUBTITLE
    
    ws_toc.cell(5, 2, "This workbook rigorously benchmarks the proposed Hardware-in-the-Loop (HIL) CODESYS SoftPLC Cyber-Physical Deception Testbed against 47 state-of-the-art research publications grouped into three distinct methodological themes.").font = Font(name="Calibri", size=10.5, color="333333")

    toc_table = [
        ["Sheet Name", "Theme / Category Description", "Paper Count", "Core Research Gap Addressed by Your Master's Work"],
        ["Theme 1 - Sim & Emul Only", "Simulation & Emulation Only (No Physical Hardware, No HIL)", f"{len(df_sim_only)} Papers", "Eliminates the 'Sim-to-Real Gap': Replaces virtual clock sharing with real ARM64 Cortex-A72 execution cycles, physical network transmission jitter, and dynamic hydraulic differential feedback."],
        ["Theme 2 - Hybrid & HIL", "Hybrid Architecture & Hardware-in-the-Loop Testbeds", f"{len(df_hybrid)} Papers", "Multi-Protocol & Edge Resource Completeness: Integrates Modbus, OPC UA, S7, DNP3 in a unified SoftPLC while experimentally quantifying SoC thermals (44.3°C), CPU overhead, and 100ms scan cycle jitter."],
        ["Theme 3 - Hardware Only", "Hardware-Only & Physical Plant Implementations (No Simulation)", f"{len(df_hard_only)} Papers", "Cost, Scalability & Reconfigurability: Delivers physical hardware interaction and real fieldbus protocol behavior without the multi-million dollar capital cost, physical safety hazards, or fixed topologies of full-scale plants."]
    ]

    for r_idx, row in enumerate(toc_table):
        for c_idx, val in enumerate(row):
            cell = ws_toc.cell(7 + r_idx, 2 + c_idx, val)
            if r_idx == 0:
                cell.font = FONT_HEADER
                cell.fill = FILL_HEADER
                cell.alignment = ALIGN_HEADER
            else:
                cell.font = FONT_DATA
                cell.border = THIN_BORDER_GRAY
                cell.alignment = ALIGN_LEFT
                if r_idx % 2 == 1:
                    cell.fill = FILL_ALT_ROW
                else:
                    cell.fill = FILL_WHITE
            if c_idx == 2 and r_idx > 0:
                cell.alignment = ALIGN_CENTER

    # Adjust widths for TOC
    ws_toc.column_dimensions['B'].width = 28
    ws_toc.column_dimensions['C'].width = 40
    ws_toc.column_dimensions['D'].width = 16
    ws_toc.column_dimensions['E'].width = 65

    # ─────────────────────────────────────────────────────────────────────────────
    # Helper to populate theme sheets
    # ─────────────────────────────────────────────────────────────────────────────
    extended_headers = headers + [
        "Direct Comparison: Gap Addressed by Your Master's Work",
        "Your Thesis Advantage (Multi-Protocol, HIL, Real-Time Physics, Edge Profiling)"
    ]

    my_work_data_sim = [
        "★ YOUR WORK: Master-Honeypot HIL SoftPLC Testbed (Mohamed Ayman, GUC 2026)",
        "Improve ICS honeypot realism via physical HIL node, closed-loop hydraulic process dynamics, multi-protocol emulation, and edge resource evaluation.",
        "Physical Raspberry Pi 4B (4GB ARM64) + Docker Cluster over 802.11ac Wi-Fi / Gigabit Ethernet.",
        "Purdue-Segmented 5-Tier HIL Architecture (Level 0-1 Physical, Level 2 Ingestion, Level 3 Enterprise, Level 3.5 IDMZ, Out-of-Band Monitoring).",
        "Yes", # Physical Hardware
        "Yes", # Simulation
        "Yes", # Emulation
        "Yes", # HIL
        "Yes", # Hybrid
        "CODESYS IEC 61131-3 Deterministic SoftPLC Runtime (100ms scan cycle, safety trip at P > 200 PSI).",
        "Embedded WebVisu HMI (:8080), Central Web HMI (:8060), InfluxDB 2.7.6 (:8086), Grafana (:3005), SCADA SSH (:2222).",
        "Modbus TCP (:502), OPC UA (:4840), Siemens S7comm (:102), DNP3 (:20000), HTTP/REST.",
        "Real-time physical telemetry stream, 9-phase MITRE ATT&CK campaign logs, raw PCAP captures, Modbus register history.",
        "False Data Injection (FDI), Pump Over-speeding (3000 RPM), Valve Tampering, Replay Attacks, Reconnaissance Probes, E-Stop Interlock Trips.",
        "6-Layer Cross-Layer Engine (Narrow Mechanism Gate, Physics Boundary Gate, ML Isolation Forest + LSTM-AE, MITRE Story Logger).",
        "Detection F1-Score (>98%), Latency (Modbus 5.8ms, OPC UA 1.6ms), Scan Jitter (100ms), CPU Util (600MHz-1.8GHz), SoC Temp (44.3°C), RAM (549MB).",
        "Experimental validation across 9-phase automated attack campaigns, physical network latency measurements, and hardware telemetry profiling.",
        "Physical testbed scale currently bounded to single-stage pipeline; future work targets multi-PLC distributed water networks.",
        "Resolves the Sim-to-Real Gap: Pure simulation papers lack physical clock cycle constraints, real embedded OS scheduling, and physical packet jitter.",
        "Provides true hardware execution on ARM Cortex-A72 SoC while executing continuous ODE differential physics in closed-loop."
    ]

    my_work_data_hybrid = [
        "★ YOUR WORK: Master-Honeypot HIL SoftPLC Testbed (Mohamed Ayman, GUC 2026)",
        "Improve ICS honeypot realism via physical HIL node, closed-loop hydraulic process dynamics, multi-protocol emulation, and edge resource evaluation.",
        "Physical Raspberry Pi 4B (4GB ARM64) + Docker Cluster over 802.11ac Wi-Fi / Gigabit Ethernet.",
        "Purdue-Segmented 5-Tier HIL Architecture (Level 0-1 Physical, Level 2 Ingestion, Level 3 Enterprise, Level 3.5 IDMZ, Out-of-Band Monitoring).",
        "Yes", "Yes", "Yes", "Yes", "Yes",
        "CODESYS IEC 61131-3 Deterministic SoftPLC Runtime (100ms scan cycle, safety trip at P > 200 PSI).",
        "Embedded WebVisu HMI (:8080), Central Web HMI (:8060), InfluxDB 2.7.6 (:8086), Grafana (:3005), SCADA SSH (:2222).",
        "Modbus TCP (:502), OPC UA (:4840), Siemens S7comm (:102), DNP3 (:20000), HTTP/REST.",
        "Real-time physical telemetry stream, 9-phase MITRE ATT&CK campaign logs, raw PCAP captures, Modbus register history.",
        "False Data Injection (FDI), Pump Over-speeding (3000 RPM), Valve Tampering, Replay Attacks, Reconnaissance Probes, E-Stop Interlock Trips.",
        "6-Layer Cross-Layer Engine (Narrow Mechanism Gate, Physics Boundary Gate, ML Isolation Forest + LSTM-AE, MITRE Story Logger).",
        "Detection F1-Score (>98%), Latency (Modbus 5.8ms, OPC UA 1.6ms), Scan Jitter (100ms), CPU Util (600MHz-1.8GHz), SoC Temp (44.3°C), RAM (549MB).",
        "Experimental validation across 9-phase automated attack campaigns, physical network latency measurements, and hardware telemetry profiling.",
        "Physical testbed scale currently bounded to single-stage pipeline; future work targets multi-PLC distributed water networks.",
        "Multi-Protocol Integration & Edge Profiling: Most hybrid testbeds support only 1 protocol (Modbus or BACnet) and omit embedded thermal/CPU profiling.",
        "Unifies Modbus TCP, OPC UA, S7, DNP3 on physical hardware with continuous thermal (44.3°C) and CPU benchmarking."
    ]

    my_work_data_hard = [
        "★ YOUR WORK: Master-Honeypot HIL SoftPLC Testbed (Mohamed Ayman, GUC 2026)",
        "Improve ICS honeypot realism via physical HIL node, closed-loop hydraulic process dynamics, multi-protocol emulation, and edge resource evaluation.",
        "Physical Raspberry Pi 4B (4GB ARM64) + Docker Cluster over 802.11ac Wi-Fi / Gigabit Ethernet.",
        "Purdue-Segmented 5-Tier HIL Architecture (Level 0-1 Physical, Level 2 Ingestion, Level 3 Enterprise, Level 3.5 IDMZ, Out-of-Band Monitoring).",
        "Yes", "Yes", "Yes", "Yes", "Yes",
        "CODESYS IEC 61131-3 Deterministic SoftPLC Runtime (100ms scan cycle, safety trip at P > 200 PSI).",
        "Embedded WebVisu HMI (:8080), Central Web HMI (:8060), InfluxDB 2.7.6 (:8086), Grafana (:3005), SCADA SSH (:2222).",
        "Modbus TCP (:502), OPC UA (:4840), Siemens S7comm (:102), DNP3 (:20000), HTTP/REST.",
        "Real-time physical telemetry stream, 9-phase MITRE ATT&CK campaign logs, raw PCAP captures, Modbus register history.",
        "False Data Injection (FDI), Pump Over-speeding (3000 RPM), Valve Tampering, Replay Attacks, Reconnaissance Probes, E-Stop Interlock Trips.",
        "6-Layer Cross-Layer Engine (Narrow Mechanism Gate, Physics Boundary Gate, ML Isolation Forest + LSTM-AE, MITRE Story Logger).",
        "Detection F1-Score (>98%), Latency (Modbus 5.8ms, OPC UA 1.6ms), Scan Jitter (100ms), CPU Util (600MHz-1.8GHz), SoC Temp (44.3°C), RAM (549MB).",
        "Experimental validation across 9-phase automated attack campaigns, physical network latency measurements, and hardware telemetry profiling.",
        "Physical testbed scale currently bounded to single-stage pipeline; future work targets multi-PLC distributed water networks.",
        "Low Cost & Complete Safety: Hardware-only testbeds cost $100K–$1M+ and cannot safely execute destructive physical overpressure attacks.",
        "Reconfigurable software-defined ODE physics coupled to low-cost ($50) physical SBC allows safe exploration of catastrophic pipeline explosions."
    ]

    def populate_theme_sheet(ws, sheet_title, df_subset, my_work_row, gap_analysis_generator):
        ws.views.sheetView[0].showGridLines = True
        
        # Title Block
        ws.cell(1, 1, sheet_title).font = FONT_TITLE
        ws.cell(2, 1, f"Comparative Analysis: Master-Honeypot HIL SoftPLC vs. Literature ({len(df_subset)} Research Sources)").font = FONT_SUBTITLE
        
        # Headers (Row 4)
        for c_idx, h_text in enumerate(extended_headers, 1):
            cell = ws.cell(4, c_idx, h_text)
            cell.font = FONT_HEADER
            cell.fill = FILL_HEADER
            cell.alignment = ALIGN_HEADER
            cell.border = THIN_BORDER_GRAY

        # Row 5: YOUR WORK (Highlighted baseline)
        for c_idx, val in enumerate(my_work_row, 1):
            cell = ws.cell(5, c_idx, val)
            cell.font = FONT_MY_WORK
            cell.fill = FILL_MY_WORK
            cell.alignment = ALIGN_LEFT
            cell.border = MY_WORK_BORDER

        # Subsequent rows: Literature papers
        curr_row = 6
        for _, r_data in df_subset.iterrows():
            paper_name = str(r_data['Paper'])
            row_vals = list(r_data)
            gap_info, adv_info = gap_analysis_generator(r_data)
            row_vals.extend([gap_info, adv_info])

            is_alt = (curr_row % 2 == 1)
            row_fill = FILL_ALT_ROW if is_alt else FILL_WHITE

            for c_idx, val in enumerate(row_vals, 1):
                cell = ws.cell(curr_row, c_idx, str(val) if val is not None else "")
                cell.font = FONT_DATA
                cell.border = THIN_BORDER_GRAY
                cell.alignment = ALIGN_LEFT
                cell.fill = row_fill
                
                # Highlight the comparison columns slightly
                if c_idx >= len(headers) + 1:
                    cell.font = FONT_DIFF
                    cell.fill = FILL_DIFF

            curr_row += 1

        # Format column widths
        for col_idx in range(1, len(extended_headers) + 1):
            col_letter = get_column_letter(col_idx)
            if col_idx == 1:
                ws.column_dimensions[col_letter].width = 30
            elif col_idx in [2, 3, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20]:
                ws.column_dimensions[col_letter].width = 36
            elif col_idx in [5, 6, 7, 8, 9]:
                ws.column_dimensions[col_letter].width = 12
            else:
                ws.column_dimensions[col_letter].width = 24

        # Freeze Panes below My Work (row 5) and after Paper column (col A)
        ws.freeze_panes = "B6"

    # ─────────────────────────────────────────────────────────────────────────────
    # Gap Analysis Generators for Each Theme
    # ─────────────────────────────────────────────────────────────────────────────
    def gap_gen_sim(r):
        gap = f"Paper relies entirely on simulated/emulated environments without physical controller hardware. Susceptible to simulation artifacts, unrealistic zero-latency network assumptions, and lacks physical ARM processor execution dynamics."
        adv = f"Master-Honeypot eliminates this simulation gap by deploying the SoftPLC directly onto physical Raspberry Pi 4B hardware, capturing genuine network jitter (5.8ms RTT) and physical ODE dynamics."
        return gap, adv

    def gap_gen_hybrid(r):
        gap = f"While utilizing hybrid/HIL methods, this work is typically constrained to a single protocol ({r.get('Industrial protocols', 'Modbus')}), uses proprietary hardware testbeds, and does not evaluate embedded controller resource/thermal overhead."
        adv = f"Master-Honeypot expands beyond single-protocol limitations by combining Modbus TCP, OPC UA, S7, and DNP3 on low-cost ARM64 hardware with continuous thermal (44.3°C) and CPU benchmarking."
        return gap, adv

    def gap_gen_hard(r):
        gap = f"Hardware-only testbed has fixed physical components, lacks programmable continuous process dynamics, entails high hardware maintenance costs, and cannot safely simulate destructive overpressure/explosion scenarios."
        adv = f"Master-Honeypot achieves full cyber-physical fidelity at $50 hardware cost while safely simulating catastrophic overpressure conditions (>200 PSI) with automated safety trip interlocks."
        return gap, adv

    # ─────────────────────────────────────────────────────────────────────────────
    # Populate the 3 Theme Sheets
    # ─────────────────────────────────────────────────────────────────────────────
    ws_theme1 = wb_tgt.create_sheet(title="Theme 1 - Sim & Emul Only")
    populate_theme_sheet(ws_theme1, "Theme 1: Comparative Analysis with Simulation & Emulation Only Research", df_sim_only, my_work_data_sim, gap_gen_sim)

    ws_theme2 = wb_tgt.create_sheet(title="Theme 2 - Hybrid & HIL")
    populate_theme_sheet(ws_theme2, "Theme 2: Comparative Analysis with Hybrid & Hardware-in-the-Loop Research", df_hybrid, my_work_data_hybrid, gap_gen_hybrid)

    ws_theme3 = wb_tgt.create_sheet(title="Theme 3 - Hardware Only")
    populate_theme_sheet(ws_theme3, "Theme 3: Comparative Analysis with Hardware-Only & Physical Plant Research", df_hard_only, my_work_data_hard, gap_gen_hard)

    # 3. Save Target Workbook
    wb_tgt.save(TARGET_FILE)
    print(f"Successfully generated comparative Excel workbook at:\n{TARGET_FILE}")

if __name__ == "__main__":
    build_comparative_workbook()
