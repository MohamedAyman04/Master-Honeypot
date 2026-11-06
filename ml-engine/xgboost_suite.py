"""
ml-engine/xgboost_suite.py
==========================
XGBoost ML Architecture & Explainability Engine for ICS Threat Detection
========================================================================

Implements two complementary roles in the Purdue Level 2 Monitor Zone:

1. Role A — Post-Detection MITRE ATT&CK Classifier (with TreeSHAP Explainability):
   - Multi-class classifier mapping anomaly feature vectors to standardized
     MITRE ATT&CK for ICS technique IDs:
       • BENIGN (Index 0): Nominal baseline operation
       • T0855  (Index 1): Unauthorized Command Message (Modbus FC6/16 forced writes)
       • T0836  (Index 2): Modify Parameter (CUSUM/EWMA stealth setpoint drift)
       • T0846  (Index 3): Network Service Discovery (Reconnaissance scanning)
       • T0856  (Index 4): Spoof Reporting Message (Replay attacks & frozen telemetry)
       • T0814  (Index 5): Denial of Service (Fieldbus flooding / burst writes)
       • T0816  (Index 6): Device Restart/Shutdown (S7 CPU Stop / PLC trips)
   - Explainability: Extracts global feature importances and exact local
     TreeSHAP contributions (pred_contribs=True) natively from XGBoost booster,
     identifying the exact telemetry and fieldbus drivers behind the classification.
   - Operates in "STANDBY (Awaiting Training Campaign)" mode with high-fidelity
     heuristic prior evaluation until full campaign training is executed.

2. Role B — Physics Residual Regressor (with Explainability):
   - Supervised surrogate regressor predicting the next expected physical pressure
     P_hat_t = f(P_t-1, Q_t, T_t, RPM_t, Valve_t).
   - Computes physical residual R_t = |P_observed - P_hat_t|.
   - Flags physical invariant violations when R_t > tau_residual (default: 15.0 PSI).
   - Explainability: Decomposes expected pressure via TreeSHAP feature attributions,
     generating physical diagnostic narratives (e.g. actuator vs sensor divergence).
   - Operates in "STANDBY" mode using analytical steady-state pump/valve curves.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

# Configure module logger
logger = logging.getLogger("xgboost_suite")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s")

# Optional XGBoost import with graceful fallback
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    xgb = None
    HAS_XGBOOST = False
    logger.warning("xgboost not found in Python environment. Fallback/standby heuristic modes active.")

# ─────────────────────────────────────────────────────────────────────────────
# MITRE ATT&CK for ICS Taxonomy Definition
# ─────────────────────────────────────────────────────────────────────────────

MITRE_TECHNIQUES: Dict[int, Dict[str, Any]] = {
    0: {
        "technique_id":   "BENIGN",
        "technique_name": "Nominal Baseline Operation",
        "tactic":         "None",
        "kill_chain":     "Nominal",
        "purdue_level":   "Level 0-2",
        "description":    "Normal operational envelope with expected hydraulic and fieldbus behavior."
    },
    1: {
        "technique_id":   "T0855",
        "technique_name": "Unauthorized Command Message",
        "tactic":         "Impair Process Control",
        "kill_chain":     "Stage 2 - ICS Impact",
        "purdue_level":   "Level 1/2",
        "description":    "Forced register write command modifying actuator setpoints or process controls."
    },
    2: {
        "technique_id":   "T0836",
        "technique_name": "Modify Parameter",
        "tactic":         "Impair Process Control",
        "kill_chain":     "Stage 2 - ICS Impact",
        "purdue_level":   "Level 0/1",
        "description":    "Stealth parameter manipulation or calibration drift bypassing static thresholds."
    },
    3: {
        "technique_id":   "T0846",
        "technique_name": "Network Service Discovery",
        "tactic":         "Discovery",
        "kill_chain":     "Stage 1 - IT Intrusion",
        "purdue_level":   "Level 2",
        "description":    "Fieldbus register enumeration, port sweeps, or protocol probe scanning."
    },
    4: {
        "technique_id":   "T0856",
        "technique_name": "Spoof Reporting Message",
        "tactic":         "Impair Process Control",
        "kill_chain":     "Stage 2 - ICS Impact",
        "purdue_level":   "Level 0/2",
        "description":    "Replay attack or falsification of sensor telemetry concealing actual plant state."
    },
    5: {
        "technique_id":   "T0814",
        "technique_name": "Denial of Service",
        "tactic":         "Inhibit Response Function",
        "kill_chain":     "Stage 2 - ICS Impact",
        "purdue_level":   "Level 1/2",
        "description":    "High-frequency fieldbus message flooding exhausting controller communication buffers."
    },
    6: {
        "technique_id":   "T0816",
        "technique_name": "Device Restart/Shutdown",
        "tactic":         "Inhibit Response Function",
        "kill_chain":     "Stage 2 - ICS Impact",
        "purdue_level":   "Level 1",
        "description":    "Unauthorized CPU stop, controller trip, or emergency shutdown command."
    }
}

# Reverse lookup mapping technique_id -> class index
TECHNIQUE_ID_TO_INDEX: Dict[str, int] = {
    info["technique_id"]: idx for idx, info in MITRE_TECHNIQUES.items()
}

# ─────────────────────────────────────────────────────────────────────────────
# Standardized Feature Specifications
# ─────────────────────────────────────────────────────────────────────────────

ROLE_A_FEATURES = [
    "pressure",
    "flow_rate",
    "temperature",
    "pump_rpm",
    "pressure_delta",
    "pressure_mean_dev",
    "inter_arrival_time",
    "write_freq_10s",
    "is_write",
    "func_code",
    "length",
    "lstm_proc_err",
    "lstm_net_err",
    "if_proc_score",
]

ROLE_B_FEATURES = [
    "pressure_lag1",
    "flow_rate",
    "temperature",
    "pump_rpm",
    "valve_pos",
    "pressure_delta",
]

DEFAULT_PHYSICS_RESIDUAL_THRESHOLD = 15.0  # PSI


# ═════════════════════════════════════════════════════════════════════════════
# ROLE A: Post-Detection MITRE ATT&CK Classifier
# ═════════════════════════════════════════════════════════════════════════════

class XGBoostMitreClassifier:
    """
    Role A: Supervised multi-class gradient boosted classifier mapping ICS
    anomalies to MITRE ATT&CK for ICS techniques with native TreeSHAP attribution.
    """

    def __init__(self, model_path: str = "/data/xgb_mitre.json"):
        self.model_path = model_path
        self.meta_path  = model_path + ".meta"
        self.model: Optional[Any] = None
        self.booster: Optional[Any] = None
        self.is_trained: bool = False
        self.training_metadata: Dict[str, Any] = {}
        self.features: List[str] = list(ROLE_A_FEATURES)
        self.classes: List[int] = list(MITRE_TECHNIQUES.keys())

        # Attempt to load pre-existing model if available on disk
        self.load()

    def load(self, path: Optional[str] = None) -> bool:
        """Loads trained XGBoost model and metadata from disk."""
        target_path = path or self.model_path
        meta_target = (path + ".meta") if path else self.meta_path

        if not os.path.exists(target_path):
            logger.info("XGBoost MITRE model not found at %s. Classifier initialized in STANDBY.", target_path)
            self.is_trained = False
            return False

        if not HAS_XGBOOST:
            logger.warning("Cannot load XGBoost model from %s: xgboost package not installed.", target_path)
            self.is_trained = False
            return False

        try:
            self.booster = xgb.Booster()
            self.booster.load_model(target_path)
            self.model = xgb.XGBClassifier()
            self.model._Booster = self.booster

            if os.path.exists(meta_target):
                with open(meta_target, "r") as f:
                    self.training_metadata = json.load(f)
                if "features" in self.training_metadata:
                    self.features = self.training_metadata["features"]

            self.is_trained = True
            logger.info("Successfully loaded XGBoost MITRE model from %s", target_path)
            return True
        except Exception as e:
            logger.error("Failed to load XGBoost model from %s: %s", target_path, e)
            self.is_trained = False
            return False

    def save(self, path: Optional[str] = None) -> bool:
        """Saves current XGBoost model and metadata to disk."""
        target_path = path or self.model_path
        meta_target = (path + ".meta") if path else self.meta_path

        if not self.is_trained or self.booster is None:
            logger.warning("Cannot save model: not yet trained.")
            return False

        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            self.booster.save_model(target_path)
            with open(meta_target, "w") as f:
                json.dump(self.training_metadata, f, indent=2)
            logger.info("Saved XGBoost MITRE model to %s", target_path)
            return True
        except Exception as e:
            logger.error("Failed to save XGBoost MITRE model to %s: %s", target_path, e)
            return False

    def train(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        eval_set: Optional[List[Tuple[Any, Any]]] = None,
        hyperparams: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trains the multi-class MITRE classifier. Ready for future campaign execution.
        """
        if not HAS_XGBOOST:
            raise RuntimeError("Cannot train XGBoost: xgboost library is not installed.")

        # Ensure DataFrame format with feature alignment
        if isinstance(X, pd.DataFrame):
            df_X = X.copy()
            for feat in self.features:
                if feat not in df_X.columns:
                    df_X[feat] = 0.0
            X_mat = df_X[self.features].values
        else:
            X_mat = np.asarray(X)

        y_vec = np.asarray(y, dtype=int)

        params = {
            "objective": "multi:softprob",
            "num_class": len(self.classes),
            "n_estimators": 120,
            "max_depth": 5,
            "learning_rate": 0.08,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "random_state": 42,
            "eval_metric": "mlogloss",
            "n_jobs": -1
        }
        if hyperparams:
            params.update(hyperparams)

        logger.info("Initiating training of XGBoost MITRE Classifier on %d samples...", len(X_mat))
        clf = xgb.XGBClassifier(**params)
        clf.fit(X_mat, y_vec, eval_set=eval_set, verbose=False)

        self.model = clf
        self.booster = clf.get_booster()
        self.is_trained = True

        # Compute training feature importances
        importances = dict(zip(self.features, [float(v) for v in clf.feature_importances_]))
        self.training_metadata = {
            "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "n_samples": int(len(X_mat)),
            "n_classes": len(self.classes),
            "features": self.features,
            "hyperparams": params,
            "feature_importances": importances
        }

        self.save()
        logger.info("XGBoost MITRE Classifier trained successfully. Top features: %s",
                    sorted(importances.items(), key=lambda x: x[1], reverse=True)[:3])
        return self.training_metadata

    def classify(self, feature_row: Union[pd.DataFrame, pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Classifies an input sample and extracts full explainability details.
        Falls back to rule-based heuristic prior when in STANDBY mode.
        """
        # Convert input to structured dict & single-row DataFrame
        if isinstance(feature_row, pd.DataFrame):
            row_dict = feature_row.iloc[0].to_dict()
        elif isinstance(feature_row, pd.Series):
            row_dict = feature_row.to_dict()
        elif isinstance(feature_row, dict):
            row_dict = dict(feature_row)
        else:
            raise ValueError(f"Unsupported feature input type: {type(feature_row)}")

        # Fill missing features with default zeros
        aligned = {feat: float(row_dict.get(feat, 0.0)) for feat in self.features}
        df_row = pd.DataFrame([aligned])[self.features]

        # ── Branch A: Trained XGBoost Model ───────────────────────────────────
        if self.is_trained and self.booster is not None and HAS_XGBOOST:
            return self._classify_trained(df_row, aligned)

        # ── Branch B: Standby Heuristic Prior (Before Training Campaign) ───────
        return self._classify_standby_heuristic(aligned)

    def _classify_trained(self, df_row: pd.DataFrame, aligned: Dict[str, float]) -> Dict[str, Any]:
        """Inference and exact TreeSHAP attribution with trained booster."""
        dmat = xgb.DMatrix(df_row.values, feature_names=self.features)
        probs = self.booster.predict(dmat)[0]  # shape (num_classes,)
        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])

        # Compute exact TreeSHAP values natively via XGBoost C++ core
        # shape: (1, num_classes, num_features + 1)
        contribs = self.booster.predict(dmat, pred_contribs=True)
        if len(contribs.shape) == 3:
            class_contribs = contribs[0, pred_idx, :-1]  # exclude bias column
        elif len(contribs.shape) == 2:
            class_contribs = contribs[0, :-1]
        else:
            class_contribs = np.zeros(len(self.features))

        # Build feature attribution list
        attributions = []
        for feat, shap_val in zip(self.features, class_contribs):
            val = aligned[feat]
            attributions.append({
                "feature": feat,
                "value": round(val, 4),
                "shap_attribution": round(float(shap_val), 4),
                "direction": "supports" if shap_val > 0 else "contradicts",
                "abs_impact": round(abs(float(shap_val)), 4)
            })
        attributions.sort(key=lambda x: x["abs_impact"], reverse=True)

        meta = MITRE_TECHNIQUES.get(pred_idx, MITRE_TECHNIQUES[0])
        narrative = self._generate_narrative(meta, confidence, attributions[:3], mode="xgboost")

        prob_dict = {
            MITRE_TECHNIQUES[i]["technique_id"]: round(float(p), 4)
            for i, p in enumerate(probs)
        }

        return {
            "mode":                 "xgboost_trained",
            "technique_id":         meta["technique_id"],
            "technique_name":       meta["technique_name"],
            "tactic":               meta["tactic"],
            "kill_chain":           meta["kill_chain"],
            "purdue_level":         meta["purdue_level"],
            "confidence":           round(confidence, 4),
            "class_probabilities":  prob_dict,
            "explainability": {
                "method":           "TreeSHAP (Native XGBoost Booster)",
                "top_features":     attributions[:5],
                "all_attributions": attributions,
                "narrative":        narrative
            }
        }

    def _classify_standby_heuristic(self, aligned: Dict[str, float]) -> Dict[str, Any]:
        """
        High-fidelity heuristic prior providing full MITRE enrichment and
        explainability when in STANDBY mode prior to training campaign.
        """
        w_freq    = aligned.get("write_freq_10s", 0.0)
        fc        = int(aligned.get("func_code", 0))
        is_write  = int(aligned.get("is_write", 0))
        p_delta   = aligned.get("pressure_delta", 0.0)
        iat       = aligned.get("inter_arrival_time", 1.0)
        p_dev     = aligned.get("pressure_mean_dev", 0.0)
        lstm_proc = aligned.get("lstm_proc_err", 0.0)
        lstm_net  = aligned.get("lstm_net_err", 0.0)
        if_proc   = aligned.get("if_proc_score", 0.0)

        # Rule evaluation hierarchy
        pred_idx = 0
        reasons = []

        if fc in (14, 15, 17) or (fc == 6 and aligned.get("length", 0) > 100):
            pred_idx = 6  # T0816 Device Restart/Shutdown
            reasons.append(f"Function code {fc} matches shutdown/stop directive")
        elif w_freq >= 20.0 or (0 < iat < 0.01 and w_freq >= 10.0):
            pred_idx = 5  # T0814 Denial of Service
            reasons.append(f"High write burst frequency ({w_freq:.1f} writes/10s)")
        elif is_write == 1 or fc in (5, 6, 15, 16):
            pred_idx = 1  # T0855 Unauthorized Command Message
            reasons.append(f"Fieldbus actuator write command observed (func_code={fc}, is_write={is_write})")
        elif abs(p_dev) > 15.0 or (abs(p_delta) > 2.0 and is_write == 0):
            pred_idx = 2  # T0836 Modify Parameter
            reasons.append(f"Stealth pressure deviation ({p_dev:.1f} PSI) without corresponding actuator writes")
        elif fc in (1, 2, 3, 4) and iat < 0.08:
            pred_idx = 3  # T0846 Network Service Discovery
            reasons.append(f"Rapid fieldbus polling sweep (IAT={iat*1000:.1f}ms, func_code={fc})")
        elif lstm_proc > 0.05 and abs(p_delta) < 0.001 and if_proc < -0.15:
            pred_idx = 4  # T0856 Spoof Reporting Message (Replay/Flatline)
            reasons.append(f"Anomalous static telemetry variance (LSTM err={lstm_proc:.4f}, IF={if_proc:.3f})")
        else:
            pred_idx = 0  # BENIGN
            reasons.append("All physical and network indicators remain within nominal baseline envelope")

        meta = MITRE_TECHNIQUES.get(pred_idx, MITRE_TECHNIQUES[0])
        confidence = 0.88 if pred_idx != 0 else 0.95

        top_features = [
            {"feature": "write_freq_10s", "value": w_freq, "shap_attribution": 0.40 if pred_idx in (1, 5) else -0.10},
            {"feature": "func_code",      "value": fc,     "shap_attribution": 0.35 if pred_idx in (1, 3, 6) else -0.05},
            {"feature": "pressure_delta", "value": p_delta,"shap_attribution": 0.30 if pred_idx == 2 else 0.02},
            {"feature": "if_proc_score",  "value": if_proc,"shap_attribution": 0.25 if if_proc < -0.10 else -0.10},
        ]
        top_features.sort(key=lambda x: abs(x["shap_attribution"]), reverse=True)

        prob_dict = {
            t["technique_id"]: (0.85 if idx == pred_idx else round((0.15 / (len(MITRE_TECHNIQUES) - 1)), 3))
            for idx, t in MITRE_TECHNIQUES.items()
        }

        narrative = self._generate_narrative(meta, confidence, top_features[:3], mode="standby_heuristic", detail="; ".join(reasons))

        return {
            "mode":                 "standby_heuristic",
            "technique_id":         meta["technique_id"],
            "technique_name":       meta["technique_name"],
            "tactic":               meta["tactic"],
            "kill_chain":           meta["kill_chain"],
            "purdue_level":         meta["purdue_level"],
            "confidence":           confidence,
            "class_probabilities":  prob_dict,
            "explainability": {
                "method":           "Standby Heuristic Prior (Awaiting Training Campaign)",
                "top_features":     top_features,
                "narrative":        narrative,
                "reasons":          reasons
            }
        }

    def _generate_narrative(
        self,
        meta: Dict[str, Any],
        confidence: float,
        top_feats: List[Dict[str, Any]],
        mode: str,
        detail: str = ""
    ) -> str:
        tid = meta["technique_id"]
        tname = meta["technique_name"]
        tactic = meta["tactic"]
        pct = confidence * 100.0

        feat_str = ", ".join([f"{f['feature']} (val={f['value']})" for f in top_feats])

        if mode == "xgboost":
            return (
                f"[XGBoost MITRE Attribution] Classified as {tid} ({tname}) under tactic '{tactic}' "
                f"with {pct:.1f}% confidence. Primary predictive drivers: {feat_str}."
            )
        else:
            d_str = f" Context: {detail}." if detail else ""
            return (
                f"[Standby MITRE Heuristic] Attributed to {tid} ({tname}) [{tactic}] "
                f"(confidence: {pct:.0f}%). Key signatures: {feat_str}.{d_str} "
                f"(Ready for future campaign training)."
            )

    def get_feature_importances(self) -> Dict[str, float]:
        """Returns global feature importances or baseline weights if in standby."""
        if self.is_trained and self.model is not None and hasattr(self.model, "feature_importances_"):
            return dict(zip(self.features, [round(float(v), 5) for v in self.model.feature_importances_]))
        # Return default balanced prior weights when in standby
        prior_weights = {
            "write_freq_10s": 0.22,
            "func_code": 0.18,
            "is_write": 0.14,
            "pressure_delta": 0.12,
            "pressure_mean_dev": 0.10,
            "if_proc_score": 0.08,
            "inter_arrival_time": 0.06,
            "lstm_proc_err": 0.04,
            "lstm_net_err": 0.03,
            "length": 0.01,
            "pressure": 0.01,
            "pump_rpm": 0.005,
            "temperature": 0.003,
            "flow_rate": 0.002
        }
        return {feat: prior_weights.get(feat, 0.01) for feat in self.features}

    def get_status(self) -> Dict[str, Any]:
        """Provides status dict for API and health monitoring."""
        return {
            "role": "Role A: Post-Detection MITRE ATT&CK Classifier",
            "is_trained": self.is_trained,
            "status": "ACTIVE (Trained Booster)" if self.is_trained else "STANDBY (Awaiting Training Campaign)",
            "model_path": self.model_path,
            "n_features": len(self.features),
            "n_classes": len(self.classes),
            "xgboost_installed": HAS_XGBOOST,
            "metadata": self.training_metadata
        }


# ═════════════════════════════════════════════════════════════════════════════
# ROLE B: Physics Residual Regressor
# ═════════════════════════════════════════════════════════════════════════════

class XGBoostPhysicsRegressor:
    """
    Role B: Gradient boosted regressor modeling physical process dynamics.
    Predicts next expected pressure P_hat_t and evaluates physical residuals
    R_t = |P_observed - P_hat_t| against hydraulic tolerance limits.
    """

    def __init__(
        self,
        model_path: str = "/data/xgb_physics.json",
        residual_threshold: float = DEFAULT_PHYSICS_RESIDUAL_THRESHOLD
    ):
        self.model_path = model_path
        self.meta_path  = model_path + ".meta"
        self.residual_threshold = residual_threshold
        self.model: Optional[Any] = None
        self.booster: Optional[Any] = None
        self.is_trained: bool = False
        self.training_metadata: Dict[str, Any] = {}
        self.features: List[str] = list(ROLE_B_FEATURES)

        self.load()

    def load(self, path: Optional[str] = None) -> bool:
        """Loads trained regression model from disk."""
        target_path = path or self.model_path
        meta_target = (path + ".meta") if path else self.meta_path

        if not os.path.exists(target_path):
            logger.info("XGBoost Physics model not found at %s. Regressor initialized in STANDBY.", target_path)
            self.is_trained = False
            return False

        if not HAS_XGBOOST:
            logger.warning("Cannot load XGBoost physics regressor from %s: xgboost not installed.", target_path)
            self.is_trained = False
            return False

        try:
            self.booster = xgb.Booster()
            self.booster.load_model(target_path)
            self.model = xgb.XGBRegressor()
            self.model._Booster = self.booster

            if os.path.exists(meta_target):
                with open(meta_target, "r") as f:
                    self.training_metadata = json.load(f)
                if "residual_threshold" in self.training_metadata:
                    self.residual_threshold = float(self.training_metadata["residual_threshold"])

            self.is_trained = True
            logger.info("Successfully loaded XGBoost Physics Regressor from %s", target_path)
            return True
        except Exception as e:
            logger.error("Failed to load XGBoost Physics Regressor from %s: %s", target_path, e)
            self.is_trained = False
            return False

    def save(self, path: Optional[str] = None) -> bool:
        """Saves current regression model and metadata to disk."""
        target_path = path or self.model_path
        meta_target = (path + ".meta") if path else self.meta_path

        if not self.is_trained or self.booster is None:
            logger.warning("Cannot save physics model: not yet trained.")
            return False

        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            self.booster.save_model(target_path)
            with open(meta_target, "w") as f:
                json.dump(self.training_metadata, f, indent=2)
            logger.info("Saved XGBoost Physics Regressor to %s", target_path)
            return True
        except Exception as e:
            logger.error("Failed to save XGBoost Physics Regressor: %s", e)
            return False

    def train(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        eval_set: Optional[List[Tuple[Any, Any]]] = None,
        hyperparams: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trains the physics surrogate regressor on nominal telemetry."""
        if not HAS_XGBOOST:
            raise RuntimeError("Cannot train XGBoost Physics Regressor: xgboost not installed.")

        if isinstance(X, pd.DataFrame):
            df_X = X.copy()
            for feat in self.features:
                if feat not in df_X.columns:
                    df_X[feat] = 0.0
            X_mat = df_X[self.features].values
        else:
            X_mat = np.asarray(X)

        y_vec = np.asarray(y, dtype=float)

        params = {
            "objective": "reg:squarederror",
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "random_state": 42,
            "eval_metric": "rmse",
            "n_jobs": -1
        }
        if hyperparams:
            params.update(hyperparams)

        logger.info("Initiating training of XGBoost Physics Regressor on %d samples...", len(X_mat))
        reg = xgb.XGBRegressor(**params)
        reg.fit(X_mat, y_vec, eval_set=eval_set, verbose=False)

        self.model = reg
        self.booster = reg.get_booster()
        self.is_trained = True

        importances = dict(zip(self.features, [float(v) for v in reg.feature_importances_]))
        self.training_metadata = {
            "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "n_samples": int(len(X_mat)),
            "features": self.features,
            "residual_threshold": self.residual_threshold,
            "hyperparams": params,
            "feature_importances": importances
        }

        self.save()
        logger.info("XGBoost Physics Regressor trained successfully. Importances: %s", importances)
        return self.training_metadata

    def predict_and_evaluate(
        self,
        feature_row: Union[pd.DataFrame, pd.Series, Dict[str, Any]],
        observed_pressure: float
    ) -> Dict[str, Any]:
        """
        Predicts expected pressure P_hat, calculates residual |P_obs - P_hat|,
        evaluates against tolerance threshold, and returns physical explainability.
        """
        if isinstance(feature_row, pd.DataFrame):
            row_dict = feature_row.iloc[0].to_dict()
        elif isinstance(feature_row, pd.Series):
            row_dict = feature_row.to_dict()
        elif isinstance(feature_row, dict):
            row_dict = dict(feature_row)
        else:
            raise ValueError(f"Unsupported feature input type: {type(feature_row)}")

        aligned = {feat: float(row_dict.get(feat, 0.0)) for feat in self.features}
        df_row = pd.DataFrame([aligned])[self.features]

        # ── Branch A: Trained XGBoost Regressor ───────────────────────────────
        if self.is_trained and self.booster is not None and HAS_XGBOOST:
            return self._predict_trained(df_row, aligned, observed_pressure)

        # ── Branch B: Standby Analytical Pump/Valve Curve ─────────────────────
        return self._predict_standby_analytical(aligned, observed_pressure)

    def _predict_trained(
        self,
        df_row: pd.DataFrame,
        aligned: Dict[str, float],
        observed_pressure: float
    ) -> Dict[str, Any]:
        """Inference and TreeSHAP attribution for physical regressor."""
        dmat = xgb.DMatrix(df_row.values, feature_names=self.features)
        pred_p = float(self.booster.predict(dmat)[0])

        residual = abs(observed_pressure - pred_p)
        residual_pct = (residual / max(pred_p, 1.0)) * 100.0
        is_anomaly = bool(residual > self.residual_threshold)

        # TreeSHAP feature contributions
        contribs = self.booster.predict(dmat, pred_contribs=True)
        feat_contribs = contribs[0, :-1]  # exclude bias

        attributions = []
        for feat, shap_val in zip(self.features, feat_contribs):
            attributions.append({
                "feature": feat,
                "value": round(aligned[feat], 4),
                "shap_attribution": round(float(shap_val), 4),
                "impact": round(abs(float(shap_val)), 4)
            })
        attributions.sort(key=lambda x: x["impact"], reverse=True)

        narrative = self._generate_narrative(
            observed_pressure, pred_p, residual, is_anomaly, attributions[:3], mode="xgboost"
        )

        return {
            "mode":                 "xgboost_trained",
            "observed_pressure":    round(observed_pressure, 3),
            "predicted_pressure":   round(pred_p, 3),
            "residual":             round(residual, 3),
            "residual_pct":         round(residual_pct, 2),
            "residual_threshold":   self.residual_threshold,
            "is_residual_anomaly":  is_anomaly,
            "explainability": {
                "method":           "TreeSHAP (Physical Booster)",
                "top_features":     attributions[:3],
                "narrative":        narrative
            }
        }

    def _predict_standby_analytical(
        self,
        aligned: Dict[str, float],
        observed_pressure: float
    ) -> Dict[str, Any]:
        """
        Analytical physics steady-state curve used in STANDBY mode prior to training.
        P_pred = 125.0 + 0.05*(RPM - 1200) - 0.35*(Valve - 50) + pressure_delta
        """
        p_lag   = aligned.get("pressure_lag1", 125.0)
        rpm     = aligned.get("pump_rpm", 1200.0)
        valve   = aligned.get("valve_pos", 50.0)
        p_delta = aligned.get("pressure_delta", 0.0)

        # Analytical steady-state pump/valve hydraulic estimate
        pred_p = 125.0 + 0.05 * (rpm - 1200.0) - 0.35 * (valve - 50.0) + (0.5 * p_delta)
        # Smooth with lag if available
        if p_lag > 0:
            pred_p = 0.7 * pred_p + 0.3 * p_lag

        residual = abs(observed_pressure - pred_p)
        residual_pct = (residual / max(pred_p, 1.0)) * 100.0
        is_anomaly = bool(residual > self.residual_threshold)

        top_features = [
            {"feature": "pump_rpm",       "value": rpm,   "contribution": round(0.05 * (rpm - 1200.0), 3)},
            {"feature": "valve_pos",      "value": valve, "contribution": round(-0.35 * (valve - 50.0), 3)},
            {"feature": "pressure_lag1",  "value": p_lag, "contribution": round(0.3 * (p_lag - 125.0), 3)},
            {"feature": "pressure_delta", "value": p_delta, "contribution": round(0.5 * p_delta, 3)}
        ]
        top_features.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        narrative = self._generate_narrative(
            observed_pressure, pred_p, residual, is_anomaly, top_features[:3], mode="standby_analytical"
        )

        return {
            "mode":                 "standby_analytical",
            "observed_pressure":    round(observed_pressure, 3),
            "predicted_pressure":   round(pred_p, 3),
            "residual":             round(residual, 3),
            "residual_pct":         round(residual_pct, 2),
            "residual_threshold":   self.residual_threshold,
            "is_residual_anomaly":  is_anomaly,
            "explainability": {
                "method":           "Analytical Hydraulic Curve (Standby)",
                "top_features":     top_features,
                "narrative":        narrative
            }
        }

    def _generate_narrative(
        self,
        observed: float,
        pred: float,
        residual: float,
        is_anom: bool,
        top_feats: List[Dict[str, Any]],
        mode: str
    ) -> str:
        status_str = "ANOMALOUS DIVERGENCE" if is_anom else "PHYSICAL INVARIANT CONSERVED"
        feat_str = ", ".join([f"{f['feature']}={f['value']}" for f in top_feats])

        if is_anom:
            return (
                f"[Physics Residual: {status_str}] Residual R = {residual:.2f} PSI exceeds threshold "
                f"({self.residual_threshold:.1f} PSI). Observed pressure ({observed:.1f} PSI) diverged from "
                f"expected ({pred:.1f} PSI). Physical parameters ({feat_str}) cannot account for this pressure "
                f"profile, indicating external manipulation or sensor injection."
            )
        else:
            return (
                f"[Physics Residual: {status_str}] Physical dynamics within hydraulic envelope "
                f"(Observed: {observed:.1f} PSI, Expected: {pred:.1f} PSI, Residual: {residual:.2f} PSI <= {self.residual_threshold:.1f} PSI). "
                f"Actuator states ({feat_str}) are fully consistent with process state."
            )

    def get_feature_importances(self) -> Dict[str, float]:
        """Returns global feature importances for physics regressor."""
        if self.is_trained and self.model is not None and hasattr(self.model, "feature_importances_"):
            return dict(zip(self.features, [round(float(v), 5) for v in self.model.feature_importances_]))
        # Analytical prior weights
        return {
            "pump_rpm": 0.35,
            "valve_pos": 0.30,
            "pressure_lag1": 0.20,
            "pressure_delta": 0.10,
            "flow_rate": 0.03,
            "temperature": 0.02
        }

    def get_status(self) -> Dict[str, Any]:
        """Provides status dict for API and health monitoring."""
        return {
            "role": "Role B: Physics Residual Regressor",
            "is_trained": self.is_trained,
            "status": "ACTIVE (Trained Booster)" if self.is_trained else "STANDBY (Awaiting Training Campaign)",
            "model_path": self.model_path,
            "residual_threshold": self.residual_threshold,
            "n_features": len(self.features),
            "xgboost_installed": HAS_XGBOOST,
            "metadata": self.training_metadata
        }


# ═════════════════════════════════════════════════════════════════════════════
# UNIFIED XGBOOST SUITE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class XGBoostSuite:
    """
    Unified manager combining Role A (MITRE Classifier) and Role B (Physics Regressor).
    Coordinates scoring, explainability summaries, and InfluxDB telemetry enrichment.
    """

    def __init__(
        self,
        mitre_model_path: str = "/data/xgb_mitre.json",
        physics_model_path: str = "/data/xgb_physics.json",
        residual_threshold: float = DEFAULT_PHYSICS_RESIDUAL_THRESHOLD
    ):
        self.mitre_classifier = XGBoostMitreClassifier(model_path=mitre_model_path)
        self.physics_regressor = XGBoostPhysicsRegressor(
            model_path=physics_model_path,
            residual_threshold=residual_threshold
        )

    def evaluate_sample(
        self,
        features_dict: Dict[str, Any],
        observed_pressure: float
    ) -> Dict[str, Any]:
        """
        Runs both Role A and Role B evaluations on a given telemetry sample.
        Returns comprehensive analysis with explanations.
        """
        # Role A: MITRE ATT&CK Classification + Explainability
        mitre_result = self.mitre_classifier.classify(features_dict)

        # Role B: Physics Residual Prediction + Explainability
        # Prepare lag and valve features for Role B if not directly passed
        physics_features = dict(features_dict)
        if "pressure_lag1" not in physics_features:
            physics_features["pressure_lag1"] = features_dict.get("pressure", 125.0) - features_dict.get("pressure_delta", 0.0)
        if "valve_pos" not in physics_features:
            physics_features["valve_pos"] = 50.0  # Nominal valve position

        physics_result = self.physics_regressor.predict_and_evaluate(physics_features, observed_pressure)

        return {
            "role_a_mitre":   mitre_result,
            "role_b_physics": physics_result,
            "summary_narrative": (
                f"{mitre_result['explainability']['narrative']} | "
                f"{physics_result['explainability']['narrative']}"
            )
        }

    def get_full_status(self) -> Dict[str, Any]:
        """Returns comprehensive status across both roles."""
        return {
            "xgboost_installed": HAS_XGBOOST,
            "role_a": self.mitre_classifier.get_status(),
            "role_b": self.physics_regressor.get_status(),
            "role_a_importances": self.mitre_classifier.get_feature_importances(),
            "role_b_importances": self.physics_regressor.get_feature_importances()
        }
