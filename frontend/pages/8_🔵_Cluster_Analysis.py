"""
Page 2 — Cluster Analysis
Validates K-Means cluster personalities match expected behaviour.
"""
import streamlit as st
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from poc.db.queries import get_all

st.set_page_config(page_title="Cluster Analysis", layout="wide")
st.title("🔵 Cluster Analysis")
st.caption("Validates K-Means cluster personalities: Frequent Close Approachers · Moderate Regulars · Distant Visitors")

df = get_all()

CLUSTER_NAMES = {0: "Frequent Close Approachers", 1: "Moderate Regulars", 2: "Distant Visitors"}
df["cluster_name"] = df["cluster"].map(CLUSTER_NAMES)

# ── Scatter 1: Velocity vs Distance ──────────────────────────────────────────
st.subheader("Velocity vs Distance by Cluster")
fig1 = px.scatter(
    df,
    x="historical_mean_distance", y="avg_velocity",
    color="cluster_name",
    hover_data=["asteroid_id", "improved_risk_score", "is_anomaly"],
    title="Avg Velocity vs Mean Approach Distance — coloured by Cluster",
    labels={
        "historical_mean_distance": "Mean Approach Distance (AU)",
        "avg_velocity": "Average Velocity (km/s)"
    },
    color_discrete_sequence=["#E74C3C", "#F39C12", "#2E86C1"]
)
fig1.update_traces(marker=dict(size=4, opacity=0.7))
st.plotly_chart(fig1, use_container_width=True)

# ── Scatter 2: Approach Regularity vs Orbit Stability ────────────────────────
st.subheader("Approach Regularity vs Orbit Stability")
fig2 = px.scatter(
    df,
    x="orbit_stability", y="approach_regularity",
    color="cluster_name",
    hover_data=["asteroid_id", "improved_risk_score"],
    title="Approach Regularity vs Orbit Stability by Cluster",
    labels={
        "orbit_stability": "Orbit Stability",
        "approach_regularity": "Approach Regularity"
    },
    color_discrete_sequence=["#E74C3C", "#F39C12", "#2E86C1"]
)
fig2.update_traces(marker=dict(size=4, opacity=0.7))
st.plotly_chart(fig2, use_container_width=True)

col1, col2 = st.columns(2)

# ── Box Plot: Risk Score per Cluster ─────────────────────────────────────────
with col1:
    fig3 = px.box(
        df, x="cluster_name", y="improved_risk_score",
        color="cluster_name",
        title="Risk Score Distribution per Cluster",
        labels={"cluster_name": "Cluster", "improved_risk_score": "Improved Risk Score"},
        color_discrete_sequence=["#E74C3C", "#F39C12", "#2E86C1"]
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Cluster Profile Table ─────────────────────────────────────────────────────
with col2:
    st.subheader("Cluster Feature Profiles (Mean Values)")
    profile_cols = [
        "improved_risk_score", "orbit_stability",
        "approach_regularity", "kinetic_energy_proxy",
        "avg_velocity", "historical_mean_distance"
    ]
    available = [c for c in profile_cols if c in df.columns]
    profile = (
        df.groupby("cluster_name")[available]
        .mean()
        .round(4)
    )
    st.dataframe(profile, use_container_width=True)
