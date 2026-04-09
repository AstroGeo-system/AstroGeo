import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_agent

st.set_page_config(page_title="Weather Monitor", page_icon="🌤️", layout="wide")

st.title("🌤️ Observation Weather Monitor")
location = st.session_state.get('location', 'Mumbai, India')
agent = get_agent()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Current Conditions")
    try:
        current = agent.get_observation_conditions(location)
        if current:
            st.metric("Status", current.get('weather_description'))
            st.metric("Temp", f"{current.get('temperature_celsius')} °C")
            st.metric("Cloud Cover", f"{current.get('cloud_cover_percent')}%")
            st.metric("Humidity", f"{current.get('humidity_percent')}%")
            st.metric("Wind", f"{current.get('wind_speed_kmh')} km/h")
        else:
            st.warning("No current weather data")
    except Exception as e:
        st.error(f"Error: {e}")

with col2:
    st.subheader("Forecast vs Current Trend")
    try:
        trend = agent.compare_forecast_vs_current(location)
        if trend:
            st.info(f"Trend: **{trend.get('trend', 'Unknown')}**")
            st.write(f"Recommendation: {trend.get('recommendation')}")
            
            # Creating a simple chart if data available (mocking forecast for viz logic reuse)
            # Ideally verify get_best_viewing_window returns enough points
            windows = agent.get_best_viewing_window(location, hours_ahead=24, min_quality=0)
            if windows:
                df = pd.DataFrame(windows)
                fig = px.line(df, x='start_time', y='overall_quality_score', 
                              title='Observation Quality Forecast (Next 24 Hours)',
                              markers=True)
                fig.add_hline(y=70, line_dash="dash", annotation_text="Good Threshold")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not calculate trend")
    except Exception as e:
        st.error(f"Error: {e}")

st.header("Best Viewing Windows")
try:
    best_windows = agent.get_best_viewing_window(location, min_quality=70)
    if best_windows:
        st.dataframe(pd.DataFrame(best_windows))
    else:
        st.info("No 'Good' quality windows (>70) in the next 24 hours.")
except Exception as e:
    st.error(f"Error fetching windows: {e}")
