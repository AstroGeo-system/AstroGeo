import os
import sys
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import json
from datetime import datetime

from evidently import Report
from evidently.presets import DataDriftPreset

try:
    from dotenv import load_dotenv
    # Load from launch_model/.env
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    load_dotenv(env_path)
    # Also load from root .env just in case
    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env')))
except ImportError:
    pass

try:
    from launch_model.utils.logger import setup_logger
    _logger, _ = setup_logger(run_name="monitoring")
except:
    import logging
    _logger = logging.getLogger(__name__)

# Tracking setup
try:
    import mlflow
    import wandb
except ImportError:
    mlflow = None
    wandb = None

def get_engine():
    """Connect to the Postgres database to fetch live inference data."""
    # Assuming this is run from project root, fallback to hardcoded if env missing
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "admin")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "astrogeo")
    
    url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(url)

def fetch_current_data():
    """Fetch real prediction requests, or generate mock data if empty."""
    engine = get_engine()
    
    query = "SELECT * FROM launch_predictions ORDER BY id DESC LIMIT 500"
    try:
        current_data = pd.read_sql(query, engine)
        if not current_data.empty:
            _logger.info(f"Fetched {len(current_data)} rows from database.")
    except Exception as e:
        _logger.warning(f"Could not read from DB (maybe table does not exist yet): {e}")
        current_data = pd.DataFrame()

    if current_data.empty:
        _logger.warning("No data in PostgreSQL! Generating MOCK data for the drift report...")
        # Create a mock dataset based off the training data, but add some drift
        try:
            ref = pd.read_csv("data/training_data.csv")
            current_data = ref.sample(200, replace=True).copy()
            # Introduce synthetic drift to wind speed and cloud cover
            current_data['wind_speed_ms'] += np.random.normal(5, 2, len(current_data))
            current_data['cloud_cover_pct'] = np.clip(current_data['cloud_cover_pct'] - 0.2, 0, 1)
            current_data['temperature_c'] += np.random.normal(2, 1.5, len(current_data))
            _logger.info("Generated synthetic drifted data for demonstration.")
        except Exception as e:
            _logger.error(f"Failed to load reference for mock: {e}")
            sys.exit(1)
            
    return current_data

def main():
    _logger.info("Starting Data Drift Detection...")
    
    ref_path = "data/training_data.csv"
    if not os.path.exists(ref_path):
        _logger.error(f"Reference data not found at {ref_path}")
        sys.exit(1)
        
    reference_data = pd.read_csv(ref_path)
    current_data = fetch_current_data()
    
    # Feature columns that exist in both (excluding ID/timestamp fields)
    ignore_cols = ['id', 'created_at', 'verification_hash', 'launch_date', 'mission_name', 'source', 'launch_site']
    features = [c for c in reference_data.columns if c not in ignore_cols and c in current_data.columns]
    
    _logger.info(f"Analyzing {len(features)} features for drift.")

    # Initialize Evidently Report
    report = Report(metrics=[
        DataDriftPreset()
    ])

    # Run tests
    snapshot = report.run(reference_data=reference_data[features], current_data=current_data[features])

    # Save HTML output
    report_path = "metrics/drift_report.html"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    snapshot.save_html(report_path)
    _logger.info(f"Saved Evidently Drift Report to {report_path}")
    
    # Log to tracking systems
    try:
        if os.getenv("TRACKING_ENABLED", "true") == "true":
            # Re-use our centralized auth helper
            try:
                # Need to add the project root to sys.path since we are running within monitoring
                import sys
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

                from tracking.setup import init_tracking
                ctx = init_tracking(run_name="drift_monitoring_run", experiment_name="astrogeo-launch-go-nogo")
            except Exception as _e:
                _logger.warning(f"Using fallback mlflow auth: {_e}")
                import mlflow
                mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "https://dagshub.com/anushkamali-2005/astro_geo.mlflow"))
                ctx = mlflow.start_run(run_name="drift_monitoring_run")

            with ctx:
                import mlflow
                mlflow.log_artifact(report_path, "monitoring")
                _logger.info("Logged drift report to MLflow.")
    except Exception as e:
        _logger.warning(f"Could not log to MLflow: {e}")

    try:
        import wandb
        if os.getenv("WANDB_API_KEY") and os.getenv("TRACKING_ENABLED", "true") == "true":
            run = wandb.init(project="astrogeo-graphrag", job_type="monitoring")
            wandb.log({
                "drift_report_html": wandb.Html(open(report_path).read(), inject=False)
            })
            run.finish()
            _logger.info("Logged drift report to W&B.")
    except Exception as e:
        _logger.warning(f"Could not log to W&B: {e}")


if __name__ == "__main__":
    main()
