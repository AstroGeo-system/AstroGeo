"""
db/queries.py — Reusable cached query functions for AstroGeo POC
"""
import pandas as pd
import streamlit as st
from sqlalchemy import text
from .connection import get_engine

TABLE = "astronomy.asteroid_ml_predictions"


@st.cache_data(ttl=300)
def get_all() -> pd.DataFrame:
    """Return full asteroid ML dataset."""
    return pd.read_sql(f"SELECT * FROM {TABLE}", get_engine())


@st.cache_data(ttl=300)
def get_top_risk(n: int = 20) -> pd.DataFrame:
    """Return top N asteroids by improved_risk_score."""
    return pd.read_sql(
        f"SELECT * FROM {TABLE} ORDER BY improved_risk_score DESC LIMIT {n}",
        get_engine()
    )


@st.cache_data(ttl=300)
def get_anomalies() -> pd.DataFrame:
    """Return all anomalous asteroids (is_anomaly = True)."""
    return pd.read_sql(
        f"SELECT * FROM {TABLE} WHERE is_anomaly = TRUE ORDER BY anomaly_score ASC",
        get_engine()
    )


@st.cache_data(ttl=300)
def get_asteroid(des: str) -> pd.DataFrame:
    """Return a single asteroid row by asteroid_id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT * FROM {TABLE} WHERE asteroid_id = :des"),
            {"des": des}
        )
        rows = result.fetchall()
        columns = result.keys()
    return pd.DataFrame(rows, columns=columns)
