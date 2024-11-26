"""Logging configuration for Shabda Setu."""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime

def setup_logging(name: str = None) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        name: Optional name for the logger. If not provided, uses the module name.
    
    Returns:
        Logger instance configured with both file and console handlers.
    """
    # Create logs directory if it doesn't exist
    project_root = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(project_root, 'data', 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"{name}_{timestamp}.log" if name else f"shabda_setu_{timestamp}.log"
    log_filepath = os.path.join(logs_dir, log_filename)

    # Get or create logger
    logger = logging.getLogger(name if name else __name__)
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers = []

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler (rotating file handler to prevent huge log files)
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
