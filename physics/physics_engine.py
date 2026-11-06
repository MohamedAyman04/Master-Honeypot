import time
import random
import os
import json
import redis


class PipelineSimulator:
    """
    Saudi Aramco Reference Multi-Stage Refinery & Pipeline Physics Engine.
    ======================================================================
    Models a 4-Stage sequential petroleum refining process train:
      • Stage 1: Crude Receiving, Pre-Heating & Electrostatic Desalting
      • Stage 2: Atmospheric Distillation Unit (ADU) & Fractionation Column
      • Stage 3: Hydrodesulfurization (HDS) High-Pressure Catalytic Reactor
      • Stage 4: Finished Product In-Line Blending & Pipeline Custody Export

    Physical Continuity & Dynamic Constraints:
      - Mass Balance: Q_crude(t) = Q_naphtha(t) + Q_diesel(t) + Q_residue(t)
      - Upstream-to-Downstream Coupling: Stage N+1 feed depends strictly on Stage N output.
      - Closed Valve Constraint: If charge valve is closed (<=1%), crude flow collapses to 0,
        starving downstream stages, causing furnace coil over-temperature and HDS quench.
      - Backward Compatibility: Exposes canonical 'pressure', 'flow_rate', 'temperature',
        'pump_rpm', 'valve_pos' to maintain zero breaking changes with existing PLCs,
        Redis state store, ML engine, and Grafana panels.
    """

    def __init__(self, use_redis: bool = False):
        self.use_redis  = use_redis
        self.redis_host = os.environ.get("REDIS_HOST", "localhost")
        self.redis_port = int(os.environ.get("REDIS_PORT", 6379))
        self.r = None

        if self.use_redis:
            try:
                self.r = redis.Redis(
                    host=self.redis_host, port=self.redis_port,
                    db=0, decode_responses=True
                )
                print(f"[PHYSICS] Connected to Redis at {self.redis_host}:{self.redis_port}")
            except Exception as e:
                print(f"[PHYSICS] Redis connection error: {e}")
                self.use_redis = False

        # ── Stage 1: Crude Oil Ingestion & Electrostatic Desalter ─────────────
        self.pump_rpm          = 1200.0     # Charge pump RPM (Modbus Reg 0 / Reg 200)
        self.valve_pos         = 0.50       # Charge valve position 0.0-1.0 (Modbus Reg 201)
        self.crude_flow_rate   = 12.0       # L/s (feed to plant, nominal 12.0 L/s)
        self.desalter_pressure = 175.0      # PSI (nominal operating band 150-200 PSI)
        self.desalter_temp     = 125.0      # °C (preheat train temperature)
        self.salt_content_ptb  = 1.8        # Pounds Per Thousand Barrels (safe < 5 PTB)
        self.wash_water_ratio  = 5.0        # % vol wash water injection

        # ── Stage 2: Atmospheric Distillation Unit (ADU) ──────────────────────
        self.furnace_temp         = 365.0   # °C (target coil outlet temperature 360-370 °C)
        self.column_top_pressure  = 1.85    # bar (overhead receiver pressure)
        self.naphtha_cut_flow     = 3.36    # L/s (~28% vol yield)
        self.diesel_cut_flow      = 5.04    # L/s (~42% vol yield)
        self.residue_cut_flow     = 3.60    # L/s (~30% vol yield)
        self.column_bottom_level  = 55.0    # % column sump liquid level

        # ── Stage 3: Hydrodesulfurization (HDS) Catalytic Reactor ─────────────
        self.h2_compressor_rpm       = 1800.0  # Hydrogen recycle compressor RPM
        self.hds_reactor_pressure    = 830.0   # PSI (operating band 750-950 PSI)
        self.hds_bed_temp            = 355.0   # °C (exothermic catalytic bed)
        self.diesel_sulfur_ppm       = 8.2     # ppm (Ultra-Low Sulfur Diesel < 10 ppm)
        self.treated_diesel_flow     = 4.94    # L/s (~98% liquid yield from diesel cut)

        # ── Stage 4: Finished Product Blending & Pipeline Export ──────────────
        self.pressure                = 122.5   # PSI (Legacy canonical export pressure)
        self.flow_rate               = 12.0    # L/s (Legacy canonical custody flow)
        self.temperature             = 28.5    # °C (Legacy canonical export temp)
        self.viscosity               = 1.0     # Relative kinematic viscosity
        self.finished_diesel_cetane  = 52.5    # Cetane index (spec: > 51.0)
        self.tank_farm_inventory_bbl = 45200.0 # Cumulative tank storage barrels

        self.last_update = time.time()

        # Load state from Redis if a previous run's state exists
        if self.use_redis and self.r and self.r.exists("pipeline_state"):
            self.load_state()

        self._enforce_valve_constraint()

    # ── Physical consistency enforcement ──────────────────────────────────────
    def _enforce_valve_constraint(self) -> None:
        """If charge valve is closed, crude flow and downstream production collapse."""
        if self.valve_pos <= 0.01:
            self.valve_pos = 0.0
            self.crude_flow_rate = 0.0
            self.naphtha_cut_flow = 0.0
            self.diesel_cut_flow = 0.0
            self.residue_cut_flow = 0.0
            self.treated_diesel_flow = 0.0
            self.flow_rate = 0.0

    def set_pump_rpm(self, rpm: float) -> None:
        self.pump_rpm = max(0.0, min(float(rpm), 3000.0))
        self._enforce_valve_constraint()
        if self.use_redis:
            self.save_state()

    def set_valve_pos(self, pos: float) -> None:
        self.valve_pos = max(0.0, min(float(pos), 1.0))
        self._enforce_valve_constraint()
        if self.use_redis:
            self.save_state()

    def set_h2_compressor_rpm(self, rpm: float) -> None:
        self.h2_compressor_rpm = max(0.0, min(float(rpm), 3600.0))
        if self.use_redis:
            self.save_state()

    def update(self, dt: float = None) -> dict:
        if self.use_redis:
            self.load_state()

        now = time.time()
        if dt is None:
            dt = min(max(now - self.last_update, 0.1), 5.0)
        self.last_update = now

        # =====================================================================
        # STAGE 1: Crude Booster Pump & Electrostatic Desalter
        # =====================================================================
        # Target crude flow rate matches legacy: (RPM / 50.0) * valve_pos
        if self.valve_pos <= 0.01:
            target_crude_flow = 0.0
            self.crude_flow_rate = 0.0
        else:
            target_crude_flow = (self.pump_rpm / 50.0) * self.valve_pos

        rate_f = min(1.0, 0.45 * dt)
        self.crude_flow_rate += (target_crude_flow - self.crude_flow_rate) * rate_f
        if self.valve_pos <= 0.01:
            self.crude_flow_rate = 0.0

        # Desalter backpressure: builds as pump speeds up against valve restriction
        target_desalter_p = 135.0 + (self.pump_rpm / 25.0) * (1.2 - (self.valve_pos * 0.4))
        rate_p = min(1.0, 0.4 * dt)
        self.desalter_pressure += (target_desalter_p - self.desalter_pressure) * rate_p

        target_desalter_t = 120.0 + (self.pump_rpm / 120.0)
        self.desalter_temp += (target_desalter_t - self.desalter_temp) * min(1.0, 0.2 * dt)

        # Salt separation efficiency (requires pressure > 140 PSI and active flow)
        if self.desalter_pressure < 130.0 or self.crude_flow_rate < 1.0:
            target_salt = 24.5  # High salt carry-over (corrosion risk!)
        else:
            target_salt = 1.8 + max(0.0, (12.0 - self.crude_flow_rate) * 0.2)
        self.salt_content_ptb += (target_salt - self.salt_content_ptb) * min(1.0, 0.3 * dt)

        # =====================================================================
        # STAGE 2: Atmospheric Distillation Unit (ADU) & Fractionation Column
        # =====================================================================
        # Upstream coupling: Fluid absorbs furnace heat duty.
        # If crude feed drops below nominal (12 L/s), furnace temperature surges!
        target_furnace_t = 365.0 + (12.0 - self.crude_flow_rate) * 5.0
        self.furnace_temp += (target_furnace_t - self.furnace_temp) * min(1.0, 0.35 * dt)

        # Distillation column top pressure depends on vapor rate from feed
        target_col_p = 1.4 + (self.crude_flow_rate / 12.0) * 0.45
        self.column_top_pressure += (target_col_p - self.column_top_pressure) * min(1.0, 0.4 * dt)

        # Mass balance cut splits (Exact 100% mass conservation: 28% + 42% + 30% = 100%)
        target_naphtha = round(self.crude_flow_rate * 0.28, 4)
        target_diesel  = round(self.crude_flow_rate * 0.42, 4)
        target_residue = round(self.crude_flow_rate * 0.30, 4)

        self.naphtha_cut_flow = target_naphtha
        self.diesel_cut_flow  = target_diesel
        self.residue_cut_flow = target_residue

        target_col_level = 55.0 + (self.crude_flow_rate - 12.0) * 1.5
        self.column_bottom_level += (target_col_level - self.column_bottom_level) * min(1.0, 0.2 * dt)

        # =====================================================================
        # STAGE 3: Hydrodesulfurization (HDS) Catalytic Reactor
        # =====================================================================
        # Upstream coupling: HDS throughput is fed directly by Stage 2 diesel cut
        target_hds_p = 450.0 + (self.h2_compressor_rpm / 1800.0) * 380.0
        self.hds_reactor_pressure += (target_hds_p - self.hds_reactor_pressure) * min(1.0, 0.4 * dt)

        # Exothermic reaction: Bed temp rises with diesel throughput and H2 pressure
        target_bed_t = 330.0 + (self.diesel_cut_flow * 3.8) + (self.hds_reactor_pressure / 100.0) * 1.2
        self.hds_bed_temp += (target_bed_t - self.hds_bed_temp) * min(1.0, 0.35 * dt)

        # Sulfur catalytic conversion (requires adequate H2 pressure and bed temperature)
        if self.hds_reactor_pressure < 720.0 or self.hds_bed_temp < 330.0 or self.diesel_cut_flow < 0.5:
            target_sulfur = 145.0  # Desulfurization failure (off-spec sulfur!)
        else:
            target_sulfur = 8.2 + max(0.0, (self.diesel_cut_flow - 5.0) * 0.4)
        self.diesel_sulfur_ppm += (target_sulfur - self.diesel_sulfur_ppm) * min(1.0, 0.4 * dt)

        self.treated_diesel_flow = self.diesel_cut_flow * 0.98

        # =====================================================================
        # STAGE 4: In-Line Blending & Mainline Pipeline Custody Export
        # =====================================================================
        # Target pressure & flow match legacy pipeline baseline for zero breakage
        target_export_p = (self.pump_rpm / 10.0) * (1.5 - (self.valve_pos * 0.8))
        self.pressure += (target_export_p - self.pressure) * min(1.0, 0.4 * dt)

        target_export_flow = self.crude_flow_rate
        self.flow_rate = 0.0 if self.valve_pos <= 0.01 else target_export_flow

        # Thermodynamics & Viscosity
        temp_gain = (self.pump_rpm / 1000.0) * 0.5 * dt
        temp_loss = (self.flow_rate * 0.05) * dt + (self.temperature - 25.0) * 0.02 * dt
        self.temperature += temp_gain - temp_loss
        self.viscosity = max(0.2, 1.0 - (self.temperature - 25.0) * 0.02)

        # Finished product specification quality
        self.finished_diesel_cetane = 52.8 if self.diesel_sulfur_ppm < 15.0 else 44.2
        self.tank_farm_inventory_bbl += (self.flow_rate * 0.08) * dt

        self._enforce_valve_constraint()

        if self.use_redis:
            self.save_state()

        return self.get_state()

    def save_state(self) -> None:
        if not self.r:
            return
        self.r.set("pipeline_state", json.dumps(self.get_state()))

    def load_state(self) -> None:
        if not self.r:
            return
        data = self.r.get("pipeline_state")
        if data:
            state = json.loads(data)
            self.pump_rpm               = state.get("pump_rpm",               self.pump_rpm)
            self.valve_pos              = state.get("valve_pos",              self.valve_pos)
            self.pressure               = state.get("pressure",               self.pressure)
            self.flow_rate              = state.get("flow_rate",              self.flow_rate)
            self.temperature            = state.get("temperature",            self.temperature)
            self.viscosity              = state.get("viscosity",              self.viscosity)
            self.desalter_pressure      = state.get("stage1_desalter_pressure", self.desalter_pressure)
            self.crude_flow_rate        = state.get("stage1_crude_flow",      self.crude_flow_rate)
            self.furnace_temp           = state.get("stage2_furnace_temp",     self.furnace_temp)
            self.column_top_pressure    = state.get("stage2_column_pressure", self.column_top_pressure)
            self.hds_reactor_pressure   = state.get("stage3_reactor_pressure", self.hds_reactor_pressure)
            self.hds_bed_temp           = state.get("stage3_bed_temp",        self.hds_bed_temp)
            self.diesel_sulfur_ppm      = state.get("stage3_sulfur_ppm",      self.diesel_sulfur_ppm)

    def get_state(self) -> dict:
        flow = 0.0 if self.valve_pos <= 0.01 else max(0.0, self.flow_rate)
        return {
            # ── Canonical Legacy Keys (Guaranteed Backward Compatibility) ─────
            "pressure":    round(max(0.0, self.pressure),  2),
            "flow_rate":   round(flow,                      2),
            "temperature": round(self.temperature,          2),
            "viscosity":   round(self.viscosity,            2),
            "pump_rpm":    self.pump_rpm,
            "valve_pos":   self.valve_pos,

            # ── Stage 1: Crude Booster & Electrostatic Desalter ───────────────
            "stage1_desalter_pressure": round(self.desalter_pressure, 1),
            "stage1_crude_flow":        round(self.crude_flow_rate, 2),
            "stage1_desalter_temp":     round(self.desalter_temp, 1),
            "stage1_salt_content_ptb":  round(self.salt_content_ptb, 2),
            "stage1_wash_water_ratio":  self.wash_water_ratio,

            # ── Stage 2: Atmospheric Distillation Unit (ADU) ──────────────────
            "stage2_furnace_temp":      round(self.furnace_temp, 1),
            "stage2_column_pressure":   round(self.column_top_pressure, 2),
            "stage2_naphtha_flow":      round(self.naphtha_cut_flow, 2),
            "stage2_diesel_flow":       round(self.diesel_cut_flow, 2),
            "stage2_residue_flow":      round(self.residue_cut_flow, 2),
            "stage2_column_level":      round(self.column_bottom_level, 1),

            # ── Stage 3: Hydrodesulfurization (HDS) Catalytic Reactor ─────────
            "stage3_reactor_pressure":     round(self.hds_reactor_pressure, 1),
            "stage3_bed_temp":             round(self.hds_bed_temp, 1),
            "stage3_sulfur_ppm":           round(self.diesel_sulfur_ppm, 1),
            "stage3_h2_compressor_rpm":    self.h2_compressor_rpm,
            "stage3_treated_diesel_flow":  round(self.treated_diesel_flow, 2),

            # ── Stage 4: Finished Product Blending & Custody Export ───────────
            "stage4_export_pressure":      round(max(0.0, self.pressure), 2),
            "stage4_export_flow":          round(flow, 2),
            "stage4_diesel_cetane":        round(self.finished_diesel_cetane, 1),
            "stage4_tank_inventory_bbl":   round(self.tank_farm_inventory_bbl, 0),
        }
