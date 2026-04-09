"""
Page 5 — Distance Forecasting (Section 5.1 from POC docs)
Linear extrapolation using distance_trend + distance_trend_r2 columns.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.queries import get_all, get_asteroid

st.set_page_config(page_title="Distance Forecasting", layout="wide")
st.title("📈 Distance Forecasting")
st.caption("Linear extrapolation using distance_trend + distance_trend_r2 — Section 5.1 from POC docs.")

# ── Helper: predict_next_distance (exactly as specified in docx) ────────────
def predict_next_distance(row, years_ahead=1):
    """
    Forward-looking distance prediction using linear extrapolation.
    distance_trend = slope (AU/year), distance_trend_r2 = model confidence
    """
    base      = float(row.get("historical_mean_distance", 0))
    slope     = float(row.get("distance_trend", 0))
    confidence = float(row.get("distance_trend_r2", 0))
    predicted = base + slope * years_ahead
    predicted = max(predicted, 0.0)          # distance can't be negative
    return {
        "predicted_dist_au": round(predicted, 6),
        "confidence_r2":      round(confidence, 4),
        "getting_closer":     slope < 0,
        "trend_slope_au_yr":  round(slope, 8),
    }

df = get_all()

# ── Asteroid picker ──────────────────────────────────────────────────────────
st.subheader("🔭 Individual Asteroid Forecast")
col_sel, col_yr = st.columns([3, 1])
with col_sel:
    selected = st.selectbox("Select Asteroid", sorted(df["asteroid_id"].unique().tolist()))
with col_yr:
    years = st.slider("Years ahead", 1, 30, 5)

row_df = get_asteroid(selected)
if row_df.empty:
    st.warning("Asteroid not found.")
    st.stop()

row = row_df.iloc[0]
pred = predict_next_distance(row, years_ahead=years)

# ── Forecast KPI row ─────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Current Mean Dist (AU)", f"{float(row.get('historical_mean_distance', 0)):.4f}")
k2.metric(f"Predicted Dist in {years}yr (AU)", f"{pred['predicted_dist_au']:.4f}")
k3.metric("Model Confidence (R²)", f"{pred['confidence_r2']:.3f}")
k4.metric(
    "Trend",
    "🔴 Getting Closer" if pred["getting_closer"] else "🟢 Moving Away",
    delta=f"{pred['trend_slope_au_yr']:+.6f} AU/yr"
)

st.markdown("---")

# ── Multi-year trajectory chart ───────────────────────────────────────────────
st.subheader(f"Distance Trajectory — {selected} over next 30 years")

year_range  = list(range(0, 31))
base_dist   = float(row.get("historical_mean_distance", 0))
slope       = float(row.get("distance_trend", 0))
r2          = float(row.get("distance_trend_r2", 0))

distances   = [max(base_dist + slope * y, 0) for y in year_range]
current_yr  = 2026
years_label = [current_yr + y for y in year_range]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=years_label, y=distances,
    mode="lines+markers",
    name="Predicted Distance",
    line=dict(color="#E74C3C" if slope < 0 else "#27AE60", width=2),
    marker=dict(size=5)
))
fig.add_hline(
    y=0.05, line_dash="dot", line_color="orange",
    annotation_text="~0.05 AU (Close Approach Threshold)",
    annotation_position="bottom right"
)
fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Predicted Mean Distance (AU)",
    title=f"{selected} — Linear Distance Extrapolation (R² = {r2:.3f})",
    height=400
)
st.plotly_chart(fig, use_container_width=True)

st.info(
    f"**Methodology:** Linear extrapolation using `distance_trend` ({slope:+.6f} AU/yr) "
    f"applied to `historical_mean_distance` ({base_dist:.4f} AU). "
    f"Model fit confidence R² = {r2:.3f}. Low R² values indicate irregular orbital patterns.",
    icon="ℹ️"
)

st.markdown("---")

# ── Bulk forecast table — top approaching asteroids ──────────────────────────
st.subheader("🌍 Top 20 Asteroids Getting Closer (Next 10 Years)")

def bulk_predict(df, years_ahead=10):
    results = []
    for _, row in df.iterrows():
        p = predict_next_distance(row, years_ahead)
        results.append({
            "asteroid_id":         row["asteroid_id"],
            "current_dist_au":     round(float(row.get("historical_mean_distance", 0)), 4),
            "predicted_dist_au":   p["predicted_dist_au"],
            "delta_au":            round(p["predicted_dist_au"] - float(row.get("historical_mean_distance", 0)), 6),
            "confidence_r2":       p["confidence_r2"],
            "getting_closer":      p["getting_closer"],
            "risk_category":       row.get("risk_category", "N/A"),
            "improved_risk_score": row.get("improved_risk_score", 0),
        })
    return pd.DataFrame(results)

with st.spinner("Computing bulk forecasts..."):
    bulk = bulk_predict(df, years_ahead=10)
    approaching = (
        bulk[bulk["getting_closer"]]
        .sort_values("delta_au")
        .head(20)
        .reset_index(drop=True)
    )

st.dataframe(
    approaching.style.background_gradient(subset=["delta_au"], cmap="Reds"),
    use_container_width=True,
    hide_index=True
)

# ── Scatter: Confidence vs Risk ───────────────────────────────────────────────
st.subheader("Model Confidence vs Risk Score")
fig2 = px.scatter(
    bulk, x="confidence_r2", y="improved_risk_score",
    color="getting_closer",
    hover_data=["asteroid_id", "delta_au"],
    title="Forecast Confidence (R²) vs Improved Risk Score",
    labels={
        "confidence_r2": "Distance Trend R² (Model Confidence)",
        "improved_risk_score": "Improved Risk Score",
        "getting_closer": "Getting Closer?"
    },
    color_discrete_map={True: "#E74C3C", False: "#27AE60"}
)
fig2.update_traces(marker=dict(size=4, opacity=0.6))
st.plotly_chart(fig2, use_container_width=True)
