"""
Logging configuration for immich-gpx.

Configures console and rotating file logging with appropriate verbosity levels.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


# Logging configuration constants
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_LOG_COUNT = 5
DEFAULT_LOG_DIR = 'logs'
LOGGER_NAME = 'immich-gpx'


def setup_logging(
    verbose: bool = False,
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """
    Configure logger with console and file output.
    
    Args:
        verbose: Enable DEBUG level logging
        log_dir: Directory for log files (default: './logs')
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Prevent adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Configure console handler for immediate user feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_format = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # Configure file handler with automatic rotation
    if log_dir is None:
        # Default to 'logs' directory in current working directory
        log_dir = str(Path.cwd() / DEFAULT_LOG_DIR)
    
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)
    
    # Create log filename with current date and time (new file for each run)
    log_file = log_path / f'{LOGGER_NAME}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Set up file handler (no rotation needed since each run gets a new file)
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG in file
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger
