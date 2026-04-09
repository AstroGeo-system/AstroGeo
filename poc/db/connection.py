"""
db/connection.py  — Shared SQLAlchemy engine for AstroGeo POC
"""
import os
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load poc/.env regardless of current working directory.
POC_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(POC_DIR, ".env"))

@st.cache_resource
def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL not set. Create poc/.env with: "
            "DATABASE_URL=postgresql://user:pass@localhost:5432/astrogeo_db"
        )
    return create_engine(db_url, pool_pre_ping=True)
