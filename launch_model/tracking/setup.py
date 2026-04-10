"""
MLflow + DagsHub experiment tracking initializer.
Call init_tracking() once at the top of any pipeline entry-point script.
"""
import os
import mlflow

# --- [TRACKING] ---
TRACKING_ENABLED = os.getenv("TRACKING_ENABLED", "true") == "true"


def init_tracking(run_name: str, experiment_name: str = "astrogeo-launch-model"):
    """
    Initialize DagsHub remote tracking and start an MLflow run.

    Required environment variables:
        DAGSHUB_USERNAME  — your DagsHub username
        DAGSHUB_REPO      — your DagsHub repository name
        DAGSHUB_TOKEN     — your DagsHub access token

    Optional:
        ENV               — deployment environment tag (default: 'dev')
        TRACKING_ENABLED  — set to 'false' to run without any tracking

    Returns:
        Active mlflow.ActiveRun context manager (or a no-op object if disabled).
    """
    if not TRACKING_ENABLED:
        # Return a no-op context that is safe to use with `with`
        from contextlib import nullcontext
        return nullcontext()

    try:
        import dagshub
        dagshub.init(
            repo_owner=os.environ["DAGSHUB_USERNAME"],
            repo_name=os.environ["DAGSHUB_REPO"],
            mlflow=True,
        )
    except KeyError as e:
        raise EnvironmentError(
            f"Missing required environment variable: {e}. "
            "Set DAGSHUB_USERNAME and DAGSHUB_REPO (see .env.example)."
        ) from e
    except Exception as e:
        # Non-fatal: fall back to local MLflow tracking
        print(f"[TRACKING] DagsHub init failed, using local tracking: {e}")

    mlflow.set_experiment(experiment_name)

    return mlflow.start_run(
        run_name=run_name,
        tags={
            "env": os.getenv("ENV", "dev"),
            "triggered_by": os.getenv("USERNAME", os.getenv("USER", "local")),
            "project": "astrogeo-graphrag",
        },
    )
