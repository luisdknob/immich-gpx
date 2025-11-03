"""
Immich GPX Photo Linker

Links GPS points from GPX files with photos stored in Immich.
Parses GPX files, queries Immich API, and matches photos with GPS coordinates.
"""

__version__ = "1.0.0"
__author__ = "Immich GPX Linker Contributors"

# Public API - import from core modules
from .core import (
    AuthenticationError,
    Config,
    ConfigurationError,
    ConnectionError,
    ErrorCodes,
    GPXParsingError,
    GPXValidationError,
    GPSMatcher,
    GPXParser,
    ImmichAPI,
    ImmichGPXLinkerError,
    ImmichGPXService,
    MatchingError,
    ProcessResult,
    setup_logging,
    UpdateError,
)

# Import utilities (safe to do here)
from .utils import (
    categorize_matches,
    print_position_update_preview,
    print_results,
    prompt_update_mode,
    update_photo_positions,
)

# Import production features
from .cache import APIResponseCache, CacheEntry
from .rate_limiter import RateLimiter
from .metrics import PerformanceMetrics
from .config_loader import ConfigLoader
from .error_handling import UpdateResult

# Import CLI main function (delayed to avoid circular imports)
def __getattr__(name):
    """Lazy loading of main function to avoid circular imports."""
    if name == "main":
        from .cli import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Version
    "__version__",
    # Core errors
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
    # Core components
    "GPXParser",
    "GPSMatcher",
    "ImmichAPI",
    "ImmichGPXService",
    "ProcessResult",
    "setup_logging",
    # CLI
    "main",
    # Utilities
    "print_results",
    "print_position_update_preview",
    "update_photo_positions",
    "categorize_matches",
    "prompt_update_mode",
    # Production features
    "APIResponseCache",
    "CacheEntry",
    "RateLimiter",
    "PerformanceMetrics",
    "ConfigLoader",
    "UpdateResult",
]
