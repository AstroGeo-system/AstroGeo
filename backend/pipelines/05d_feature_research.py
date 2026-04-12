# backend/pipelines/05d_feature_research.py
import joblib, json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt

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

print("Correlation with Success:")
correlations = df.corr()['success'].sort_values()
print(correlations)

# Load current model to check feature importance
model_path = 'data/models/launch/launch_model.pkl'
meta_path = 'data/models/launch/launch_model_meta.json'

if os.path.exists(model_path) and os.path.exists(meta_path):
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    
    ensemble = joblib.load(model_path)
    # The ensemble has ('rf', rf) and ('lr', lr). We check RF importance.
    rf = ensemble.named_estimators_['rf']
    importances = pd.Series(rf.feature_importances_, index=meta['features']).sort_values(ascending=False)
    print("\nRF Feature Importances:")
    print(importances)
else:
    print("\nModel file not found.")
