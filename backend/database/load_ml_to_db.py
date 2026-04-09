import pandas as pd
from sqlalchemy import create_engine, text
import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from backend.config import settings

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)

print("="*70)
print("LOADING ML RESULTS TO POSTGRESQL")
print("="*70)

# Load your ML analysis results
df = pd.read_csv('/Users/khushikhanna/Desktop/astrogeo/data/ml/asteroid_ml_analysis_improved.csv')
print(f"\nLoaded {len(df):,} asteroids")

# Clean data types
df['asteroid_id'] = df['asteroid_id'].astype(str)

# Handle datetime columns
date_cols = ['first_observed', 'last_observed', 'next_predicted_approach', 'final_predicted_approach']
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# Boolean columns
bool_cols = ['has_historical_data', 'has_future_data', 'has_both_datasets', 
             'is_pha_candidate', 'is_frequent_visitor', 'is_anomaly']
for col in bool_cols:
    if col in df.columns:
        df[col] = df[col].fillna(False).astype(bool)

print("\nLoading to PostgreSQL...")

with engine.connect() as conn:
    conn.execute(text("SET search_path TO astronomy"))
    
    # Drop old table if exists
    conn.execute(text("DROP TABLE IF EXISTS asteroid_ml_predictions CASCADE"))
    conn.commit()
    
    # Create new table
    df.to_sql(
        'asteroid_ml_predictions',
        engine,
        schema='astronomy',
        if_exists='replace',
        index=False,
        method='multi',
        chunksize=500
    )
    
    print("✅ Table created: astronomy.asteroid_ml_predictions")
    
    # Create indexes for fast queries
    print("\nCreating indexes...")  
    
    conn.execute(text("""
        CREATE INDEX idx_ml_asteroid_id ON asteroid_ml_predictions(asteroid_id)
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_ml_risk_score ON asteroid_ml_predictions(improved_risk_score DESC)
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_ml_risk_category ON asteroid_ml_predictions(adaptive_risk_category)
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_ml_cluster ON asteroid_ml_predictions(cluster)
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_ml_pha ON asteroid_ml_predictions(is_pha_candidate) WHERE is_pha_candidate = true
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_ml_anomaly ON asteroid_ml_predictions(is_anomaly) WHERE is_anomaly = true
    """))
    
    conn.commit()
    print("✅ Indexes created")

# Verify
with engine.connect() as conn:
    conn.execute(text("SET search_path TO astronomy"))
    
    result = conn.execute(text("SELECT COUNT(*) FROM asteroid_ml_predictions"))
    count = result.fetchone()[0]
    print(f"\n✅ LOADED: {count:,} asteroids")
    
    # Test query
    print("\n" + "="*70)
    print("TEST QUERY: Top 5 Highest Risk Asteroids")
    print("="*70)
    
    result = conn.execute(text("""
        SELECT 
            asteroid_id,
            improved_risk_score,
            adaptive_risk_category,
            ROUND(historical_min_distance::numeric, 4) as min_dist_au,
            is_pha_candidate
        FROM asteroid_ml_predictions
        ORDER BY improved_risk_score DESC
        LIMIT 5
    """))
    
    for row in result:
        print(f"  {row[0]}: risk={row[1]:.1f} ({row[2]}), dist={row[3]}AU, PHA={row[4]}")

print("\n" + "="*70)
print("✅ SUCCESS! ML DATA IN DATABASE")
print("="*70)