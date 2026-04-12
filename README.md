# AstroGeo: Cross-Domain Knowledge Graph & Risk Engine

**AstroGeo** is an advanced multi-agent system designed to correlate astronomical events with terrestrial geospatial data. It leverages a high-fidelity **Knowledge Graph (Neo4j)** and **GraphRAG** orchestration to synthesize insights across solar weather, asteroid trajectories, and Earth's atmospheric conditions.

---

## 🚀 Key Features

### 1. Cross-Domain Orchestration (LangGraph)
*   Routes natural language queries through specialized **Domain Agents** (Astronomy, Geospatial, Weather).
*   Synthesizes disparate data sources (e.g., "Did solar flares in 2021 affect Indian launch success rates?") using a unified GraphRAG pipeline.

### 2. Launch Risk Engine v2.0 (Weather-Aware)
*   **Predictive Model**: A Voting Ensemble (Random Forest + Logistic Regression) trained on 46 years of ERA5 weather data for Sriharikota.
*   **Minority Class Boosting**: Uses **SMOTE oversampling** to achieve high recall on historical failure cases, providing a conservative 0.35 risk threshold for safety-critical decisions.
*   **Explainable AI**: Full **SHAP integration** to identify specific weather drivers (e.g., precipitation, monsoon cycles) behind every risk prediction.

### 3. Cryptographic Verification Pipeline
*   **Data Integrity**: Implements a deterministic SHA-256 hashing system for all ML predictions.
*   **Tamper-Evidence**: Rest API endpoints allow live verification of prediction records against the original model version and input features.

### 4. ERA5 Weather Pipeline
*   High-resolution daily weather ingestion for global launch sites (1980–2026).
*   Tracks temperature, pressure, humidity, wind velocity, and monsoonal cycles for deep correlation analysis.

---

## 🛠 Tech Stack

*   **Graph DB**: Neo4j (GraphRAG, Cypher)
*   **Relational DB**: PostgreSQL (ERA5, Launch History, Predictions)
*   **Orchestration**: LangGraph, FastAPI
*   **Machine Learning**: Scikit-learn, Imbalanced-Learn, SHAP, Joblib
*   **Data Sources**: ERA5 (Copernicus), ISRO/SDSC Launch Logs, NASA JPL Asteroid Data

---

## 📂 Project Structure

```bash
├── backend/
│   ├── main.py                # FastAPI endpoints (Verify, Query, Model Cards)
│   ├── orchestrator/          # LangGraph agents and GraphRAG logic
│   ├── pipelines/             # Data ingestion (ERA5, Scrapers, Seeding)
│   └── responsible_ai/        # SHAP analysis and Verification logic
├── data/
│   ├── models/                # Trained PKL files and metadata
│   └── shap/                  # Local explainability visualizations
└── docs/                      # Technical walkthroughs and research notes
```

---

## 🚦 Getting Started

### 1. Environment Setup
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```

### 2. Run Verification API
```bash
python3 backend/main.py
```

---

## 🧪 Model Performance (v2.0)
*   **F1-Score (Failures)**: 0.50 (Optimized for High Recall)
*   **CV ROC-AUC**: 0.687
*   **Training Basis**: 108 Sriharikota launches matched to daily ERA5 weather.

---

## 📜 Research Context
AstroGeo is developed as a tool for cross-domain anomaly detection, aiming to bridge the gap between spaceflight operations and environmental geospatial analytics.
