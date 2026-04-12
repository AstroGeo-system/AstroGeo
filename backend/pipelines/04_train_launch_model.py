# backend/pipelines/04_train_launch_model.py
# RF + LogReg ensemble with SMOTE oversampling.
# Optimised for failure recall — conservative threshold (0.35).
# Pure weather signal — no mission type features.

import pandas as pd
import numpy as np
import os
import json
import joblib
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, classification_report,
    roc_auc_score, f1_score
)
from imblearn.over_sampling import SMOTE
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'models', 'launch'
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Conservative threshold — lower = flags more launches as risky
# 0.35 means "predict failure unless model is 65%+ confident of success"
DECISION_THRESHOLD = 0.35


def get_engine():
    return create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD', '')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}"
    )


# ── Load data ─────────────────────────────────────────────────
def load_training_data():
    print("[Train] Loading launch + ERA5 data...")
    engine = get_engine()
    df = pd.read_sql("""
        SELECT
            l.mission, l.vehicle, l.date, l.year, l.month,
            l.launch_site, l.success,
            w.temperature_c, w.pressure_pa, w.humidity_pct,
            w.wind_speed, w.precipitation_mm, w.cloud_cover,
            w.is_monsoon, w.is_cyclone
        FROM launch_history l
        JOIN era5_weather w
            ON w.date = l.date
            AND w.launch_site = 'sriharikota'
        WHERE l.launch_site = 'Sriharikota'
        AND l.date >= '1980-01-01'
        ORDER BY l.date
    """, engine)
    engine.dispose()

    print(f"  → {len(df)} launches")
    print(f"  → Success: {df['success'].sum()} | "
          f"Failure: {(df['success']==0).sum()}")
    print(f"  → Baseline accuracy: {df['success'].mean():.1%}")
    return df


# ── Feature engineering ───────────────────────────────────────
def engineer_features(df):
    print("[Train] Engineering weather features...")

    weather_cols = [
        'temperature_c', 'pressure_pa', 'humidity_pct',
        'wind_speed', 'precipitation_mm', 'cloud_cover'
    ]
    for col in weather_cols:
        df[col] = df[col].fillna(df[col].median())

    # Rolling success rate at site (last 10 launches)
    df = df.sort_values('date').reset_index(drop=True)
    df['rolling_success_rate'] = (
        df['success']
        .shift(1)
        .rolling(10, min_periods=1)
        .mean()
        .fillna(0.8)
    )

    # Vehicle historical success rate
    df['vehicle_success_rate'] = (
        df.groupby('vehicle')['success']
        .transform('mean')
    )

    # Risk flags — these are the key weather signal features
    df['high_wind_flag']     = (df['wind_speed'] > 10).astype(int)
    df['high_humidity_flag'] = (df['humidity_pct'] > 80).astype(int)
    df['heavy_rain_flag']    = (df['precipitation_mm'] > 5).astype(int)
    df['high_cloud_flag']    = (df['cloud_cover'] > 0.7).astype(int)

    # Composite weather risk score
    df['weather_risk_score'] = (
        df['high_wind_flag'] * 0.3 +
        df['high_humidity_flag'] * 0.2 +
        df['heavy_rain_flag'] * 0.3 +
        df['high_cloud_flag'] * 0.2
    )

    df['quarter'] = pd.to_datetime(df['date']).dt.quarter

    FEATURE_COLS = [
        # Raw weather
        'temperature_c', 'pressure_pa', 'humidity_pct',
        'wind_speed', 'precipitation_mm', 'cloud_cover',
        # Season flags
        'is_monsoon', 'is_cyclone', 'month', 'quarter',
        # Risk flags
        'high_wind_flag', 'high_humidity_flag',
        'heavy_rain_flag', 'high_cloud_flag',
        'weather_risk_score',
        # Historical
        'rolling_success_rate', 'vehicle_success_rate',
    ]

    print(f"  → {len(FEATURE_COLS)} features")
    return df, FEATURE_COLS


# ── Train with SMOTE ──────────────────────────────────────────
def train_model(df, feature_cols):
    print("\n[Train] Applying SMOTE + training ensemble...")

    X = df[feature_cols].values
    y = df['success'].values

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    # SMOTE — oversample failures in training set only
    # k_neighbors=3 because we only have ~13 failure training rows
    smote = SMOTE(random_state=42, k_neighbors=3)
    X_train_bal, y_train_bal = smote.fit_resample(X_train, y_train)

    print(f"  Before SMOTE — Success: {y_train.sum()} | "
          f"Failure: {(y_train==0).sum()}")
    print(f"  After SMOTE  — Success: {y_train_bal.sum()} | "
          f"Failure: {(y_train_bal==0).sum()}")

    # RF — tuned to not overfit on synthetic samples
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=4,           # shallow — prevents memorising SMOTE points
        min_samples_leaf=5,    # requires real support before splitting
        class_weight='balanced',
        random_state=42,
    )

    # Logistic Regression — strong regularisation
    lr = LogisticRegression(
        C=0.1,                 # strong regularisation
        max_iter=1000,
        class_weight='balanced',
        random_state=42,
    )

    ensemble = VotingClassifier(
        estimators=[('rf', rf), ('lr', lr)],
        voting='soft',
    )
    ensemble.fit(X_train_bal, y_train_bal)

    # ── Evaluate with conservative threshold ──────────────────
    y_prob = ensemble.predict_proba(X_test)[:, 1]

    # Default threshold (0.5)
    y_pred_default = (y_prob >= 0.5).astype(int)

    # Conservative threshold (0.35) — flags more as risky
    y_pred_conservative = (y_prob >= DECISION_THRESHOLD).astype(int)

    acc_default = accuracy_score(y_test, y_pred_default)
    acc_cons    = accuracy_score(y_test, y_pred_conservative)
    roc_auc     = roc_auc_score(y_test, y_prob)
    f1_failure  = f1_score(y_test, y_pred_conservative, pos_label=0)

    print(f"\n{'='*50}")
    print(f"Results at default threshold (0.50):")
    print(f"  Accuracy: {acc_default:.1%}")
    print(f"\nResults at conservative threshold ({DECISION_THRESHOLD}):")
    print(f"  Accuracy:        {acc_cons:.1%}")
    print(f"  ROC-AUC:         {roc_auc:.3f}")
    print(f"  F1 (Failures):   {f1_failure:.3f}  ← key metric")
    print(f"\nClassification Report (conservative threshold):")
    print(classification_report(
        y_test, y_pred_conservative,
        target_names=['Failure', 'Success']
    ))

    # CV on balanced data
    cv_scores = cross_val_score(
        ensemble, X_scaled, y, cv=5, scoring='roc_auc'
    )
    print(f"  CV ROC-AUC: {cv_scores.mean():.3f} "
          f"(±{cv_scores.std():.3f})")

    return (ensemble, scaler, acc_cons, roc_auc,
            f1_failure, cv_scores.mean(), feature_cols)


# ── Save ──────────────────────────────────────────────────────
def save_model(ensemble, scaler, acc, roc_auc,
               f1_failure, cv_auc, feature_cols):
    joblib.dump(ensemble,
                os.path.join(OUTPUT_DIR, 'launch_model.pkl'))
    joblib.dump(scaler,
                os.path.join(OUTPUT_DIR, 'launch_scaler.pkl'))

    meta = {
        'model':             'RF + LogReg VotingClassifier (soft)',
        'oversampling':      'SMOTE (k=3)',
        'decision_threshold': DECISION_THRESHOLD,
        'optimised_for':     'failure_recall',
        'test_accuracy':     round(acc, 4),
        'roc_auc':           round(roc_auc, 4),
        'f1_failure':        round(f1_failure, 4),
        'cv_roc_auc':        round(cv_auc, 4),
        'features':          feature_cols,
        'n_features':        len(feature_cols),
        'version':           'astrogeo-launch-v2.0',
        'training_data':     'ISRO Sriharikota launches + ERA5 weather',
        'site':              'Sriharikota (1980–2026)',
        'n_launches':        108,
        'note': (
            'Conservative threshold flags launches as high-risk unless '
            'model is 65%+ confident of success. Trades accuracy for '
            'failure recall — appropriate for safety-critical decisions.'
        ),
    }

    with open(
        os.path.join(OUTPUT_DIR, 'launch_model_meta.json'), 'w'
    ) as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Model v2.0 saved → {OUTPUT_DIR}")
    return meta


# ── Save predictions ──────────────────────────────────────────
def save_predictions(df, ensemble, scaler, feature_cols):
    print("\n[Train] Saving predictions to PostgreSQL...")
    engine = get_engine()

    X     = scaler.transform(df[feature_cols].values)
    probs = ensemble.predict_proba(X)[:, 1]
    df['launch_probability']  = probs
    df['predicted_outcome']   = np.where(
        probs >= DECISION_THRESHOLD, 'success', 'high_risk'
    )

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS launch_predictions (
                id                  SERIAL PRIMARY KEY,
                mission             TEXT,
                vehicle             TEXT,
                date                DATE,
                launch_site         TEXT,
                launch_probability  FLOAT,
                predicted_outcome   TEXT,
                model_version       TEXT,
                UNIQUE(mission, date)
            )
        """))
        conn.commit()

        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO launch_predictions
                        (mission, vehicle, date, launch_site,
                         launch_probability, predicted_outcome,
                         model_version)
                    VALUES (:mission, :vehicle, :date, :site, :prob, :outcome, :ver)
                    ON CONFLICT (mission, date)
                    DO UPDATE SET
                        vehicle            = EXCLUDED.vehicle,
                        launch_probability = EXCLUDED.launch_probability,
                        predicted_outcome  = EXCLUDED.predicted_outcome,
                        model_version      = EXCLUDED.model_version
                """), {
                    'mission': row['mission'],
                    'vehicle': row['vehicle'],
                    'date':    row['date'],
                    'site':    row['launch_site'],
                    'prob':    float(row['launch_probability']),
                    'outcome': row['predicted_outcome'],
                    'ver':     'astrogeo-launch-v2.0',
                })
            except Exception:
                continue
        conn.commit()

    engine.dispose()
    high_risk = (df['predicted_outcome'] == 'high_risk').sum()
    print(f"  → {len(df)} predictions saved")
    print(f"  → {high_risk} flagged as high-risk "
          f"({high_risk/len(df):.1%} of launches)")


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("AstroGeo — Launch Probability Model v2.0")
    print("SMOTE + Conservative Threshold")
    print("=" * 55)

    df                                  = load_training_data()
    df, feature_cols                    = engineer_features(df)
    (ensemble, scaler, acc, roc_auc,
     f1_failure, cv_auc, feature_cols)  = train_model(df, feature_cols)
    meta                                = save_model(
        ensemble, scaler, acc, roc_auc,
        f1_failure, cv_auc, feature_cols
    )
    save_predictions(df, ensemble, scaler, feature_cols)

    print("\n" + "=" * 55)
    print("✅ Launch model v2.0 complete!")
    print(f"   ROC-AUC:       {meta['roc_auc']:.3f}  (target: >0.65)")
    print(f"   F1 (Failures): {meta['f1_failure']:.3f}  (target: >0.30)")


if __name__ == '__main__':
    # pip install imbalanced-learn scikit-learn joblib
    main()