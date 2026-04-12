import streamlit as st
import pandas as pd
from utils import get_agent

st.set_page_config(page_title="Observation Planner", page_icon="📅", layout="wide")

st.title("📅 Observation Planner")
location = st.session_state.get('location', 'Mumbai, India')
agent = get_agent()

st.header(f"Plan for {location}")

if st.button("Generate Tonight's Plan"):
    with st.spinner("Analyzing satellites and weather..."):
        try:
            plan = agent.get_observation_plan(location)
            
            # Weather Summary
            st.subheader("Weather Assessment")
            w = plan.get('current_weather', {})
            st.info(f"{w.get('weather_description', 'Unknown')} - Quality: {w.get('quality_category', 'N/A')}")
            
            # Windows
            st.subheader("Best Viewing Windows")
            windows = plan.get('best_viewing_windows', [])
            if windows:
                for win in windows:
                    st.success(f"Time: {win['start_time']} | Quality Score: {win['overall_quality_score']}")
            else:
                st.warning("No prime viewing windows found.")
            
            # Top Passes
            st.subheader("Recommended Targets")
            passes = plan.get('satellite_passes', [])
            if passes:
                for p in passes:
                    with st.expander(f"🛰️ {p['name']} at {p['rise_time'].split(' ')[1]}"):
                        st.write(f"Max Elevation: {p['max_elevation_deg']}°")
                        st.write(f"Brightness (Mag): {p['magnitude']}")
                        st.write(f"Direction: {p.get('azimuth_rise_deg', 'N/A')}°")
            else:
                st.write("No high-quality satellite passes.")
                
        except Exception as e:
            st.error(f"Failed to generate plan: {e}")
