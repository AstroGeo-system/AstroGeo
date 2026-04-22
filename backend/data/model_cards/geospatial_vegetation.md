<!-- data/model_cards/geospatial_vegetation.md -->

# Model Card: Geospatial Vegetation Change Detection
**Model ID:** `astrogeo-geospatial-rf-v1`
**Last Updated:** 2026-01-31
**Status:** Production

---

## Model Details
| Field | Value |
|---|---|
| Algorithm | Random Forest Classifier |
| Library | scikit-learn 1.x |
| Trees | 200 (max_depth=10) |
| Version | v1.0 |
| Training Date | January 2026 |
| Maintainer | AstroGeo Team |

---

## Intended Use
Classifies land cover change across 17 Indian zones using Sentinel-2 
NDVI composites. Detects vegetation loss, urban growth, stable 
vegetation, and stable non-vegetation from 2018 to present.

**In scope:**
- Annual land cover change monitoring across all Indian states
- Drought early warning support via NDVI trend analysis
- Input data for the cross-domain drought composite index
- Research and policy communication

**Out of scope:**
- Sub-annual or real-time change detection
- Individual field-level precision agriculture
- Legal land use dispute evidence

---

## Training Data
| Field | Value |
|---|---|
| Source | ESA Sentinel-2 via Google Earth Engine |
| Coverage | 17 zones — all 28 Indian states + 8 UTs |
| Years | 2018, 2019, 2020, 2022, 2024 |
| Images per Zone | 4–17 cloud-free composites |
| Label Source | ESA WorldCover v200 + delta band derivation |
| Training Samples | ~50,000 pixels across all zones |

---

## Features
| Feature | Description |
|---|---|
| `ndvi_mean` | Annual post-monsoon median NDVI |
| `delta_total` | NDVI change 2018→2024 |
| `delta_recent` | NDVI change 2022→2024 |
| `land_cover_class` | ESA WorldCover base classification |
| `cloud_free_count` | Number of valid observations |

---

## Performance Metrics
| Metric | Value |
|---|---|
| Test Accuracy | **82%** |
| Cross-Val Accuracy | **77.9%** (5-fold) |
| Classes | 4 (vegetation loss, urban growth, stable veg, stable non-veg) |
| Worst Class | Class 1 (vegetation loss) — fixed via delta band derivation |

---

## SHAP Feature Importance
Full beeswarm and heatmap available in `data/shap/geospatial/`.
`delta_total` and `delta_recent` are the dominant predictors — 
static land cover class has lower importance than temporal change signal.

---

## Known Limitations
- **Cloud contamination:** Despite SCL masking, some zones in Northeast 
  India have fewer than 5 valid observations per year. Confidence scores 
  are lower in these zones.
- **Annual resolution only:** Cannot detect within-season stress events 
  such as flash droughts.
- **Label noise:** Vegetation loss labels derived from delta bands — 
  some agricultural fallow may be misclassified as vegetation loss.
- **No crop type distinction:** Model detects change, not crop species.

---

## Ethical Considerations
NDVI decline classifications should not be used to make land acquisition 
or displacement decisions without ground truth validation. Model outputs 
are probabilistic indicators, not ground truth measurements.

---

## Verification
Per-zone per-year predictions stored in PostgreSQL `ndvi_results` table 
with confidence scores. SHA-256 hashes auditable via Verify Predictions UI.