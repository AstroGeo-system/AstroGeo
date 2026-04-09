"""
Page 4 — Asteroid Deep-Dive
Single asteroid investigation — Evidence Chain view.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from poc.db.queries import get_all, get_asteroid

st.set_page_config(page_title="Asteroid Detail", layout="wide")
st.title("🔍 Asteroid Deep-Dive")
st.caption("Single asteroid investigation — Evidence Chain view.")

df = get_all()

CLUSTER_NAMES = {0: "Frequent Close Approachers", 1: "Moderate Regulars", 2: "Distant Visitors"}
df["cluster_name"] = df["cluster"].map(CLUSTER_NAMES)

# ── Asteroid Selector ─────────────────────────────────────────────────────────
des = st.selectbox(
    "Select Asteroid",
    options=sorted(df["asteroid_id"].unique().tolist()),
    index=0
)

row_df = get_asteroid(des)
if row_df.empty:
    st.error("Asteroid not found in database.")
    st.stop()

row = row_df.iloc[0]

st.markdown("---")

# ── Main Metrics ──────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    risk_val = float(row.get("improved_risk_score", 0))
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_val,
        title={"text": "Improved Risk Score", "font": {"size": 20}},
        number={"font": {"size": 48}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": "#E74C3C"},
            "bgcolor": "white",
            "steps": [
                {"range": [0, 33], "color": "#27AE60"},
                {"range": [33, 66], "color": "#F39C12"},
                {"range": [66, 100], "color": "#E74C3C"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": risk_val
            }
        }
    ))
    fig_gauge.update_layout(height=300, margin=dict(t=40, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col2:
    cluster_id = int(row.get("cluster", -1))
    st.metric("Cluster", CLUSTER_NAMES.get(cluster_id, "Unknown"))
    st.metric("Anomaly", "Yes ⚠️" if row.get("is_anomaly") else "No ✅")
    st.metric("Risk Category", str(row.get("risk_category", "N/A")))
    st.metric("Adaptive Risk", str(row.get("adaptive_risk_category", "N/A")))
    ld = row.get("closest_lunar_distance")
    st.metric("Closest Lunar Distance", f"{float(ld):.2f} LD" if ld is not None else "N/A")
    pHA = "Yes 🔴" if row.get("is_pha_candidate") else "No"
    st.metric("PHA Candidate", pHA)

st.markdown("---")

# ── Radar Chart: 6 Key Features ───────────────────────────────────────────────
st.subheader("Feature Radar — vs Cluster Mean")

radar_features = [
    "orbit_stability", "approach_regularity", "kinetic_energy_proxy",
    "avg_velocity", "data_quality_score", "historical_mean_distance"
]
available_radar = [f for f in radar_features if f in df.columns and f in row_df.columns]

if available_radar:
    cluster_df = df[df["cluster"] == cluster_id]
    cluster_means = cluster_df[available_radar].mean()

    # Normalise both to 0-1 using dataset min/max
    feat_min = df[available_radar].min()
    feat_max = df[available_radar].max()
    feat_range = (feat_max - feat_min).replace(0, 1)

    asteroid_vals = [(float(row.get(f, 0)) - feat_min[f]) / feat_range[f] for f in available_radar]
    cluster_vals = [(cluster_means[f] - feat_min[f]) / feat_range[f] for f in available_radar]

    labels = [f.replace("_", " ").title() for f in available_radar]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=asteroid_vals + [asteroid_vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name=des,
        line_color="#E74C3C"
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=cluster_vals + [cluster_vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name=f"Cluster Mean ({CLUSTER_NAMES.get(cluster_id, '?')})",
        line_color="#2E86C1",
        opacity=0.6
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title=f"{des} vs Cluster Mean"
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# ── Full Feature Table ────────────────────────────────────────────────────────
st.subheader("📋 Full Feature Vector")
transposed = row_df.T.reset_index()
transposed.columns = ["Feature", "Value"]
st.dataframe(transposed, use_container_width=True, hide_index=True)
