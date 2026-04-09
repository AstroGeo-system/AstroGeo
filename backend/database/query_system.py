from sqlalchemy import create_engine, text
import pandas as pd

import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from backend.config import settings

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)

# ============================================================================
# QUERY FUNCTIONS
# ============================================================================

def get_high_risk_asteroids(limit=20):
    """Get highest risk asteroids"""
    
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO astronomy"))
        
        result = conn.execute(text(f"""
            SELECT 
                asteroid_id,
                improved_risk_score,
                adaptive_risk_category,
                historical_min_distance,
                estimated_diameter_km,
                avg_velocity,
                is_pha_candidate
            FROM asteroid_ml_predictions
            ORDER BY improved_risk_score DESC
            LIMIT {limit}
        """))
        
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def get_phas():
    """Get all Potentially Hazardous Asteroids"""
    
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO astronomy"))
        
        result = conn.execute(text("""
            SELECT 
                asteroid_id,
                improved_risk_score,
                historical_min_distance,
                estimated_diameter_km,
                historical_frequency
            FROM asteroid_ml_predictions
            WHERE is_pha_candidate = true
            ORDER BY improved_risk_score DESC
        """))
        
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def get_anomalies():
    """Get all anomalous asteroids"""
    
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO astronomy"))
        
        result = conn.execute(text("""
            SELECT 
                asteroid_id,
                anomaly_score,
                improved_risk_score,
                cluster,
                historical_min_distance,
                avg_velocity
            FROM asteroid_ml_predictions
            WHERE is_anomaly = true
            ORDER BY anomaly_score ASC
            LIMIT 50
        """))
        
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def get_cluster_summary():
    """Summarize asteroid clusters"""
    
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO astronomy"))
        
        result = conn.execute(text("""
            SELECT 
                cluster,
                COUNT(*) as asteroid_count,
                ROUND(AVG(improved_risk_score)::numeric, 2) as avg_risk_score,
                ROUND(AVG(historical_min_distance)::numeric, 4) as avg_min_distance,
                ROUND(AVG(avg_velocity)::numeric, 1) as avg_velocity,
                SUM(CASE WHEN is_pha_candidate THEN 1 ELSE 0 END) as pha_count
            FROM asteroid_ml_predictions
            GROUP BY cluster
            ORDER BY cluster
        """))
        
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def search_asteroid(asteroid_id):
    """Get complete info for specific asteroid"""
    
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO astronomy"))
        
        result = conn.execute(text("""
            SELECT *
            FROM asteroid_ml_predictions
            WHERE asteroid_id = :id
        """), {'id': asteroid_id})
        
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None

# ============================================================================
# TEST THE FUNCTIONS
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("TESTING QUERY FUNCTIONS")
    print("="*70)
    
    # Test 1: High risk
    print("\n1. TOP 10 HIGHEST RISK ASTEROIDS:")
    high_risk = get_high_risk_asteroids(10)
    for idx, row in high_risk.iterrows():
        print(f"  {row['asteroid_id']}: risk={row['improved_risk_score']:.1f}, "
              f"dist={row['historical_min_distance']:.4f}AU, "
              f"PHA={row['is_pha_candidate']}")
    
    # Test 2: PHAs
    print("\n2. POTENTIALLY HAZARDOUS ASTEROIDS:")
    phas = get_phas()
    print(f"  Total PHAs: {len(phas)}")
    if len(phas) > 0:
        print(f"  Highest risk PHA: {phas.iloc[0]['asteroid_id']} (score: {phas.iloc[0]['improved_risk_score']:.1f})")
    
    # Test 3: Anomalies
    print("\n3. ANOMALOUS ASTEROIDS:")
    anomalies = get_anomalies()
    print(f"  Total anomalies: {len(anomalies)}")
    if len(anomalies) > 0:
        print(f"  Most anomalous: {anomalies.iloc[0]['asteroid_id']} (score: {anomalies.iloc[0]['anomaly_score']:.3f})")
    
    # Test 4: Clusters
    print("\n4. CLUSTER SUMMARY:")
    clusters = get_cluster_summary()
    print(clusters.to_string(index=False))
    
    # Test 5: Search specific asteroid
    print("\n5. SEARCH SPECIFIC ASTEROID:")
    if len(high_risk) > 0:
        test_id = high_risk.iloc[0]['asteroid_id']
        info = search_asteroid(test_id)
        if info:
            print(f"  Asteroid: {info['asteroid_id']}")
            print(f"  Risk: {info['improved_risk_score']:.1f} ({info['adaptive_risk_category']})")
            print(f"  Cluster: {info['cluster']}")
            print(f"  Min distance: {info['historical_min_distance']:.6f} AU")
    
    print("\n" + "="*70)
    print("✅ ALL QUERY FUNCTIONS WORKING!")
    print("="*70)