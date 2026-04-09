# 07_store_results.py
# AstroGeo — Store NDVI pipeline results to PostgreSQL
# Run AFTER 06_train_rf.py completes

import os
import json
import hashlib
import datetime
import joblib
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from geospatial_agent import (
    build_training_image_for_zone,
    generate_pipeline_hash,
    INDIA_ZONES,
    ANALYSIS_YEARS,
    CHANGE_CLASSES,
)

MODEL_FILE   = '../models/geospatial_rf_model.pkl'
SHAP_CSV     = '../outputs/shap_mean_abs_values.csv'
RESULTS_FILE = '../models/rf_training_results.json'

FEATURE_COLS = [
    'ndvi_2018', 'ndvi_2019', 'ndvi_2020',
    'ndvi_2022', 'ndvi_2024',
    'delta_total', 'delta_recent',
]
CLASS_LABELS = {
    0: 'Stable vegetation',
    1: 'Vegetation loss',
    2: 'Urban growth',
    3: 'Stable other',
}

DB_CONFIG = {
    'host':     os.getenv('DB_HOST', 'localhost'),
    'port':     int(os.getenv('DB_PORT', 5432)),
    'dbname':   os.getenv('DB_NAME', 'astrogeo'),
    'user':     os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
}


# ── Database setup ───────────────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def create_tables(conn):
    """Create ndvi_results and model_registry tables if not exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aoi_metadata (
                id              SERIAL PRIMARY KEY,
                zone_name       VARCHAR(100) UNIQUE NOT NULL,
                states          TEXT[],
                bbox_west       FLOAT,
                bbox_south      FLOAT,
                bbox_east       FLOAT,
                bbox_north      FLOAT,
                cloud_threshold INTEGER,
                start_month     INTEGER,
                end_month       INTEGER,
                created_at      TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS ndvi_results (
                id                  SERIAL PRIMARY KEY,
                aoi_id              INTEGER REFERENCES aoi_metadata(id),
                zone_name           VARCHAR(100),
                year                INTEGER,
                ndvi_mean           FLOAT,
                ndvi_min            FLOAT,
                ndvi_max            FLOAT,
                ndvi_std            FLOAT,
                delta_total_mean    FLOAT,
                delta_recent_mean   FLOAT,
                change_class        INTEGER,
                change_class_label  VARCHAR(50),
                confidence          FLOAT,
                shap_top_feature    VARCHAR(100),
                sample_count        INTEGER,
                verification_hash   VARCHAR(64),
                created_at          TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS geospatial_model_registry (
                id              SERIAL PRIMARY KEY,
                model_version   VARCHAR(50),
                model_file      VARCHAR(200),
                training_rows   INTEGER,
                test_accuracy   FLOAT,
                cv_accuracy     FLOAT,
                top_feature     VARCHAR(100),
                zones_used      TEXT[],
                shap_values     JSONB,
                trained_at      TIMESTAMP,
                registered_at   TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_ndvi_zone
                ON ndvi_results(zone_name);
            CREATE INDEX IF NOT EXISTS idx_ndvi_year
                ON ndvi_results(year);
            CREATE INDEX IF NOT EXISTS idx_ndvi_class
                ON ndvi_results(change_class);
        """)
    conn.commit()
    print('Tables created / verified.')


# ── Insert AOI metadata ──────────────────────────────────────
def upsert_aoi_metadata(conn, zone_name: str) -> int:
    """Insert zone metadata, return aoi_id."""
    config = INDIA_ZONES[zone_name]
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO aoi_metadata
                (zone_name, states, bbox_west, bbox_south,
                 bbox_east, bbox_north, cloud_threshold,
                 start_month, end_month)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (zone_name) DO UPDATE
                SET states = EXCLUDED.states
            RETURNING id
        """, (
            zone_name,
            config['states'],
            config['bbox']['west'],
            config['bbox']['south'],
            config['bbox']['east'],
            config['bbox']['north'],
            config['cloud_threshold'],
            config['start_month'],
            config['end_month'],
        ))
        aoi_id = cur.fetchone()[0]
    conn.commit()
    return aoi_id


# ── Compute stats from training CSV ─────────────────────────
def compute_zone_stats(zone_name: str,
                        df: pd.DataFrame,
                        model,
                        shap_df: pd.DataFrame) -> list:
    """
    Compute per-year NDVI statistics and RF predictions for a zone.
    Returns list of row dicts for ndvi_results table.
    """
    zone_df = df[df['zone'] == zone_name].copy()
    if len(zone_df) == 0:
        print(f'  No data for zone: {zone_name}')
        return []

    rows        = []
    X_zone      = zone_df[FEATURE_COLS].values
    predictions = model.predict(X_zone)
    probas      = model.predict_proba(X_zone)

    # Get most common predicted class and its confidence
    from collections import Counter
    pred_counts   = Counter(predictions)
    change_class  = pred_counts.most_common(1)[0][0]
    confidence    = float(probas[:, change_class].mean())
    change_label  = CHANGE_CLASSES.get(change_class, 'unknown')

    # Top SHAP feature for this class (SHAP CSV index uses class names)
    class_name = CLASS_LABELS.get(int(change_class))
    if class_name and class_name in shap_df.index:
        top_feature = shap_df.loc[class_name].idxmax()
    else:
        top_feature = 'unknown'

    pipeline_hash = generate_pipeline_hash(zone_name, ANALYSIS_YEARS)

    # One row per year
    for year in ANALYSIS_YEARS:
        ndvi_col = f'ndvi_{year}'
        if ndvi_col not in zone_df.columns:
            continue

        ndvi_vals = zone_df[ndvi_col].dropna()
        if len(ndvi_vals) == 0:
            continue

        rows.append({
            'zone_name':         zone_name,
            'year':              year,
            'ndvi_mean':         round(float(ndvi_vals.mean()), 4),
            'ndvi_min':          round(float(ndvi_vals.min()), 4),
            'ndvi_max':          round(float(ndvi_vals.max()), 4),
            'ndvi_std':          round(float(ndvi_vals.std()), 4),
            'delta_total_mean':  round(float(zone_df['delta_total'].mean()), 4),
            'delta_recent_mean': round(float(zone_df['delta_recent'].mean()), 4),
            'change_class':      int(change_class),
            'change_class_label':change_label,
            'confidence':        round(confidence, 4),
            'shap_top_feature':  top_feature,
            'sample_count':      len(ndvi_vals),
            'verification_hash': pipeline_hash,
        })

    return rows


# ── Insert NDVI results ──────────────────────────────────────
def insert_ndvi_results(conn, aoi_id: int, rows: list):
    """Bulk insert NDVI results rows."""
    if not rows:
        return 0

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO ndvi_results (
                aoi_id, zone_name, year,
                ndvi_mean, ndvi_min, ndvi_max, ndvi_std,
                delta_total_mean, delta_recent_mean,
                change_class, change_class_label,
                confidence, shap_top_feature,
                sample_count, verification_hash
            ) VALUES %s
        """, [
            (
                aoi_id,
                r['zone_name'], r['year'],
                r['ndvi_mean'], r['ndvi_min'],
                r['ndvi_max'], r['ndvi_std'],
                r['delta_total_mean'], r['delta_recent_mean'],
                r['change_class'], r['change_class_label'],
                r['confidence'], r['shap_top_feature'],
                r['sample_count'], r['verification_hash'],
            )
            for r in rows
        ])
    conn.commit()
    return len(rows)


# ── Register model ───────────────────────────────────────────
def register_model(conn, results: dict, shap_df: pd.DataFrame):
    """Store model metadata in geospatial_model_registry."""
    shap_json = shap_df.to_dict()

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO geospatial_model_registry (
                model_version, model_file, training_rows,
                test_accuracy, cv_accuracy, top_feature,
                zones_used, shap_values, trained_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            'v1.0-india',
            MODEL_FILE,
            results['training_rows'],
            results['test_accuracy'],
            results['cv_accuracy_mean'],
            results['top_feature_overall'],
            list(INDIA_ZONES.keys()),
            json.dumps(shap_json),
            results['trained_at'],
        ))
    conn.commit()
    print('Model registered in geospatial_model_registry.')


# ── Main ─────────────────────────────────────────────────────
if __name__ == '__main__':
    print('Loading model and data...')
    model   = joblib.load(MODEL_FILE)
    df      = pd.read_csv('../data/ndvi_training_india_combined.csv')
    shap_df = pd.read_csv(SHAP_CSV, index_col=0)

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    print(f'Model loaded: {MODEL_FILE}')
    print(f'Training data: {len(df):,} rows, {df["zone"].nunique()} zones')

    conn = get_connection()
    print('Connected to PostgreSQL.')

    create_tables(conn)
    register_model(conn, results, shap_df)

    total_inserted = 0
    zones_in_data  = df['zone'].unique()

    for zone_name in zones_in_data:
        print(f'\nProcessing: {zone_name}')

        aoi_id    = upsert_aoi_metadata(conn, zone_name)
        zone_rows = compute_zone_stats(zone_name, df, model, shap_df)
        inserted  = insert_ndvi_results(conn, aoi_id, zone_rows)

        print(f'  Inserted {inserted} rows (aoi_id={aoi_id})')
        total_inserted += inserted

    conn.close()

    print('\n' + '=' * 55)
    print('STEP 7 COMPLETE')
    print('=' * 55)
    print(f'Total rows inserted: {total_inserted}')
    print(f'Zones stored:        {len(zones_in_data)}')
    print(f'Tables populated:')
    print(f'  aoi_metadata ({len(zones_in_data)} zones)')
    print(f'  ndvi_results ({total_inserted} rows)')
    print(f'  geospatial_model_registry (1 model version)')
    print(f'\nNext: python 08_streamlit_page.py')
