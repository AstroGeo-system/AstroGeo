# backend/responsible_ai/shap_asteroid.py
# Retrains Isolation Forest + KMeans in-memory from saved feature CSV,
# generates SHAP analysis, saves plots + summary JSON to data/shap/asteroid/

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import shap
import os
import json
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# ── Config ────────────────────────────────────────────────────
FEATURES_CSV  = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'ml', 'asteroid_features_ml_ready.csv'
)
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'shap', 'asteroid'
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# These are the 9 engineered features from your pipeline
# Adjust names if your CSV columns differ
FEATURE_COLS = [
    'dist_min',
    'dist_max', 
    'v_rel_mean',
    'v_inf_mean',
    'approach_count',
    'orbit_stability',
    'distance_trend',
    'kinetic_energy_proxy',
    'approach_regularity',
]


# ── Load features ─────────────────────────────────────────────
def load_features():
    print(f"[SHAP] Loading features from {FEATURES_CSV}")
    df = pd.read_csv(FEATURES_CSV)
    print(f"  → {len(df)} asteroids, columns: {list(df.columns)}")

    # Use only columns that exist in the CSV
    available = [c for c in FEATURE_COLS if c in df.columns]
    missing   = [c for c in FEATURE_COLS if c not in df.columns]

    if missing:
        print(f"  ⚠️  Missing columns (will skip): {missing}")
    if not available:
        # Fallback — use all numeric columns except identifiers
        available = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude   = ['id', 'index', 'is_anomaly', 'cluster',
                     'risk_score', 'improved_risk_score']
        available = [c for c in available if c not in exclude]
        print(f"  → Falling back to all numeric features: {available}")

    print(f"  → Using {len(available)} features: {available}")
    return df, available


# ── Retrain models ────────────────────────────────────────────
def retrain_models(df, feature_cols):
    print("\n[SHAP] Retraining models in-memory...")

    X_raw = df[feature_cols].fillna(df[feature_cols].median())

    scaler = StandardScaler()
    X      = scaler.fit_transform(X_raw)

    # Isolation Forest — same params as original pipeline
    iso = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    iso.fit(X)
    print("  ✅ Isolation Forest retrained")

    # KMeans — 3 clusters same as original
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    km.fit(X)
    print("  ✅ KMeans retrained")

    return iso, km, X, X_raw, scaler, feature_cols


# ── SHAP for Isolation Forest ─────────────────────────────────
def shap_isolation_forest(iso, X, X_raw, feature_cols):
    print("\n[SHAP] Computing SHAP for Isolation Forest...")

    # Use KernelExplainer with sample for speed
    # score_samples gives anomaly score (higher = more normal)
    background = shap.sample(X, 100, random_state=42)
    explainer  = shap.KernelExplainer(
        iso.score_samples,
        background
    )

    # Explain a sample of 200 asteroids
    sample_size = min(200, len(X))
    X_sample    = X[:sample_size]
    X_raw_sample = X_raw.iloc[:sample_size]

    print(f"  Computing SHAP values for {sample_size} asteroids...")
    shap_values = explainer.shap_values(X_sample, silent=True)

    # ── Plot 1: Feature importance bar chart ──────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    mean_abs = np.abs(shap_values).mean(axis=0)
    sorted_idx = np.argsort(mean_abs)[::-1]

    bars = ax.barh(
        [feature_cols[i] for i in sorted_idx],
        mean_abs[sorted_idx],
        color='#e74c3c',
        alpha=0.8,
    )
    ax.set_xlabel('Mean |SHAP Value|', fontsize=12)
    ax.set_title(
        'Isolation Forest — Feature Importance\n'
        'Which features drive asteroid anomaly detection?',
        fontsize=13, fontweight='bold'
    )
    ax.invert_yaxis()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'iso_feature_importance.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ Saved: {path}")

    # ── Plot 2: Beeswarm ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 7))
    shap.summary_plot(
        shap_values,
        X_raw_sample,
        feature_names=feature_cols,
        show=False,
        plot_type='dot',
    )
    plt.title(
        'Isolation Forest SHAP — Beeswarm\n'
        'High SHAP = more anomalous behaviour',
        fontsize=12, fontweight='bold'
    )
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'iso_beeswarm.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ Saved: {path}")

    return shap_values, mean_abs, feature_cols


# ── SHAP for KMeans ───────────────────────────────────────────
def shap_kmeans(km, X, X_raw, feature_cols):
    print("\n[SHAP] Computing SHAP for KMeans clusters...")

    # Use TreeExplainer-style via KernelExplainer on cluster distance
    def cluster_distance(X_input):
        """Returns distance to nearest cluster centre."""
        distances = km.transform(X_input)
        return -distances.min(axis=1)  # negative = closer = more typical

    background = shap.sample(X, 100, random_state=42)
    explainer  = shap.KernelExplainer(cluster_distance, background)

    sample_size  = min(200, len(X))
    X_sample     = X[:sample_size]
    X_raw_sample = X_raw.iloc[:sample_size]

    print(f"  Computing SHAP values for {sample_size} asteroids...")
    shap_values = explainer.shap_values(X_sample, silent=True)

    # ── Plot 3: KMeans feature importance ─────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    mean_abs   = np.abs(shap_values).mean(axis=0)
    sorted_idx = np.argsort(mean_abs)[::-1]

    ax.barh(
        [feature_cols[i] for i in sorted_idx],
        mean_abs[sorted_idx],
        color='#3498db',
        alpha=0.8,
    )
    ax.set_xlabel('Mean |SHAP Value|', fontsize=12)
    ax.set_title(
        'KMeans Clustering — Feature Importance\n'
        'Which features determine asteroid cluster assignment?',
        fontsize=13, fontweight='bold'
    )
    ax.invert_yaxis()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'kmeans_feature_importance.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ Saved: {path}")

    # ── Plot 4: Cluster distribution ──────────────────────────
    cluster_labels = km.predict(X)
    cluster_counts = pd.Series(cluster_labels).value_counts().sort_index()
    cluster_names  = {
        0: 'Frequent Close\nApproachers',
        1: 'Moderate\nRegulars',
        2: 'Distant\nVisitors',
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#e74c3c', '#f39c12', '#2ecc71']
    bars   = ax.bar(
        [cluster_names.get(i, f'Cluster {i}')
         for i in cluster_counts.index],
        cluster_counts.values,
        color=colors[:len(cluster_counts)],
        alpha=0.85,
        edgecolor='white',
    )
    for bar, count in zip(bars, cluster_counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 20,
            str(count),
            ha='center', fontsize=11, fontweight='bold'
        )
    ax.set_ylabel('Number of Asteroids', fontsize=12)
    ax.set_title(
        'KMeans Cluster Distribution\n'
        'Asteroid population by behavioural group',
        fontsize=13, fontweight='bold'
    )
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'kmeans_cluster_distribution.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ Saved: {path}")

    return shap_values, mean_abs


# ── Save summary JSON ─────────────────────────────────────────
def save_summary(iso_importance, km_importance, feature_cols):
    """
    Saves machine-readable SHAP summary for the Streamlit
    Model Cards page and the audit ledger.
    """
    summary = {
        'isolation_forest': {
            'model':       'IsolationForest',
            'n_estimators': 100,
            'contamination': 0.05,
            'top_features': [
                {
                    'feature':    feature_cols[i],
                    'importance': float(iso_importance[i]),
                }
                for i in np.argsort(iso_importance)[::-1]
            ],
        },
        'kmeans': {
            'model':      'KMeans',
            'n_clusters': 3,
            'top_features': [
                {
                    'feature':    feature_cols[i],
                    'importance': float(km_importance[i]),
                }
                for i in np.argsort(km_importance)[::-1]
            ],
        },
    }

    path = os.path.join(OUTPUT_DIR, 'asteroid_shap_summary.json')
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n  ✅ Summary JSON saved: {path}")
    return summary


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("AstroGeo — Asteroid SHAP Analysis")
    print("Models: Isolation Forest + KMeans")
    print("=" * 55)

    # 1. Load
    df, feature_cols = load_features()

    # 2. Retrain
    iso, km, X, X_raw, scaler, feature_cols = retrain_models(
        df, feature_cols
    )

    # 3. SHAP — Isolation Forest
    iso_shap, iso_importance, _ = shap_isolation_forest(
        iso, X, X_raw, feature_cols
    )

    # 4. SHAP — KMeans
    km_shap, km_importance = shap_kmeans(
        km, X, X_raw, feature_cols
    )

    # 5. Save summary
    summary = save_summary(iso_importance, km_importance, feature_cols)

    print("\n" + "=" * 55)
    print("✅ SHAP analysis complete!")
    print(f"   Output directory: {OUTPUT_DIR}")
    print("\nTop 3 anomaly drivers (Isolation Forest):")
    for item in summary['isolation_forest']['top_features'][:3]:
        print(f"   {item['feature']:<25} {item['importance']:.4f}")
    print("\nTop 3 cluster drivers (KMeans):")
    for item in summary['kmeans']['top_features'][:3]:
        print(f"   {item['feature']:<25} {item['importance']:.4f}")


if __name__ == '__main__':
    # pip install shap scikit-learn pandas matplotlib
    main()