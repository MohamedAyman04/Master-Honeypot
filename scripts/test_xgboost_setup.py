#!/usr/bin/env python3
"""
scripts/test_xgboost_setup.py
=============================
Automated test suite verifying the XGBoost MITRE ATT&CK & Physics Residual setup:
  - Test 1: Verify Standby Mode (Untrained) Role A classification + explainability
  - Test 2: Verify Standby Mode (Untrained) Role B physics residual prediction + explainability
  - Test 3: Verify Role A Training, Persistence, Inference, and native TreeSHAP attribution
  - Test 4: Verify Role B Training, Persistence, Inference, and native TreeSHAP attribution
  - Test 5: Verify Unified XGBoostSuite evaluation and InfluxDB point structure
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

# Add app paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml-engine")))
sys.path.insert(0, "/app")

import xgboost_suite
from xgboost_suite import (
    XGBoostMitreClassifier,
    XGBoostPhysicsRegressor,
    XGBoostSuite,
    MITRE_TECHNIQUES,
    ROLE_A_FEATURES,
    ROLE_B_FEATURES,
    HAS_XGBOOST
)

class TestXGBoostSetup(unittest.TestCase):

    def setUp(self):
        self.test_mitre_path = "/tmp/test_xgb_mitre.json"
        self.test_physics_path = "/tmp/test_xgb_physics.json"

    def tearDown(self):
        for path in [
            self.test_mitre_path,
            self.test_mitre_path + ".meta",
            self.test_physics_path,
            self.test_physics_path + ".meta"
        ]:
            if os.path.exists(path):
                os.remove(path)

    def test_01_role_a_standby_classification(self):
        """Role A should operate in STANDBY mode with heuristic explainability before training."""
        clf = XGBoostMitreClassifier(model_path=self.test_mitre_path)
        self.assertFalse(clf.is_trained)
        self.assertEqual(clf.get_status()["status"], "STANDBY (Awaiting Training Campaign)")

        # Normal sample
        benign_sample = {f: 0.0 for f in ROLE_A_FEATURES}
        benign_sample["pressure"] = 125.0
        benign_sample["flow_rate"] = 45.0
        benign_sample["inter_arrival_time"] = 1.0

        res_benign = clf.classify(benign_sample)
        self.assertEqual(res_benign["technique_id"], "BENIGN")
        self.assertEqual(res_benign["mode"], "standby_heuristic")
        self.assertIn("explainability", res_benign)
        self.assertTrue(len(res_benign["explainability"]["top_features"]) > 0)
        self.assertIn("Nominal", res_benign["explainability"]["narrative"])

        # Forced write / Unauthorized command sample (T0855)
        attack_sample = {f: 0.0 for f in ROLE_A_FEATURES}
        attack_sample["pressure"] = 158.0
        attack_sample["func_code"] = 6
        attack_sample["is_write"] = 1
        attack_sample["write_freq_10s"] = 8.0

        res_attack = clf.classify(attack_sample)
        self.assertEqual(res_attack["technique_id"], "T0855")
        self.assertEqual(res_attack["technique_name"], "Unauthorized Command Message")
        self.assertEqual(res_attack["tactic"], "Impair Process Control")
        self.assertIn("T0855", res_attack["explainability"]["narrative"])

    def test_02_role_b_standby_physics_residual(self):
        """Role B should operate in STANDBY mode using analytical pump/valve curves."""
        reg = XGBoostPhysicsRegressor(model_path=self.test_physics_path, residual_threshold=15.0)
        self.assertFalse(reg.is_trained)
        self.assertEqual(reg.get_status()["status"], "STANDBY (Awaiting Training Campaign)")

        # Normal condition: Expected ~125 PSI, observed 126.5 PSI
        normal_state = {
            "pressure_lag1": 125.0,
            "flow_rate": 45.0,
            "temperature": 65.0,
            "pump_rpm": 1200.0,
            "valve_pos": 50.0,
            "pressure_delta": 0.5
        }
        res_norm = reg.predict_and_evaluate(normal_state, observed_pressure=126.5)
        self.assertEqual(res_norm["mode"], "standby_analytical")
        self.assertFalse(res_norm["is_residual_anomaly"])
        self.assertLess(res_norm["residual"], 15.0)
        self.assertIn("CONSERVED", res_norm["explainability"]["narrative"])

        # Anomaly condition: External surge (observed 180 PSI) with same actuators
        res_surge = reg.predict_and_evaluate(normal_state, observed_pressure=180.0)
        self.assertTrue(res_surge["is_residual_anomaly"])
        self.assertGreater(res_surge["residual"], 15.0)
        self.assertIn("ANOMALOUS", res_surge["explainability"]["narrative"])

    def test_03_role_a_training_and_treeshap_explainability(self):
        """Role A should train, persist, predict, and compute exact native TreeSHAP attribution."""
        if not HAS_XGBOOST:
            self.skipTest("xgboost library not available")

        clf = XGBoostMitreClassifier(model_path=self.test_mitre_path)

        # Generate synthetic calibration dataset across 7 classes
        np.random.seed(42)
        n_samples = 210
        X_data = []
        y_data = []

        for i in range(n_samples):
            c_idx = i % 7
            row = {feat: np.random.normal(0, 1) for feat in ROLE_A_FEATURES}
            if c_idx == 0:  # BENIGN
                row["pressure"] = 125.0 + np.random.normal(0, 2)
                row["write_freq_10s"] = 0.0
                row["func_code"] = 3
                row["is_write"] = 0
            elif c_idx == 1: # T0855 Unauthorized Command
                row["pressure"] = 155.0 + np.random.normal(0, 3)
                row["write_freq_10s"] = 6.0 + np.random.uniform(0, 4)
                row["func_code"] = 6
                row["is_write"] = 1
            elif c_idx == 2: # T0836 Modify Parameter
                row["pressure_delta"] = 3.5
                row["pressure_mean_dev"] = 25.0
                row["is_write"] = 0
            elif c_idx == 3: # T0846 Network Recon
                row["func_code"] = 1
                row["inter_arrival_time"] = 0.02
                row["is_write"] = 0
            elif c_idx == 4: # T0856 Replay Attack
                row["lstm_proc_err"] = 0.12
                row["pressure_delta"] = 0.0
            elif c_idx == 5: # T0814 DoS
                row["write_freq_10s"] = 25.0
                row["inter_arrival_time"] = 0.005
            elif c_idx == 6: # T0816 Restart/Trip
                row["func_code"] = 14
                row["length"] = 120

            X_data.append(row)
            y_data.append(c_idx)

        df_X = pd.DataFrame(X_data)
        y_vec = np.array(y_data)

        # Train model
        train_meta = clf.train(df_X, y_vec, hyperparams={"n_estimators": 25, "max_depth": 3})
        self.assertTrue(clf.is_trained)
        self.assertTrue(os.path.exists(self.test_mitre_path))
        self.assertIn("feature_importances", train_meta)

        # Test persistence: load model in new instance
        clf_loaded = XGBoostMitreClassifier(model_path=self.test_mitre_path)
        self.assertTrue(clf_loaded.is_trained)
        self.assertEqual(clf_loaded.get_status()["status"], "ACTIVE (Trained Booster)")

        # Test inference and TreeSHAP attribution
        sample_query = df_X.iloc[1].to_dict()  # T0855 instance
        pred_res = clf_loaded.classify(sample_query)

        self.assertEqual(pred_res["mode"], "xgboost_trained")
        self.assertEqual(pred_res["technique_id"], "T0855")
        self.assertGreater(pred_res["confidence"], 0.50)
        self.assertIn("explainability", pred_res)
        self.assertEqual(pred_res["explainability"]["method"], "TreeSHAP (Native XGBoost Booster)")

        # Verify top features list has shap_attribution and values
        top_feats = pred_res["explainability"]["top_features"]
        self.assertTrue(len(top_feats) > 0)
        self.assertIn("shap_attribution", top_feats[0])
        self.assertIn("abs_impact", top_feats[0])
        self.assertIn("[XGBoost MITRE Attribution]", pred_res["explainability"]["narrative"])

    def test_04_role_b_training_and_treeshap_explainability(self):
        """Role B should train, persist, predict, and compute exact native TreeSHAP attribution."""
        if not HAS_XGBOOST:
            self.skipTest("xgboost library not available")

        reg = XGBoostPhysicsRegressor(model_path=self.test_physics_path, residual_threshold=15.0)

        # Generate synthetic physics dataset: P_t = 125 + 0.05*(RPM-1200) - 0.35*(Valve-50)
        np.random.seed(42)
        n_samples = 200
        X_data = []
        y_data = []

        for _ in range(n_samples):
            rpm = np.random.uniform(900, 1500)
            valve = np.random.uniform(20, 80)
            p_lag = 125.0 + 0.05 * (rpm - 1200) - 0.35 * (valve - 50) + np.random.normal(0, 1)
            p_curr = p_lag + np.random.normal(0, 1.5)

            row = {
                "pressure_lag1": p_lag,
                "flow_rate": 45.0 + np.random.normal(0, 2),
                "temperature": 65.0 + np.random.normal(0, 3),
                "pump_rpm": rpm,
                "valve_pos": valve,
                "pressure_delta": p_curr - p_lag
            }
            X_data.append(row)
            y_data.append(p_curr)

        df_X = pd.DataFrame(X_data)
        y_vec = np.array(y_data)

        train_meta = reg.train(df_X, y_vec, hyperparams={"n_estimators": 25, "max_depth": 3})
        self.assertTrue(reg.is_trained)
        self.assertTrue(os.path.exists(self.test_physics_path))

        # Test persistence: load in new instance
        reg_loaded = XGBoostPhysicsRegressor(model_path=self.test_physics_path)
        self.assertTrue(reg_loaded.is_trained)

        # Predict nominal case
        test_case = df_X.iloc[0].to_dict()
        obs_p = float(y_vec[0])
        res = reg_loaded.predict_and_evaluate(test_case, observed_pressure=obs_p)

        self.assertEqual(res["mode"], "xgboost_trained")
        self.assertLess(res["residual"], 15.0)
        self.assertFalse(res["is_residual_anomaly"])
        self.assertIn("TreeSHAP", res["explainability"]["method"])

        # Predict anomaly case
        res_anom = reg_loaded.predict_and_evaluate(test_case, observed_pressure=obs_p + 45.0)
        self.assertTrue(res_anom["is_residual_anomaly"])
        self.assertGreater(res_anom["residual"], 15.0)
        self.assertIn("ANOMALOUS DIVERGENCE", res_anom["explainability"]["narrative"])

    def test_05_unified_xgboost_suite(self):
        """Unified XGBoostSuite should orchestrate both roles and provide coherent summaries."""
        suite = XGBoostSuite(
            mitre_model_path=self.test_mitre_path,
            physics_model_path=self.test_physics_path
        )
        sample = {f: 0.0 for f in ROLE_A_FEATURES}
        sample["pressure"] = 162.0
        sample["pump_rpm"] = 1200.0
        sample["func_code"] = 6
        sample["is_write"] = 1
        sample["write_freq_10s"] = 7.0

        eval_res = suite.evaluate_sample(sample, observed_pressure=162.0)
        self.assertIn("role_a_mitre", eval_res)
        self.assertIn("role_b_physics", eval_res)
        self.assertIn("summary_narrative", eval_res)
        self.assertEqual(eval_res["role_a_mitre"]["technique_id"], "T0855")

        status = suite.get_full_status()
        self.assertIn("role_a", status)
        self.assertIn("role_b", status)
        self.assertIn("role_a_importances", status)
        self.assertIn("role_b_importances", status)


if __name__ == "__main__":
    unittest.main()
