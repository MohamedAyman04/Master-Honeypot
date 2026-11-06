#!/usr/bin/env python3
"""
Comprehensive Test Suite for 4-Stage Saudi Aramco Reference Refinery Physics Pipeline
====================================================================================
Tests:
  1. Nominal Steady-State & Mass Conservation (Q_crude = Q_naphtha + Q_diesel + Q_residue)
  2. Valve Safety Constraint (Closed valve -> instantaneous flow collapse across all stages)
  3. Upstream Starvation & Furnace Thermal Surge (Feed loss -> Furnace coil over-temp)
  4. Modbus FC6 Setpoint Over-Speed Surge (1200 RPM -> 2400 RPM pressure spike)
  5. Catalytic Hydrotreating (HDS) Failure & Sulfur Off-Spec Degradation
  6. Backward Compatibility for Legacy SCADA / PLC / ML interfaces
"""

import sys
import os
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.physics_engine import PipelineSimulator


class TestRefineryPhysicsPipeline(unittest.TestCase):
    def setUp(self):
        # Create fresh simulator instance in standalone mode (no external redis required for unit tests)
        self.sim = PipelineSimulator(use_redis=False)
        self.sim.set_pump_rpm(1200)
        self.sim.set_valve_pos(0.5)

    def test_01_nominal_steady_state_and_backward_compatibility(self):
        """Test steady-state convergence and legacy key compatibility."""
        print("\n[TEST 1] Nominal Steady-State & Backward Compatibility...")
        for _ in range(10):
            state = self.sim.update(dt=1.0)

        # Legacy Keys (Ensures zero breakage in existing PLCs and dashboards)
        for key in ["pressure", "flow_rate", "temperature", "pump_rpm", "valve_pos", "viscosity"]:
            self.assertIn(key, state, f"Missing legacy key: {key}")

        self.assertAlmostEqual(state["pump_rpm"], 1200.0, delta=1.0)
        self.assertAlmostEqual(state["valve_pos"], 0.50, delta=0.01)
        self.assertGreater(state["pressure"], 115.0)
        self.assertLess(state["pressure"], 135.0)
        self.assertAlmostEqual(state["flow_rate"], 12.0, delta=1.5)

        # Stage 1 Checks
        self.assertGreater(state["stage1_desalter_pressure"], 160.0)
        self.assertLess(state["stage1_salt_content_ptb"], 4.0, "Salt should be within safe spec (< 5 PTB)")

        # Stage 2 Checks
        self.assertAlmostEqual(state["stage2_furnace_temp"], 365.0, delta=5.0)
        self.assertGreater(state["stage2_column_pressure"], 1.5)

        # Stage 3 Checks
        self.assertGreater(state["stage3_reactor_pressure"], 800.0)
        self.assertLess(state["stage3_sulfur_ppm"], 10.0, "ULSD target must be < 10 ppm")

        # Stage 4 Checks
        self.assertGreater(state["stage4_diesel_cetane"], 51.0, "Commercial diesel cetane index > 51.0")
        print("  [✓] Legacy compatibility and nominal steady-state verified.")

    def test_02_mass_conservation_in_fractionation_column(self):
        """Verify strict mass balance: Q_crude = Q_naphtha + Q_diesel + Q_residue."""
        print("\n[TEST 2] Mass Conservation across Fractionation Cuts...")
        for _ in range(5):
            state = self.sim.update(dt=1.0)

        crude = state["stage1_crude_flow"]
        cuts_sum = round(
            state["stage2_naphtha_flow"] +
            state["stage2_diesel_flow"] +
            state["stage2_residue_flow"], 2
        )
        print(f"  Crude Feed: {crude:.2f} L/s | Sum of Cuts: {cuts_sum:.2f} L/s (Naphtha={state['stage2_naphtha_flow']:.2f}, Diesel={state['stage2_diesel_flow']:.2f}, Residue={state['stage2_residue_flow']:.2f})")
        self.assertAlmostEqual(crude, cuts_sum, delta=0.05, msg="Mass balance violated across distillation column!")
        print("  [✓] Distillation column mass conservation verified.")

    def test_03_closed_valve_safety_interlock(self):
        """Closing charge valve must immediately collapse crude and downstream production to zero."""
        print("\n[TEST 3] Closed Valve Interlock Across All 4 Stages...")
        self.sim.set_valve_pos(0.0)
        state = self.sim.update(dt=1.0)

        self.assertEqual(state["flow_rate"], 0.0)
        self.assertEqual(state["stage1_crude_flow"], 0.0)
        self.assertEqual(state["stage2_naphtha_flow"], 0.0)
        self.assertEqual(state["stage2_diesel_flow"], 0.0)
        self.assertEqual(state["stage2_residue_flow"], 0.0)
        self.assertEqual(state["stage3_treated_diesel_flow"], 0.0)
        print("  [✓] Valve closure interlock successfully arrested all downstream flow.")

    def test_04_upstream_starvation_furnace_overheating_cascade(self):
        """Throttling crude feed starves furnace tubes, causing severe over-temperature."""
        print("\n[TEST 4] Feed Starvation & Furnace Tube Overheating Cascade...")
        # Step 1: Baseline run
        for _ in range(5):
            baseline = self.sim.update(dt=1.0)
        furnace_t_base = baseline["stage2_furnace_temp"]

        # Step 2: Severe feed throttling (valve at 5%)
        self.sim.set_valve_pos(0.05)
        for _ in range(15):
            throttled = self.sim.update(dt=1.0)

        furnace_t_starved = throttled["stage2_furnace_temp"]
        print(f"  Baseline Furnace Temp: {furnace_t_base:.1f} °C -> Starved Furnace Temp: {furnace_t_starved:.1f} °C")
        self.assertGreater(furnace_t_starved, furnace_t_base + 30.0, "Furnace temperature did not surge under crude starvation!")
        print("  [✓] Cascading furnace over-temperature anomaly confirmed.")

    def test_05_modbus_overspeed_surge_cascade(self):
        """Forcing pump to 2400 RPM surges Desalter, Column Top, and Export Pressure."""
        print("\n[TEST 5] Modbus FC6 Over-Speed Injection Surge Cascade...")
        # Baseline
        for _ in range(5):
            baseline = self.sim.update(dt=1.0)

        # Attack: Modbus FC6 injection (2400 RPM)
        self.sim.set_pump_rpm(2400)
        for _ in range(10):
            surged = self.sim.update(dt=1.0)

        print(f"  Desalter Pressure: {baseline['stage1_desalter_pressure']:.1f} -> {surged['stage1_desalter_pressure']:.1f} PSI")
        print(f"  Export Pressure  : {baseline['pressure']:.1f} -> {surged['pressure']:.1f} PSI")

        self.assertGreater(surged["stage1_desalter_pressure"], baseline["stage1_desalter_pressure"] + 40.0)
        self.assertGreater(surged["pressure"], baseline["pressure"] + 20.0)
        print("  [✓] Cross-stage pressure surge propagation confirmed.")

    def test_06_hds_catalytic_failure_and_sulfur_trip(self):
        """Dropping H2 compressor speed drops reactor pressure, causing off-spec sulfur trip."""
        print("\n[TEST 6] HDS Hydrogen Loss & Off-Spec Fuel Quality Trip...")
        for _ in range(5):
            baseline = self.sim.update(dt=1.0)
        self.assertLess(baseline["stage3_sulfur_ppm"], 10.0)

        # Attack: Trip H2 compressor to 200 RPM
        self.sim.set_h2_compressor_rpm(200.0)
        for _ in range(15):
            tripped = self.sim.update(dt=1.0)

        print(f"  HDS Reactor Pressure: {baseline['stage3_reactor_pressure']:.1f} -> {tripped['stage3_reactor_pressure']:.1f} PSI")
        print(f"  Diesel Sulfur PPM   : {baseline['stage3_sulfur_ppm']:.1f} -> {tripped['stage3_sulfur_ppm']:.1f} ppm")
        print(f"  Diesel Cetane Index : {baseline['stage4_diesel_cetane']:.1f} -> {tripped['stage4_diesel_cetane']:.1f}")

        self.assertLess(tripped["stage3_reactor_pressure"], 720.0)
        self.assertGreater(tripped["stage3_sulfur_ppm"], 100.0, "Off-spec sulfur was not detected during H2 pressure drop!")
        self.assertLess(tripped["stage4_diesel_cetane"], 48.0, "Cetane index did not degrade under off-spec fuel!")
        print("  [✓] Environmental fuel specification trip verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
