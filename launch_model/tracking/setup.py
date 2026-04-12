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

    username = os.environ["DAGSHUB_USERNAME"]
    repo = os.environ["DAGSHUB_REPO"]
    token = os.environ.get("DAGSHUB_TOKEN", "")

    tracking_uri = f"https://dagshub.com/{username}/{repo}.mlflow"
    os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
    os.environ["MLFLOW_TRACKING_USERNAME"] = username
    os.environ["MLFLOW_TRACKING_PASSWORD"] = token

    mlflow.set_tracking_uri(tracking_uri)

    try:
        import dagshub
        dagshub.init(
            repo_owner=username,
            repo_name=repo,
            mlflow=True,
        )
    except Exception as e:
        # dagshub.init() may fail on Windows (charmap codec) — not fatal
        # since we already set the tracking URI directly above
        print(f"[TRACKING] dagshub.init() skipped (URI already set): {e}")


    mlflow.set_experiment(experiment_name)

    return mlflow.start_run(
        run_name=run_name,
        tags={
            "env": os.getenv("ENV", "dev"),
            "triggered_by": os.getenv("USERNAME", os.getenv("USER", "local")),
            "project": "astrogeo-graphrag",
        },
    )
