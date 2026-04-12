"""
Page 1 — Risk Dashboard
Validates: Are our risk scores ranking the right asteroids?
"""
import streamlit as st
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from poc.db.queries import get_all, get_top_risk

st.set_page_config(page_title="Risk Dashboard", layout="wide")
st.title("🚨 Asteroid Risk Dashboard")
st.caption("Validates that improved_risk_score is ranking the right objects.")

df = get_all()
top = get_top_risk(20)

# ── KPI Row ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Asteroids", f"{len(df):,}")
c2.metric("High Risk", f"{len(df[df['risk_category'] == 'High']):,}")
c3.metric("Anomalies", f"{int(df['is_anomaly'].sum()):,}")
c4.metric("Mean Risk Score", f"{df['improved_risk_score'].mean():.2f}")

st.markdown("---")

# ── Leaderboard ───────────────────────────────────────────────────────────────
st.subheader("🏆 Top 20 Highest Risk Asteroids")
display_cols = [
    "asteroid_id", "improved_risk_score", "risk_category",
    "adaptive_risk_category", "is_anomaly", "is_pha_candidate",
    "estimated_diameter_km", "cluster"
]
available = [c for c in display_cols if c in top.columns]
st.dataframe(
    top[available].style.background_gradient(
        subset=["improved_risk_score"], cmap="Reds"
    ),
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    fig = px.histogram(
        df, x="improved_risk_score", nbins=50,
        title="Risk Score Distribution",
        labels={"improved_risk_score": "Improved Risk Score"},
        color_discrete_sequence=["#2E86C1"]
    )
    fig.update_layout(bargap=0.05)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig2 = px.pie(
        df, names="risk_category",
        title="Risk Category Breakdown",
        color="risk_category",
        color_discrete_map={"High": "#E74C3C", "Medium": "#F39C12", "Low": "#27AE60"}
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Anomaly per cluster bar ───────────────────────────────────────────────────
CLUSTER_NAMES = {0: "Frequent Close Approachers", 1: "Moderate Regulars", 2: "Distant Visitors"}
df["cluster_name"] = df["cluster"].map(CLUSTER_NAMES)

anomaly_by_cluster = (
    df.groupby("cluster_name")["is_anomaly"]
    .sum()
    .reset_index()
    .rename(columns={"is_anomaly": "anomaly_count"})
)
fig3 = px.bar(
    anomaly_by_cluster, x="cluster_name", y="anomaly_count",
    title="Anomaly Count per Cluster",
    labels={"cluster_name": "Cluster", "anomaly_count": "Anomalies"},
    color="cluster_name",
    color_discrete_sequence=["#E74C3C", "#F39C12", "#2E86C1"]
)
st.plotly_chart(fig3, use_container_width=True)
