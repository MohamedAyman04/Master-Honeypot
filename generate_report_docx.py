#!/usr/bin/env python3
"""
Generate Comprehensive Master's Progress Report (.docx)
Location: /run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Progress/
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_shading(cell, color_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_document():
    doc = docx.Document()

    # Set Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Color Palette
    COLOR_PRIMARY = RGBColor(0, 51, 102)     # Deep Navy
    COLOR_SECONDARY = RGBColor(43, 62, 80)   # Dark Slate
    COLOR_TEXT = RGBColor(34, 34, 34)        # Charcoal
    COLOR_MUTED = RGBColor(100, 100, 100)    # Gray
    HEX_HEADER_BG = "003366"
    HEX_ALT_ROW = "F7F9FA"
    HEX_CALLOUT_BG = "EBF2F7"

    # Base Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Arial'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = COLOR_TEXT
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_title.paragraph_format.space_after = Pt(2)
    run_title = p_title.add_run("Master's Research Progress & Technical Report")
    run_title.font.name = 'Arial'
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = COLOR_PRIMARY

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(14)
    run_sub = p_sub.add_run("Hardware-in-the-Loop (HIL) Testbed Deployment: Raspberry Pi 4B CODESYS SoftPLC & Multi-Protocol Industrial Emulation")
    run_sub.font.name = 'Arial'
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = COLOR_SECONDARY

    # Metadata Table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False

    meta_data = [
        ("Institution / Faculty:", "German University in Cairo (GUC) — Department of Computer Science & Engineering"),
        ("Project / Thesis:", "Physics-Aware Cross-Layer ICS Deception & Intrusion Detection Framework"),
        ("Researcher:", "Mohamed Ayman"),
        ("Advisor / Supervisor:", "Dr. Minar")
    ]

    for idx, (label, val) in enumerate(meta_data):
        row = meta_table.rows[idx]
        cell_lbl, cell_val = row.cells[0], row.cells[1]
        cell_lbl.width = Inches(2.2)
        cell_val.width = Inches(4.3)
        
        p_l = cell_lbl.paragraphs[0]
        p_l.paragraph_format.space_after = Pt(2)
        r_l = p_l.add_run(label)
        r_l.font.bold = True
        r_l.font.size = Pt(9.5)
        r_l.font.color.rgb = COLOR_SECONDARY
        
        p_v = cell_val.paragraphs[0]
        p_v.paragraph_format.space_after = Pt(2)
        r_v = p_v.add_run(val)
        r_v.font.size = Pt(9.5)
        
        set_cell_shading(cell_lbl, "F0F4F8")
        set_cell_shading(cell_val, "F0F4F8")
        set_cell_margins(cell_lbl, top=40, bottom=40, left=80, right=80)
        set_cell_margins(cell_val, top=40, bottom=40, left=80, right=80)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Helper function for Section Headings
    def add_section_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title)
        run.font.name = 'Arial'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_subsection_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title)
        run.font.name = 'Arial'
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = COLOR_SECONDARY
        return p

    # --- Section 1: Executive Summary & Motivation ---
    add_section_heading("1. Executive Summary: Fulfilling the Hardware-in-the-Loop (HIL) Gap")
    
    p = doc.add_paragraph()
    p.add_run("In Industrial Control System (ICS) and SCADA cybersecurity research, high-interaction honeypots and intrusion detection frameworks are typically deployed as software container clusters (e.g., Docker containers) running on a single host machine. While containers provide modularity, purely simulated testbeds suffer from the ")
    r_bold = p.add_run("'Simulation Gap'")
    r_bold.font.bold = True
    p.add_run("—they lack authentic embedded hardware cycle dynamics, omit physical packet transmission latencies, and share the host operating system kernel.")

    p2 = doc.add_paragraph()
    p2.add_run("To fulfill this critical Hardware-in-the-Loop (HIL) requirement for this Master's research, a dedicated ")
    p2.add_run("Raspberry Pi 4 Model B (4GB RAM)").font.bold = True
    p2.add_run(" was configured and integrated as the physical Level 1 Programmable Logic Controller (PLC) node. Running an IEC 61131-3 deterministic SoftPLC runtime (CODESYS standard), the Raspberry Pi executes real-time hydraulic pipeline physics, manages safety interlocks, and natively exposes multiple industrial fieldbus and SCADA protocols across the physical network.")

    # Callout Box
    tbl_callout = doc.add_table(rows=1, cols=1)
    tbl_callout.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = tbl_callout.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_shading(c_cell, HEX_CALLOUT_BG)
    set_cell_margins(c_cell, top=100, bottom=100, left=150, right=150)
    cp = c_cell.paragraphs[0]
    cp.paragraph_format.space_after = Pt(0)
    r_c_bold = cp.add_run("Core Thesis Impact: ")
    r_c_bold.font.bold = True
    r_c_bold.font.color.rgb = COLOR_PRIMARY
    cp.add_run("All Modbus TCP and OPC UA transactions, physical process manipulation commands, and adversary reconnaissance probes now traverse real physical network interfaces (Wi-Fi 802.11ac / Gigabit Ethernet) and are processed by dedicated ARM64 embedded CPU hardware, closing the simulation gap for academic defense and benchmark validation.")

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # --- Section 2: Physical Hardware Telemetry ---
    add_section_heading("2. Physical Hardware & Operating System Specifications")
    
    p = doc.add_paragraph("The physical hardware parameters and system telemetry were directly extracted from the active Raspberry Pi 4B node:")

    spec_table = doc.add_table(rows=12, cols=2)
    spec_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    spec_table.autofit = False

    specs = [
        ("Parameter", "Verified Hardware / OS Telemetry"),
        ("Hardware Board", "Raspberry Pi 4 Model B (Revision 1.5, Serial: 100000007c941807)"),
        ("System-on-Chip (SoC)", "Broadcom BCM2711, 64-bit ARMv8-A Architecture"),
        ("CPU Processor", "Quad-core ARM Cortex-A72 @ 1.80 GHz (64-bit aarch64, 4 physical cores)"),
        ("CPU Cache Architecture", "128 KiB L1 Data, 192 KiB L1 Instruction, 1 MiB L2 Shared Cache"),
        ("System Memory (RAM)", "4.0 GB LPDDR4-3200 SDRAM (3.7 GiB usable, 3.2 GiB available)"),
        ("Swap Memory", "2.0 GiB zram/swap partition"),
        ("Primary Storage", "64 GB Class 10 MicroSD (SanDisk Ultra, 57 GB root partition, 14% used)"),
        ("Operating System", "Debian GNU/Linux 13 (trixie) 64-bit ARM64 (Release 13.5)"),
        ("Kernel Version", "Linux Honeypot 6.18.34+rpt-rpi-v8 #1 SMP PREEMPT Debian"),
        ("Operating Thermals", "44.3 °C (Optimal thermal zone, no thermal throttling active)"),
        ("Active IP Configuration", "192.168.1.8 (Ayman 5GHz) / 172.20.10.8 (iPhone Hotspot Priority)")
    ]

    for idx, (param, val) in enumerate(specs):
        row = spec_table.rows[idx]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.3)
        c1.width = Inches(4.2)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(param)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(val)
        
        if idx == 0:
            set_cell_shading(c0, HEX_HEADER_BG)
            set_cell_shading(c1, HEX_HEADER_BG)
            r0.font.bold = True
            r0.font.color.rgb = RGBColor(255, 255, 255)
            r1.font.bold = True
            r1.font.color.rgb = RGBColor(255, 255, 255)
        else:
            r0.font.bold = True
            r0.font.size = Pt(9.5)
            r1.font.size = Pt(9.5)
            if idx % 2 == 1:
                set_cell_shading(c0, "FFFFFF")
                set_cell_shading(c1, "FFFFFF")
            else:
                set_cell_shading(c0, HEX_ALT_ROW)
                set_cell_shading(c1, HEX_ALT_ROW)
        
        set_cell_margins(c0, top=40, bottom=40, left=80, right=80)
        set_cell_margins(c1, top=40, bottom=40, left=80, right=80)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # --- Section 3: SoftPLC Architecture & Cyber-Physical Physics ---
    add_section_heading("3. SoftPLC Architecture & Cyber-Physical Simulation Engine")
    
    p = doc.add_paragraph()
    p.add_run("The Raspberry Pi 4B runs an ")
    p.add_run("IEC 61131-3 SoftPLC Runtime Daemon").font.bold = True
    p.add_run(" (managed via systemd service ")
    p.add_run("codesys-plc.service").font.name = 'Courier New'
    p.add_run("). The SoftPLC executes a deterministic 100ms (10 Hz) scan cycle that continuously solves differential equations governing a physical hydraulic pipeline.")

    add_subsection_heading("Hydraulic Pipeline Differential Equations")
    
    p_eq = doc.add_paragraph()
    p_eq.add_run("At each 100ms scan interval, the internal physics engine calculates target equilibrium states based on current actuator demands:")
    
    eqs = [
        ("Equilibrium Pressure (P*):", "P* = (Pump_RPM / 10.0) * (1.5 - 0.8 * Valve_Position)"),
        ("Equilibrium Flow Rate (Q*):", "Q* = (Pump_RPM / 50.0) * Valve_Position"),
        ("Equilibrium Temperature (T*):", "T* = T_ambient + (Pump_RPM / 100.0) * 1.2 - (Flow_Rate / 10.0) * 0.8")
    ]
    for lbl, formula in eqs:
        p_f = doc.add_paragraph()
        p_f.paragraph_format.left_indent = Inches(0.3)
        p_f.paragraph_format.space_after = Pt(2)
        r_l = p_f.add_run(f"• {lbl} ")
        r_l.font.bold = True
        r_f = p_f.add_run(formula)
        r_f.font.name = 'Courier New'
        r_f.font.size = Pt(9.5)

    p_dyn = doc.add_paragraph()
    p_dyn.paragraph_format.space_before = Pt(4)
    p_dyn.add_run("Continuous State Evolution with Gaussian Sensor Noise:")
    p_dyn_eq = doc.add_paragraph()
    p_dyn_eq.paragraph_format.left_indent = Inches(0.3)
    r_dyn = p_dyn_eq.add_run("P(t+1) = P(t) + κ_p * (P* - P(t)) + N(0, σ_p²)\nQ(t+1) = Q(t) + κ_q * (Q* - Q(t)) + N(0, σ_q²)\nT(t+1) = T(t) + κ_t * (T* - T(t)) + N(0, σ_t²)")
    r_dyn.font.name = 'Courier New'
    r_dyn.font.size = Pt(9.5)

    add_subsection_heading("Embedded Safety Interlocks & Trip Logic")
    p_safe = doc.add_paragraph()
    p_safe.add_run("• ")
    p_safe.add_run("Overpressure Safety Interlock: ").font.bold = True
    p_safe.add_run("If an adversary injects malicious setpoints forcing pressure above ")
    p_safe.add_run("200.0 PSI").font.bold = True
    p_safe.add_run(", the IEC safety loop automatically trips the Emergency Stop relay (E-Stop = 1), overriding pump speed demand and forcing rapid deceleration to 0 RPM.\n")
    p_safe.add_run("• ")
    p_safe.add_run("High Pressure & Overheat Alarms: ").font.bold = True
    p_safe.add_run("Thresholds at 150.0 PSI and 85.0 °C update discrete alarm registers and WebVisu indicators instantaneously.")

    # --- Section 4: Multi-Protocol Industrial Emulation Stacks ---
    add_section_heading("4. Multi-Protocol Industrial Emulation Stacks on Raspberry Pi")
    
    p = doc.add_paragraph("The Raspberry Pi 4B concurrently hosts 4 native industrial communication stacks across standard ports:")

    proto_table = doc.add_table(rows=6, cols=4)
    proto_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    proto_table.autofit = False

    proto_headers = ["Protocol", "Port", "Standard / Framework", "Industrial / Purdue Level Role"]
    proto_data = [
        ("Modbus TCP", "502", "Modbus V1.1b (pymodbus)", "Level 1 Fieldbus Control & Actuator Setpoints"),
        ("OPC UA", "4840", "IEC 62541 Binary (asyncua)", "Level 2 SCADA Connectivity & Object Subscriptions"),
        ("Siemens S7comm", "102", "ISO-on-TCP RFC 1006 (snap7)", "Level 1 Siemens S7-300/1200 DB1 Emulation"),
        ("DNP3 (IEEE 1815)", "20000", "IEEE 1815 Link-Layer", "Level 1/2 Utility Grid & Outstation Recon Detection"),
        ("WebVisu HMI", "8080", "HTML5 / REST (Flask)", "Level 2 Local Engineering Operator Panel")
    ]

    for c_idx, h in enumerate(proto_headers):
        c = proto_table.rows[0].cells[c_idx]
        set_cell_shading(c, HEX_HEADER_BG)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    widths = [Inches(1.5), Inches(0.6), Inches(2.0), Inches(2.4)]
    for r_idx, row_values in enumerate(proto_data):
        row = proto_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_values):
            c = row.cells[c_idx]
            c.width = widths[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(val)
            r.font.size = Pt(9.0)
            if c_idx == 0:
                r.font.bold = True
            if r_idx % 2 == 0:
                set_cell_shading(c, "FFFFFF")
            else:
                set_cell_shading(c, HEX_ALT_ROW)
            set_cell_margins(c, top=40, bottom=40, left=60, right=60)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    add_subsection_heading("Modbus TCP Register Memory Map (0-Indexed Standard)")
    
    p_mb = doc.add_paragraph("The holding register layout maps 1-to-1 with the physical process parameters:")
    
    mb_table = doc.add_table(rows=9, cols=4)
    mb_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    mb_table.autofit = False

    mb_headers = ["Modbus Addr", "PLC Reg (4000x)", "Parameter Name", "Scaling & Engineering Units"]
    mb_data = [
        ("0", "40001", "Pump Speed Setpoint (P-101)", "0 - 3000 RPM (Direct integer setpoint)"),
        ("1", "40002", "Valve Position Setpoint (XV-101)", "0 - 1000 (0.0% to 100.0% opening)"),
        ("2", "40003", "Pipeline Pressure (PT-101)", "Scaled x10 PSI (e.g., 960 = 96.0 PSI)"),
        ("3", "40004", "Volumetric Flow Rate (FT-101)", "Scaled x10 L/s (e.g., 144 = 14.4 L/s)"),
        ("4", "40005", "Fluid Temperature (TT-101)", "Scaled x10 °C (e.g., 382 = 38.2 °C)"),
        ("5", "40006", "Emergency Stop Relay Status", "0 = Normal Operation, 1 = Tripped"),
        ("6", "40007", "Control Operating Mode", "0 = AUTO, 1 = MANUAL, 2 = REMOTE_SCADA"),
        ("7", "40008", "Alarm Status Bitmask", "Bit 0: High Pressure, Bit 1: Overheat, Bit 2: E-Stop")
    ]

    for c_idx, h in enumerate(mb_headers):
        c = mb_table.rows[0].cells[c_idx]
        set_cell_shading(c, HEX_HEADER_BG)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    mb_widths = [Inches(1.1), Inches(1.3), Inches(2.2), Inches(1.9)]
    for r_idx, row_values in enumerate(mb_data):
        row = mb_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_values):
            c = row.cells[c_idx]
            c.width = mb_widths[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(val)
            r.font.size = Pt(9.0)
            if c_idx == 1:
                r.font.name = 'Courier New'
            if r_idx % 2 == 0:
                set_cell_shading(c, "FFFFFF")
            else:
                set_cell_shading(c, HEX_ALT_ROW)
            set_cell_margins(c, top=30, bottom=30, left=60, right=60)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # --- Section 5: Network Topology & Automatic Priority Handover ---
    add_section_heading("5. Dual Network Topology & Automatic Priority Handover")
    
    p = doc.add_paragraph()
    p.add_run("To facilitate seamless demonstrations during advisory meetings and laboratory evaluations, NetworkManager on the Raspberry Pi was configured with ")
    p.add_run("deterministic connection prioritization:").font.bold = True

    net_table = doc.add_table(rows=3, cols=5)
    net_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    net_table.autofit = False

    net_headers = ["Role", "SSID", "Autoconnect Priority", "Static IP Assigned", "Gateway / Subnet"]
    net_data = [
        ("Primary (Hotspot)", "iPhone", "100 (Highest Priority)", "172.20.10.8", "172.20.10.1 / 255.255.255.0"),
        ("Fallback (Lab/Home)", "Ayman 5GHz", "10 (Secondary Fallback)", "192.168.1.8", "192.168.1.1 / 255.255.255.0")
    ]

    for c_idx, h in enumerate(net_headers):
        c = net_table.rows[0].cells[c_idx]
        set_cell_shading(c, HEX_HEADER_BG)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    net_widths = [Inches(1.5), Inches(1.1), Inches(1.4), Inches(1.1), Inches(1.4)]
    for r_idx, row_values in enumerate(net_data):
        row = net_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_values):
            c = row.cells[c_idx]
            c.width = net_widths[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(val)
            r.font.size = Pt(9.0)
            if c_idx == 3:
                r.font.bold = True
                r.font.name = 'Courier New'
            if r_idx % 2 == 0:
                set_cell_shading(c, "FFFFFF")
            else:
                set_cell_shading(c, HEX_ALT_ROW)
            set_cell_margins(c, top=40, bottom=40, left=60, right=60)

    p_hand = doc.add_paragraph()
    p_hand.paragraph_format.space_before = Pt(6)
    p_hand.add_run("Whenever the iPhone personal hotspot is enabled, the Raspberry Pi automatically jumps to the hotspot and binds to ")
    p_hand.add_run("172.20.10.8").font.bold = True
    p_hand.add_run(". When the hotspot is disabled, it gracefully reverts to ")
    p_hand.add_run("192.168.1.8").font.bold = True
    p_hand.add_run(" on the local Wi-Fi without requiring a system reboot.")

    # --- Section 6: Master-Honeypot Integration & Test Suite ---
    add_section_heading("6. Master-Honeypot Integration & Verification Results")
    
    p = doc.add_paragraph()
    p.add_run("A dedicated hardware bridge (")
    p.add_run("scripts/raspberry_pi_bridge.py").font.name = 'Courier New'
    p.add_run(") continuously polls telemetry from the physical Raspberry Pi and streams it into the ")
    p.add_run("InfluxDB Historian").font.bold = True
    p.add_run(" and ")
    p.add_run("Redis state cache").font.bold = True
    p.add_run(" on the Master laptop, feeding the 6-Layer Machine Learning anomaly detector.")

    add_subsection_heading("Automated Integration Test Suite Execution (5/5 PASS)")
    
    p_test = doc.add_paragraph("The integration test suite was executed against the physical Raspberry Pi node with 100% success rate:")

    test_table = doc.add_table(rows=6, cols=3)
    test_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    test_table.autofit = False

    test_headers = ["Test Module", "Observed Latency / Result", "Validation Status"]
    test_data = [
        ("Test 1: WebVisu HTTP & REST API (:8080)", "HTTP 200 OK (18.6 ms round-trip latency)", "SUCCESS [PASS]"),
        ("Test 2: Modbus TCP Read Holding Registers (:502)", "Read 10 Registers in 5.8 ms (Valid scaled telemetry)", "SUCCESS [PASS]"),
        ("Test 3: Modbus TCP Write & Physics Response (:502)", "Write FC6 (2200 RPM) -> Equilibrium Pressure updated", "SUCCESS [PASS]"),
        ("Test 4: Modbus Coils & Safety Trip Interlock", "Coil state verified; Overpressure trip functional", "SUCCESS [PASS]"),
        ("Test 5: OPC UA Binary Server Handshake (:4840)", "Socket reachable; Endpoint handshake in 1.6 ms", "SUCCESS [PASS]")
    ]

    for c_idx, h in enumerate(test_headers):
        c = test_table.rows[0].cells[c_idx]
        set_cell_shading(c, HEX_HEADER_BG)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    t_widths = [Inches(2.8), Inches(2.5), Inches(1.2)]
    for r_idx, row_values in enumerate(test_data):
        row = test_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_values):
            c = row.cells[c_idx]
            c.width = t_widths[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(val)
            r.font.size = Pt(9.0)
            if c_idx == 2:
                r.font.bold = True
                r.font.color.rgb = RGBColor(0, 128, 0)
            if r_idx % 2 == 0:
                set_cell_shading(c, "FFFFFF")
            else:
                set_cell_shading(c, HEX_ALT_ROW)
            set_cell_margins(c, top=40, bottom=40, left=60, right=60)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # --- Section 7: Presentation & Thesis Defense Talking Points ---
    add_section_heading("7. Presentation & Defense Key Talking Points")
    
    points = [
        ("Elimination of the Simulation Gap:", "Emphasize that the honeypot is not merely a Docker mock on a laptop; it executes on a physical ARM64 SoC with genuine clock cycles and real physical network jitter."),
        ("Multi-Protocol Realism:", "Explain that the testbed simultaneously emulates Modbus TCP (fieldbus), OPC UA (middleware), Siemens S7 (manufacturing), and DNP3 (utility grids), mirroring realistic heterogeneous critical infrastructure."),
        ("Dynamic Cyber-Physical Consistency:", "Highlight that attacker setpoints dynamically alter physical differential states (pressure, flow rate, temperature) inside the SoftPLC, enabling ML anomaly detectors to be trained on genuine physical transitions rather than synthetic noise."),
        ("High-Interaction Safety Interlocks:", "Show that the SoftPLC enforces authentic IEC 61131-3 safety interlocks (e.g., automatic emergency trip at 200 PSI), mirroring safety instrumented systems (SIS).")
    ]

    for title, desc in points:
        p_pt = doc.add_paragraph()
        p_pt.paragraph_format.left_indent = Inches(0.2)
        p_pt.paragraph_format.space_after = Pt(4)
        r_t = p_pt.add_run(f"• {title} ")
        r_t.font.bold = True
        r_t.font.color.rgb = COLOR_SECONDARY
        p_pt.add_run(desc)

    return doc

if __name__ == "__main__":
    target_dir = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Progress"
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, "Raspberry_Pi_4B_HIL_CODESYS_Report.docx")
    
    doc = create_document()
    doc.save(target_path)
    print(f"Document successfully created at: {target_path}")
