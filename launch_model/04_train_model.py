"""
Script 04 — Train the Model
Soft Voting Ensemble: RandomForestClassifier + LogisticRegression
Output: models/ensemble.pkl, models/scaler.pkl, models/shap_explainer.pkl
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import joblib
import shap
import os
import json
from pathlib import Path

# --- [TRACKING] ---
TRACKING_ENABLED = os.getenv("TRACKING_ENABLED", "true") == "true"
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from utils.logger import setup_logger
    from utils.run_tracker import track_stage, set_logger
    _logger, _log_file = setup_logger(run_name="training")
    set_logger(_logger)
except Exception as _e:
    import logging
    _logger = logging.getLogger(__name__)
    _log_file = None
    track_stage = lambda name: (lambda fn: fn)
    print(f"[TRACKING] Logger setup failed (non-fatal): {_e}")

try:
    import mlflow
    import mlflow.sklearn
    from tracking.setup import init_tracking
except Exception as _e:
    print(f"[TRACKING] MLflow import failed (non-fatal): {_e}")
    mlflow = None
    init_tracking = None
# --- [TRACKING] ---

Path("models").mkdir(exist_ok=True)
Path("metrics").mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# Load training data
# ─────────────────────────────────────────────
_logger.info("=== SCRIPT 04: training START ===")

# --- [TRACKING] Load config params for MLflow ---
try:
    import yaml
    with open("configs/model_config.yaml") as _cfg_f:
        _config = yaml.safe_load(_cfg_f)
    _logger.info(f"Config loaded: {_config}")
except Exception as _cfg_e:
    _config = {}
    _logger.warning(f"[TRACKING] Could not load model_config.yaml: {_cfg_e}")

_tracking_ctx = init_tracking(run_name="train_run", experiment_name="astrogeo-launch-go-nogo") if (TRACKING_ENABLED and init_tracking) else __import__("contextlib").nullcontext()

with _tracking_ctx:
  try:
    # --- [TRACKING] Log hyper-params ---
    if TRACKING_ENABLED and mlflow:
        try:
            if _config:
                mlflow.log_params(_config)
        except Exception as _e:
            _logger.warning(f"[TRACKING] mlflow.log_params failed: {_e}")

    df = pd.read_csv('data/training_data.csv', parse_dates=['launch_date'])

    FEATURE_COLS = [
    'cloud_cover_pct', 'wind_speed_ms', 'precipitation_mm', 'temperature_c',
    'relative_humidity_pct', 'surface_pressure_hpa', 'precip_3day_sum',
    'cloud_cover_day_minus_1', 'wind_speed_max_3day', 'month', 'is_monsoon_season',
    'day_of_year', 'is_cyclone_season', 'vehicle_PSLV', 'vehicle_GSLV',
    'vehicle_LVM3', 'vehicle_Falcon'
    ]
    TARGET_COL = 'label'

    available_features = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_features]
    y = df[TARGET_COL]

    print(f"Dataset: {X.shape} | Labels -> 1:{y.sum()} Go, 0:{(y==0).sum()} No-Go")
    _logger.info(f"Dataset: {X.shape[0]} rows, {X.shape[1]} features | Go:{int(y.sum())} No-Go:{int((y==0).sum())}")

    # --- [TRACKING] Dataset stats ---
    if TRACKING_ENABLED and mlflow:
        try:
            mlflow.log_param("dataset_rows", X.shape[0])
            mlflow.log_param("dataset_features", X.shape[1])
        except Exception as _e:
            _logger.warning(f"[TRACKING] dataset param logging failed: {_e}")

    # ─────────────────────────────────────────────
    # Sanity check (doc section 7.5)
    # ─────────────────────────────────────────────
    nogo_pct = (y == 0).mean() * 100
    if nogo_pct < 10:
        print(f"WARNING: Only {nogo_pct:.1f}% No-Go examples. Model may underfit. "
              "Consider adding more scrub/delay records.")

    # ─────────────────────────────────────────────
    # Train / test split (time-aware: future launches for test)
    # ─────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Fit scaler ONLY on training data (doc note: avoid leakage)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    # ─────────────────────────────────────────────
    # Model architecture (doc section 7.1)
    # Soft voting ensemble: RF + LR
    # ─────────────────────────────────────────────
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=5,
        class_weight='balanced',   # handles class imbalance
        random_state=42
    )

    lr = LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight='balanced',
        random_state=42
    )

    ensemble = VotingClassifier(
        estimators=[('rf', rf), ('lr', lr)],
        voting='soft'             # average predict_proba() outputs
    )

    # ─────────────────────────────────────────────
    # Train
    # ─────────────────────────────────────────────
    print("Training ensemble...")
    _logger.info("Fitting ensemble model...")
    ensemble.fit(X_train_scaled, y_train)

    # ─────────────────────────────────────────────
    # Evaluation
    # ─────────────────────────────────────────────
    y_proba = ensemble.predict_proba(X_test_scaled)[:, 1]
    y_pred  = ensemble.predict(X_test_scaled)

    auc = roc_auc_score(y_test, y_proba)
    print(f"\nROC-AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Cross-validation to confirm
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(ensemble, X_train_scaled, y_train, cv=cv, scoring='roc_auc')
    print(f"\n5-Fold CV AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    if auc < 0.80:
        print("\nWARNING: ROC-AUC below 0.80. Consider: "
              "adding scrub examples, increasing max_depth to 8, "
              "or checking feature importance for leakage.")

    # --- [TRACKING] Log evaluation metrics ---
    _scores = {"roc_auc": round(auc, 6),
               "cv_auc_mean": round(float(cv_scores.mean()), 6),
               "cv_auc_std": round(float(cv_scores.std()), 6)}
    _logger.success(f"Metrics: {_scores}")
    if TRACKING_ENABLED and mlflow:
        try:
            mlflow.log_metrics(_scores)
        except Exception as _e:
            _logger.warning(f"[TRACKING] metric logging failed: {_e}")
    # Save scores.json for DVC metrics
    with open("metrics/scores.json", "w") as _mf:
        json.dump(_scores, _mf, indent=2)
    _logger.info("Saved metrics/scores.json")

    # ─────────────────────────────────────────────
    # SHAP explainer (uses only the Random Forest)
    # ─────────────────────────────────────────────
    print("\nBuilding SHAP explainer...")
    _logger.info("Building SHAP explainer...")
    rf_fitted = ensemble.named_estimators_['rf']
    explainer = shap.TreeExplainer(rf_fitted)

    # ─────────────────────────────────────────────
    # Save artifacts
    # ─────────────────────────────────────────────
    joblib.dump(ensemble, 'models/ensemble.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')
    joblib.dump(explainer, 'models/shap_explainer.pkl')

    # Save feature column list so inference scripts know the order
    with open('models/feature_cols.json', 'w') as f:
        json.dump(available_features, f)

    print(f"\nSaved: models/ensemble.pkl, models/scaler.pkl, "
          f"models/shap_explainer.pkl, models/feature_cols.json")
    _logger.success("Model artifacts saved to models/")

    # --- [TRACKING] Log model + artifacts to MLflow ---
    if TRACKING_ENABLED and mlflow:
        try:
            mlflow.sklearn.log_model(
                ensemble, "model",
                registered_model_name="astrogeo-launch-go-nogo"
            )
            mlflow.log_artifact("models/feature_cols.json", "model_meta")
            if _log_file:
                mlflow.log_artifact(_log_file, "logs")
            mlflow.set_tag("run_status", "SUCCESS")
            _logger.success("[TRACKING] MLflow model + artifacts logged.")
        except Exception as _e:
            _logger.warning(f"[TRACKING] MLflow model logging failed (non-fatal): {_e}")

    _logger.info("=== SCRIPT 04: training DONE ===")

  except Exception as _run_exc:
    _logger.critical(f"RUN FAILED: {type(_run_exc).__name__}: {_run_exc}")
    if TRACKING_ENABLED and mlflow:
        try:
            import traceback as _tb_mod
            mlflow.set_tag("run_status", "FAILED")
            mlflow.set_tag("failure_reason", str(_run_exc)[:300])
            mlflow.log_text(_tb_mod.format_exc(), "errors/training_traceback.txt")
            if _log_file:
                mlflow.log_artifact(_log_file, "logs")
        except Exception:
            pass
    raise
