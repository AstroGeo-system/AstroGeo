# test_ndvi_pipeline.py
# Run from VS Code terminal: python test_ndvi_pipeline.py

from geospatial_agent import (
    build_aoi, get_annual_collection, compute_annual_ndvi,
    build_ndvi_stack, add_change_metrics, load_worldcover,
    reclassify_worldcover, build_training_image, run_ndvi_pipeline,
    DEFAULT_PUNE_AOI, ANALYSIS_YEARS, SENTINEL2_COLLECTION
)
import ee

print('=== AstroGeo Geospatial Agent — Step 3+4 Tests ===')

# --- shared objects, built once and reused across all tests ---
aoi = build_aoi(DEFAULT_PUNE_AOI)

# Test 1: AOI construction
print('\n[1] Testing AOI construction...')
print(f'    AOI type: {type(aoi)}')
print('    PASS')

# Test 2: Collection size per year
print('\n[2] Testing annual collection sizes...')
for year in ANALYSIS_YEARS:
    col = get_annual_collection(aoi, year)
    count = col.size().getInfo()               # ← inside the loop
    print(f'    {year}: {count} cloud-free images')
    assert count > 0, f'No images found for {year} — check AOI or date range'
print('    PASS — all years have data')

# Test 3: Single NDVI computation
print('\n[3] Testing NDVI computation for 2024...')
ndvi_2024 = compute_annual_ndvi(aoi, 2024)
band_names = ndvi_2024.bandNames().getInfo()
print(f'    Band names: {band_names}')
assert band_names == ['ndvi_2024'], 'Band name mismatch'

sample = ndvi_2024.sample(region=aoi, scale=100, numPixels=50)
values = [f['properties']['ndvi_2024']       # ← one clean list comprehension
          for f in sample.getInfo()['features']]
print(f'    Sample NDVI values (min/max): {min(values):.3f} / {max(values):.3f}')
assert -1.0 <= min(values) <= 1.0, 'NDVI out of valid range'
print('    PASS')

# Test 4: Full NDVI stack
print('\n[4] Testing full NDVI stack...')
stack, aoi_obj = run_ndvi_pipeline(DEFAULT_PUNE_AOI)  # ← direct import, no __import__
bands = stack.bandNames().getInfo()
print(f'    Bands in stack: {bands}')
assert len(bands) == 7, f'Expected 7 bands, got {len(bands)}'
print('    PASS')

# Test 5: WorldCover loading
print('\n[5] Testing WorldCover loading...')
wc = load_worldcover(aoi_obj)
wc_classes = wc.reduceRegion(
    reducer=ee.Reducer.frequencyHistogram(),
    geometry=aoi_obj,
    scale=100,
    maxPixels=1e8                              # ← safe for large AOIs
).getInfo()
print(f'    WorldCover classes present: {list(wc_classes.get("wc_label", {}).keys())}')
print('    PASS')

# Test 6: Full training image
print('\n[6] Testing full training image build...')
training_img, _, _ = build_training_image(DEFAULT_PUNE_AOI)
all_bands = training_img.bandNames().getInfo()
print(f'    All bands: {all_bands}')
assert 'change_class' in all_bands, 'change_class band missing'
assert len(all_bands) == 8, f'Expected 8 bands, got {len(all_bands)}'
print('    PASS')

print('\n=== All tests passed. Ready for Step 5 (pixel sampling). ===')