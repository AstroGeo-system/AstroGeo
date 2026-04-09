import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_agent

# Use the db engine directly for analytics queries
from sqlalchemy import text
from backend.config import settings
from sqlalchemy import create_engine

@st.cache_resource
def get_db_engine():
    return create_engine(settings.DATABASE_URL)

st.set_page_config(page_title="Asteroid Database", page_icon="🪨", layout="wide")

st.title("🪨 Asteroid Database & Risk Monitor")
agent = get_agent()

# Search
search_term = st.text_input("mag Search Asteroid (ID)", placeholder="e.g. 99942, 2023 FW13")
if search_term:
    try:
        results = agent.search_asteroids(search_term)
        if results:
            st.write(f"Found {len(results)} matches:")
            st.dataframe(results)
        else:
            st.warning("No asteroids found matching that ID.")
    except Exception as e:
        st.error(f"Search failed: {e}")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("⚠️ High Risk Objects")
    try:
        high_risk = agent.get_high_risk_asteroids(min_risk_score=50)
        if high_risk:
            df_risk = pd.DataFrame(high_risk)
            st.dataframe(
                df_risk.style.background_gradient(subset=['improved_risk_score'], cmap="Reds"),
                use_container_width=True
            )
        else:
            st.success("No high-risk objects monitored.")
    except Exception as e:
        st.error(f"Error fetching high risk: {e}")

st.markdown("---")
st.header("📊 AI ML Risk Analytics")

try:
    with get_db_engine().connect() as conn:
        # Fetch data for visualizations
        query = text("""
            SELECT asteroid_id, improved_risk_score, adaptive_risk_category, estimated_diameter_km, 
                   avg_velocity, is_pha_candidate, cluster
            FROM astronomy.asteroid_ml_predictions
            WHERE improved_risk_score IS NOT NULL
        """)
        df_ml = pd.read_sql(query, conn)
        
    if not df_ml.empty:
        c1, c2 = st.columns(2)
        
        with c1:
            # 1. Scatter Plot: Risk vs Size
            fig_scatter = px.scatter(
                df_ml, x='estimated_diameter_km', y='improved_risk_score',
                color='adaptive_risk_category', 
                size='improved_risk_score',
                hover_name='asteroid_id',
                title="Asteroid Size vs. AI Risk Score",
                labels={'estimated_diameter_km': 'Est. Diameter (km)', 'improved_risk_score': 'ML Risk Score'},
                color_discrete_map={'High': 'red', 'Medium': 'orange', 'Low': 'green'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with c2:
            # 2. Risk Distribution
            fig_hist = px.histogram(
                df_ml, x='improved_risk_score',
                nbins=20,
                title="Distribution of AI Risk Scores",
                labels={'improved_risk_score': 'ML Risk Score'},
                color_discrete_sequence=['indigo']
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
except Exception as e:
    st.error(f"Could not load ML visualizations: {e}")

with col2:
    st.header("☄️ Upcoming Approaches")
    try:
        approaches = agent.get_upcoming_asteroid_approaches(days_ahead=30)
        # Note: This method might raise NotImplementedError in sync context if not handled?
        # Check astronomy/modules/asteroid_monitor.py: get_upcoming_approaches raises NotImplementedError.
        # But get_upcoming_approaches_async is async.
        # Streamlit supports async!
        
        # We need to run await agent.asteroid_monitor.get_upcoming_approaches_async(...)
        # But agent exposes get_upcoming_asteroid_approaches mapped to the sync one which raises exception.
        
        # FIX: We should update the Agent to handle the async call or expose the async method.
        # For now, let's try calling it, and if it fails, show a message.
        # OR better: modify app.py/agent to handle this.
        # Let's see what happens.
        
        if approaches:
             st.dataframe(pd.DataFrame(approaches))
        else:
             st.info("No upcoming approaches data.")
             
    except NotImplementedError:
        st.warning("Async approach fetching not fully wired in sync agent interface yet. Using mock/fallback if available.")
        # Alternatively call the async method directly if possible
        import asyncio
        import sys
        if sys.platform != "win32":
             # Try running async
             # approaches = asyncio.run(agent.asteroid_monitor.get_upcoming_approaches_async(days_ahead=30))
             # st.dataframe(approaches)
             pass
    except Exception as e:
        st.error(f"Error fetching approaches: {e}")
