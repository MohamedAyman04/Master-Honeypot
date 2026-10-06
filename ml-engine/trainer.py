"""
ML Engine / Trainer  (v8 — 4-Model Decoupled Suite + 5-Layer Detection + NMG Alert Fused)
========================================================================================
Architecture Specification (Purdue Level 2 Monitor Zone):
  1. Four Decoupled Machine Learning Engines:
     • LSTM-AE proc : Physical process sequence autoencoder (pressure, flow, temp, pump_rpm, deltas)
     • LSTM-AE net  : Network traffic sequence autoencoder (IAT, write_freq, func_code, lengths)
     • IF proc      : Isolation Forest on physical process parameters
     • IF net       : Isolation Forest on fieldbus network traffic
     • Replay LSTM  : Variance-focused sequence model for replay attacks
  2. Five Hierarchical Detection Layers:
     • Layer 0 (Physical Process)       : Conservation laws, CUSUM drift, hydraulic boundaries
     • Layer 1 (Fieldbus & PLCs)        : Modbus forced writes, S7/DNP3 unauthorized functions
     • Layer 2 (SCADA & Operations)     : SSH intrusion, physics API on :5100, lateral movement
     • Layer 3 (Enterprise Workstations): Terminal command anomalies, canary honeytokens (.kdbx/.pdf/.xlsx)
     • Layer 4 (Perimeter & DMZ Gateway): Gateway brute force, scanner user-agents, credential spraying
  3. Alert Fused (Narrow Mechanism Gate NMG Engine):
     • A_NMG = A_net ∨ (|S_proc| > τ_proc ∧ f_write_10s == 0) ∨ Consensus(Layers)
     • False-positive suppression on legitimate operational transients
     • Streams multi-dimensional alerts to InfluxDB, Story Logger, and Grafana
"""

import time
import os
import sys
import uuid
import threading
import collections
import statistics
import json
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ── MITRE ATT&CK for ICS enrichment ───────────────────────────────────────────
_base_dir = os.path.dirname(os.path.abspath(__file__))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)
_parent_dir = os.path.dirname(_base_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from shared.mitre_mapping import enrich_point as _mitre_enrich
except ImportError:
    def _mitre_enrich(point, event_type):   # graceful no-op if module missing
        return point

# ── Configuration ──────────────────────────────────────────────────────────────
INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://ics_historian:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "supersecrettoken")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "my_refinery")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "sensor_logs")

# ── Model Storage Paths ───────────────────────────────────────────────────────
IF_PROC_FILE         = "/data/if_proc.pkl"
IF_NET_FILE          = "/data/if_net.pkl"
LSTM_PROC_FILE       = "/data/lstm_proc.keras"
SCALER_PROC_FILE     = "/data/scaler_proc.pkl"
LSTM_NET_FILE        = "/data/lstm_net.keras"
SCALER_NET_FILE      = "/data/scaler_net.pkl"

# Backward compatibility paths
IF_MODEL_FILE        = "/data/model.pkl"
LSTM_MODEL_FILE      = "/data/lstm_model.keras"
SCALER_FILE          = "/data/scaler.pkl"
REPLAY_LSTM_FILE     = "/data/replay_lstm.keras"
REPLAY_SCALER_FILE   = "/data/replay_scaler.pkl"
TRAINING_START_FILE  = "/data/training_start.txt"

WARMUP_PERIOD  = 180   # seconds of training before models are frozen
MIN_SAMPLES    = 50    # minimum rows needed before any model can train
LOOP_INTERVAL  = 15    # main loop cadence (seconds)

# ── Feature Definitions ───────────────────────────────────────────────────────
PROC_FEATURES = ["pressure", "flow_rate", "temperature", "pump_rpm", "pressure_delta", "pressure_mean_dev"]
NET_FEATURES  = ["inter_arrival_time", "write_freq_10s", "is_write", "func_code", "length"]

# ── Startup grace period ───────────────────────────────────────────────────────
STARTUP_GRACE_SECONDS = 120
_boot_time = time.time()

def in_grace_period() -> bool:
    return (time.time() - _boot_time) < STARTUP_GRACE_SECONDS

# ── IsolationForest hyper-parameters ──────────────────────────────────────────
IF_CONTAMINATION   = 0.01
IF_N_ESTIMATORS    = 200
IF_SCORE_THRESHOLD = -0.18

# ── LSTM Autoencoder hyper-parameters ──────────────────────────────────────────
LSTM_SEQ_LEN        = 20
LSTM_LATENT_DIM     = 16
LSTM_EPOCHS         = 15
LSTM_BATCH_SIZE     = 32
LSTM_THRESHOLD_PCTL = 99
LSTM_ERROR_MARGIN   = 3.5
LSTM_MIN_THRESHOLD  = 0.01

# ── Replay LSTM hyper-parameters ──────────────────────────────────────────────
REPLAY_LSTM_SEQ_LEN        = 15
REPLAY_LSTM_LATENT_DIM     = 16
REPLAY_LSTM_EPOCHS         = 15
REPLAY_LSTM_BATCH_SIZE     = 32
REPLAY_LSTM_THRESHOLD_PCTL = 95

# ── EWMA/CUSUM parameters ─────────────────────────────────────────────────────
EWMA_ALPHA      = 0.20
CUSUM_K         = 0.5
CUSUM_THRESHOLD = 6.0
CUSUM_SLOPE_MAX = 0.50

SESSION_ID = secrets.token_hex(4)

# ── Runtime State Holders ──────────────────────────────────────────────────────
_if_proc_model     = None
_if_net_model      = None
_lstm_proc_model   = None
_lstm_proc_scaler  = None
_lstm_proc_thresh  = None
_lstm_net_model    = None
_lstm_net_scaler   = None
_lstm_net_thresh   = None
_replay_lstm_model = None
_replay_lstm_scaler= None
_replay_lstm_thresh= None

_ewma_state          = None
_cusum_pos           = 0.0
_cusum_neg           = 0.0
_cumulative_dev      = 0.0
_drift_confirm_count = 0
DRIFT_CONFIRM_NEEDED = 2
_pressure_history    = collections.deque(maxlen=30)
_slope_history       = collections.deque(maxlen=10)
_drift_attack_seen   = False
_drift_attack_seen_time = 0.0
_seen_injection_ts   = set()

# ── Narrative / Story Logger Integration ───────────────────────────────────────
STORY_LOGGER_URL = os.environ.get("STORY_LOGGER_URL", "http://story_logger:8600")

def _story_run_id() -> str:
    env_run_id = os.environ.get("STORY_RUN_ID", "").strip()
    if env_run_id:
        return env_run_id
    try:
        req = urllib.request.Request(
            f"{STORY_LOGGER_URL}/story/current",
            headers={"User-Agent": "ml_engine/5.0"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            run_id = data.get("run_id", "").strip()
            if run_id:
                return run_id
    except Exception:
        pass
    return f"run_{SESSION_ID}"

def _story_log(event_type: str, message: str, severity: str = "info", details: dict | None = None) -> None:
    dt = details or {}
    payload = {
        "sensor": "synthetic",
        "level": "Level 2",
        "journey_id": _story_run_id(),
        "event_type": event_type,
        "src_ip": dt.get("src_ip", "0.0.0.0"),
        "stage": "S1",
        "outcome": "observed",
        "meta": {
            "session_id": SESSION_ID,
            "message": message,
            "component": "ml-engine",
            **dt
        }
    }
    try:
        req = urllib.request.Request(
            f"{STORY_LOGGER_URL}/story/events",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "ml_engine/5.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1.5):
            pass
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# Shared LSTM building blocks
# ═══════════════════════════════════════════════════════════════════════════════

def _build_lstm_autoencoder(n_features: int, seq_len: int, latent_dim: int):
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input, LSTM, RepeatVector, TimeDistributed, Dense
    from tensorflow.keras.optimizers import Adam

    inp     = Input(shape=(seq_len, n_features))
    encoded = LSTM(latent_dim, activation="tanh", return_sequences=False)(inp)
    repeated = RepeatVector(seq_len)(encoded)
    decoded  = LSTM(latent_dim, activation="tanh", return_sequences=True)(repeated)
    out      = TimeDistributed(Dense(n_features))(decoded)

    model = Model(inputs=inp, outputs=out)
    model.compile(optimizer=Adam(learning_rate=1e-3), loss="mse")
    return model

def _make_sequences(scaled: np.ndarray, seq_len: int) -> np.ndarray:
    seqs = []
    for i in range(len(scaled) - seq_len + 1):
        seqs.append(scaled[i : i + seq_len])
    return np.array(seqs, dtype=np.float32)

def _reconstruction_errors(model, sequences: np.ndarray) -> np.ndarray:
    preds = model.predict(sequences, verbose=0)
    return np.mean((sequences - preds) ** 2, axis=(1, 2))

# ═══════════════════════════════════════════════════════════════════════════════
# Model Training & Persistence Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _train_lstm_model(df_features: pd.DataFrame, model_path: str, scaler_path: str, name: str):
    import tensorflow as tf
    tf.get_logger().setLevel("ERROR")

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df_features.values).astype(np.float32)

    if len(scaled) < LSTM_SEQ_LEN + 1:
        print(f"[{name}] Insufficient data for sequence training.")
        return None, None, None

    sequences  = _make_sequences(scaled, LSTM_SEQ_LEN)
    n_features = scaled.shape[1]

    model = _build_lstm_autoencoder(n_features, LSTM_SEQ_LEN, LSTM_LATENT_DIM)
    model.fit(sequences, sequences, epochs=LSTM_EPOCHS, batch_size=LSTM_BATCH_SIZE, shuffle=True, verbose=0)

    train_errors = _reconstruction_errors(model, sequences)
    threshold    = float(np.percentile(train_errors, LSTM_THRESHOLD_PCTL))
    threshold    = max(threshold, LSTM_MIN_THRESHOLD)
    print(f"[{name}] Trained — threshold={threshold:.6f}")

    try:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        model.save(model_path)
        joblib.dump(scaler, scaler_path)
        joblib.dump(threshold, scaler_path + ".threshold")
        print(f"[{name}] Saved → {model_path}")
    except Exception as e:
        print(f"[{name}] Save failed: {e}")

    return model, scaler, threshold

def _load_lstm_model(model_path: str, scaler_path: str, name: str):
    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(scaler_path + ".threshold")):
        return None, None, None
    try:
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")
        model  = tf.keras.models.load_model(model_path)
        scaler = joblib.load(scaler_path)
        thresh = joblib.load(scaler_path + ".threshold")
        print(f"[{name}] Loaded from disk (threshold={thresh:.6f})")
        return model, scaler, thresh
    except Exception as e:
        print(f"[{name}] Load failed ({e})")
        return None, None, None

def _score_lstm_instance(model, scaler, threshold, df_subset: pd.DataFrame) -> tuple[bool, float]:
    if model is None or scaler is None or threshold is None:
        return False, 0.0
    if len(df_subset) < LSTM_SEQ_LEN:
        return False, 0.0

    tail   = df_subset.tail(LSTM_SEQ_LEN).values.astype(np.float32)
    scaled = np.clip(scaler.transform(tail), 0.0, 1.0)
    seq    = scaled[np.newaxis, :, :]

    error = float(_reconstruction_errors(model, seq)[0])
    effective_thresh = max(threshold, LSTM_MIN_THRESHOLD) * LSTM_ERROR_MARGIN
    return bool(error > effective_thresh), error

def _train_if_instance(df_features: pd.DataFrame, model_path: str, name: str):
    model = IsolationForest(contamination=IF_CONTAMINATION, random_state=42, n_estimators=IF_N_ESTIMATORS)
    model.fit(df_features)
    try:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        print(f"[{name}] Trained and saved → {model_path}")
    except Exception as e:
        print(f"[{name}] Save failed: {e}")
    return model

def _load_if_instance(model_path: str, name: str):
    if not os.path.exists(model_path):
        return None
    try:
        model = joblib.load(model_path)
        print(f"[{name}] Loaded from disk: {model_path}")
        return model
    except Exception as e:
        print(f"[{name}] Load failed ({e})")
        return None

def _score_if_instance(model, recent_row: pd.DataFrame) -> tuple[bool, float]:
    if model is None or recent_row.empty:
        return False, 0.0
    preds  = model.predict(recent_row)
    scores = model.decision_function(recent_row)
    score  = float(scores[0])
    return bool(preds[0] == -1 and score < IF_SCORE_THRESHOLD), score

# ── Replay LSTM training & scoring ─────────────────────────────────────────────
def _build_replay_features(pressure_values: list) -> np.ndarray | None:
    if len(pressure_values) < REPLAY_LSTM_SEQ_LEN + 5:
        return None
    s = pd.Series(pressure_values)
    p_delta   = s.diff().fillna(0).values
    roll_std  = s.rolling(5, min_periods=1).std().fillna(0).values
    base_dev  = (s - s.iloc[0]).abs().values
    return np.column_stack([p_delta, roll_std, base_dev]).astype(np.float32)

def _train_replay_lstm(pressure_values: list):
    feat = _build_replay_features(pressure_values)
    if feat is None or len(feat) < REPLAY_LSTM_SEQ_LEN + 1:
        return None, None, None
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(feat).astype(np.float32)
    seqs   = _make_sequences(scaled, REPLAY_LSTM_SEQ_LEN)
    model  = _build_lstm_autoencoder(scaled.shape[1], REPLAY_LSTM_SEQ_LEN, REPLAY_LSTM_LATENT_DIM)
    model.fit(seqs, seqs, epochs=REPLAY_LSTM_EPOCHS, batch_size=REPLAY_LSTM_BATCH_SIZE, shuffle=True, verbose=0)
    errors = _reconstruction_errors(model, seqs)
    thresh = float(np.percentile(errors, REPLAY_LSTM_THRESHOLD_PCTL))
    try:
        model.save(REPLAY_LSTM_FILE)
        joblib.dump(scaler, REPLAY_SCALER_FILE)
        joblib.dump(thresh, REPLAY_SCALER_FILE + ".threshold")
    except Exception:
        pass
    return model, scaler, thresh

def _score_replay_lstm(pressure_values: list) -> tuple[bool, float]:
    global _replay_lstm_model, _replay_lstm_scaler, _replay_lstm_thresh
    if _replay_lstm_model is None or _replay_lstm_scaler is None or _replay_lstm_thresh is None:
        return False, 0.0
    feat = _build_replay_features(pressure_values)
    if feat is None or len(feat) < REPLAY_LSTM_SEQ_LEN:
        return False, 0.0
    tail = feat[-REPLAY_LSTM_SEQ_LEN:]
    try:
        scaled = np.clip(_replay_lstm_scaler.transform(tail), 0.0, 1.0)
        seq    = scaled[np.newaxis, :, :]
        err    = float(_reconstruction_errors(_replay_lstm_model, seq)[0])
        return bool(err > _replay_lstm_thresh), err
    except Exception:
        return False, 0.0

# ═══════════════════════════════════════════════════════════════════════════════
# Initialization & Disk Loading
# ═══════════════════════════════════════════════════════════════════════════════

_if_proc_model                     = _load_if_instance(IF_PROC_FILE, "IF-proc")
_if_net_model                      = _load_if_instance(IF_NET_FILE, "IF-net")
_lstm_proc_model, _lstm_proc_scaler, _lstm_proc_thresh = _load_lstm_model(LSTM_PROC_FILE, SCALER_PROC_FILE, "LSTM-AE-proc")
_lstm_net_model,  _lstm_net_scaler,  _lstm_net_thresh  = _load_lstm_model(LSTM_NET_FILE,  SCALER_NET_FILE,  "LSTM-AE-net")
_replay_lstm_model, _replay_lstm_scaler, _replay_lstm_thresh = _load_lstm_model(REPLAY_LSTM_FILE, REPLAY_SCALER_FILE, "Replay-LSTM")

print(f"--- ML ENGINE v8 (Decoupled Suite & 5 Layers) [session={SESSION_ID}] ---")
print(f"    Grace period    : {STARTUP_GRACE_SECONDS}s")
print(f"    IF proc on disk : {_if_proc_model is not None}")
print(f"    IF net on disk  : {_if_net_model is not None}")
print(f"    LSTM proc disk  : {_lstm_proc_model is not None}")
print(f"    LSTM net disk   : {_lstm_net_model is not None}")

db_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = db_client.write_api(write_options=SYNCHRONOUS)
query_api = db_client.query_api()

_api_state = {
    "model_ready":       _if_proc_model is not None and _if_net_model is not None,
    "lstm_ready":        _lstm_proc_model is not None and _lstm_net_model is not None,
    "replay_lstm_ready": _replay_lstm_model is not None,
    "in_warmup":         _if_proc_model is None,
    "in_grace":          True,
    "sample_count":      0,
    "last_if_proc_score":None,
    "last_if_net_score": None,
    "last_lstm_proc_err":None,
    "last_lstm_net_err": None,
    "layer_0_active":    0,
    "layer_1_active":    0,
    "layer_2_active":    0,
    "layer_3_active":    0,
    "layer_4_active":    0,
    "alert_fused_active":0,
    "fused_status":      "NORMAL",
    "fused_score":       0.5,
    "recent_alerts":     collections.deque(maxlen=200),
    "ewma":              None,
    "cusum_pos":         0.0,
    "cusum_neg":         0.0,
}
_api_lock = threading.Lock()

def _write_grafana_event(metric_type: str, value: float, event_type: str, severity: str, source: str, detail: str = "") -> None:
    try:
        p = (Point("grafana_events")
             .tag("metric_type", metric_type)
             .tag("event_type",  event_type)
             .tag("severity",    severity)
             .tag("source",      source)
             .tag("session_id",  SESSION_ID)
             .field("value",     float(value))
             .field("detail",    str(detail)[:256])
             .time(time.time_ns(), WritePrecision.NS))
        write_api.write(bucket=INFLUX_BUCKET, record=p)
    except Exception:
        pass

def _record_alert(alert_type: str, detail: str, score: float) -> None:
    with _api_lock:
        _api_state["recent_alerts"].append({
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "alert_type": alert_type,
            "detail":     detail,
            "score":      score,
            "session_id": SESSION_ID,
        })

# ═══════════════════════════════════════════════════════════════════════════════
# Feature Extraction (Decoupled Process and Network)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_pipeline_features(lookback: str = "-1h") -> pd.DataFrame:
    query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {lookback})
  |> filter(fn: (r) => r["_measurement"] == "pipeline_metrics")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''
    try:
        result = query_api.query_data_frame(query)
        if isinstance(result, list):
            result = pd.concat(result) if result else pd.DataFrame()
        if result.empty:
            return pd.DataFrame()
    except Exception as e:
        print(f"InfluxDB fetch error: {e}")
        return pd.DataFrame()

    for col in ["pressure", "flow_rate", "temperature", "pump_rpm"]:
        if col not in result.columns:
            result[col] = 0.0

    result["_time"] = pd.to_datetime(result["_time"]).dt.tz_localize(None)
    result = result.sort_values("_time").reset_index(drop=True)

    result["inter_arrival_time"]    = result["_time"].diff().dt.total_seconds().fillna(0)
    result["pressure_delta"]        = result["pressure"].diff().fillna(0)
    result["pressure_rolling_mean"] = result["pressure"].rolling(10, min_periods=1).mean()
    result["pressure_mean_dev"]     = result["pressure"] - result["pressure_rolling_mean"]

    result["write_freq_10s"] = 0.0
    result["is_write"]       = 0
    result["func_code"]      = 0
    result["length"]         = 0

    try:
        net_query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {lookback})
  |> filter(fn: (r) => r["_measurement"] == "correlation_logs")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''
        net = query_api.query_data_frame(net_query)
        if isinstance(net, list):
            net = pd.concat(net) if net else pd.DataFrame()
        if not net.empty:
            net["_time"] = pd.to_datetime(net["_time"]).dt.tz_localize(None)
            net = net.sort_values("_time").reset_index(drop=True)
            net["is_write"]  = 1
            net["func_code"] = 6
            net["length"]    = net.get("value", pd.Series([0] * len(net))).astype(int)
            net_idx = net.set_index("_time")
            net_idx["write_freq_10s"] = net_idx["is_write"].rolling("10s").sum().fillna(0)
            net["write_freq_10s"] = net_idx["write_freq_10s"].values
            result = pd.merge_asof(
                result,
                net[["_time", "is_write", "func_code", "length", "write_freq_10s"]],
                on="_time", direction="backward",
                tolerance=pd.Timedelta("1s")
            )
            for col in ["is_write", "func_code", "length", "write_freq_10s"]:
                new_col = col + "_y"
                if new_col in result.columns:
                    result[col] = result[new_col].fillna(
                        result[col + "_x"] if col + "_x" in result.columns else 0
                    )
                    result.drop(
                        columns=[c for c in [col + "_x", col + "_y"] if c in result.columns],
                        inplace=True
                    )
    except Exception as e:
        pass

    for c in PROC_FEATURES + NET_FEATURES:
        if c not in result.columns:
            result[c] = 0.0

    return result

# ═══════════════════════════════════════════════════════════════════════════════
# CUSUM / EWMA & Expert Rules
# ═══════════════════════════════════════════════════════════════════════════════

def run_ewma_cusum(current_pressure: float) -> tuple[bool, str]:
    global _ewma_state, _cusum_pos, _cusum_neg, _cumulative_dev
    if _ewma_state is None:
        _ewma_state = current_pressure
        _cusum_pos = 0.0
        _cusum_neg = 0.0
        _cumulative_dev = 0.0
        return False, "EWMA baseline initialized"

    _ewma_state = EWMA_ALPHA * current_pressure + (1.0 - EWMA_ALPHA) * _ewma_state
    dev = current_pressure - _ewma_state
    _cumulative_dev += dev

    _cusum_pos = max(0.0, _cusum_pos + dev - CUSUM_K)
    _cusum_neg = min(0.0, _cusum_neg + dev + CUSUM_K)

    _pressure_history.append(current_pressure)
    if len(_pressure_history) >= 2:
        s = (_pressure_history[-1] - _pressure_history[0]) / len(_pressure_history)
        _slope_history.append(s)

    with _api_lock:
        _api_state["ewma"]      = round(_ewma_state, 3)
        _api_state["cusum_pos"] = round(_cusum_pos, 3)
        _api_state["cusum_neg"] = round(_cusum_neg, 3)

    drift_detected = (_cusum_pos > CUSUM_THRESHOLD) or (_cusum_neg < -CUSUM_THRESHOLD)
    detail = (f"P={current_pressure:.2f} EWMA={_ewma_state:.2f} "
              f"C+={_cusum_pos:.2f} C-={_cusum_neg:.2f} Dev={_cumulative_dev:.2f}")
    return drift_detected, detail

def has_recent_writes() -> bool:
    query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -60s)
  |> filter(fn: (r) => r["_measurement"] == "modbus_events"
                   and r["fc_type"] == "write"
                   and r["_field"] == "register")
  |> filter(fn: (r) => r["_value"] >= 200.0)
  |> count()
'''
    try:
        tables = query_api.query(query)
        for table in tables:
            for record in table.records:
                if record.get_value() > 0:
                    return True
    except Exception:
        pass
    return False

def _sensor_writes_detected() -> bool:
    query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -60s)
  |> filter(fn: (r) => r["_measurement"] == "modbus_events"
                   and r["fc_type"] == "write"
                   and r["_field"] == "register")
  |> filter(fn: (r) => r["_value"] < 200.0 and r["_value"] >= 100.0)
  |> count()
'''
    try:
        tables = query_api.query(query)
        for table in tables:
            for record in table.records:
                if record.get_value() > 0:
                    return True
    except Exception:
        pass
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# 5 Hierarchical Detection Layer Evaluators
# ═══════════════════════════════════════════════════════════════════════════════

def query_event_count(measurement: str, field_filter: str = "", lookback: str = "-60s") -> int:
    f_clause = f'and {field_filter}' if field_filter else ''
    q = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {lookback})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}" {f_clause})
  |> count()
'''
    try:
        for t in query_api.query(q):
            for r in t.records:
                v = r.get_value()
                if v and v > 0:
                    return int(v)
    except Exception:
        pass
    return 0

def evaluate_layers(features: pd.DataFrame, ml_states: dict) -> dict:
    """
    Evaluates Layers 0 through 4 based on physical invariants, telemetry, and Influx logs.
    """
    recent = features.tail(1)
    p_curr = float(recent["pressure"].iloc[0]) if not recent.empty else 132.0
    w_freq = float(recent["write_freq_10s"].iloc[0]) if not recent.empty else 0.0

    # Layer 0: Process Dynamics & Invariants
    # Nominal operating pressure is ~132.0 PSI (1200 RPM pump, 50% valve).
    # Normal regulation envelope: 90.0 - 180.0 PSI.
    # Anomaly triggers on dynamic CUSUM drift, over/under pressure trips, or ML model detection.
    drift, _ = run_ewma_cusum(p_curr)
    l0_active = int(drift or p_curr > 185.0 or p_curr < 50.0 or ml_states["is_if_proc_anom"] or ml_states["is_lstm_proc_anom"])

    # Layer 1: Fieldbus & Controller (Modbus / S7 / DNP3)
    modbus_writes = query_event_count("modbus_events", 'r["fc_type"] == "write"')
    s7_writes     = query_event_count("s7comm_events", 'r["function"] == "write"')
    forced_writes = _sensor_writes_detected() or has_recent_writes()
    l1_active     = int(forced_writes or modbus_writes > 0 or s7_writes > 0 or w_freq > 2.0 or ml_states["is_if_net_anom"] or ml_states["is_lstm_net_anom"])

    # Layer 2: SCADA & Operations
    ssh_fails = query_event_count("hplog", 'r["sensor"] == "scada"')
    l2_active = int(ssh_fails > 0)

    # Layer 3: Enterprise & Workstations
    ws_cmds = query_event_count("external_events", 'r["event_type"] == "WORKSTATION_COMMAND"')
    l3_active = int(ws_cmds > 0)

    # Layer 4: Perimeter & DMZ Gateway
    gw_anom = query_event_count("honeypot_attacker_telemetry", 'r["device"] == "dmz_gateway" and r["is_anomaly"] == 1')
    l4_active = int(gw_anom > 0)

    return {
        "l0": l0_active,
        "l1": l1_active,
        "l2": l2_active,
        "l3": l3_active,
        "l4": l4_active
    }

# ═══════════════════════════════════════════════════════════════════════════════
# Alert Fused (Narrow Mechanism Gate NMG Logic)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_alert_fused(layers: dict, ml_states: dict, recent_features: pd.DataFrame) -> tuple[int, str, float, str]:
    l0, l1, l2, l3, l4 = layers["l0"], layers["l1"], layers["l2"], layers["l3"], layers["l4"]
    w_freq = float(recent_features["write_freq_10s"].iloc[-1]) if not recent_features.empty else 0.0
    p_curr = float(recent_features["pressure"].iloc[-1]) if not recent_features.empty else 132.0

    # Narrow Mechanism Gate (NMG) Conditions:
    # Stealth manipulation: Layer 0 active with major drift from nominal 132 PSI baseline (> 35 PSI) without Modbus writes
    stealth_manipulation  = bool(l0 and w_freq == 0 and abs(p_curr - 132.0) > 35.0)
    cyber_physical_attack = bool(l1 and l0)
    multi_layer_consensus = sum([l0, l1, l2, l3, l4]) >= 2
    ml_cross_consensus    = bool((ml_states["is_if_proc_anom"] or ml_states["is_lstm_proc_anom"]) and
                                 (ml_states["is_if_net_anom"]  or ml_states["is_lstm_net_anom"]))

    is_alert_fused = int(stealth_manipulation or cyber_physical_attack or multi_layer_consensus or ml_cross_consensus)

    if is_alert_fused:
        status = "ATTACK_CONFIRMED"
        score  = -1.0
        reason = "NMG Gated Attack Confirmed (Cross-Layer / Cyber-Physical)"
    elif sum([l0, l1, l2, l3, l4]) > 0 or any(ml_states.values()):
        status = "SUSPICIOUS"
        score  = -0.5
        reason = "Isolated Anomaly Observed"
    else:
        status = "NORMAL"
        score  = 0.5
        reason = "Nominal Baseline"

    return is_alert_fused, status, score, reason

# ═══════════════════════════════════════════════════════════════════════════════
# Main ML & Detection Cycle
# ═══════════════════════════════════════════════════════════════════════════════

def run_ml_cycle() -> None:
    features = fetch_pipeline_features(lookback="-2h")
    with _api_lock:
        _api_state["sample_count"] = len(features)
        _api_state["in_grace"]     = in_grace_period()

    if len(features) < MIN_SAMPLES:
        print(f"Collecting samples... ({len(features)}/{MIN_SAMPLES})")
        return

    global _if_proc_model, _if_net_model, _lstm_proc_model, _lstm_proc_scaler, _lstm_proc_thresh
    global _lstm_net_model, _lstm_net_scaler, _lstm_net_thresh, _replay_lstm_model

    # ── Training / Warmup Phase ───────────────────────────────────────────────
    needs_training = (_if_proc_model is None or _if_net_model is None or
                      _lstm_proc_model is None or _lstm_net_model is None)

    if needs_training:
        print("[ML] Training decoupled 4-model suite on live data...")
        with _api_lock:
            _api_state["in_warmup"] = True

        if _if_proc_model is None:
            _if_proc_model = _train_if_instance(features[PROC_FEATURES], IF_PROC_FILE, "IF-proc")
        if _if_net_model is None:
            _if_net_model = _train_if_instance(features[NET_FEATURES], IF_NET_FILE, "IF-net")
        if _lstm_proc_model is None:
            _lstm_proc_model, _lstm_proc_scaler, _lstm_proc_thresh = _train_lstm_model(features[PROC_FEATURES], LSTM_PROC_FILE, SCALER_PROC_FILE, "LSTM-AE-proc")
        if _lstm_net_model is None:
            _lstm_net_model, _lstm_net_scaler, _lstm_net_thresh = _train_lstm_model(features[NET_FEATURES], LSTM_NET_FILE, SCALER_NET_FILE, "LSTM-AE-net")
        if _replay_lstm_model is None:
            _replay_lstm_model, _replay_lstm_scaler, _replay_lstm_thresh = _train_replay_lstm(features["pressure"].tolist())

        with _api_lock:
            _api_state["in_warmup"]   = False
            _api_state["model_ready"] = True
            _api_state["lstm_ready"]  = True

    # ── Detection Phase ───────────────────────────────────────────────────────
    if in_grace_period():
        rem = STARTUP_GRACE_SECONDS - (time.time() - _boot_time)
        print(f"[GRACE] {rem:.0f}s remaining — evaluating models without alert dispatch.")
        return

    recent = features.tail(1)

    # 1. Score the 4 ML Engines
    is_if_proc_anom, if_proc_score = _score_if_instance(_if_proc_model, recent[PROC_FEATURES])
    is_if_net_anom,  if_net_score  = _score_if_instance(_if_net_model,  recent[NET_FEATURES])
    is_lstm_proc_anom, lstm_proc_err = _score_lstm_instance(_lstm_proc_model, _lstm_proc_scaler, _lstm_proc_thresh, features[PROC_FEATURES])
    is_lstm_net_anom,  lstm_net_err  = _score_lstm_instance(_lstm_net_model,  _lstm_net_scaler,  _lstm_net_thresh,  features[NET_FEATURES])

    ml_states = {
        "is_if_proc_anom": is_if_proc_anom,
        "is_if_net_anom":  is_if_net_anom,
        "is_lstm_proc_anom": is_lstm_proc_anom,
        "is_lstm_net_anom":  is_lstm_net_anom
    }

    # 2. Evaluate the 5 Detection Layers
    layers = evaluate_layers(features, ml_states)

    # 3. Compute Narrow Mechanism Gate Alert Fusion
    is_alert_fused, fused_status, fused_score, reason = compute_alert_fused(layers, ml_states, recent)

    with _api_lock:
        _api_state["last_if_proc_score"] = round(if_proc_score, 4)
        _api_state["last_if_net_score"]  = round(if_net_score, 4)
        _api_state["last_lstm_proc_err"] = round(lstm_proc_err, 6)
        _api_state["last_lstm_net_err"]  = round(lstm_net_err, 6)
        _api_state["layer_0_active"]     = layers["l0"]
        _api_state["layer_1_active"]     = layers["l1"]
        _api_state["layer_2_active"]     = layers["l2"]
        _api_state["layer_3_active"]     = layers["l3"]
        _api_state["layer_4_active"]     = layers["l4"]
        _api_state["alert_fused_active"] = is_alert_fused
        _api_state["fused_status"]       = fused_status
        _api_state["fused_score"]        = fused_score

    # 4. Stream Structured Security Metrics to InfluxDB
    point = (
        Point("security_metrics")
        .tag("sensor", "ml_engine")
        .tag("session_id", SESSION_ID)
        .tag("fused_status", fused_status)
        .field("is_anomaly", int(is_alert_fused))
        .field("anomaly_score", float(fused_score))
        .field("alert_fused_active", int(is_alert_fused))
        .field("alert_fused_score", float(fused_score))
        .field("layer_0_active", layers["l0"])
        .field("layer_1_active", layers["l1"])
        .field("layer_2_active", layers["l2"])
        .field("layer_3_active", layers["l3"])
        .field("layer_4_active", layers["l4"])
        .field("active_layers_count", sum(layers.values()))
        .field("lstm_ae_proc_error", float(lstm_proc_err))
        .field("lstm_ae_proc_anom", int(is_lstm_proc_anom))
        .field("lstm_ae_net_error", float(lstm_net_err))
        .field("lstm_ae_net_anom", int(is_lstm_net_anom))
        .field("if_proc_score", float(if_proc_score))
        .field("if_proc_anom", int(is_if_proc_anom))
        .field("if_net_score", float(if_net_score))
        .field("if_net_anom", int(is_if_net_anom))
        .time(time.time_ns(), WritePrecision.NS)
    )
    if is_alert_fused:
        _mitre_enrich(point, "alert_fused")
    write_api.write(bucket=INFLUX_BUCKET, record=point)

    # 5. Dispatch Alert Events
    if is_alert_fused:
        print(f"!!! ALERT FUSED TRIGGERED ({fused_status}) !!! {reason}")
        _record_alert("ALERT_FUSED", reason, fused_score)
        f_p = (Point("security_alerts")
               .tag("alert_type", "ALERT_FUSED")
               .tag("session_id", SESSION_ID)
               .field("detail", reason)
               .field("score", fused_score)
               .time(time.time_ns(), WritePrecision.NS))
        _mitre_enrich(f_p, "alert_fused")
        write_api.write(bucket=INFLUX_BUCKET, record=f_p)
        _write_grafana_event("alert_fused", fused_score, "ALERT_FUSED", "critical", "ml-engine", reason)

    # Layer specific alert dispatches
    for idx, (l_key, l_val) in enumerate(layers.items()):
        if l_val == 1:
            l_name = f"layer_{idx}_detection"
            _record_alert(l_name.upper(), f"Layer {idx} active anomaly", -0.8)
            l_p = (Point("security_alerts")
                   .tag("alert_type", l_name.upper())
                   .tag("session_id", SESSION_ID)
                   .field("detail", f"Layer {idx} active")
                   .field("score", -0.8)
                   .time(time.time_ns(), WritePrecision.NS))
            _mitre_enrich(l_p, l_name)
            write_api.write(bucket=INFLUX_BUCKET, record=l_p)

    print(
        f"[ML] Proc=(IF:{if_proc_score:.3f} LSTM:{lstm_proc_err:.4f}) | "
        f"Net=(IF:{if_net_score:.3f} LSTM:{lstm_net_err:.4f}) | "
        f"Layers=[{layers['l0']},{layers['l1']},{layers['l2']},{layers['l3']},{layers['l4']}] | "
        f"Fused={fused_status}"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# Background API Server
# ═══════════════════════════════════════════════════════════════════════════════

def _start_api_server() -> None:
    try:
        from fastapi import FastAPI, Query as FQuery
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn

        app = FastAPI(title="ICS Honeypot Monitor Zone ML Engine", version="8.0.0")
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

        @app.get("/health")
        def health():
            with _api_lock:
                return {
                    "status":            "ok",
                    "session_id":        SESSION_ID,
                    "model_ready":       _api_state["model_ready"],
                    "lstm_ready":        _api_state["lstm_ready"],
                    "in_warmup":         _api_state["in_warmup"],
                    "in_grace":          _api_state["in_grace"],
                    "sample_count":      _api_state["sample_count"],
                    "fused_status":      _api_state["fused_status"],
                    "uptime_seconds":    round(time.time() - _boot_time, 1)
                }

        @app.get("/alerts")
        def get_alerts(limit: int = FQuery(default=200, le=1000)):
            with _api_lock:
                alerts = list(_api_state["recent_alerts"])
            return {"count": len(alerts), "alerts": alerts[-limit:][::-1]}

        @app.get("/metrics")
        def get_metrics():
            with _api_lock:
                return dict(_api_state)

        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    except Exception as e:
        print(f"[API] Error: {e}")

api_thread = threading.Thread(target=_start_api_server, daemon=True)
api_thread.start()
time.sleep(2)
_story_log("ml_engine_started", "ML engine startup complete (4 models + 5 layers)", details={"session_id": SESSION_ID})

# ═══════════════════════════════════════════════════════════════════════════════
# Main Detection Loop
# ═══════════════════════════════════════════════════════════════════════════════
print(f"[ML] Entering Monitor Zone detection loop. Grace period ends in {STARTUP_GRACE_SECONDS}s.")
while True:
    try:
        run_ml_cycle()
    except Exception as e:
        print(f"ML loop error: {e}")
    time.sleep(LOOP_INTERVAL)
