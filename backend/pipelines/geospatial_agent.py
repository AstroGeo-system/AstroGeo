# geospatial_agent.py
# AstroGeo — Geospatial Agent
# Full India coverage — 17 zones, all 28 states + 8 UTs
# Requires: earthengine-api, psycopg2, pandas, numpy

import ee
import json
import os
import hashlib
import datetime
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import psycopg2
import joblib
MODEL_FILE_PATH = os.path.join(os.path.dirname(__file__), "../models/geospatial_rf_model.pkl")

EE_PROJECT = os.getenv("EE_PROJECT")
if EE_PROJECT:
    ee.Initialize(project=EE_PROJECT)
else:
    # Uses the default project associated with your Earth Engine credentials.
    ee.Initialize()

# ── Constants ────────────────────────────────────────────────
SENTINEL2_COLLECTION = 'COPERNICUS/S2_SR_HARMONIZED'
SCALE_METRES         = 10
ANALYSIS_YEARS       = [2018, 2019, 2020, 2022, 2024]

CHANGE_CLASSES = {
    0: 'stable_vegetation',
    1: 'vegetation_loss',
    2: 'urban_growth',
    3: 'stable_other',
}

# ── Zone definitions — all Indian states and UTs ─────────────
# Each zone has:
#   bbox            — geographic bounding box
#   start_month     — beginning of cloud-free window
#   end_month       — end of cloud-free window
#   year_offset     — 1 if window crosses Dec→Jan boundary
#   cloud_threshold — max CLOUDY_PIXEL_PERCENTAGE
#   states          — which states this zone covers
#   notes           — why this window was chosen

INDIA_ZONES = {

    'punjab_haryana_delhi': {
        'bbox': {'west': 73.8, 'south': 27.6, 'east': 77.8, 'north': 32.5},
        'start_month': 11, 'end_month': 12, 'year_offset': 0,
        'cloud_threshold': 15,
        'states': ['Punjab', 'Haryana', 'Delhi', 'Chandigarh'],
        'notes': 'Post-kharif harvest window. Wheat sown, clear skies.',
    },

    'uttar_pradesh_bihar': {
        'bbox': {'west': 77.8, 'south': 24.0, 'east': 88.5, 'north': 28.5},
        'start_month': 11, 'end_month': 12, 'year_offset': 0,
        'cloud_threshold': 20,
        'states': ['Uttar Pradesh', 'Bihar'],
        'notes': 'Post-monsoon harvest. Rabi crop sowing visible.',
    },

    'west_bengal_sikkim': {
        'bbox': {'west': 85.8, 'south': 21.5, 'east': 89.9, 'north': 27.5},
        'start_month': 11, 'end_month': 12, 'year_offset': 0,
        'cloud_threshold': 25,
        'states': ['West Bengal', 'Sikkim'],
        'notes': 'Post-monsoon. Bay of Bengal influence reduces Nov onwards.',
    },

    'rajasthan': {
        'bbox': {'west': 69.5, 'south': 23.0, 'east': 78.3, 'north': 30.2},
        'start_month': 10, 'end_month': 12, 'year_offset': 0,
        'cloud_threshold': 10,
        'states': ['Rajasthan'],
        'notes': 'Arid zone. Extremely clear skies Oct–Dec.',
    },

    'gujarat_dadra_dd': {
        'bbox': {'west': 68.1, 'south': 20.0, 'east': 74.5, 'north': 24.7},
        'start_month': 10, 'end_month': 11, 'year_offset': 0,
        'cloud_threshold': 15,
        'states': ['Gujarat', 'Dadra & NH', 'Daman & Diu'],
        'notes': 'Post-monsoon. Kutch drought zone + Saurashtra agriculture.',
    },

    'maharashtra_marathwada': {
        'bbox': {'west': 74.5, 'south': 17.5, 'east': 77.8, 'north': 20.5},
        'start_month': 10, 'end_month': 11, 'year_offset': 0,
        'cloud_threshold': 20,
        'states': ['Maharashtra (Marathwada)'],
        'notes': 'Most drought-affected region. Latur, Osmanabad, Beed.',
    },

    'maharashtra_vidarbha': {
        'bbox': {'west': 77.8, 'south': 18.5, 'east': 80.9, 'north': 22.0},
        'start_month': 10, 'end_month': 11, 'year_offset': 0,
        'cloud_threshold': 20,
        'states': ['Maharashtra (Vidarbha)'],
        'notes': 'Cotton belt. Highest farmer distress. Nagpur, Amravati.',
    },

    'madhya_pradesh_chhattisgarh': {
        'bbox': {'west': 74.0, 'south': 17.8, 'east': 84.4, 'north': 26.9},
        'start_month': 11, 'end_month': 12, 'year_offset': 0,
        'cloud_threshold': 20,
        'states': ['Madhya Pradesh', 'Chhattisgarh'],
        'notes': 'Central India forests + agriculture. Post-kharif window.',
    },

    'jharkhand_odisha': {
        'bbox': {'west': 81.5, 'south': 17.8, 'east': 87.5, 'north': 24.0},
        'start_month': 11, 'end_month': 12, 'year_offset': 0,
        'cloud_threshold': 20,
        'states': ['Jharkhand', 'Odisha'],
        'notes': 'Tribal agricultural land, mining disturbance. Sal forests.',
    },

    'andhra_telangana_coast': {
        'bbox': {'west': 76.8, 'south': 13.5, 'east': 84.8, 'north': 19.9},
        'start_month': 12, 'end_month': 2, 'year_offset': 1,
        'cloud_threshold': 25,
        'states': ['Andhra Pradesh', 'Telangana'],
        'notes': 'Post NE monsoon. Sriharikota ISRO launch site. '
                 'Cyclone corridor. Year offset — Dec 2024 to Feb 2025.',
    },

    'karnataka_goa': {
        'bbox': {'west': 74.0, 'south': 11.5, 'east': 78.6, 'north': 18.5},
        'start_month': 1, 'end_month': 3, 'year_offset': 1,
        'cloud_threshold': 25,
        'states': ['Karnataka', 'Goa'],
        'notes': 'SW + NE monsoon dual influence. Jan–Mar is clearest window.',
    },

    'kerala_lakshadweep': {
        'bbox': {'west': 72.0, 'south': 8.0, 'east': 77.6, 'north': 12.8},
        'start_month': 1, 'end_month': 3, 'year_offset': 1,
        'cloud_threshold': 30,
        'states': ['Kerala', 'Lakshadweep'],
        'notes': 'Two monsoon seasons. Jan–Mar only reliable clear window.',
    },

    'tamil_nadu_puducherry': {
        'bbox': {'west': 76.2, 'south': 8.0, 'east': 80.4, 'north': 13.6},
        'start_month': 1, 'end_month': 3, 'year_offset': 1,
        'cloud_threshold': 25,
        'states': ['Tamil Nadu', 'Puducherry'],
        'notes': 'NE monsoon ends Dec. Jan–Mar best window.',
    },

    'northeast_assam_meghalaya': {
        'bbox': {'west': 88.5, 'south': 24.0, 'east': 96.5, 'north': 28.2},
        'start_month': 12, 'end_month': 2, 'year_offset': 1,
        'cloud_threshold': 35,
        'states': ['Assam', 'Meghalaya', 'Tripura'],
        'notes': 'Brahmaputra plain + Khasi hills. Dec–Feb least cloudy.',
    },

    'northeast_hill_states': {
        'bbox': {'west': 93.0, 'south': 21.5, 'east': 97.4, 'north': 29.3},
        'start_month': 12, 'end_month': 2, 'year_offset': 1,
        'cloud_threshold': 40,
        'states': ['Arunachal Pradesh', 'Nagaland', 'Manipur', 'Mizoram'],
        'notes': 'Heavy rainfall year-round. Highest threshold necessary.',
    },

    'himachal_uttarakhand': {
        'bbox': {'west': 75.5, 'south': 28.5, 'east': 81.1, 'north': 31.5},
        'start_month': 9, 'end_month': 10, 'year_offset': 0,
        'cloud_threshold': 25,
        'states': ['Himachal Pradesh', 'Uttarakhand'],
        'notes': 'Pre-snow window. Apple orchards, alpine meadows, glaciers.',
    },

    'kashmir_ladakh': {
        'bbox': {'west': 73.5, 'south': 32.0, 'east': 80.4, 'north': 37.6},
        'start_month': 8, 'end_month': 9, 'year_offset': 0,
        'cloud_threshold': 20,
        'states': ['Jammu & Kashmir', 'Ladakh'],
        'notes': 'Aug–Sep only summer window before snow. Glacial monitoring.',
    },

    'andaman_nicobar': {
        'bbox': {'west': 92.2, 'south': 6.7, 'east': 94.0, 'north': 13.7},
        'start_month': 2, 'end_month': 4, 'year_offset': 1,
        'cloud_threshold': 30,
        'states': ['Andaman & Nicobar Islands'],
        'notes': 'Inter-monsoon window Feb–Apr. Tropical rainforest monitoring.',
    },
}


# ── AOI builder ──────────────────────────────────────────────
def build_aoi(bbox: Dict) -> ee.Geometry:
    """Convert bbox dict to GEE Geometry."""
    if 'coordinates' in bbox:
        return ee.Geometry.Polygon(bbox['coordinates'])
    return ee.Geometry.Rectangle([
        bbox['west'], bbox['south'],
        bbox['east'], bbox['north'],
    ])


# ── Cloud masking ────────────────────────────────────────────
def mask_s2_clouds(image: ee.Image) -> ee.Image:
    """SCL-based cloud mask for Sentinel-2 L2A."""
    scl = image.select('SCL')
    mask = (scl.neq(3)   # cloud shadow
              .And(scl.neq(8))   # medium cloud
              .And(scl.neq(9))   # high cloud
              .And(scl.neq(10))) # thin cirrus
    return image.updateMask(mask)


# ── Annual collection — zone-aware ───────────────────────────
def get_annual_collection(aoi: ee.Geometry,
                           year: int,
                           start_month: int,
                           end_month: int,
                           year_offset: int,
                           cloud_threshold: int) -> ee.ImageCollection:
    """
    Fetch cloud-filtered Sentinel-2 collection for a given year
    and zone-specific seasonal window.

    year_offset=1 means the window crosses into the next year
    e.g. start_month=12, end_month=2, year_offset=1
         → Dec 2024 to Feb 2025
    """
    if year_offset == 1:
        # Window crosses year boundary
        start = f'{year}-{start_month:02d}-01'
        end   = f'{year + 1}-{end_month:02d}-28'
    else:
        start = f'{year}-{start_month:02d}-01'
        # End date: first day of month after end_month
        end_y = year + 1 if end_month == 12 else year
        end_m = 1 if end_month == 12 else end_month + 1
        end   = f'{end_y}-{end_m:02d}-01'

    return (
        ee.ImageCollection(SENTINEL2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
        .map(mask_s2_clouds)
    )


# ── NDVI per year ────────────────────────────────────────────
def compute_annual_ndvi(aoi: ee.Geometry,
                         year: int,
                         zone_config: Dict) -> ee.Image:
    """Compute cloud-free median NDVI for one year in a given zone."""
    collection = get_annual_collection(
        aoi, year,
        zone_config['start_month'],
        zone_config['end_month'],
        zone_config['year_offset'],
        zone_config['cloud_threshold'],
    )
    median = collection.median()
    ndvi   = median.normalizedDifference(['B8', 'B4'])
    return ndvi.rename(f'ndvi_{year}')


# ── NDVI stack ───────────────────────────────────────────────
def build_ndvi_stack(aoi: ee.Geometry,
                      zone_config: Dict) -> ee.Image:
    """Build 5-band multitemporal NDVI stack for a zone."""
    ndvi_images = [
        compute_annual_ndvi(aoi, year, zone_config)
        for year in ANALYSIS_YEARS
    ]
    return ee.Image.cat(ndvi_images)


# ── Change metrics ───────────────────────────────────────────
def add_change_metrics(ndvi_stack: ee.Image) -> ee.Image:
    """Add delta_total and delta_recent bands."""
    ndvi_2018    = ndvi_stack.select('ndvi_2018')
    ndvi_2022    = ndvi_stack.select('ndvi_2022')
    ndvi_2024    = ndvi_stack.select('ndvi_2024')
    delta_total  = ndvi_2024.subtract(ndvi_2018).rename('delta_total')
    delta_recent = ndvi_2024.subtract(ndvi_2022).rename('delta_recent')
    return ndvi_stack.addBands(delta_total).addBands(delta_recent)


# ── WorldCover ───────────────────────────────────────────────
def load_worldcover(aoi: ee.Geometry) -> ee.Image:
    """Load ESA WorldCover v200 clipped to AOI."""
    return (
        ee.ImageCollection('ESA/WorldCover/v200')
        .first()
        .clip(aoi)
        .rename('wc_label')
    )


def reclassify_worldcover(worldcover: ee.Image) -> ee.Image:
    """
    Reclassify 11-class WorldCover into 4 change detection classes.
    Class 0 = stable_vegetation (trees, shrubs, grass, cropland)
    Class 1 = vegetation_loss   (RF learns from negative delta bands)
    Class 2 = urban_growth      (built-up)
    Class 3 = stable_other      (water, bare, wetland, snow)
    """
    wc = worldcover.select('wc_label')
    return (
        wc
        .where(wc.gte(0),  3)   # default: stable other
        .where(wc.eq(10),  0)   # trees
        .where(wc.eq(20),  0)   # shrubland
        .where(wc.eq(30),  0)   # grassland
        .where(wc.eq(40),  0)   # cropland
        .where(wc.eq(60),  3)   # bare → stable other (RF learns loss from deltas)
        .where(wc.eq(50),  2)   # built-up → urban growth
        .rename('change_class')
        .toInt()
    )


# ── Vegetation loss label from NDVI change ───────────────────
def apply_vegetation_loss_label(training_image: ee.Image) -> ee.Image:
    """
    Override Class 0 pixels where strong NDVI decline occurred
    → reclassify them as Class 1 (vegetation loss).

    Conditions for Class 1:
      - WorldCover says vegetation (Class 0) — was green in 2021
      - delta_total < -0.15 — significant 6-year NDVI decline
      - ndvi_2018 > 0.25 — was actually vegetated in baseline year
    """
    wc_class    = training_image.select('change_class')
    delta_total = training_image.select('delta_total')
    ndvi_2018   = training_image.select('ndvi_2018')

    was_vegetation    = wc_class.eq(0)
    significant_loss  = delta_total.lt(-0.15)
    was_green_in_2018 = ndvi_2018.gt(0.25)

    loss_mask = was_vegetation.And(significant_loss).And(was_green_in_2018)

    updated_class = wc_class.where(loss_mask, 1)

    base_bands = training_image.select([
        'ndvi_2018', 'ndvi_2019', 'ndvi_2020',
        'ndvi_2022', 'ndvi_2024',
        'delta_total', 'delta_recent',
    ])
    return base_bands.addBands(updated_class.rename('change_class').toInt())


# ── Full zone pipeline ───────────────────────────────────────
def build_training_image_for_zone(zone_name: str) -> Tuple[ee.Image, ee.Geometry]:
    """
    Full pipeline for one zone.
    Returns 8-band training image and AOI geometry.

    Bands: ndvi_2018, ndvi_2019, ndvi_2020, ndvi_2022, ndvi_2024,
           delta_total, delta_recent, change_class
    """
    config = INDIA_ZONES[zone_name]
    aoi    = build_aoi(config['bbox'])

    stack      = build_ndvi_stack(aoi, config)
    full_stack = add_change_metrics(stack)
    worldcover = load_worldcover(aoi)
    wc_label   = reclassify_worldcover(worldcover)

    training_image = full_stack.addBands(wc_label)
    training_image = apply_vegetation_loss_label(training_image)
    return training_image, aoi


# ── Verification hash ────────────────────────────────────────
def generate_pipeline_hash(zone_name: str, years: List[int]) -> str:
    """Deterministic SHA-256 hash of pipeline parameters."""
    config = INDIA_ZONES[zone_name]
    payload = json.dumps({
        'zone':       zone_name,
        'bbox':       config['bbox'],
        'years':      years,
        'collection': SENTINEL2_COLLECTION,
        'cloud_pct':  config['cloud_threshold'],
        'start_month':config['start_month'],
        'end_month':  config['end_month'],
        'worldcover': 'ESA/WorldCover/v200',
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


# ── Live NDVI / change prediction helpers ─────────────────────

def _db_config() -> dict:
    """
    Build DB connection config at call-time (not import-time).

    This avoids Streamlit import-order issues where `backend/.env` may be loaded
    after `geospatial_agent` is imported.
    """
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "astrogeo_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


def _get_db_connection():
    return psycopg2.connect(**_db_config())


def get_live_ndvi(zone_name: str, year: Optional[int] = None) -> dict:
    """
    Compute live NDVI for current or recent year using GEE.
    Uses the same cloud masking and median composite as training pipeline.
    Does NOT retrain the model — feeds features into existing RF.
    """
    if year is None:
        year = datetime.datetime.utcnow().year

    config = INDIA_ZONES[zone_name]
    aoi = build_aoi(config["bbox"])

    collection = get_annual_collection(
        aoi,
        year,
        config["start_month"],
        config["end_month"],
        config["year_offset"],
        config["cloud_threshold"],
    )

    count = collection.size().getInfo()

    if count == 0:
        # Season hasn't started yet — fall back to most recent scenes this year.
        collection = (
            ee.ImageCollection(SENTINEL2_COLLECTION)
            .filterBounds(aoi)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .filter(
                ee.Filter.lt(
                    "CLOUDY_PIXEL_PERCENTAGE", config["cloud_threshold"] + 15
                )
            )
            .map(mask_s2_clouds)
            .sort("system:time_start", False)
            .limit(5)
        )
        count = collection.size().getInfo()

    if count == 0:
        return {
            "status": "no_data",
            "reason": f"No cloud-free images found for {zone_name} {year}",
            "year": year,
        }

    median = collection.median()
    ndvi_live = median.normalizedDifference(["B8", "B4"]).rename(f"ndvi_{year}")

    stats = (
        ndvi_live.reduceRegion(
            reducer=ee.Reducer.mean()
            .combine(ee.Reducer.min(), "", True)
            .combine(ee.Reducer.max(), "", True)
            .combine(ee.Reducer.stdDev(), "", True),
            geometry=aoi,
            scale=100,
            maxPixels=1e8,
            bestEffort=True,
        )
        .getInfo()
        or {}
    )

    ndvi_mean = stats.get(f"ndvi_{year}_mean")
    ndvi_min = stats.get(f"ndvi_{year}_min")
    ndvi_max = stats.get(f"ndvi_{year}_max")
    ndvi_std = stats.get(f"ndvi_{year}_stdDev")

    if ndvi_mean is None:
        return {
            "status": "no_data",
            "reason": "GEE stats returned None",
            "year": year,
        }

    return {
        "status": "ok",
        "year": year,
        "zone_name": zone_name,
        "ndvi_mean": round(float(ndvi_mean), 4),
        "ndvi_min": round(float(ndvi_min), 4) if ndvi_min is not None else None,
        "ndvi_max": round(float(ndvi_max), 4) if ndvi_max is not None else None,
        "ndvi_std": round(float(ndvi_std), 4) if ndvi_std is not None else None,
        "image_count": int(count),
    }


def predict_live_change(
    zone_name: str, year: Optional[int] = None, model=None
) -> dict:
    """
    Run live change detection for a zone using current GEE data
    and the trained RF model.

    Builds features by combining:
      - Stored historical NDVI from PostgreSQL (2018–2024)
      - Live current year NDVI from GEE
      - Recomputed delta bands using live vs stored baseline
    """
    if year is None:
        year = datetime.datetime.utcnow().year
    if model is None:
        model = joblib.load(MODEL_FILE_PATH)

    # Historical NDVI for this zone from ndvi_results.
    conn = _get_db_connection()
    hist_df = pd.read_sql(
        """
        SELECT year, ndvi_mean
        FROM ndvi_results n
        JOIN aoi_metadata a ON n.aoi_id = a.id
        WHERE a.zone_name = %s
          AND year IN (2018, 2019, 2020, 2022, 2024)
        ORDER BY year
        """,
        conn,
        params=(zone_name,),
    )
    conn.close()

    if len(hist_df) < 5:
        return {
            "status": "error",
            "reason": f"Insufficient historical data for {zone_name}",
        }

    hist = dict(zip(hist_df["year"], hist_df["ndvi_mean"]))

    live = get_live_ndvi(zone_name, year)
    if live.get("status") != "ok":
        return live

    ndvi_2018 = float(hist.get(2018, 0.0))
    ndvi_2024_or_latest = (
        float(live["ndvi_mean"])
        if year >= 2024
        else float(hist.get(2024, live["ndvi_mean"]))
    )

    features = np.array(
        [
            [
                float(hist.get(2018, 0.0)),
                float(hist.get(2019, 0.0)),
                float(hist.get(2020, 0.0)),
                float(hist.get(2022, 0.0)),
                ndvi_2024_or_latest,
                ndvi_2024_or_latest - ndvi_2018,
                ndvi_2024_or_latest - float(hist.get(2022, 0.0)),
            ]
        ]
    )

    prediction = int(model.predict(features)[0])
    probas = model.predict_proba(features)[0]
    confidence = float(probas[prediction])

    return {
        "status": "ok",
        "zone_name": zone_name,
        "year": year,
        "is_live": year > max(ANALYSIS_YEARS),
        "ndvi_current": float(live["ndvi_mean"]),
        "ndvi_baseline_2018": ndvi_2018,
        "delta_from_2018": round(ndvi_2024_or_latest - ndvi_2018, 4),
        "change_class": prediction,
        "change_class_label": CHANGE_CLASSES[prediction],
        "confidence": round(confidence, 4),
        "image_count": live["image_count"],
        "data_source": "GEE_live" if year >= 2025 else "PostgreSQL",
        "verification_hash": generate_pipeline_hash(zone_name, [year]),
    }


def get_or_compute_live(zone_name: str, year: int, model=None) -> dict:
    """
    Cache live predictions in PostgreSQL for 7 days.
    Returns cached row when available, otherwise computes via GEE + RF.
    """
    conn = _get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT n.ndvi_mean,
               n.change_class,
               n.change_class_label,
               n.confidence,
               n.created_at
        FROM ndvi_results n
        JOIN aoi_metadata a ON n.aoi_id = a.id
        WHERE a.zone_name = %s
          AND n.year = %s
          AND n.created_at > NOW() - INTERVAL '7 days'
        ORDER BY n.created_at DESC
        LIMIT 1
        """,
        (zone_name, year),
    )
    row = cur.fetchone()

    if row:
        conn.close()
        return {
            "status": "ok",
            "zone_name": zone_name,
            "year": year,
            "ndvi_mean": float(row[0]),
            "change_class": int(row[1]),
            "change_class_label": row[2],
            "confidence": float(row[3]),
            "data_source": "cache",
            "cached_at": row[4].isoformat() if row[4] else None,
        }

    conn.close()
    result = predict_live_change(zone_name, year, model=model)
    if result.get("status") != "ok":
        return result

    conn = _get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ndvi_results (
            aoi_id, zone_name, year,
            ndvi_mean, ndvi_min, ndvi_max, ndvi_std,
            delta_total_mean, delta_recent_mean,
            change_class, change_class_label,
            confidence, shap_top_feature,
            sample_count, verification_hash
        )
        SELECT
            a.id, %s, %s,
            %s, NULL, NULL, NULL,
            NULL, NULL,
            %s, %s,
            %s, NULL,
            NULL, %s
        FROM aoi_metadata a
        WHERE a.zone_name = %s
        """,
        (
            zone_name,
            year,
            result["ndvi_current"],
            result["change_class"],
            result["change_class_label"],
            result["confidence"],
            result["verification_hash"],
            zone_name,
        ),
    )
    conn.commit()
    conn.close()
    return result
