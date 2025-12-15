"""
Observability Logging

Configures structured logging for the application.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging():
    """
    Configure logging for the application.
    
    Sets up structured logging with appropriate format and level.
    Logs to both console and file (with rotation).
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(logging.INFO)
    
    # File handler with rotation (10 MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        logs_dir / "tav_engine.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.DEBUG)  # Capture all logs to file
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,  # Capture everything at root level
        handlers=[console_handler, file_handler]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Log the logging setup
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Logging initialized - logs saved to: {logs_dir.absolute() / 'tav_engine.log'}")
