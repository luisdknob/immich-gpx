"""
Core modules for immich-gpx-linker.
"""

from .config import Config
from .errors import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    ErrorCodes,
    GPXParsingError,
    GPXValidationError,
    ImmichGPXLinkerError,
    MatchingError,
    UpdateError,
)
from .gpx_parser import GPXParser
from .gps_matcher import GPSMatcher
from .immich_client import ImmichAPI
from .logger import setup_logging
from .service import ImmichGPXService, ProcessResult

__all__ = [
    "Config",
    "ErrorCodes",
    "ImmichGPXLinkerError",
    "ConfigurationError",
    "GPXValidationError",
    "GPXParsingError",
    "ConnectionError",
    "AuthenticationError",
    "MatchingError",
    "UpdateError",
    "GPXParser",
    "GPSMatcher",
    "ImmichAPI",
    "ImmichGPXService",
    "ProcessResult",
    "setup_logging",
]
