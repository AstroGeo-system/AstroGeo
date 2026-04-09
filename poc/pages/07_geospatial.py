"""
Page 7 — Geospatial NDVI & Change Explorer

Fast wiring: PostgreSQL data (ndvi_results) + SHAP heatmap image (shap_heatmap.png)
into a single interactive Streamlit page.
"""

import os
import sys
import copy
import json
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium
from sqlalchemy import text
from dotenv import load_dotenv

# Make `poc/` importable (so `db.connection` works).
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Project root for static artifacts (and backend/.env).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SHAP_HEATMAP_PATH = os.path.join(PROJECT_ROOT, os.path.join("backend", "outputs", "shap_heatmap.png"))

# Load backend DB + GEE env vars so live inference uses the same settings.
load_dotenv(os.path.join(PROJECT_ROOT, "backend", ".env"))

# Ensure Earth Engine project is available for live inference inside Streamlit.
os.environ.setdefault("EE_PROJECT", os.getenv("EE_PROJECT", "astrogeo-gee-491204"))

from db.connection import get_engine  # noqa: E402


st.set_page_config(page_title="Geospatial NDVI Explorer", layout="wide")
st.title("🌍 Geospatial NDVI & Change Explorer")
st.caption("Zone selector updates map + NDVI time series + SHAP heatmap caption.")


# Zone rectangles for the folium map (bbox from `geospatial_agent.py`).
ZONE_BBOX = {
    "punjab_haryana_delhi": {"west": 73.8, "south": 27.6, "east": 77.8, "north": 32.5},
    "uttar_pradesh_bihar": {"west": 77.8, "south": 24.0, "east": 88.5, "north": 28.5},
    "west_bengal_sikkim": {"west": 85.8, "south": 21.5, "east": 89.9, "north": 27.5},
    "rajasthan": {"west": 69.5, "south": 23.0, "east": 78.3, "north": 30.2},
    "gujarat_dadra_dd": {"west": 68.1, "south": 20.0, "east": 74.5, "north": 24.7},
    "maharashtra_marathwada": {"west": 74.5, "south": 17.5, "east": 77.8, "north": 20.5},
    "maharashtra_vidarbha": {"west": 77.8, "south": 18.5, "east": 80.9, "north": 22.0},
    "madhya_pradesh_chhattisgarh": {"west": 74.0, "south": 17.8, "east": 84.4, "north": 26.9},
    "jharkhand_odisha": {"west": 81.5, "south": 17.8, "east": 87.5, "north": 24.0},
    "andhra_telangana_coast": {"west": 76.8, "south": 13.5, "east": 84.8, "north": 19.9},
    "karnataka_goa": {"west": 74.0, "south": 11.5, "east": 78.6, "north": 18.5},
    "kerala_lakshadweep": {"west": 72.0, "south": 8.0, "east": 77.6, "north": 12.8},
    "tamil_nadu_puducherry": {"west": 76.2, "south": 8.0, "east": 80.4, "north": 13.6},
    "northeast_assam_meghalaya": {"west": 88.5, "south": 24.0, "east": 96.5, "north": 28.2},
    "northeast_hill_states": {"west": 93.0, "south": 21.5, "east": 97.4, "north": 29.3},
    "himachal_uttarakhand": {"west": 75.5, "south": 28.5, "east": 81.1, "north": 31.5},
    "kashmir_ladakh": {"west": 73.5, "south": 32.0, "east": 80.4, "north": 37.6},
    "andaman_nicobar": {"west": 92.2, "south": 6.7, "east": 94.0, "north": 13.7},
}


CHANGE_CLASS_COLORS = {
    0: "#2ca02c",  # stable vegetation (green)
    1: "#d62728",  # vegetation loss (red)
    2: "#ff7f0e",  # urban growth (orange)
    3: "#7f7f7f",  # stable other (gray)
}

# Map admin state name → our NDVI zone bucket name
# Note: Maharashtra is split into two zones; for the fast choropleth we map the state
# to `maharashtra_marathwada`. `maharashtra_vidarbha` is still available via zone dropdown
# and NDVI charts / confidence / SHAP caption.
STATE_TO_ZONE = {
    "Andhra Pradesh": "andhra_telangana_coast",
    "Telangana": "andhra_telangana_coast",
    "Arunachal Pradesh": "northeast_hill_states",
    "Assam": "northeast_assam_meghalaya",
    "Meghalaya": "northeast_assam_meghalaya",
    "Tripura": "northeast_assam_meghalaya",
    "Sikkim": "west_bengal_sikkim",
    "West Bengal": "west_bengal_sikkim",
    "Bihar": "uttar_pradesh_bihar",
    "Uttar Pradesh": "uttar_pradesh_bihar",
    "Chhattisgarh": "madhya_pradesh_chhattisgarh",
    "Madhya Pradesh": "madhya_pradesh_chhattisgarh",
    "Goa": "karnataka_goa",
    "Gujarat": "gujarat_dadra_dd",
    "Haryana": "punjab_haryana_delhi",
    "Punjab": "punjab_haryana_delhi",
    "Delhi": "punjab_haryana_delhi",
    "Himachal Pradesh": "himachal_uttarakhand",
    "Uttarakhand": "himachal_uttarakhand",
    "Jharkhand": "jharkhand_odisha",
    "Odisha": "jharkhand_odisha",
    "Karnataka": "karnataka_goa",
    "Kerala": "kerala_lakshadweep",
    "Maharashtra": "maharashtra_marathwada",
    "Manipur": "northeast_hill_states",
    "Mizoram": "northeast_hill_states",
    "Nagaland": "northeast_hill_states",
    "Rajasthan": "rajasthan",
    "Tamil Nadu": "tamil_nadu_puducherry",
    "Jammu & Kashmir": "kashmir_ladakh",
    "Ladakh": "kashmir_ladakh",
}


POC_DIR = os.path.dirname(os.path.dirname(__file__))
GEOJSON_PATH = os.path.join(POC_DIR, "india_states.geojson")


def _get_state_name_key(geojson: dict) -> str:
    """Try to detect the GeoJSON property key that stores the state name."""
    props = geojson["features"][0].get("properties", {}) if geojson.get("features") else {}
    for k in ["NAME_1", "ST_NM", "state", "name"]:
        if k in props:
            return k
    # Fallback: first string property
    for k, v in props.items():
        if isinstance(v, str) and v.strip():
            return k
    return "NAME_1"


@st.cache_data(ttl=86400)
def load_india_geojson() -> dict:
    """
    Load state boundary polygons (GeoJSON) for Folium.
    Downloads once into `poc/india_states.geojson`.
    """
    if not os.path.exists(GEOJSON_PATH):
        url = (
            "https://raw.githubusercontent.com/Subhash9325/"
            "GeoJson-Data-of-Indian-States/master/Indian_States"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
            f.write(resp.text)
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Per-zone GEE timeout (seconds). GEE calls can be slow; 90s is generous.
_GEE_ZONE_TIMEOUT = 90
# Max parallel workers — GEE rate-limits concurrent requests; 6 is safe.
_GEE_MAX_WORKERS = 6


@st.cache_data(ttl=300)
def fetch_predictions_for_year(year: int, zones: list[str]) -> pd.DataFrame:
    """
    For historical years (training years), read predictions from ndvi_results.
    For live years (>= 2025), call geospatial_agent.get_or_compute_live()
    in parallel using ThreadPoolExecutor to avoid a 10-minute serial hang.
    """
    # Historical: use DB rows directly.
    if year in [2018, 2019, 2020, 2022, 2024]:
        engine = get_engine()
        sql = text(
            """
            SELECT
                zone_name,
                year,
                change_class,
                change_class_label,
                confidence,
                shap_top_feature
            FROM ndvi_results
            WHERE year = :year
            ORDER BY zone_name
            """
        )
        return pd.read_sql(sql, engine, params={"year": year})

    # Live: use GEE + RF via geospatial_agent — run zones in parallel.
    sys.path.insert(0, PROJECT_ROOT)
    from backend.pipelines.geospatial_agent import get_or_compute_live  # type: ignore

    records: list[dict] = []
    failed_zones: list[str] = []

    progress = st.progress(0, text=f"Fetching live {year} data from Google Earth Engine…")
    total = len(zones)

    def _fetch_one(zone: str) -> dict:
        return get_or_compute_live(zone, year)

    completed_count = 0
    with ThreadPoolExecutor(max_workers=_GEE_MAX_WORKERS) as executor:
        future_to_zone = {executor.submit(_fetch_one, z): z for z in zones}
        for future in as_completed(future_to_zone):
            zone = future_to_zone[future]
            completed_count += 1
            progress.progress(
                completed_count / total,
                text=f"GEE live inference: {completed_count}/{total} zones done…",
            )
            try:
                res = future.result(timeout=_GEE_ZONE_TIMEOUT)
            except FuturesTimeoutError:
                failed_zones.append(zone)
                continue
            except Exception:
                failed_zones.append(zone)
                continue

            if res.get("status") != "ok":
                failed_zones.append(zone)
                continue

            records.append(
                {
                    "zone_name": zone,
                    "year": year,
                    "change_class": res["change_class"],
                    "change_class_label": res["change_class_label"],
                    "confidence": res["confidence"],
                    # For live years we don't recompute per-class SHAP; leave blank.
                    "shap_top_feature": "",
                }
            )

    progress.empty()
    if failed_zones:
        st.warning(
            f"⚠️ {len(failed_zones)} zone(s) timed out or returned no data "
            f"and were skipped: {', '.join(failed_zones)}"
        )

    return pd.DataFrame.from_records(records)


def build_india_choropleth(
    geojson: dict,
    preds_year_df: pd.DataFrame,
    selected_zone: str,
) -> folium.Map:
    """Build Folium map with real state polygons colored by predicted change class."""
    state_name_key = _get_state_name_key(geojson)

    zone_to_class = {
        str(r["zone_name"]): int(r["change_class"])
        for _, r in preds_year_df.iterrows()
    }
    zone_to_label = {
        str(r["zone_name"]): str(r["change_class_label"])
        for _, r in preds_year_df.iterrows()
    }
    zone_to_conf = {
        str(r["zone_name"]): float(r["confidence"])
        for _, r in preds_year_df.iterrows()
    }
    zone_to_shap = {
        str(r["zone_name"]): str(r.get("shap_top_feature", ""))
        for _, r in preds_year_df.iterrows()
    }

    augmented = copy.deepcopy(geojson)
    for feature in augmented.get("features", []):
        props = feature.get("properties", {})
        state_name = props.get(state_name_key, "")
        zone = STATE_TO_ZONE.get(state_name)

        cls = zone_to_class.get(zone) if zone else None
        label = zone_to_label.get(zone) if zone else None
        conf = zone_to_conf.get(zone) if zone else None
        shap_top_feature = zone_to_shap.get(zone) if zone else ""

        props["pred_zone"] = zone or ""
        props["pred_change_class"] = -1 if cls is None else int(cls)
        props["pred_change_label"] = label or "No data"
        props["pred_confidence"] = "" if conf is None else float(conf)
        props["pred_shap_top_feature"] = shap_top_feature or ""
        props["is_selected_zone"] = (zone == selected_zone)

    def style_function(feature):
        props = feature.get("properties", {})
        cls = int(props.get("pred_change_class", -1))
        fill_color = CHANGE_CLASS_COLORS.get(cls, "#cccccc")
        is_selected = bool(props.get("is_selected_zone", False))
        border_color = "#000000" if is_selected else "#333333"
        weight = 3 if is_selected else 1
        return {
            "fillColor": fill_color,
            "color": border_color,
            "weight": weight,
            "fillOpacity": 0.75,
        }

    m = folium.Map(location=[22.5, 82.0], zoom_start=5, tiles="CartoDB positron")

    folium.GeoJson(
        augmented,
        name="India states",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                state_name_key,
                "pred_change_label",
                "pred_zone",
                "pred_shap_top_feature",
            ],
            aliases=["State:", "Predicted:", "Zone:", "Top SHAP feature:"],
            sticky=True,
            labels=True,
        ),
    ).add_to(m)

    legend_html = f"""
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: white; padding: 12px 16px; border: 1px solid #ccc;
                border-radius: 8px; font-size: 13px; line-height: 1.8;">
        <div style="font-weight: 700; margin-bottom: 6px;">Change Class Legend</div>
        <div><span style="background:{CHANGE_CLASS_COLORS[0]}; display:inline-block;width:14px;height:14px;margin-right:6px;"></span>0 Stable vegetation</div>
        <div><span style="background:{CHANGE_CLASS_COLORS[1]}; display:inline-block;width:14px;height:14px;margin-right:6px;"></span>1 Vegetation loss</div>
        <div><span style="background:{CHANGE_CLASS_COLORS[2]}; display:inline-block;width:14px;height:14px;margin-right:6px;"></span>2 Urban growth</div>
        <div><span style="background:{CHANGE_CLASS_COLORS[3]}; display:inline-block;width:14px;height:14px;margin-right:6px;"></span>3 Stable other</div>
        <div><span style="background:#cccccc; display:inline-block;width:14px;height:14px;margin-right:6px;"></span>No data</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    return m


@st.cache_data(ttl=300)
def fetch_zones() -> list[str]:
    engine = get_engine()
    df = pd.read_sql(text("SELECT DISTINCT zone_name FROM ndvi_results ORDER BY zone_name"), engine)
    return df["zone_name"].astype(str).tolist()


@st.cache_data(ttl=300)
def fetch_zone_timeseries(zone_name: str) -> pd.DataFrame:
    engine = get_engine()
    sql = text(
        "SELECT year, ndvi_mean "
        "FROM ndvi_results "
        "WHERE zone_name = :zone_name "
        "ORDER BY year"
    )
    return pd.read_sql(sql, engine, params={"zone_name": zone_name})


zones = fetch_zones()
if not zones:
    st.error("No zones found in `ndvi_results`. Run pipeline steps 5–7 first.")
    st.stop()

geojson = load_india_geojson()

BASE_YEARS = [2018, 2019, 2020, 2022, 2024]
current_year = datetime.datetime.utcnow().year
extra_years = [y for y in [2025, current_year] if y not in BASE_YEARS]
year_options = BASE_YEARS + extra_years

# Default to the most recent *historical* year so the page loads instantly.
# Users can deliberately slide to 2025 for live GEE inference.
_default_year = 2024 if 2024 in year_options else year_options[0]
selected_year = st.select_slider(
    "Select year (map coloring)",
    options=year_options,
    value=_default_year,
)

if selected_year >= 2025:
    st.info(
        f"🛰️ Live data — fetching {selected_year} NDVI from "
        f"Google Earth Engine via the trained RF model. "
        f"Results are cached in PostgreSQL for 7 days."
    )

preds_year_df = fetch_predictions_for_year(selected_year, zones)
if preds_year_df.empty:
    st.error("No prediction rows found for the selected year.")
    st.stop()

selected_zone = st.selectbox("Select zone", zones, index=0)

timeseries_df = fetch_zone_timeseries(selected_zone)
zone_rows = preds_year_df[preds_year_df["zone_name"] == selected_zone]
if zone_rows.empty:
    # Defensive fallback (shouldn't happen if DB is consistent)
    st.warning("No prediction row for selected zone/year found; SHAP caption may be incomplete.")
    latest_row = {}
else:
    latest_row = zone_rows.iloc[0]

col_map, col_chart = st.columns([1, 1], gap="large")

with col_map:
    st.subheader(f"India state map — predicted change class ({selected_year})")
    ind_map = build_india_choropleth(geojson, preds_year_df, selected_zone)
    # Use a dynamic key so Streamlit fully re-renders the map
    # whenever the year or zone selection changes.
    st_folium(ind_map, width=900, height=560, key=f"map_{selected_year}_{selected_zone}")

with col_chart:
    st.subheader(f"NDVI time-series — {selected_zone}")
    fig = px.line(
        timeseries_df,
        x="year",
        y="ndvi_mean",
        markers=True,
        title=None,
    )
    fig.update_layout(xaxis_title="Year", yaxis_title="Mean NDVI", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

col_shap, col_details = st.columns([1, 1], gap="large")

with col_shap:
    st.subheader("SHAP Heatmap (global model)")
    if os.path.exists(SHAP_HEATMAP_PATH):
        st.image(
            SHAP_HEATMAP_PATH,
            caption=(
                f"Selected zone ({selected_year}) prediction: {latest_row.get('change_class_label','N/A')} "
                f"(confidence={float(latest_row.get('confidence',0)):.3f}). "
                f"Top SHAP feature: {latest_row.get('shap_top_feature','N/A')}."
            ),
            use_container_width=True,
        )
    else:
        st.warning(f"Missing artifact: {SHAP_HEATMAP_PATH}")

with col_details:
    st.subheader("Selected Zone Summary")
    st.write(f"Zone: `{selected_zone}`")
    st.write(f"Predicted class: `{latest_row.get('change_class_label','N/A')}`")
    st.write(f"Confidence: `{float(latest_row.get('confidence',0)):.3f}`")
    st.write(f"Top SHAP feature: `{latest_row.get('shap_top_feature','N/A')}`")
    st.dataframe(timeseries_df, use_container_width=True)

