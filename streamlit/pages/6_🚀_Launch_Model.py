"""
Script 06 — Streamlit Launch Probability Page
Page 6: AI Launch Probability gauge, SHAP insights, historical table, and live future prediction.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import joblib
import shap
import json
import os
import cdsapi
from utils import get_agent, datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

st.set_page_config(
    page_title="Launch Probability — AstroGeo",
    page_icon="🚀",
    layout="wide"
)

# ─────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────
@st.cache_resource
def get_engine():
    url = os.getenv('DATABASE_URL') or (
        f"postgresql://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','')}@"
        f"{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}/"
        f"{os.getenv('DB_NAME','astrogeo')}"
    )
    return create_engine(url, pool_pre_ping=True)

@st.cache_data(ttl=300)
def load_launch_data():
    try:
        return pd.read_sql("SELECT * FROM launch_predictions ORDER BY launch_date DESC", get_engine())
    except Exception as e:
        st.warning(f"DB not available: {e}. Using CSV fallback.")
        return pd.read_csv('../launch_model/data/training_data.csv', parse_dates=['launch_date'])

# ─────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────
@st.cache_resource
def load_model():
    ensemble  = joblib.load('../launch_model/models/ensemble.pkl')
    scaler    = joblib.load('../launch_model/models/scaler.pkl')
    explainer = joblib.load('../launch_model/models/shap_explainer.pkl')
    with open('../launch_model/models/feature_cols.json') as f:
        feature_cols = json.load(f)
    return ensemble, scaler, explainer, feature_cols

def assign_category(prob):
    if prob > 0.75: return ('Favorable',   '#27AE60')
    if prob >= 0.50: return ('Marginal',   '#F39C12')
    return ('Unfavorable', '#E74C3C')

# ─────────────────────────────────────────────
# Gauge (doc section 9.2)
# ─────────────────────────────────────────────
def build_gauge(prob_score, title="Launch Probability"):
    cat, color = assign_category(prob_score)
    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=prob_score * 100,
        title={'text': title, 'font': {'size': 20}},
        number={'suffix': '%', 'font': {'size': 40}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar':  {'color': color},
            'steps': [
                {'range': [0,  50], 'color': '#FADBD8'},
                {'range': [50, 75], 'color': '#FDEBD0'},
                {'range': [75,100], 'color': '#D5F5E3'},
            ],
            'threshold': {
                'line': {'color': 'black', 'width': 4},
                'thickness': 0.75,
                'value': prob_score * 100
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
    return fig

# ─────────────────────────────────────────────
# ERA5 climatological mean for future dates (doc section 9.3)
# ─────────────────────────────────────────────
def get_climatological_weather(selected_date, site='sriharikota'):
    nc_path = f'../launch_model/data/era5_{site}.nc'
    if not os.path.exists(nc_path):
        # Default fallback values (Sriharikota annual averages)
        return {
            'cloud_cover_pct': 40.0, 'wind_speed_ms': 5.0,
            'precipitation_mm': 2.0, 'temperature_c': 28.0,
            'relative_humidity_pct': 70.0, 'surface_pressure_hpa': 1010.0,
            'precip_3day_sum': 6.0, 'cloud_cover_day_minus_1': 38.0,
            'wind_speed_max_3day': 7.0
        }
    import xarray as xr
    ds = xr.open_dataset(nc_path)
    lat = 13.75 if site == 'sriharikota' else 28.50
    lon = 80.25 if site == 'sriharikota' else -80.75
    point = ds.sel(latitude=lat, longitude=lon, method='nearest')
    pdf = point.to_dataframe().reset_index()
    time_col = 'valid_time' if 'valid_time' in pdf.columns else 'time'
    pdf[time_col] = pd.to_datetime(pdf[time_col])
    pdf['day_of_year'] = pdf[time_col].dt.dayofyear
    target_doy = pd.Timestamp(selected_date).dayofyear
    seasonal = pdf[pdf['day_of_year'] == target_doy].mean(numeric_only=True)
    return {
        'cloud_cover_pct': float(seasonal.get('tcc', 0.4)) * 100,
        'wind_speed_ms': float(np.sqrt(seasonal.get('u10', 4)**2 + seasonal.get('v10', 3)**2)),
        'precipitation_mm': float(seasonal.get('tp', 0.002)) * 1000,
        'temperature_c': float(seasonal.get('t2m', 301)) - 273.15,
        'relative_humidity_pct': 70.0,
        'surface_pressure_hpa': float(seasonal.get('sp', 101000)) / 100,
        'precip_3day_sum': float(seasonal.get('tp', 0.002)) * 1000 * 3,
        'cloud_cover_day_minus_1': float(seasonal.get('tcc', 0.4)) * 100,
        'wind_speed_max_3day': float(np.sqrt(seasonal.get('u10', 4)**2 + seasonal.get('v10', 3)**2)) * 1.2
    }

def predict_for_date(selected_date, vehicle, ensemble, scaler, explainer, feature_cols):
    weather = get_climatological_weather(selected_date, site='sriharikota')
    dt = pd.Timestamp(selected_date)
    row = {**weather,
        'month': dt.month, 'day_of_year': dt.dayofyear,
        'is_monsoon_season': int(dt.month in [6,7,8,9]),
        'is_cyclone_season': int(dt.month in [10,11,12]),
        'vehicle_PSLV':   int('PSLV' in vehicle),
        'vehicle_GSLV':   int('GSLV' in vehicle),
        'vehicle_LVM3':   int('LVM3' in vehicle or 'Mk III' in vehicle),
        'vehicle_Falcon': int('Falcon' in vehicle),
    }
    X = pd.DataFrame([[row.get(c, 0) for c in feature_cols]], columns=feature_cols)
    X_scaled = scaler.transform(X)
    prob = float(ensemble.predict_proba(X_scaled)[0, 1])
    sv = explainer.shap_values(X_scaled)
    if isinstance(sv, list):
        sv_arr = sv[1][0]
    elif len(np.shape(sv)) == 3:
        sv_arr = sv[0, :, 1]
    else:
        sv_arr = sv[0]
    top_idx = np.argmax(np.abs(sv_arr))
    top_factor = feature_cols[top_idx]
    top_shap = float(sv_arr[top_idx])
    top5_idx = np.argsort(np.abs(sv_arr))[-5:][::-1]
    top5 = [(feature_cols[j], float(sv_arr[j])) for j in top5_idx]
    return prob, weather, top_factor, top_shap, top5

# ─────────────────────────────────────────────
# Page layout
# ─────────────────────────────────────────────
st.title("🚀 Launch Probability")
st.markdown("AI-powered launch readiness assessment using ERA5 historical weather and ML ensemble.")

df = load_launch_data()

# ── KPI Row (doc section 9.1)
total = len(df)
fav_pct   = (df.get('category', pd.Series(['Favorable'] * total)) == 'Favorable').mean() * 100
marg_pct  = (df.get('category', pd.Series(['Marginal']  * total)) == 'Marginal').mean()  * 100
unf_pct   = 100 - fav_pct - marg_pct

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Launches", f"{total:,}")
k2.metric("Favorable",  f"{fav_pct:.1f}%")
k3.metric("Marginal",   f"{marg_pct:.1f}%")
k4.metric("Unfavorable", f"{unf_pct:.1f}%")

st.divider()

# ── Select a launch
col_left, col_right = st.columns([1, 1])

with col_left:
    if 'mission_name' in df.columns and not df.empty:
        missions = df['mission_name'].dropna().unique().tolist()
        selected_mission = st.selectbox("Select Mission", missions)
        row = df[df['mission_name'] == selected_mission].iloc[0]
        prob_score = float(row.get('probability_score', 0.75))

        st.plotly_chart(build_gauge(prob_score), use_container_width=True)
    else:
        prob_score = 0.75
        st.plotly_chart(build_gauge(prob_score), use_container_width=True)

with col_right:
    cat, cat_color = assign_category(prob_score)
    st.markdown(
        f"<div style='padding:12px;border-radius:8px;background:{cat_color}25;"
        f"border-left:4px solid {cat_color}'>"
        f"<h3 style='color:{cat_color};margin:0'>{cat}</h3>"
        f"<p style='margin:4px 0 0'>Top Risk Factor: "
        f"<b>{row.get('top_risk_factor','N/A') if 'top_risk_factor' in dir() else 'N/A'}</b></p>"
        f"</div>",
        unsafe_allow_html=True
    )

    # SHAP bar chart (doc section 9.1)
    try:
        ensemble, sc, explainer, feature_cols = load_model()
        sv = explainer.shap_values(sc.transform([[row.get(c, 0) for c in feature_cols]]))
        # Newer shap returns a 3D array (samples, features, classes)
        if isinstance(sv, list):
            sv_arr = sv[1][0]
        elif len(np.shape(sv)) == 3:
            sv_arr = sv[0, :, 1]
        else:
            sv_arr = sv[0]
            
        top5_idx = np.argsort(np.abs(sv_arr))[-5:][::-1]
        shap_df = pd.DataFrame({
            'Feature': [feature_cols[j] for j in top5_idx],
            'SHAP Value': [sv_arr[j] for j in top5_idx]
        })
        shap_fig = px.bar(shap_df, x='SHAP Value', y='Feature', orientation='h',
                          title='Top 5 Risk Drivers',
                          color='SHAP Value', color_continuous_scale='RdYlGn')
        shap_fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(shap_fig, use_container_width=True)
    except Exception:
        st.info("Train the model first (run 04_train_model.py) to see SHAP explanations.")

# ── Historical table
st.subheader("📋 Historical Predictions")
display_cols = ['launch_date', 'mission_name', 'vehicle', 'source',
                'probability_score', 'category', 'actual_label', 'predicted_label']
available_display = [c for c in display_cols if c in df.columns]
st.dataframe(df[available_display], use_container_width=True, height=300)

# ─────────────────────────────────────────────
# Sidebar — Real-Time Future Prediction (doc section 9.3)
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🔮 Future Date Prediction")
    future_date = st.date_input("Launch Date", value=date.today() + timedelta(days=30),
                                min_value=date.today())
    vehicle_choice = st.selectbox("Vehicle", ['PSLV-XL', 'PSLV-CA', 'GSLV Mk II', 'LVM3'])

    if st.button("Predict Launch Probability", type='primary'):
        try:
            ensemble, sc, explainer, feature_cols = load_model()
            prob, weather, top_factor, top_shap, top5 = predict_for_date(
                future_date, vehicle_choice, ensemble, sc, explainer, feature_cols
            )
            cat, cat_color = assign_category(prob)

            st.plotly_chart(build_gauge(prob, f"{vehicle_choice} on {future_date}"),
                            use_container_width=True)
            st.markdown(
                f"<div style='padding:8px;border-radius:6px;background:{cat_color}25;"
                f"border-left:4px solid {cat_color}'>"
                f"<b style='color:{cat_color}'>{cat}</b><br>"
                f"Top risk: <b>{top_factor}</b></div>",
                unsafe_allow_html=True
            )

            st.markdown("**Weather Estimate Used:**")
            weather_df = pd.DataFrame({'Value': weather}).applymap(lambda x: f"{x:.2f}")
            st.dataframe(weather_df, use_container_width=True)

            st.markdown("**Top 3 SHAP Drivers:**")
            for feat, val in top5[:3]:
                arrow = "🔴" if val < 0 else "🟢"
                st.write(f"{arrow} **{feat}**: {val:+.3f}")
        except Exception as e:
            st.error(f"Prediction failed — ensure model is trained first.\n\n{e}")
