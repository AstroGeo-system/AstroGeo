"""
Pipeline stage tracker — decorator + context helpers for MLflow + Loguru.

Usage:
    from utils.run_tracker import track_stage, set_logger

    set_logger(logger)          # call once after setup_logger()

    @track_stage("data_ingestion")
    def run_ingestion():
        ...
"""
import os
import time
import traceback
from functools import wraps

# Loguru logger instance — replaced at runtime by set_logger()
from loguru import logger as _default_logger
_logger = _default_logger

# --- [TRACKING] ---
TRACKING_ENABLED = os.getenv("TRACKING_ENABLED", "true") == "true"


def set_logger(logger_instance):
    """Bind the module-level logger to the one created by setup_logger()."""
    global _logger
    _logger = logger_instance


def track_stage(stage_name: str):
    """
    Decorator to track any pipeline stage.
    Logs start time, end time, duration, and exact failure location.
    On error: logs type, message, full traceback, and writes all to MLflow.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger.info(f"[STAGE START] {stage_name} -> {func.__name__}()")
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                _logger.success(
                    f"[STAGE DONE] {stage_name} completed in {duration:.2f}s"
                )
                # --- [TRACKING] ---
                if TRACKING_ENABLED:
                    try:
                        import mlflow
                        mlflow.log_metric(
                            f"stage_{stage_name}_duration_sec", round(duration, 2)
                        )
                        mlflow.set_tag(f"stage_{stage_name}_status", "SUCCESS")
                    except Exception as mlflow_err:
                        _logger.warning(
                            f"[TRACKING] MLflow metric logging failed (non-fatal): {mlflow_err}"
                        )
                return result

            except Exception as e:
                duration = time.time() - start
                tb = traceback.format_exc()
                _logger.error(
                    f"[STAGE FAILED] {stage_name} failed after {duration:.2f}s"
                )
                _logger.error(f"Error type    : {type(e).__name__}")
                _logger.error(f"Error message : {str(e)}")
                _logger.error(f"Traceback:\n{tb}")

                # --- [TRACKING] ---
                if TRACKING_ENABLED:
                    try:
                        import mlflow
                        mlflow.set_tag(f"stage_{stage_name}_status", "FAILED")
                        mlflow.set_tag(f"stage_{stage_name}_error", type(e).__name__)
                        mlflow.set_tag(
                            f"stage_{stage_name}_error_msg", str(e)[:200]
                        )
                        mlflow.log_text(tb, f"errors/{stage_name}_traceback.txt")
                    except Exception as mlflow_err:
                        _logger.warning(
                            f"[TRACKING] MLflow failure logging failed (non-fatal): {mlflow_err}"
                        )
                raise  # re-raise so the pipeline halts correctly
        return wrapper
    return decorator
