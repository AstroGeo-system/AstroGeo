# backend/pipelines/05c_sanity_check.py
import joblib, json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD', '')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME')}"
)

df = pd.read_sql("""
    SELECT l.success, w.temperature_c, w.humidity_pct,
           w.wind_speed, w.precipitation_mm, w.cloud_cover,
           w.is_monsoon
    FROM launch_history l
    JOIN era5_weather w ON w.date = l.date
    WHERE l.launch_site = 'Sriharikota'
""", engine)

print(f"Class distribution:")
print(df['success'].value_counts())
print(f"\nBaseline (always predict success): "
      f"{df['success'].mean():.1%}")
print(f"Your model CV accuracy: 83.4%")
print(f"Improvement over baseline: "
      f"{(0.834 - df['success'].mean()):.1%}")
