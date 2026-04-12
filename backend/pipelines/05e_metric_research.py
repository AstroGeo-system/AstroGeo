# backend/pipelines/05e_metric_research.py
import joblib, json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import make_scorer, f1_score, roc_auc_score

load_dotenv('backend/.env')

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD', '')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME')}"
)

df = pd.read_sql("""
    SELECT l.success, w.temperature_c, w.humidity_pct,
           w.wind_speed, w.precipitation_mm, w.cloud_cover,
           w.is_monsoon, w.is_cyclone, l.month
    FROM launch_history l
    JOIN era5_weather w ON w.date = l.date
    WHERE l.launch_site = 'Sriharikota'
""", engine)

# Fill NaNs
df = df.fillna(df.median())

X = df.drop(columns=['success'])
y = df['success']

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

def eval_model(name, features):
    print(f"\n--- Model: {name} ---")
    X_sub = df[features]
    rf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    
    acc = cross_val_score(rf, X_sub, y, cv=skf, scoring='accuracy').mean()
    f1_f = cross_val_score(rf, X_sub, y, cv=skf, scoring=make_scorer(f1_score, pos_label=0)).mean()
    auc = cross_val_score(rf, X_sub, y, cv=skf, scoring='roc_auc').mean()
    
    print(f"Accuracy: {acc:.1%}")
    print(f"F1 (Failures): {f1_f:.3f}")
    print(f"ROC-AUC: {auc:.3f}")

eval_model("All Features", X.columns.tolist())
eval_model("Weather Only", ['temperature_c', 'humidity_pct', 'wind_speed', 'precipitation_mm', 'cloud_cover'])
eval_model("Top 3", ['cloud_cover', 'humidity_pct', 'temperature_c'])
