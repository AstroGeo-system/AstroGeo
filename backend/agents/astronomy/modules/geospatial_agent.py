# geospatial_agent.py
# AstroGeo — Geospatial Agent (Steps 3–4)
# Requires: earthengine-api, geojson, psycopg2

import ee
import json
import hashlib
import datetime
import psycopg2
from typing import List, Dict, Optional

ee.Initialize(project='astrogeo-gee-491204')

SENTINEL2_COLLECTION = 'COPERNICUS/S2_SR_HARMONIZED'
CLOUD_THRESHOLD      = 20
SCALE_METRES         = 10
ANALYSIS_YEARS       = [2018, 2019, 2020, 2022, 2024]
MONTH_START          = 10
MONTH_END            = 11

DEFAULT_PUNE_AOI = {
    'west': 73.6, 'south': 18.2,
    'east': 74.3, 'north': 18.8
}


def build_aoi(geojson_bbox: Dict) -> ee.Geometry:
    if 'coordinates' in geojson_bbox:
        return ee.Geometry.Polygon(geojson_bbox['coordinates'])
    else:
        return ee.Geometry.Rectangle([
            geojson_bbox['west'],
            geojson_bbox['south'],
            geojson_bbox['east'],
            geojson_bbox['north'],
        ])


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    scl = image.select('SCL')
    cloud_shadow = scl.neq(3)
    cloud_med    = scl.neq(8)
    cloud_high   = scl.neq(9)
    cirrus       = scl.neq(10)
    mask = cloud_shadow.And(cloud_med).And(cloud_high).And(cirrus)
    return image.updateMask(mask)


def get_annual_collection(aoi: ee.Geometry, year: int) -> ee.ImageCollection:
    start = f'{year}-{MONTH_START:02d}-01'
    end   = f'{year}-12-01'          # FIX 2: Dec 1 exclusive = full Oct+Nov

    collection = (
        ee.ImageCollection(SENTINEL2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_THRESHOLD))
        .map(mask_s2_clouds)
    )
    return collection


def compute_annual_ndvi(aoi: ee.Geometry, year: int) -> ee.Image:
    # FIX 1: removed getInfo() count check — no blocking server call here
    collection   = get_annual_collection(aoi, year)
    median_image = collection.median()
    ndvi         = median_image.normalizedDifference(['B8', 'B4'])
    return ndvi.rename(f'ndvi_{year}')


def build_ndvi_stack(aoi: ee.Geometry) -> ee.Image:
    print('Building NDVI stack — computing 5 annual composites...')
    ndvi_images = []
    for year in ANALYSIS_YEARS:
        print(f'  Processing {year}...')
        ndvi_images.append(compute_annual_ndvi(aoi, year))
    stack = ee.Image.cat(ndvi_images)
    print(f'Stack complete. Bands: {ANALYSIS_YEARS}')
    return stack


def add_change_metrics(ndvi_stack: ee.Image) -> ee.Image:
    ndvi_2018    = ndvi_stack.select('ndvi_2018')
    ndvi_2022    = ndvi_stack.select('ndvi_2022')
    ndvi_2024    = ndvi_stack.select('ndvi_2024')
    delta_total  = ndvi_2024.subtract(ndvi_2018).rename('delta_total')
    delta_recent = ndvi_2024.subtract(ndvi_2022).rename('delta_recent')
    return ndvi_stack.addBands(delta_total).addBands(delta_recent)


def run_ndvi_pipeline(geojson_bbox: Dict) -> tuple:
    aoi        = build_aoi(geojson_bbox)
    stack      = build_ndvi_stack(aoi)
    full_stack = add_change_metrics(stack)
    return full_stack, aoi


def load_worldcover(aoi: ee.Geometry) -> ee.Image:
    return (
        ee.ImageCollection('ESA/WorldCover/v200')
        .first()
        .clip(aoi)
        .rename('wc_label')
    )


CHANGE_CLASSES = {
    0: 'stable_vegetation',
    1: 'vegetation_loss',
    2: 'urban_growth',
    3: 'stable_other',
}


def reclassify_worldcover(worldcover: ee.Image) -> ee.Image:
    wc = worldcover.select('wc_label')
    reclassified = (
        wc
        .where(wc.gte(0), 3)      # default: stable other
        .where(wc.eq(10), 0)      # trees       → stable vegetation
        .where(wc.eq(20), 0)      # shrubland   → stable vegetation
        .where(wc.eq(30), 0)      # grassland   → stable vegetation
        .where(wc.eq(40), 0)      # cropland    → stable vegetation
        .where(wc.eq(60), 3)      # FIX 3: bare land → stable other (not loss)
        .where(wc.eq(50), 2)      # built-up    → urban growth
    )
    return reclassified.rename('change_class').toInt()


def build_training_image(geojson_bbox: Dict) -> tuple:
    full_stack, aoi = run_ndvi_pipeline(geojson_bbox)
    print('Loading ESA WorldCover v200...')
    worldcover      = load_worldcover(aoi)
    wc_reclassified = reclassify_worldcover(worldcover)
    training_image  = full_stack.addBands(wc_reclassified)
    print('Training image ready — 8 bands total.')
    return training_image, aoi, full_stack


def generate_pipeline_hash(geojson_bbox: Dict, years: List[int],
                           collection: str) -> str:
    # FIX 4: removed computed_at — hash must be deterministic for same inputs
    payload = json.dumps({
        'aoi':        geojson_bbox,
        'years':      years,
        'collection': collection,
        'cloud_pct':  CLOUD_THRESHOLD,
        'months':     [MONTH_START, MONTH_END],
        'worldcover': 'ESA/WorldCover/v200',
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()