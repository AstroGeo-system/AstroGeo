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

os.makedirs('models', exist_ok=True)

# ─────────────────────────────────────────────
# Load training data
# ─────────────────────────────────────────────
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

print(f"Dataset: {X.shape} | Labels → 1:{y.sum()} Go, 0:{(y==0).sum()} No-Go")

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

# ─────────────────────────────────────────────
# SHAP explainer (uses only the Random Forest)
# ─────────────────────────────────────────────
print("\nBuilding SHAP explainer...")
rf_fitted = ensemble.named_estimators_['rf']
explainer = shap.TreeExplainer(rf_fitted)

# ─────────────────────────────────────────────
# Save artifacts
# ─────────────────────────="models/"
# ─────────────────────────────────────────────
joblib.dump(ensemble, 'models/ensemble.pkl')
joblib.dump(scaler, 'models/scaler.pkl')
joblib.dump(explainer, 'models/shap_explainer.pkl')

# Save feature column list so inference scripts know the order
import json
with open('models/feature_cols.json', 'w') as f:
    json.dump(available_features, f)

print(f"\nSaved: models/ensemble.pkl, models/scaler.pkl, "
      f"models/shap_explainer.pkl, models/feature_cols.json")
