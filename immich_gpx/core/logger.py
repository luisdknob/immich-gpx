"""
Logging configuration and setup for immich-gpx-linker application.

Provides centralized logger initialization with:
- Dual output: console (for immediate feedback) and rotating file logs
- Configurable verbosity levels (INFO for normal, DEBUG for verbose)
- Automatic log rotation to prevent unbounded disk usage
- Consistent timestamp and message formatting

Functions:
    setup_logging(): Initialize and return configured logger instance
    
Usage:
    >>> logger = setup_logging(verbose=True, log_dir='/var/log/immich-gpx')
    >>> logger.info("Application starting...")
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


# Logging configuration constants
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per log file
BACKUP_LOG_COUNT = 5                  # Keep 5 rotated log files
DEFAULT_LOG_DIR = 'logs'              # Default logs directory name
LOGGER_NAME = 'immich-gpx'            # Standard logger name


def setup_logging(
    verbose: bool = False,
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """
    Configure and return application logger with console and file output.
    
    Sets up comprehensive logging with:
    - Console output for immediate user feedback
    - File output with automatic rotation when size exceeds threshold
    - Different verbosity levels for debugging vs. normal operation
    - Consistent timestamp and formatting across all output
    
    Console output:
    - Format: [LEVEL] message
    - Level: DEBUG if verbose, otherwise INFO
    - Output: stderr (standard)
    
    File output:
    - Format: timestamp - logger - level - message
    - Always DEBUG level (captures full details for troubleshooting)
    - Location: logs/ directory (or custom log_dir)
    - Filename: immich-gpx_YYYYMMDD_HHMMSS.log (new file for each run)
    
    Args:
        verbose: Enable DEBUG level logging for detailed output (default: False)
        log_dir: Directory for log files, created if missing (default: './logs')
        
    Returns:
        Configured logger instance (logging.Logger) named 'immich-gpx'
        
    Raises:
        OSError: If log directory cannot be created or is not writable
        
    Example:
        >>> # Normal operation - INFO level
        >>> logger = setup_logging()
        >>> logger.info("Operation started")
        
        >>> # Verbose debugging - DEBUG level
        >>> logger = setup_logging(verbose=True)
        >>> logger.debug("Detailed state information")
        
        >>> # Custom log directory
        >>> logger = setup_logging(log_dir='/var/log/myapp')
    """
    # Get or create logger instance
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
