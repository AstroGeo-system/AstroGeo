"""
Script 05 — Save to PostgreSQL
Runs inference on all training rows, assigns categories, generates SHA-256 hashes, and writes to launch_predictions table.
"""
import pandas as pd
import numpy as np
import joblib
import shap
import hashlib
import json
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# ─────────────────────────────────────────────
# DB connection
# ─────────────────────────────────────────────
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'astrogeo')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
TABLE_NAME = os.getenv('TABLE_NAME', 'launch_predictions')
MODEL_VERSION = os.getenv('MODEL_VERSION', 'rf_lr_ensemble_v1.0')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create table if not exists (doc section 8.1)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS launch_predictions (
    id                  SERIAL PRIMARY KEY,
    mission_name        VARCHAR(200),
    launch_date         DATE NOT NULL,
    launch_site         VARCHAR(100),
    vehicle             VARCHAR(100),
    source              VARCHAR(50),
    cloud_cover_pct     FLOAT,
    wind_speed_ms       FLOAT,
    precipitation_mm    FLOAT,
    temperature_c       FLOAT,
    relative_humidity   FLOAT,
    surface_pressure_hpa FLOAT,
    is_monsoon_season   BOOLEAN,
    is_cyclone_season   BOOLEAN,
    probability_score   FLOAT NOT NULL,
    category            VARCHAR(20) NOT NULL,
    top_risk_factor     VARCHAR(100),
    top_risk_value      FLOAT,
    actual_label        INTEGER,
    predicted_label     INTEGER NOT NULL,
    verification_hash   VARCHAR(64),
    model_version       VARCHAR(50),
    created_at          TIMESTAMP DEFAULT NOW()
);
"""
with engine.connect() as conn:
    conn.execute(text(CREATE_TABLE_SQL))
    conn.commit()
print("Table ready.")

# ─────────────────────────────────────────────
# Load model + data
# ─────────────────────────────────────────────
ensemble = joblib.load('models/ensemble.pkl')
scaler = joblib.load('models/scaler.pkl')
explainer = joblib.load('models/shap_explainer.pkl')

with open('models/feature_cols.json') as f:
    FEATURE_COLS = json.load(f)

df = pd.read_csv('data/training_data.csv', parse_dates=['launch_date'])
X = df[FEATURE_COLS]
X_scaled = scaler.transform(X)

# ─────────────────────────────────────────────
# Run inference
# ─────────────────────────────────────────────
proba = ensemble.predict_proba(X_scaled)[:, 1]
pred_label = ensemble.predict(X_scaled)

# SHAP values for top risk factor
print("Calculating SHAP values for top risk factors...")
sv = explainer.shap_values(X_scaled)
# Newer shap returns a 3D array (samples, features, classes) or list of 2D arrays
if isinstance(sv, list):
    sv = sv[1]
elif len(np.shape(sv)) == 3:
    sv = sv[:, :, 1]

top_risk_factors = [FEATURE_COLS[np.argmax(np.abs(row))] for row in sv]
top_risk_values  = [sv[i, np.argmax(np.abs(sv[i]))] for i in range(len(sv))]

# ─────────────────────────────────────────────
# Helpers (doc sections 8.2, 8.3)
# ─────────────────────────────────────────────
def assign_category(prob):
    if prob > 0.75: return 'Favorable'
    if prob >= 0.50: return 'Marginal'
    return 'Unfavorable'

def generate_hash(mission, date, prob, cloud, model_ver):
    raw = f'{mission}|{date}|{round(prob, 6)}|{round(cloud, 4)}|{model_ver}'
    return hashlib.sha256(raw.encode()).hexdigest()

# ─────────────────────────────────────────────
# Build records
# ─────────────────────────────────────────────
records = []
for i, row in df.iterrows():
    prob = float(proba[i])
    cloud = float(row.get('cloud_cover_pct', 0.0))
    records.append({
        'mission_name':        str(row.get('mission_name', '')),
        'launch_date':         str(row['launch_date'].date()),
        'launch_site':         str(row.get('launch_site', '')),
        'vehicle':             str(row.get('vehicle', '')),
        'source':              str(row.get('source', '')),
        'cloud_cover_pct':     cloud,
        'wind_speed_ms':       float(row.get('wind_speed_ms', 0.0)),
        'precipitation_mm':    float(row.get('precipitation_mm', 0.0)),
        'temperature_c':       float(row.get('temperature_c', 0.0)),
        'relative_humidity':   float(row.get('relative_humidity_pct', 0.0)),
        'surface_pressure_hpa': float(row.get('surface_pressure_hpa', 0.0)),
        'is_monsoon_season':   bool(row.get('is_monsoon_season', 0)),
        'is_cyclone_season':   bool(row.get('is_cyclone_season', 0)),
        'probability_score':   prob,
        'category':            assign_category(prob),
        'top_risk_factor':     top_risk_factors[i],
        'top_risk_value':      float(top_risk_values[i]),
        'actual_label':        int(row['label']) if pd.notna(row.get('label')) else None,
        'predicted_label':     int(pred_label[i]),
        'verification_hash':   generate_hash(
            row.get('mission_name', ''), row['launch_date'].date(), prob, cloud, MODEL_VERSION
        ),
        'model_version':       MODEL_VERSION,
    })

# ─────────────────────────────────────────────
# Write to DB
# ─────────────────────────────────────────────
records_df = pd.DataFrame(records)
records_df.to_sql(TABLE_NAME, engine, if_exists='replace', index=False)
print(f"Inserted {len(records_df)} rows into '{TABLE_NAME}'.")

# Verify (doc step 7)
with engine.connect() as conn:
    result = conn.execute(text(
        f"SELECT COUNT(*), AVG(probability_score), "
        f"COUNT(*) FILTER (WHERE category='Favorable') FROM {TABLE_NAME}"
    )).fetchone()
    print(f"\nDB verification:")
    print(f"  Total rows:    {result[0]}")
    print(f"  Avg prob:      {result[1]:.3f}")
    print(f"  Favorable:     {result[2]}")
