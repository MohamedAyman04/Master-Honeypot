import pptx
from pptx.util import Pt
from pptx.dml.color import RGBColor

file_path = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Presentations/experimental_literature_review.pptx"
prs = pptx.Presentation(file_path)

def set_text(shape, text, font_name="Calibri", size_pt=None, bold=None, color_rgb=None):
    shape.text_frame.clear()
    p = shape.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = text
    if font_name:
        r.font.name = font_name
    if size_pt:
        r.font.size = Pt(size_pt)
    if bold is not None:
        r.font.bold = bold
    if color_rgb:
        r.font.color.rgb = color_rgb

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 1: TITLE SLIDE
# ─────────────────────────────────────────────────────────────────────────────
slide1 = prs.slides[0]
set_text(slide1.shapes[0], "EXPERIMENTAL FOUNDATIONS", size_pt=11, bold=True, color_rgb=RGBColor(0, 0x33, 0x66))
set_text(slide1.shapes[1], "Experimental Architectures &\nMethodologies of Five Physical\nIndustrial Testbeds", size_pt=32, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide1.shapes[2], "Physical Schneider, Siemens, Allen-Bradley, and BACnet industrial controllers validated on real water, power, and building processes", size_pt=14, color_rgb=RGBColor(0x44, 0x44, 0x44))
set_text(slide1.shapes[4], "WonderICS Water Rig (Schneider M580)  ·  Thermal Power HIL (Schneider M580)  ·  EnCyCris Substation (Siemens Relays)  ·  TAMU BAS Lab (Chillers)  ·  Marine PMS (Allen-Bradley)", size_pt=10, bold=True, color_rgb=RGBColor(0x22, 0x22, 0x22))

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 2: WonderICS & G-ICS Water Circulation Rig (Schneider M580 / M340)
# ─────────────────────────────────────────────────────────────────────────────
slide2 = prs.slides[1]
set_text(slide2.shapes[0], "SOURCE 01  ·  PHYSICAL WATER & CHEMICAL TESTBED (G-ICS / WONDERICS)", size_pt=10, bold=True, color_rgb=RGBColor(0x78, 0x28, 0x1F))
set_text(slide2.shapes[1], "Schneider Modicon M580 & M340 PLCs with Physical Water Loops", size_pt=20, bold=True, color_rgb=RGBColor(0, 0, 0))

# Component 1
set_text(slide2.shapes[5], "Industrial PLC controllers", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide2.shapes[6], "Physical Schneider Modicon M580 & M340 PLCs running Schneider Unity Pro / Control Expert", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 2
set_text(slide2.shapes[8], "Physical process plant", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide2.shapes[9], "Real physical water circulation loop with motorized pumps, physical tanks, flowmeters, and chemical dosing", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 3
set_text(slide2.shapes[11], "SCADA & Hardware TAP", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide2.shapes[12], "PcVue industrial SCADA server, OPNsense boundary firewalls, and custom 8-channel analog I/O interface boards", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Methodology
set_text(slide2.shapes[15], "Evaluates physical-in-the-loop cyber-attacks by executing live Modbus/TCP register manipulation, unauthorized logic injection, and hardware-level Man-in-the-Middle (MITM) attacks using malicious physical interface taps on running water loops.", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Results
set_text(slide2.shapes[18], "100%", size_pt=28, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide2.shapes[19], "Physical breaker trips and hydraulic overflow conditions captured under live attack. Proves that attackers manipulating PLC setpoints directly disrupt physical water levels; provides the direct empirical justification for our testbed's closed-loop hydraulic safety interlocks.", size_pt=10.5, color_rgb=RGBColor(0x22, 0x22, 0x22))

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 3: Thermal Power Plant HIL (Schneider M580)
# ─────────────────────────────────────────────────────────────────────────────
slide3 = prs.slides[2]
set_text(slide3.shapes[0], "SOURCE 02  ·  THERMAL POWER GENERATION HIL TESTBED", size_pt=10, bold=True, color_rgb=RGBColor(0x78, 0x28, 0x1F))
set_text(slide3.shapes[1], "Schneider Modicon M580 Closed-Loop PID Steam Control", size_pt=20, bold=True, color_rgb=RGBColor(0, 0, 0))

# Component 1
set_text(slide3.shapes[5], "Physical controller", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide3.shapes[6], "Physical Schneider Electric Modicon M580 PLC executing real-time closed-loop PID control algorithms", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 2
set_text(slide3.shapes[8], "Thermal process plant", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide3.shapes[9], "Industrial-grade thermal power generation plant with 22 physical sensors, 5 controllers, and 15 physical actuators", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 3
set_text(slide3.shapes[11], "SCADA environment", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide3.shapes[12], "CITECT SCADA software, dedicated Operator Workstations (OWS), and Engineering Workstations (EWS)", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Methodology
set_text(slide3.shapes[15], "Performs process-aware STRIDE threat modeling and injects live Modbus/TCP packet tampering, setpoint alteration, and Stuxnet-style sensor value replay directly targeting the physical M580 PLC's PID control loop.", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Results
set_text(slide3.shapes[18], "Quantified exact process variable deviations, response delays, and controller destabilization during physical attacks. Demonstrates that physical PLCs blindly trust corrupted fieldbus registers, motivating our dynamic deception engine to present authentic physical state evolution.", size_pt=11, color_rgb=RGBColor(0x22, 0x22, 0x22))

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 4: EnCyCris Substation (Siemens SICAM & SIPROTEC 5)
# ─────────────────────────────────────────────────────────────────────────────
slide4 = prs.slides[3]
set_text(slide4.shapes[0], "SOURCE 03  ·  ENCYCRIS DIGITAL ENERGY SUBSTATION TESTBED", size_pt=10, bold=True, color_rgb=RGBColor(0x78, 0x28, 0x1F))
set_text(slide4.shapes[1], "Physical Siemens SIPROTEC 5 Relays & SICAM A8000 Gateways", size_pt=20, bold=True, color_rgb=RGBColor(0, 0, 0))

# Component 1
set_text(slide4.shapes[5], "Physical IED protection", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide4.shapes[6], "Physical Siemens SIPROTEC 5 (7VK87/7SA87) protection relays and Siemens SICAM A8000 gateway", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 2
set_text(slide4.shapes[8], "Substation bus layer", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide4.shapes[9], "High-voltage Process Bus and Station Bus executing IEC 61850 GOOSE and Sampled Values (SV)", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 3
set_text(slide4.shapes[11], "Test & injection hardware", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide4.shapes[12], "Omicron CMC precision test equipment, PTP grandmaster clocks, and Siemens SICAM SCC HMI", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Methodology
set_text(slide4.shapes[15], "Implements a full physical-virtual substation enclave. Injects Sampled Values (SV) spoofing, GOOSE message injection, and PTP time synchronization attacks via Omicron CMC hardware to measure physical protection trip times.", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Results
set_text(slide4.shapes[18], "Sub-millisecond GOOSE transmission and microsecond fault isolation validated on physical Siemens relays. Demonstrates the extreme sensitivity of physical grid relays to network delay and packet injection, directly informing our multi-protocol edge latency benchmarks.", size_pt=11, color_rgb=RGBColor(0x22, 0x22, 0x22))

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 5: Texas A&M BACnet BAS Lab (Physical Chillers/Boilers)
# ─────────────────────────────────────────────────────────────────────────────
slide5 = prs.slides[4]
set_text(slide5.shapes[0], "SOURCE 04  ·  TEXAS A&M BAS LAB HIL TESTBED", size_pt=10, bold=True, color_rgb=RGBColor(0x78, 0x28, 0x1F))
set_text(slide5.shapes[1], "Physical BACnet DDC Controllers Wired to Industrial Chillers", size_pt=20, bold=True, color_rgb=RGBColor(0, 0, 0))

# Component 1
set_text(slide5.shapes[5], "Physical DDC controllers", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide5.shapes[6], "Real commercial building controllers (chillers, air handling units, VAV boxes) on ARCNET daisy-chain", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 2
set_text(slide5.shapes[8], "Physical HVAC plant", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide5.shapes[9], "Real multi-zone physical water chillers, steam boilers, and air distribution systems at TAMU Energy Lab", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 3 (Shape 18 & 19)
set_text(slide5.shapes[18], "Supervisory management", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide5.shapes[19], "Central BACnet/IP BAS supervisory server, ControlDesk interface, and multi-protocol IP routers", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Methodology (Shape 12)
set_text(slide5.shapes[12], "Conducts physical cyber-attack experiments on live building equipment, injecting BACnet device reinitialization, rogue master setpoint overwrites, and volumetric flow throttling while logging physical thermodynamic response.", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Results (Shape 15)
set_text(slide5.shapes[15], "Documented physical temperature drift and mechanical actuator strain under protocol exploits. Proves that fieldbus manipulation directly degrades mechanical plant health, directly validating our thesis's hydraulic valve throttling and temperature modeling.", size_pt=11, color_rgb=RGBColor(0x22, 0x22, 0x22))

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 6: Marine Power Management System (Allen-Bradley & KTE)
# ─────────────────────────────────────────────────────────────────────────────
slide6 = prs.slides[5]
set_text(slide6.shapes[0], "SOURCE 05  ·  MARINE POWER MANAGEMENT SYSTEM (PMS) HILS", size_pt=10, bold=True, color_rgb=RGBColor(0x78, 0x28, 0x1F))
set_text(slide6.shapes[1], "Physical Allen-Bradley PLC & Main Switchboard (MSBD)", size_pt=20, bold=True, color_rgb=RGBColor(0, 0, 0))

# Component 1
set_text(slide6.shapes[5], "Physical PLC hardware", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide6.shapes[6], "Real physical Allen-Bradley industrial PLC and physical KTE PMS2500 controller", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 2
set_text(slide6.shapes[8], "Physical switchboard", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide6.shapes[9], "Full-scale physical Main Switchboard (MSBD) with physical generator circuit breakers and 4-20mA I/O", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Component 3 (Shape 19 & 20)
set_text(slide6.shapes[19], "Supervisory console", size_pt=12.5, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide6.shapes[20], "Simulation Control Console (SCC) with HTML5-based HMI and Modbus TCP/OPC communication link", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Methodology (Shape 12)
set_text(slide6.shapes[12], "Validates closed-loop hardware-in-the-loop stability under severe physical fault injection, including generator blackout, preferential load tripping, and governor frequency desynchronization.", size_pt=11, color_rgb=RGBColor(0x3A, 0x3A, 0x3A))

# Results (Shape 15 & 16)
set_text(slide6.shapes[15], "100 µs", size_pt=28, bold=True, color_rgb=RGBColor(0, 0, 0))
set_text(slide6.shapes[16], "PMS cyclic execution verified at 100 µs determinism on physical Allen-Bradley hardware. Confirms that physical controllers require strict deterministic scan execution, motivating our CODESYS SoftPLC 100ms deterministic scan cycle.", size_pt=10.5, color_rgb=RGBColor(0x22, 0x22, 0x22))

prs.save(file_path)
print("Successfully updated experimental_literature_review.pptx with real PLC testbeds!")
