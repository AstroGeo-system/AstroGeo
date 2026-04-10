"""
Structured logging system using Loguru.
Creates per-run timestamped log files with full traceback diagnosis.
"""
import sys
import traceback
from datetime import datetime
from pathlib import Path
from loguru import logger


def setup_logger(run_name: str, log_dir: str = "logs"):
    """
    Initialize a structured Loguru logger for a named pipeline run.

    Args:
        run_name: Identifier for this run (e.g. 'training', 'preprocessing').
        log_dir:  Directory to write log files into.

    Returns:
        (logger, log_file_path) tuple.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/{run_name}_{timestamp}.log"

    # Remove any previously registered handlers (safe to call multiple times)
    logger.remove()

    # Console handler — coloured, human-readable
    logger.add(
        sys.stdout,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # File handler — full detail with backtrace & variable introspection
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}",
        backtrace=True,       # Full traceback on exceptions
        diagnose=True,        # Variable values at failure point
        retention="30 days",
        rotation="100 MB",
        level="DEBUG",
    )

    logger.info(f"Logger initialized. Run: {run_name}. Log file: {log_file}")
    return logger, log_file
