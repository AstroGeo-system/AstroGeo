"""
Page 3 — Anomaly Explorer
Explores Isolation Forest results — asteroids that don't fit any normal orbital pattern.
"""
import streamlit as st
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.queries import get_all, get_anomalies

st.set_page_config(page_title="Anomaly Explorer", layout="wide")
st.title("🔴 Anomaly Explorer")
st.caption("Isolation Forest anomalies — asteroids that defy normal orbital patterns.")

df = get_all()
anomalies = get_anomalies()

CLUSTER_NAMES = {0: "Frequent Close Approachers", 1: "Moderate Regulars", 2: "Distant Visitors"}
df["cluster_name"] = df["cluster"].map(CLUSTER_NAMES)

# ── KPI + Toggle ──────────────────────────────────────────────────────────────
col_kpi, col_toggle = st.columns([1, 3])
with col_kpi:
    st.metric("Confirmed Anomalies", f"{len(anomalies):,}")
    st.metric("Anomaly Rate", f"{len(anomalies)/len(df)*100:.1f}%")

with col_toggle:
    show_only_anomalies = st.toggle("Show anomalies only", value=False)

plot_df = anomalies if show_only_anomalies else df

st.markdown("---")

# ── Quadrant Scatter: Anomaly Score vs Risk Score ─────────────────────────────
st.subheader("Anomaly Score vs Risk Score — Quadrant View")
fig = px.scatter(
    plot_df,
    x="anomaly_score", y="improved_risk_score",
    color=plot_df["is_anomaly"].map({True: "Anomaly", False: "Normal"}),
    symbol="risk_category",
    hover_data=["asteroid_id", "cluster"],
    title="Anomaly Score vs Improved Risk Score",
    labels={
        "anomaly_score": "Anomaly Score (lower = more anomalous)",
        "improved_risk_score": "Improved Risk Score"
    },
    color_discrete_map={"Anomaly": "#E74C3C", "Normal": "#2E86C1"}
)
fig.add_vline(
    x=0, line_dash="dash", line_color="orange",
    annotation_text="Anomaly Threshold", annotation_position="top right"
)
fig.update_traces(marker=dict(size=5, opacity=0.75))
st.plotly_chart(fig, use_container_width=True)

# ── Anomaly Table ─────────────────────────────────────────────────────────────
st.subheader("📋 Anomalous Asteroids")
cols = [
    "asteroid_id", "anomaly_score", "improved_risk_score",
    "risk_category", "cluster", "orbit_stability",
    "is_pha_candidate", "estimated_diameter_km"
]
available = [c for c in cols if c in anomalies.columns]
st.dataframe(
    anomalies[available].style.background_gradient(
        subset=["anomaly_score"], cmap="Reds_r"
    ),
    use_container_width=True,
    hide_index=True
)

# ── Feature Contribution Bar ──────────────────────────────────────────────────
st.subheader("📊 Feature Means: Anomalies vs Normal")
feature_cols = [
    "orbit_stability", "approach_regularity", "kinetic_energy_proxy",
    "avg_velocity", "historical_mean_distance", "frequency_change_ratio"
]
available_feats = [c for c in feature_cols if c in df.columns]
if available_feats:
    comparison = df.groupby("is_anomaly")[available_feats].mean().T.reset_index()
    comparison.columns = ["feature", "Normal", "Anomaly"]
    fig2 = px.bar(
        comparison.melt(id_vars="feature", var_name="group", value_name="mean_value"),
        x="feature", y="mean_value", color="group", barmode="group",
        title="Mean Feature Values: Anomalies vs Normal",
        color_discrete_map={"Anomaly": "#E74C3C", "Normal": "#2E86C1"}
    )
    fig2.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig2, use_container_width=True)
