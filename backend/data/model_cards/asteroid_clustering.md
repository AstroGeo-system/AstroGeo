<!-- data/model_cards/asteroid_clustering.md -->

# Model Card: Asteroid Behavioural Clustering
**Model ID:** `astrogeo-asteroid-kmeans-v1`
**Last Updated:** 2026-01-31
**Status:** Production

---

## Model Details
| Field | Value |
|---|---|
| Algorithm | KMeans (k=3) |
| Library | scikit-learn 1.x |
| Version | v1.0 |
| Training Date | January 2026 |
| Maintainer | AstroGeo Team |

---

## Intended Use
Groups asteroids into 3 behavioural clusters based on orbital and 
approach characteristics. Used to provide context in the AstroGeo 
Risk Dashboard and Cluster Analysis pages.

**In scope:**
- Exploratory analysis of asteroid population structure
- Science communication and public education
- Supporting risk triage alongside Isolation Forest scores

**Out of scope:**
- Official asteroid classification (use MPC taxonomy)
- Replacing physical orbital mechanics analysis

---

## Training Data
Same dataset as Isolation Forest model above.

---

## Cluster Definitions
| Cluster | Name | Description | SHAP Driver |
|---|---|---|---|
| 0 | Frequent Close Approachers | High approach count, irregular intervals | `approach_regularity` |
| 1 | Moderate Regulars | Stable orbits, predictable patterns | `orbit_stability` |
| 2 | Distant Visitors | Large miss distances, outward trend | `distance_trend` (0.4452 ⭐) |

---

## Performance Metrics
| Metric | Value |
|---|---|
| Number of Clusters | 3 |
| Initialisation | k-means++ (n_init=10) |
| Validation | Silhouette score + domain expert review |
| Cluster Stability | Verified consistent across 5 random seeds |

---

## Known Limitations
- **k is fixed at 3:** May not reflect true population structure. 
  Chosen for interpretability over statistical optimality.
- **Euclidean distance assumption:** KMeans assumes spherical clusters. 
  Asteroid feature space may have non-spherical structure.
- **No temporal component:** Clusters are static snapshots. An asteroid 
  may change cluster membership as new approaches are observed.

---

## Verification
SHA-256 hash per prediction row. Auditable via Verify Predictions UI.