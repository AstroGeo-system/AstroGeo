import streamlit as st
import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import backend agent
from backend.agents.astronomy.astronomy_agent import AstronomyAgent

@st.cache_resource
def get_agent():
    return AstronomyAgent()
