import ee
ee.Initialize(project='astrogeo-gee-491204')

# Test: get one Sentinel-2 image over Pune
aoi = ee.Geometry.Rectangle([73.6, 18.2, 74.3, 18.8])
collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
    .filterBounds(aoi) \
    .filterDate("2024-01-01", "2024-03-31") \
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))

print("Images found:", collection.size().getInfo())