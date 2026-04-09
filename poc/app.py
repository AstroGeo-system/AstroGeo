"""
app.py — AstroGeo POC Home / Landing Page
"""
import streamlit as st

st.set_page_config(
    page_title="AstroGeo-AI | Asteroid Intelligence",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("☄️ AstroGeo-AI — Asteroid Intelligence POC")
st.markdown("""
Welcome to the **AstroGeo-AI Streamlit Proof of Concept**.  
This app validates the asteroid ML pipeline results — K-Means clustering, 
Isolation Forest anomaly detection, and the composite risk scoring model.

---

### 📋 Pages
| Page | Purpose |
|---|---|
| 🚨 Risk Dashboard | Validate risk scores & leaderboard |
| 🔵 Cluster Analysis | Explore K-Means cluster behaviour |
| 🔴 Anomaly Explorer | Investigate Isolation Forest anomalies |
| 🔍 Asteroid Detail | Deep-dive into any individual asteroid |
| 🌍 Geospatial Explorer | Visualize NDVI change + SHAP in PostgreSQL |

👈 **Use the sidebar to navigate.**
""")

st.info("Data source: `astronomy.asteroid_ml_predictions` — PostgreSQL via CNEOS ML pipeline", icon="🗄️")
