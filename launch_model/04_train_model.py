"""
Script 04 — Train the Model
Soft Voting Ensemble: RandomForestClassifier + LogisticRegression
Output: models/ensemble.pkl, models/scaler.pkl, models/shap_explainer.pkl

COMPREHENSIVE MLflow + WANDB + DagsHub tracking:
- Per-model metrics (RF, LR, Ensemble)
- Dataset profiling
- Confusion matrix & classification report
- SHAP summary & feature importance plots
- Feature correlations
- All hyperparameters & model architecture
"""
import os, sys
# Fix Windows cp1252 stdout crash when MLflow prints emoji
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np
import hashlib
import time
import platform
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, classification_report, confusion_matrix,
    accuracy_score, precision_score, recall_score, f1_score,
    log_loss, matthews_corrcoef, cohen_kappa_score,
    balanced_accuracy_score, mean_squared_error, mean_absolute_error,
    r2_score, precision_recall_curve, roc_curve, brier_score_loss
)
import joblib
import shap
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

try:
    import wandb
except ImportError:
    print(f"[TRACKING] wandb import failed. Run pip install wandb")
    wandb = None
# --- [TRACKING] ---

Path("models").mkdir(exist_ok=True)
Path("metrics").mkdir(exist_ok=True)
Path("plots").mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Compute ALL metrics for any model
# ══════════════════════════════════════════════════════════════════════════════
def compute_all_metrics(model, X_test, y_test, prefix=""):
    """Compute every classification + regression-style metric for a model."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        # --- Classification core ---
        f"{prefix}accuracy": round(accuracy_score(y_test, y_pred), 6),
        f"{prefix}balanced_accuracy": round(balanced_accuracy_score(y_test, y_pred), 6),
        f"{prefix}roc_auc": round(roc_auc_score(y_test, y_proba), 6),
        f"{prefix}log_loss": round(log_loss(y_test, y_proba), 6),
        f"{prefix}brier_score": round(brier_score_loss(y_test, y_proba), 6),
        f"{prefix}matthews_corrcoef": round(matthews_corrcoef(y_test, y_pred), 6),
        f"{prefix}cohen_kappa": round(cohen_kappa_score(y_test, y_pred), 6),

        # --- Per-class precision/recall/f1 ---
        f"{prefix}precision_class0": round(report['0']['precision'], 6),
        f"{prefix}precision_class1": round(report['1']['precision'], 6),
        f"{prefix}recall_class0": round(report['0']['recall'], 6),
        f"{prefix}recall_class1": round(report['1']['recall'], 6),
        f"{prefix}f1_class0": round(report['0']['f1-score'], 6),
        f"{prefix}f1_class1": round(report['1']['f1-score'], 6),

        # --- Weighted / Macro averages ---
        f"{prefix}precision_weighted": round(precision_score(y_test, y_pred, average='weighted'), 6),
        f"{prefix}precision_macro": round(precision_score(y_test, y_pred, average='macro'), 6),
        f"{prefix}recall_weighted": round(recall_score(y_test, y_pred, average='weighted'), 6),
        f"{prefix}recall_macro": round(recall_score(y_test, y_pred, average='macro'), 6),
        f"{prefix}f1_weighted": round(f1_score(y_test, y_pred, average='weighted'), 6),
        f"{prefix}f1_macro": round(f1_score(y_test, y_pred, average='macro'), 6),

        # --- Regression-style (treating predictions as continuous) ---
        f"{prefix}mse": round(mean_squared_error(y_test, y_pred), 6),
        f"{prefix}rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 6),
        f"{prefix}mae": round(mean_absolute_error(y_test, y_pred), 6),
        f"{prefix}r2_score": round(r2_score(y_test, y_pred), 6),

        # --- Confusion matrix components ---
        f"{prefix}true_positives": int(tp),
        f"{prefix}true_negatives": int(tn),
        f"{prefix}false_positives": int(fp),
        f"{prefix}false_negatives": int(fn),
        f"{prefix}specificity": round(tn / (tn + fp) if (tn + fp) > 0 else 0, 6),
        f"{prefix}sensitivity": round(tp / (tp + fn) if (tp + fn) > 0 else 0, 6),
    }
    return metrics, y_pred, y_proba, cm, report


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Generate and save confusion matrix plot
# ══════════════════════════════════════════════════════════════════════════════
def save_confusion_matrix_plot(cm, model_name, filename):
    """Save a confusion matrix heatmap as PNG."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                    xticklabels=['No-Go (0)', 'Go (1)'],
                    yticklabels=['No-Go (0)', 'Go (1)'])
        ax.set_xlabel('Predicted', fontsize=12)
        ax.set_ylabel('Actual', fontsize=12)
        ax.set_title(f'Confusion Matrix — {model_name}', fontsize=14)
        plt.tight_layout()
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        _logger.warning(f"Could not save confusion matrix plot: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Generate and save feature importance plot
# ══════════════════════════════════════════════════════════════════════════════
def save_feature_importance_plot(importances, feature_names, filename):
    """Save feature importance bar chart as PNG."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        sorted_idx = np.argsort(importances)
        fig, ax = plt.subplots(figsize=(10, max(6, len(feature_names) * 0.4)))
        ax.barh(range(len(sorted_idx)), importances[sorted_idx], color='steelblue')
        ax.set_yticks(range(len(sorted_idx)))
        ax.set_yticklabels([feature_names[i] for i in sorted_idx])
        ax.set_xlabel('Importance', fontsize=12)
        ax.set_title('Random Forest Feature Importance', fontsize=14)
        plt.tight_layout()
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        _logger.warning(f"Could not save feature importance plot: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Generate SHAP summary plot
# ══════════════════════════════════════════════════════════════════════════════
def save_shap_summary_plot(explainer, X_data, feature_names, filename):
    """Save SHAP summary (beeswarm) plot as PNG."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        sv = explainer.shap_values(X_data)
        if isinstance(sv, list):
            sv = sv[1]
        elif len(np.shape(sv)) == 3:
            sv = sv[:, :, 1]

        fig, ax = plt.subplots(figsize=(12, max(6, len(feature_names) * 0.4)))
        shap.summary_plot(sv, X_data, feature_names=feature_names,
                          show=False, plot_type="bar")
        plt.title('SHAP Feature Impact — Go/No-Go', fontsize=14)
        plt.tight_layout()
        fig = plt.gcf()
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close('all')
        return True
    except Exception as e:
        _logger.warning(f"Could not save SHAP summary plot: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Dataset profiling
# ══════════════════════════════════════════════════════════════════════════════
def profile_dataset(df, feature_cols, target_col):
    """Generate comprehensive dataset profile as a dict."""
    X = df[feature_cols]
    y = df[target_col]

    # SHA-256 hash of the data for reproducibility
    data_hash = hashlib.sha256(
        pd.util.hash_pandas_object(df).values.tobytes()
    ).hexdigest()[:16]

    profile = {
        "data_hash": data_hash,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "num_features": len(feature_cols),
        "target_column": target_col,
        "class_distribution": {
            "Go_count": int(y.sum()),
            "NoGo_count": int((y == 0).sum()),
            "Go_pct": round(y.mean() * 100, 2),
            "NoGo_pct": round((1 - y.mean()) * 100, 2),
            "class_ratio": round(y.sum() / max((y == 0).sum(), 1), 2),
        },
        "missing_values": {col: int(X[col].isna().sum()) for col in feature_cols},
        "total_missing": int(X.isna().sum().sum()),
        "feature_stats": {},
    }

    for col in feature_cols:
        profile["feature_stats"][col] = {
            "mean": round(float(X[col].mean()), 4),
            "std": round(float(X[col].std()), 4),
            "min": round(float(X[col].min()), 4),
            "max": round(float(X[col].max()), 4),
            "median": round(float(X[col].median()), 4),
            "skew": round(float(X[col].skew()), 4),
            "kurtosis": round(float(X[col].kurtosis()), 4),
        }

    return profile


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
_logger.info("=== SCRIPT 04: training START ===")
TRAIN_START = time.time()

# --- [TRACKING] Load config params for tracking ---
try:
    import yaml
    with open("configs/model_config.yaml") as _cfg_f:
        _config = yaml.safe_load(_cfg_f)
    _logger.info(f"Config loaded: {_config}")
except Exception as _cfg_e:
    _config = {}
    _logger.warning(f"[TRACKING] Could not load model_config.yaml: {_cfg_e}")

# Initialize MLflow
_tracking_ctx = init_tracking(run_name="train_run", experiment_name="astrogeo-launch-go-nogo") if (TRACKING_ENABLED and init_tracking) else __import__("contextlib").nullcontext()

# Initialize WandB
if TRACKING_ENABLED and wandb:
    try:
        wandb.init(
            project="astrogeo-graphrag",
            name="train_run",
            config=_config,
            tags=["training", "ensemble", "rf+lr"]
        )
        _logger.success("[TRACKING] W&B initialized successfully!")
    except Exception as _e:
        _logger.warning(f"[TRACKING] W&B initialization failed: {_e}")
        wandb = None


with _tracking_ctx:
  try:
    # ══════════════════════════════════════════════════
    # LOG: Hyperparameters from YAML config
    # ══════════════════════════════════════════════════
    if TRACKING_ENABLED and mlflow:
        try:
            if _config:
                mlflow.log_params(_config)
        except Exception as _e:
            _logger.warning(f"[TRACKING] mlflow.log_params failed: {_e}")

    # ══════════════════════════════════════════════════
    # LOAD DATA
    # ══════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════
    # LOG: Dataset profiling (comprehensive)
    # ══════════════════════════════════════════════════
    data_profile = profile_dataset(df, available_features, TARGET_COL)

    if TRACKING_ENABLED:
        profile_path = "metrics/dataset_profile.json"
        with open(profile_path, "w") as pf:
            json.dump(data_profile, pf, indent=2)

        # MLflow
        if mlflow:
            try:
                mlflow.log_param("dataset_rows", X.shape[0])
                mlflow.log_param("dataset_features", X.shape[1])
                mlflow.log_param("dataset_hash", data_profile["data_hash"])
                
                mlflow.log_metric("class_Go_count", data_profile["class_distribution"]["Go_count"])
                mlflow.log_metric("class_NoGo_count", data_profile["class_distribution"]["NoGo_count"])
                
                mlflow.log_artifact(profile_path, "data_profile")
            except Exception as _e:
                _logger.warning(f"[TRACKING] MLflow profiling failed: {_e}")

        # WandB
        if wandb:
            try:
                wandb.config.update({
                    "dataset_rows": X.shape[0],
                    "dataset_features": X.shape[1],
                    "dataset_hash": data_profile["data_hash"],
                    "class_distribution": data_profile["class_distribution"]
                })
                wandb.save(profile_path)
            except Exception as _e:
                _logger.warning(f"[TRACKING] W&B profiling failed: {_e}")

        # Feature correlations
        corr_matrix = X.corr()
        corr_path = "metrics/feature_correlations.csv"
        corr_matrix.to_csv(corr_path)
        if mlflow: mlflow.log_artifact(corr_path, "data_profile")
        if wandb: wandb.save(corr_path)


    # ─────────────────────────────────────────────
    # Train / test split
    # ─────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Fit scaler ONLY on training data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    if TRACKING_ENABLED:
        scaler_info = {
            "scaler_type": "StandardScaler",
            "means": {available_features[i]: round(float(scaler.mean_[i]), 4) for i in range(len(available_features))},
            "scales": {available_features[i]: round(float(scaler.scale_[i]), 4) for i in range(len(available_features))},
        }
        with open("metrics/scaler_stats.json", "w") as sf:
            json.dump(scaler_info, sf, indent=2)
        if mlflow: mlflow.log_artifact("metrics/scaler_stats.json", "data_profile")
        if wandb: wandb.save("metrics/scaler_stats.json")

    # ─────────────────────────────────────────────
    # Model architecture
    # ─────────────────────────────────────────────
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=5,
        class_weight='balanced',
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
        voting='soft'
    )

    # ─────────────────────────────────────────────
    # Train
    # ─────────────────────────────────────────────
    print("Training ensemble...")
    _logger.info("Fitting ensemble model...")
    train_start_time = time.time()
    ensemble.fit(X_train_scaled, y_train)
    train_duration = time.time() - train_start_time

    # ══════════════════════════════════════════════════════════════════════
    # EVALUATE
    # ══════════════════════════════════════════════════════════════════════
    rf_fitted = ensemble.named_estimators_['rf']
    lr_fitted = ensemble.named_estimators_['lr']

    models_to_eval = {
        "rf_": rf_fitted,
        "lr_": lr_fitted,
        "ensemble_": ensemble,
    }

    all_metrics = {}
    
    for prefix, model in models_to_eval.items():
        _logger.info(f"Evaluating {prefix.rstrip('_')}...")
        metrics, y_pred, y_proba, cm, report = compute_all_metrics(
            model, X_test_scaled, y_test, prefix=prefix
        )
        all_metrics.update(metrics)
        
        # Save confusion matrix plot per model
        model_name = prefix.rstrip('_').upper()
        cm_file = f"plots/confusion_matrix_{prefix.rstrip('_')}.png"
        save_confusion_matrix_plot(cm, model_name, cm_file)
        
        if wandb:
            wandb.log({f"{model_name}_Confusion_Matrix": wandb.Image(cm_file)})

    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(ensemble, X_train_scaled, y_train, cv=cv, scoring='roc_auc')
    all_metrics["cv_auc_mean"] = round(float(cv_scores.mean()), 6)
    all_metrics["cv_auc_std"] = round(float(cv_scores.std()), 6)

    # ══════════════════════════════════════════════════
    # LOG: ALL metrics
    # ══════════════════════════════════════════════════
    _logger.success(f"All metrics computed: {len(all_metrics)} total")
    
    with open("metrics/scores.json", "w") as _mf:
        json.dump(all_metrics, _mf, indent=2)

    if TRACKING_ENABLED:
        if mlflow: mlflow.log_metrics(all_metrics)
        if wandb: wandb.log(all_metrics)

    # ─────────────────────────────────────────────
    # SHAP and Feature Importance
    # ─────────────────────────────────────────────
    explainer = shap.TreeExplainer(rf_fitted)
    shap_plot_path = "plots/shap_summary.png"
    save_shap_summary_plot(explainer, X_test_scaled, available_features, shap_plot_path)

    importances = rf_fitted.feature_importances_
    importance_plot_path = "plots/feature_importance.png"
    save_feature_importance_plot(importances, available_features, importance_plot_path)

    if wandb:
        wandb.log({
            "Feature_Importance": wandb.Image(importance_plot_path),
            "SHAP_Summary": wandb.Image(shap_plot_path)
        })

    # Save artifacts locally
    joblib.dump(ensemble, 'models/ensemble.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')
    joblib.dump(explainer, 'models/shap_explainer.pkl')
    with open('models/feature_cols.json', 'w') as f:
        json.dump(available_features, f)

    # ══════════════════════════════════════════════════
    # LOG: Artifacts to Trackers
    # ══════════════════════════════════════════════════
    if TRACKING_ENABLED:
        # MLflow
        if mlflow:
            mlflow.sklearn.log_model(ensemble, "model", registered_model_name="astrogeo-launch-go-nogo")
            mlflow.log_artifact(importance_plot_path, "plots")
            mlflow.log_artifact(shap_plot_path, "plots")
            
        # WandB
        if wandb:
            artifact = wandb.Artifact(name="launch_ensemble_model", type="model")
            artifact.add_dir("models")
            wandb.log_artifact(artifact)

    total_duration = time.time() - TRAIN_START
    print(f"Total duration: {total_duration:.1f}s")
    _logger.info("=== SCRIPT 04: training DONE ===")

  except Exception as _run_exc:
    _logger.critical(f"RUN FAILED: {type(_run_exc).__name__}: {_run_exc}")
    raise
  finally:
      if wandb: wandb.finish()
