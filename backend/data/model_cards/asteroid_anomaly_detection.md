<!-- data/model_cards/asteroid_anomaly_detection.md -->

# Model Card: Asteroid Anomaly Detection
**Model ID:** `astrogeo-asteroid-isolation-forest-v1`
**Last Updated:** 2026-01-31
**Status:** Production

---

## Model Details
| Field | Value |
|---|---|
| Algorithm | Isolation Forest |
| Library | scikit-learn 1.x |
| Version | v1.0 |
| Training Date | January 2026 |
| Maintainer | AstroGeo Team |

---

## Intended Use
Detects statistically anomalous asteroids in NASA CNEOS close approach 
data that deviate from typical orbital and approach behaviour patterns. 
Intended for use by space researchers, planetary defense analysts, and 
science communicators.

**In scope:**
- Flagging unusual asteroid approach patterns for further investigation
- Supporting risk prioritisation in the AstroGeo dashboard
- Research and educational demonstration

**Out of scope:**
- Real-time collision prediction (use JPL Sentry for this)
- Legal or governmental planetary defense decision-making
- Any use case requiring sub-day data freshness

---

## Training Data
| Field | Value |
|---|---|
| Source | NASA CNEOS Close Approach Data (cneos.jpl.nasa.gov) |
| Date Range | 1900 – 2200 (historical + projected) |
| Total Records | ~35,000 close approach events |
| Features Used | 4 engineered features (see below) |
| Label Type | Unsupervised — no ground truth labels |

---

## Features
| Feature | Description | SHAP Importance |
|---|---|---|
| `kinetic_energy_proxy` | Estimated impact energy from mass + velocity | 0.0211 ⭐ |
| `approach_regularity` | Consistency of approach intervals over time | 0.0194 |
| `orbit_stability` | Variance in orbital path across approaches | 0.0156 |
| `distance_trend` | Direction of change in miss distance over time | 0.0089 |

---

## Performance Metrics
| Metric | Value |
|---|---|
| Contamination Rate | 5% (tuned parameter) |
| Anomalies Detected | ~5% of asteroid population |
| Validation Method | Expert cross-check against JPL risk tables |
| False Positive Risk | Medium — unsupervised, use as triage tool only |

---

## Known Limitations
- **No ground truth:** Isolation Forest is unsupervised. Anomaly ≠ dangerous.
- **Feature coverage:** Only 4 of 9 engineered features were available at 
  training time. Richer features may change rankings.
- **Data bias:** CNEOS data is biased toward well-observed asteroids. 
  Newly discovered objects may score anomalously simply due to sparse 
  observation history.
- **Static model:** No online learning. Requires manual retraining when 
  CNEOS data distribution shifts (monitored by drift detection script).

---

## Ethical Considerations
This model is intended for scientific research and education. Anomaly 
scores should never be communicated to the public as collision warnings 
without expert validation. High anomaly score ≠ imminent threat.

---

## Verification
Every prediction row in PostgreSQL carries a SHA-256 hash of the input 
features + model version + output score. Verify any prediction using the 
Verify Predictions page in the AstroGeo Streamlit POC.