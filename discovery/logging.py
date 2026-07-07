"""Central structured logging for the pipeline."""
import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("/var/log/pipeline")

def setup_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """Create a logger with consistent formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)
    
    # File handler (optional)
    if log_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / log_file)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get or create a logger."""
    return logging.getLogger(f"pipeline.{name}")
