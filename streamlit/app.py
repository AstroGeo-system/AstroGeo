import streamlit as st
import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Import backend agent
from backend.agents.astronomy.astronomy_agent import AstronomyAgent

st.set_page_config(
    page_title="AstroGeo",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from utils import get_agent

try:
    agent = get_agent()
except Exception as e:
    st.error(f"Failed to initialize Astronomy Agent: {e}")
    st.stop()

# Title and Intro
st.title("🛰️ AstroGeo: Your Space Observation Assistant")
st.markdown("""
Welcome to **AstroGeo**! 
Track satellites, check observation weather, and monitor near-earth asteroids in real-time.
""")

# Sidebar - Location Selector
st.sidebar.header("📍 Observation Location")
locations = agent.get_available_locations()
location_names = [loc['name'] for loc in locations] if locations else ["Mumbai, India"]

# Add "New Location" option logic could be added here
selected_location = st.sidebar.selectbox(
    "Select Location", 
    location_names,
    index=0 if location_names else 0
)

# Store location in session state for other pages
st.session_state['location'] = selected_location

# Dashboard Overview
st.header(f"🔭 Overview for {selected_location}")

col1, col2, col3 = st.columns(3)

# 1. Weather Snapshot
with col1:
    st.subheader("🌤️ Weather")
    try:
        weather = agent.get_observation_conditions(selected_location)
        if weather:
            st.metric("Condition", weather.get('weather_description', 'Unknown'))
            st.metric("Cloud Cover", f"{weather.get('cloud_cover_percent', 0)}%", delta_color="inverse")
            st.metric("Quality", weather.get('quality_category', 'N/A'))
        else:
            st.warning("No weather data available")
    except Exception as e:
        st.error(f"Error: {e}")

# 2. Next ISS Pass
with col2:
    st.subheader("🛰️ Next ISS Pass")
    try:
        iss_pass = agent.get_next_iss_pass(selected_location)
        if iss_pass:
            st.metric("Rise Time", iss_pass['rise_time'].split(' ')[1])
            st.metric("Max Elevation", f"{iss_pass['max_elevation_deg']}°")
            st.metric("Duration", f"{iss_pass.get('duration_seconds', 0) // 60}m {iss_pass.get('duration_seconds', 0) % 60}s")
        else:
            st.info("No visible passes soon")
    except Exception as e:
        st.error(f"Error: {e}")

# 3. Asteroid Alert
with col3:
    st.subheader("🪨 Asteroid Risk")
    try:
        high_risk = agent.get_high_risk_asteroids(min_risk_score=50)
        if high_risk:
            top_risk = high_risk[0]
            st.metric("High Risk Object", top_risk['asteroid_id'])
            st.metric("Risk Score", f"{top_risk.get('improved_risk_score', 0):.1f}")
            st.warning(f"{len(high_risk)} risky objects tracked")
        else:
            st.success("No high-risk asteroids detected currently")
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")
st.info("👈 Use the sidebar to navigate to detailed trackers and planners.")
