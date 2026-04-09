# 05_sample_pixels.py
# Exports stratified pixel samples to Google Drive as CSV
# Run once — takes 5–15 minutes depending on GEE queue

import ee
import os
from geospatial_agent import build_training_image, DEFAULT_PUNE_AOI

EE_PROJECT = os.getenv("EE_PROJECT")
if EE_PROJECT:
    ee.Initialize(project=EE_PROJECT)
else:
    ee.Initialize()

print('Building training image...')
training_image, aoi, _ = build_training_image(DEFAULT_PUNE_AOI)

print('Starting stratified sampling...')
samples = training_image.stratifiedSample(
    numPoints=2000,
    classBand='change_class',
    region=aoi,
    scale=10,               # Sentinel-2 native resolution
    seed=42,                # reproducible sampling
    geometries=False        # coordinates not needed — CSV only
)

print('Submitting export task to Google Drive...')
task = ee.batch.Export.table.toDrive(
    collection=samples,
    description='ndvi_training_samples_pune',
    folder='AstroGeo_GEE_Exports',   # will be created in your Drive
    fileNamePrefix='ndvi_training_samples_pune',
    fileFormat='CSV'
)
task.start()

print(f'Task submitted. Task ID: {task.id}')
print('Monitor progress at: https://code.earthengine.google.com/tasks')
print('Download the CSV from Google Drive once status shows "COMPLETED"')
