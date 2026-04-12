# backend/responsible_ai/04b_shap_launch.py
# SHAP analysis for launch probability model.
# Shows which weather variables drive failure predictions.

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap
import joblib
import json
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

MODEL_DIR  = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'models', 'launch'
)
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'shap', 'launch'
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FEATURE_COLS = [
    'temperature_c', 'pressure_pa', 'humidity_pct',
    'wind_speed', 'precipitation_mm', 'cloud_cover',
    'is_monsoon', 'is_cyclone', 'month', 'quarter',
    'high_wind_flag', 'high_humidity_flag',
    'heavy_rain_flag', 'high_cloud_flag',
    'weather_risk_score',
    'rolling_success_rate', 'vehicle_success_rate',
]


def load_data_and_model():
    engine = create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD', '')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}"
    )
    df = pd.read_sql("""
        SELECT l.success, l.mission, l.vehicle,
               w.temperature_c, w.pressure_pa, w.humidity_pct,
               w.wind_speed, w.precipitation_mm, w.cloud_cover,
               w.is_monsoon, w.is_cyclone,
               EXTRACT(MONTH FROM l.date) AS month,
               EXTRACT(QUARTER FROM l.date) AS quarter
        FROM launch_history l
        JOIN era5_weather w
            ON w.date = l.date
            AND w.launch_site = 'sriharikota'
        WHERE l.launch_site = 'Sriharikota'
    """, engine)
    engine.dispose()

    # Rebuild engineered features
    df['high_wind_flag']     = (df['wind_speed'] > 10).astype(int)
    df['high_humidity_flag'] = (df['humidity_pct'] > 80).astype(int)
    df['heavy_rain_flag']    = (df['precipitation_mm'] > 5).astype(int)
    df['high_cloud_flag']    = (df['cloud_cover'] > 0.7).astype(int)
    df['weather_risk_score'] = (
        df['high_wind_flag'] * 0.3 +
        df['high_humidity_flag'] * 0.2 +
        df['heavy_rain_flag'] * 0.3 +
        df['high_cloud_flag'] * 0.2
    )
    # Use actual vehicle success rate if possible, or median
    df['vehicle_success_rate'] = df.groupby('vehicle')['success'].transform('mean')
    df['rolling_success_rate'] = 0.8 # Placeholder for SHAP consistency

    ensemble = joblib.load(
        os.path.join(MODEL_DIR, 'launch_model.pkl')
    )
    scaler   = joblib.load(
        os.path.join(MODEL_DIR, 'launch_scaler.pkl')
    )

    # Use the EXACT list of features the model expects
    X_raw     = df[FEATURE_COLS].fillna(0) # Fill NaNs with 0 for binary flags
    X_scaled  = scaler.transform(X_raw.values)

    print(f"[SHAP] Loaded {len(df)} launches, "
          f"{len(FEATURE_COLS)} features matched.")
    return df, X_scaled, X_raw, FEATURE_COLS, ensemble


def run_shap(ensemble, X_scaled, X_raw, feature_cols):
    print("[SHAP] Computing values (KernelExplainer)...")

    # Use RF component — faster + more interpretable
    rf_model   = ensemble.named_estimators_['rf']
    background = shap.sample(X_scaled, 50, random_state=42)
    explainer  = shap.KernelExplainer(
        rf_model.predict_proba, background
    )
    shap_values = explainer.shap_values(
        X_scaled, silent=True
    )

    # In newer SHAP versions with certain models, KernelExplainer 
    # returns an array of shape (N, features, 2)
    if isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        sv_failure = shap_values[:, :, 0]
    elif isinstance(shap_values, list):
        sv_failure = shap_values[0]
    else:
        sv_failure = shap_values

    # ── Plot 1: Feature importance (failure prediction) ───────
    mean_abs   = np.abs(sv_failure).mean(axis=0)
    sorted_idx = np.argsort(mean_abs)[::-1]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(
        [feature_cols[i] for i in sorted_idx],
        mean_abs[sorted_idx],
        color='#e74c3c', alpha=0.85
    )
    ax.set_xlabel('Mean |SHAP Value| — Contribution to Failure Risk',
                  fontsize=11)
    ax.set_title(
        'Launch Probability Model — Weather Feature Importance\n'
        'Which conditions most increase failure risk?',
        fontsize=13, fontweight='bold'
    )
    ax.invert_yaxis()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'launch_feature_importance.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ {path}")

    # ── Plot 2: Beeswarm ──────────────────────────────────────
    shap.summary_plot(
        sv_failure, X_raw,
        feature_names=feature_cols,
        show=False, plot_type='dot'
    )
    plt.title(
        'Launch Model SHAP Beeswarm\n'
        'High SHAP = stronger push toward failure prediction',
        fontsize=12, fontweight='bold'
    )
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'launch_beeswarm.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ {path}")

    # ── Save summary JSON ─────────────────────────────────────
    summary = {
        'model':   'RF + LogReg VotingClassifier v2.0',
        'optimised_for': 'failure_recall',
        'threshold': 0.35,
        'top_failure_drivers': [
            {
                'feature':    feature_cols[i],
                'importance': float(mean_abs[i]),
            }
            for i in sorted_idx[:5]
        ],
    }
    path = os.path.join(OUTPUT_DIR, 'launch_shap_summary.json')
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✅ {path}")

    return summary


def main():
    print("=" * 55)
    print("AstroGeo — Launch Model SHAP Analysis")
    print("=" * 55)

    df, X_scaled, X_raw, feature_cols, ensemble = (
        load_data_and_model()
    )
    summary = run_shap(ensemble, X_scaled, X_raw, feature_cols)

    print("\nTop 5 failure risk drivers:")
    for item in summary['top_failure_drivers']:
        print(f"  {item['feature']:<25} {item['importance']:.4f}")
    print("\n✅ Launch SHAP complete!")


if __name__ == '__main__':
    main()
