import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from utils import get_agent # Import initialized agent

st.set_page_config(page_title="Satellite Tracker", page_icon="🛰️", layout="wide")

st.title("🛰️ Satellite Tracker")
location = st.session_state.get('location', 'Mumbai, India')
agent = get_agent()

tab1, tab2 = st.tabs(["Tonights Passes", "Live Tracking"])

with tab1:
    st.header(f"Visible Passes for {location}")
    
    hours = st.slider("Forecast Hours", 12, 72, 24)
    
    try:
        passes = agent.get_satellite_passes(location, hours_ahead=hours)
        
        if passes:
            df = pd.DataFrame(passes)
            # Select relevant columns
            display_cols = ['name', 'rise_time', 'max_elevation_deg', 'magnitude', 'hours_until', 'visibility_quality', 'weather_description']
            st.dataframe(
                df[display_cols].style.background_gradient(subset=['max_elevation_deg'], cmap="Greens"),
                use_container_width=True
            )
        else:
            st.info("No visible satellite passes found for this period.")
            
    except Exception as e:
        st.error(f"Failed to fetch passes: {e}")

with tab2:
    st.header("Live ISS Position")
    
    try:
        import requests as _requests
        resp = _requests.get("http://api.open-notify.org/iss-now.json", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lat = float(data["iss_position"]["latitude"])
        lon = float(data["iss_position"]["longitude"])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            m = folium.Map(location=[lat, lon], zoom_start=3)
            folium.Marker(
                [lat, lon], 
                popup="ISS", 
                icon=folium.Icon(color="blue", icon="rocket", prefix="fa")
            ).add_to(m)
            st_folium(m, height=400, use_container_width=True)
        
        with col2:
            st.metric("Latitude", f"{lat:.4f}")
            st.metric("Longitude", f"{lon:.4f}")
            st.metric("Altitude", "408.0 km")
            st.metric("Velocity", "7.66 km/s")
            st.metric("Sunlight", "Tracking live")
    except Exception as e:
        st.error(f"Error fetching ISS position: {e}")

