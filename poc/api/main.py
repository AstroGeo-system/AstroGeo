"""
poc/api/main.py — FastAPI backend (Section 5.2 from POC docs)
Minimum viable 5 endpoints wrapping the same PostgreSQL queries.

ROUTE ORDER MATTERS:
  - collection_router (/alerts, /clusters, /anomalies) registered FIRST
  - detail_router (/{des}, /{des}/predict) registered AFTER
  This prevents FastAPI's wildcard /{des} from swallowing named paths.
"""
from fastapi import FastAPI, HTTPException, APIRouter
from sqlalchemy import create_engine, text
import datetime
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
TABLE = "astronomy.asteroid_ml_predictions"

app = FastAPI(
    title="AstroGeo-AI Asteroid API",
    description="FastAPI backend for asteroid ML predictions — Section 5.2",
    version="1.0.0"
)

# Two routers: collection (named paths) MUST be registered before wildcard
collection_router = APIRouter(prefix="/api/asteroids", tags=["collections"])
detail_router     = APIRouter(prefix="/api/asteroids", tags=["detail"])


# ── Shared helpers ─────────────────────────────────────────────────────────────
def query_df(sql: str, params: dict = None):
    params = params or {}
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()
        cols = list(result.keys())
    return [dict(zip(cols, row)) for row in rows]


def predict_next_distance(row: dict, years_ahead: int = 1) -> dict:
    """Linear extrapolation using distance_trend + distance_trend_r2."""
    base       = float(row.get("historical_mean_distance") or 0)
    slope      = float(row.get("distance_trend") or 0)
    confidence = float(row.get("distance_trend_r2") or 0)
    predicted  = max(base + slope * years_ahead, 0.0)
    return {
        "predicted_dist_au": round(predicted, 6),
        "confidence_r2":     round(confidence, 4),
        "getting_closer":    slope < 0,
        "trend_slope_au_yr": round(slope, 8),
    }


# ── Endpoint 1: GET /api/asteroids/alerts ────────────────────────────────────
@collection_router.get("/alerts", summary="Top N risky asteroids, filtered by anomaly flag")
def get_alerts(n: int = 10, anomaly_only: bool = False):
    """Top N by improved_risk_score, optionally filtered to is_anomaly=True."""
    where = "WHERE is_anomaly = TRUE" if anomaly_only else ""
    rows = query_df(f"""
        SELECT asteroid_id, improved_risk_score, adaptive_risk_category,
               is_anomaly, is_pha_candidate, estimated_diameter_km, cluster
        FROM {TABLE} {where}
        ORDER BY improved_risk_score DESC
        LIMIT :n
    """, {"n": n})
    return {"count": len(rows), "alerts": rows}


# ── Endpoint 3: GET /api/asteroids/clusters ───────────────────────────────────
@collection_router.get("/clusters", summary="Cluster summary stats + member lists")
def get_clusters(members_limit: int = 5):
    """Cluster summary statistics grouped by cluster ID."""
    CLUSTER_NAMES = {0: "Frequent Close Approachers", 1: "Moderate Regulars", 2: "Distant Visitors"}
    stats = query_df(f"""
        SELECT cluster,
               COUNT(*)                                         AS member_count,
               ROUND(AVG(improved_risk_score)::numeric, 2)     AS avg_risk_score,
               ROUND(AVG(orbit_stability)::numeric, 4)         AS avg_orbit_stability,
               SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END)     AS anomaly_count,
               SUM(CASE WHEN is_pha_candidate THEN 1 ELSE 0 END) AS pha_count
        FROM {TABLE}
        GROUP BY cluster
        ORDER BY cluster
    """)
    members = query_df(f"""
        SELECT cluster, asteroid_id, improved_risk_score
        FROM (
            SELECT cluster, asteroid_id, improved_risk_score,
                   ROW_NUMBER() OVER (PARTITION BY cluster ORDER BY improved_risk_score DESC) AS rn
            FROM {TABLE}
        ) t
        WHERE rn <= :lim
        ORDER BY cluster, improved_risk_score DESC
    """, {"lim": members_limit})

    from collections import defaultdict
    member_map = defaultdict(list)
    for m in members:
        member_map[m["cluster"]].append({
            "asteroid_id": m["asteroid_id"],
            "risk_score":  m["improved_risk_score"]
        })

    result = []
    for s in stats:
        cid = s["cluster"]
        result.append({**s, "cluster_name": CLUSTER_NAMES.get(cid, "Unknown"),
                       "top_members": member_map.get(cid, [])})
    return {"clusters": result}


# ── Endpoint 4: GET /api/asteroids/anomalies ──────────────────────────────────
@collection_router.get("/anomalies", summary="All is_anomaly=True rows")
def get_anomalies(limit: int = 100):
    """All confirmed anomalous asteroids ordered by anomaly score."""
    rows = query_df(f"""
        SELECT asteroid_id, anomaly_score, improved_risk_score,
               risk_category, cluster, orbit_stability,
               is_pha_candidate, estimated_diameter_km
        FROM {TABLE}
        WHERE is_anomaly = TRUE
        ORDER BY anomaly_score ASC
        LIMIT :lim
    """, {"lim": limit})
    return {"count": len(rows), "anomalies": rows}


# ── Endpoint 5: GET /api/asteroids/{des}/predict ──────────────────────────────
@detail_router.get("/{des}/predict", summary="Forward-looking distance prediction")
def predict_asteroid(des: str, years_ahead: int = 5):
    """Linear distance extrapolation using distance_trend columns."""
    rows = query_df(f"""
        SELECT asteroid_id, historical_mean_distance,
               distance_trend, distance_trend_r2,
               improved_risk_score, next_predicted_approach
        FROM {TABLE} WHERE asteroid_id = :des
    """, {"des": des})
    if not rows:
        raise HTTPException(status_code=404, detail=f"Asteroid '{des}' not found")
    row = rows[0]
    forecast = predict_next_distance(row, years_ahead)
    return {
        "asteroid_id":  des,
        "years_ahead":  years_ahead,
        "current": {
            "mean_distance_au":        row.get("historical_mean_distance"),
            "next_predicted_approach": str(row.get("next_predicted_approach", ""))
        },
        "forecast":    forecast,
        "risk_score":  row.get("improved_risk_score"),
    }


# ── Endpoint 2: GET /api/asteroids/{des} ─────────────────────────────────────
@detail_router.get("/{des}", summary="Full feature vector for one asteroid")
def get_asteroid(des: str):
    """Complete feature row for a single asteroid."""
    rows = query_df(f"SELECT * FROM {TABLE} WHERE asteroid_id = :des", {"des": des})
    if not rows:
        raise HTTPException(status_code=404, detail=f"Asteroid '{des}' not found")
    return rows[0]


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}


# Register routers: collection routes BEFORE detail (wildcard) routes
app.include_router(collection_router)
app.include_router(detail_router)


# ══════════════════════════════════════════════════════════════════════════════
# ISRO Launch Probability Endpoints (doc section 12)
# ══════════════════════════════════════════════════════════════════════════════
import numpy as np
import joblib
import json
import hashlib
from pathlib import Path

LAUNCH_MODEL_DIR = Path(__file__).parent.parent.parent / "launch_model"
LAUNCH_TABLE = "launch_predictions"

_model_cache = {}

def get_launch_model():
    """Lazy-load model artifacts once. Return (ensemble, scaler, explainer, feature_cols)."""
    if _model_cache:
        return _model_cache["ensemble"], _model_cache["scaler"], \
               _model_cache["explainer"], _model_cache["feature_cols"]
    models_dir = LAUNCH_MODEL_DIR / "models"
    if not (models_dir / "ensemble.pkl").exists():
        raise HTTPException(status_code=503, detail="Launch model not trained yet. Run 04_train_model.py first.")
    _model_cache["ensemble"]    = joblib.load(models_dir / "ensemble.pkl")
    _model_cache["scaler"]      = joblib.load(models_dir / "scaler.pkl")
    _model_cache["explainer"]   = joblib.load(models_dir / "shap_explainer.pkl")
    with open(models_dir / "feature_cols.json") as f:
        _model_cache["feature_cols"] = json.load(f)
    return _model_cache["ensemble"], _model_cache["scaler"], \
           _model_cache["explainer"], _model_cache["feature_cols"]


def get_climatological_weather(selected_date: str, site: str = "sriharikota") -> dict:
    """Return ERA5 climatological mean or sensible defaults if nc file missing."""
    nc_path = LAUNCH_MODEL_DIR / "data" / f"era5_{site}.nc"
    if not nc_path.exists():
        return {"cloud_cover_pct": 40.0, "wind_speed_ms": 5.0, "precipitation_mm": 2.0,
                "temperature_c": 28.0, "relative_humidity_pct": 70.0,
                "surface_pressure_hpa": 1010.0, "precip_3day_sum": 6.0,
                "cloud_cover_day_minus_1": 38.0, "wind_speed_max_3day": 7.0}
    try:
        import xarray as xr
        ds = xr.open_dataset(nc_path)
        lat = 13.75 if site == "sriharikota" else 28.50
        lon = 80.25 if site == "sriharikota" else -80.75
        point = ds.sel(latitude=lat, longitude=lon, method="nearest")
        pdf = point.to_dataframe().reset_index()
        time_col = "valid_time" if "valid_time" in pdf.columns else "time"
        pdf[time_col] = pd.to_datetime(pdf[time_col])
        pdf["day_of_year"] = pdf[time_col].dt.dayofyear
        target_doy = pd.Timestamp(selected_date).dayofyear
        seasonal = pdf[pdf["day_of_year"] == target_doy].mean(numeric_only=True)
        return {
            "cloud_cover_pct":       float(seasonal.get("tcc", 0.4)) * 100,
            "wind_speed_ms":         float(np.sqrt(seasonal.get("u10", 4)**2 + seasonal.get("v10", 3)**2)),
            "precipitation_mm":      float(seasonal.get("tp", 0.002)) * 1000,
            "temperature_c":         float(seasonal.get("t2m", 301)) - 273.15,
            "relative_humidity_pct": 70.0,
            "surface_pressure_hpa":  float(seasonal.get("sp", 101000)) / 100,
            "precip_3day_sum":       float(seasonal.get("tp", 0.002)) * 1000 * 3,
            "cloud_cover_day_minus_1": float(seasonal.get("tcc", 0.4)) * 100,
            "wind_speed_max_3day":   float(np.sqrt(seasonal.get("u10", 4)**2 + seasonal.get("v10", 3)**2)) * 1.2
        }
    except Exception as e:
        return {"cloud_cover_pct": 40.0, "wind_speed_ms": 5.0, "precipitation_mm": 2.0,
                "temperature_c": 28.0, "relative_humidity_pct": 70.0,
                "surface_pressure_hpa": 1010.0, "precip_3day_sum": 6.0,
                "cloud_cover_day_minus_1": 38.0, "wind_speed_max_3day": 7.0}


isro_router = APIRouter(prefix="/api/isro", tags=["ISRO Launch Probability"])


# ── Endpoint 1: GET /api/isro/launch-probability (doc 12.1) ──────────────────
@isro_router.get("/launch-probability", summary="Launch probability for a specific date/vehicle")
def get_launch_probability(date: str, vehicle: str = "PSLV-XL"):
    """
    Load model → fetch ERA5 for date → engineer features → predict_proba → return.
    date: YYYY-MM-DD format
    vehicle: e.g. PSLV-XL, GSLV Mk II, LVM3, Falcon 9
    """
    ensemble, scaler, explainer, feature_cols = get_launch_model()

    weather = get_climatological_weather(date, site="sriharikota")
    dt = datetime.date.fromisoformat(date)
    row = {**weather,
        "month":              dt.month,
        "day_of_year":        dt.timetuple().tm_yday,
        "is_monsoon_season":  int(dt.month in [6, 7, 8, 9]),
        "is_cyclone_season":  int(dt.month in [10, 11, 12]),
        "vehicle_PSLV":       int("PSLV" in vehicle),
        "vehicle_GSLV":       int("GSLV" in vehicle),
        "vehicle_LVM3":       int("LVM3" in vehicle or "Mk III" in vehicle),
        "vehicle_Falcon":     int("Falcon" in vehicle),
    }
    X = [[row.get(c, 0) for c in feature_cols]]
    X_scaled = scaler.transform(X)
    prob = float(ensemble.predict_proba(X_scaled)[0, 1])

    # SHAP top risk factor
    sv = explainer.shap_values(X_scaled)
    sv_arr = sv[1][0] if isinstance(sv, list) else sv[0]
    top_idx = int(np.argmax(np.abs(sv_arr)))
    top_risk_factor = feature_cols[top_idx]

    category = "Favorable" if prob > 0.75 else ("Marginal" if prob >= 0.50 else "Unfavorable")

    return {
        "probability":     round(prob, 4),
        "category":        category,
        "top_risk_factor": top_risk_factor,
        "weather":         weather,
        "date":            date,
        "vehicle":         vehicle,
    }


# ── Endpoint 2: GET /api/isro/launches (doc 12.2) ────────────────────────────
@isro_router.get("/launches", summary="Historical launch predictions from the DB")
def get_launches(limit: int = 50, source: str = None):
    """Return launch_predictions table rows ordered by launch_date DESC."""
    try:
        where = "WHERE source = :source" if source else ""
        params = {"limit": limit}
        if source:
            params["source"] = source
        rows = query_df(
            f"SELECT * FROM {LAUNCH_TABLE} ORDER BY launch_date DESC LIMIT :limit",
            params
        )
        return {"count": len(rows), "launches": rows}
    except Exception as e:
        # Table might not exist yet if model hasn't been run
        raise HTTPException(status_code=503, detail=f"Launch table not found. Run 05_save_to_db.py first. Error: {e}")


import pandas as pd  # needed for date lookups above
app.include_router(isro_router)
