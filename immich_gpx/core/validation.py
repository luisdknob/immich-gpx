"""
Input validation module for immich-gpx-linker.

Provides comprehensive validation functions for all user-provided data:
- GPS coordinates (latitude, longitude)
- Date/time values (ISO 8601 format)
- File paths and sizes (GPX files)
- URLs (Immich server)
- Configuration parameters (threshold, timeout, API key)
- API responses (photos, matches)

Each validation function raises ValueError with clear error messages
when validation fails. Functions designed to fail fast and report issues immediately.

Functions:
    validate_latitude(): Validate latitude coordinate (-90 to +90)
    validate_longitude(): Validate longitude coordinate (-180 to +180)
    validate_gps_point(): Validate GPS coordinate pair
    validate_datetime(): Validate ISO 8601 datetime
    validate_gpx_file(): Validate GPX file format and content
    validate_immich_url(): Validate Immich server URL
    validate_threshold(): Validate time threshold parameter
    validate_timeout(): Validate request timeout parameter
    validate_api_key(): Validate Immich API key
    validate_photo_response(): Validate photo object from API
    validate_match_object(): Validate GPS match structure

Usage:
    >>> validate_latitude(40.7128)  # Valid NYC latitude
    >>> validate_longitude(-74.0060)  # Valid NYC longitude
    >>> validate_gps_point(40.7128, -74.0060)  # Validate pair
"""

import socket
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


# Validation constants
GPS_ERA_START = datetime(1980, 1, 6)
LATITUDE_MIN = -90.0
LATITUDE_MAX = 90.0
LONGITUDE_MIN = -180.0
LONGITUDE_MAX = 180.0
MAX_GPX_FILE_SIZE_MB = 100
MIN_API_KEY_LENGTH = 20
THRESHOLD_MIN_SECONDS = 1
THRESHOLD_MAX_SECONDS = 3600
TIMEOUT_MIN_SECONDS = 1
TIMEOUT_MAX_SECONDS = 300


def validate_latitude(value: float) -> None:
    """
    Validate GPS latitude coordinate.
    
    Args:
        value: Latitude in degrees
        
    Returns:
        None
        
    Raises:
        ValueError: If latitude is not a number or outside valid range
        
    Example:
        >>> validate_latitude(40.7128)  # Valid (NYC)
        >>> validate_latitude(0.0)      # Valid (equator)
        >>> validate_latitude(91.0)     # Raises ValueError
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(
            f"Latitude must be a number, got {type(value).__name__}"
        )
    
    if value < LATITUDE_MIN or value > LATITUDE_MAX:
        raise ValueError(
            f"Latitude must be between {LATITUDE_MIN} and {LATITUDE_MAX}, "
            f"got {value}"
        )


def validate_longitude(value: float) -> None:
    """
    Validate GPS longitude coordinate.
    
    Args:
        value: Longitude in degrees
        
    Returns:
        None
        
    Raises:
        ValueError: If longitude is not a number or outside valid range
        
    Example:
        >>> validate_longitude(-74.0060)  # Valid (NYC)
        >>> validate_longitude(0.0)       # Valid (prime meridian)
        >>> validate_longitude(181.0)     # Raises ValueError
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(
            f"Longitude must be a number, got {type(value).__name__}"
        )
    
    if value < LONGITUDE_MIN or value > LONGITUDE_MAX:
        raise ValueError(
            f"Longitude must be between {LONGITUDE_MIN} and {LONGITUDE_MAX}, "
            f"got {value}"
        )


def validate_gps_point(
    latitude: float,
    longitude: float,
) -> None:
    """
    Validate GPS coordinate pair.
    
    Args:
        latitude: Latitude in degrees (-90 to +90)
        longitude: Longitude in degrees (-180 to +180)
        
    Returns:
        None
        
    Raises:
        ValueError: If either coordinate is invalid
        
    Example:
        >>> validate_gps_point(40.7128, -74.0060)  # NYC
        >>> validate_gps_point(51.5074, -0.1278)   # London
    """
    validate_latitude(latitude)
    validate_longitude(longitude)


def validate_datetime(dt_str: str) -> datetime:
    """
    Validate and parse ISO 8601 datetime string.
    
    Accepts datetime strings in ISO 8601 format with optional timezone:
    - 2024-01-15T12:30:00Z (UTC)
    - 2024-01-15T12:30:00+00:00 (explicit UTC)
    
    Validates:
    - Format is ISO 8601 compliant
    - Not in the future
    - Not before GPS era (1980-01-06)
    
    Args:
        dt_str: ISO 8601 datetime string
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If invalid format or out of valid range
        
    Example:
        >>> dt = validate_datetime("2024-01-15T12:30:00Z")
        >>> dt.year
        2024
    """
    try:
        # Parse ISO 8601 format (replace Z with UTC offset)
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError, TypeError) as e:
        raise ValueError(
            f"Invalid datetime format: '{dt_str}'. "
            f"Expected ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ or +HH:MM)"
        ) from e
    
    # Check not in future
    now = datetime.now(UTC).replace(tzinfo=None)
    if dt.replace(tzinfo=None) > now:
        raise ValueError(
            f"Datetime cannot be in the future: {dt_str}"
        )
    
    # Check not before GPS era
    dt_naive = dt.replace(tzinfo=None)
    if dt_naive < GPS_ERA_START:
        raise ValueError(
            f"Datetime cannot be before GPS era (1980-01-06): {dt_str}"
        )
    
    return dt


def validate_gpx_file(file_path: str) -> None:
    """
    Validate GPX file before processing.
    
    Performs comprehensive validation:
    - File exists and is readable
    - File extension is .gpx
    - File size within limits (max 100 MB)
    - Valid XML structure
    - Contains track points
    
    Args:
        file_path: Path to GPX file
        
    Returns:
        None
        
    Raises:
        ValueError: If any validation check fails
        
    Example:
        >>> validate_gpx_file('track.gpx')  # Valid
        >>> validate_gpx_file('data.txt')    # Raises ValueError
    """
    path = Path(file_path)
    
    # Check exists
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    
    # Check is file (not directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    # Check extension
    if path.suffix.lower() != '.gpx':
        raise ValueError(
            f"File must have .gpx extension, got {path.suffix}. "
            f"File: {file_path}"
        )
    
    # Check file size
    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise ValueError(f"File is empty: {file_path}")
    
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > MAX_GPX_FILE_SIZE_MB:
        raise ValueError(
            f"File too large: {size_mb:.1f}MB (max {MAX_GPX_FILE_SIZE_MB}MB). "
            f"File: {file_path}"
        )
    
    # Check valid XML
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(
            f"Invalid XML in GPX file: {e}"
        ) from e
    except Exception as e:
        raise ValueError(
            f"Error parsing GPX file: {e}"
        ) from e
    
    # Check has track points
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # Try with namespace first
    trkpts = root.findall('.//gpx:trkpt', ns)
    
    # Fall back to no namespace if none found
    if not trkpts:
        trkpts = root.findall('.//trkpt')
    
    if not trkpts:
        raise ValueError(
            f"GPX file contains no track points (trkpt elements). "
            f"File: {file_path}"
        )


def validate_immich_url(url: str) -> None:
    """
    Validate Immich server URL format and basic structure.
    
    Validates:
    - URL not empty
    - Scheme is http or https
    - Hostname present
    
    Note: Does not verify DNS resolution (allows offline development).
    
    Args:
        url: URL to validate
        
    Returns:
        None
        
    Raises:
        ValueError: If URL format is invalid
        
    Example:
        >>> validate_immich_url("http://localhost:2283")
        >>> validate_immich_url("https://immich.example.com")
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL cannot be empty or non-string")
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {url}") from e
    
    # Check scheme
    if not parsed.scheme:
        raise ValueError(
            f"URL must include scheme (http:// or https://): {url}"
        )
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(
            f"URL must use http:// or https://, got {parsed.scheme}://. "
            f"URL: {url}"
        )
    
    # Check hostname
    if not parsed.hostname:
        raise ValueError(f"URL must include hostname: {url}")


def validate_threshold(value: float) -> None:
    """
    Validate time threshold parameter for GPS matching.
    
    Threshold must be a positive integer between 1 and 3600 seconds.
    Default is 60 seconds.
    
    Args:
        value: Time threshold in seconds
        
    Returns:
        None
        
    Raises:
        ValueError: If threshold is not an integer or out of range
        
    Example:
        >>> validate_threshold(60)  # Valid (1 minute)
        >>> validate_threshold(120)  # Valid (2 minutes)
        >>> validate_threshold(0)    # Raises ValueError
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            f"Threshold must be integer, got {type(value).__name__}"
        )
    
    if value < THRESHOLD_MIN_SECONDS or value > THRESHOLD_MAX_SECONDS:
        raise ValueError(
            f"Threshold must be {THRESHOLD_MIN_SECONDS}-{THRESHOLD_MAX_SECONDS} seconds, "
            f"got {value}"
        )


def validate_timeout(value: int) -> None:
    """
    Validate API request timeout parameter.
    
    Timeout must be a positive integer between 1 and 300 seconds.
    Default is 10 seconds.
    
    Args:
        value: Request timeout in seconds
        
    Returns:
        None
        
    Raises:
        ValueError: If timeout is not an integer or out of range
        
    Example:
        >>> validate_timeout(10)   # Valid (10 seconds)
        >>> validate_timeout(30)   # Valid (30 seconds)
        >>> validate_timeout(301)  # Raises ValueError
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            f"Timeout must be integer, got {type(value).__name__}"
        )
    
    if value < TIMEOUT_MIN_SECONDS or value > TIMEOUT_MAX_SECONDS:
        raise ValueError(
            f"Timeout must be {TIMEOUT_MIN_SECONDS}-{TIMEOUT_MAX_SECONDS} seconds, "
            f"got {value}"
        )


def validate_api_key(key: str) -> None:
    """
    Validate Immich API key format and content.
    
    Validates:
    - Must be string
    - Minimum length 20 characters
    - No leading/trailing whitespace
    - No spaces in key
    
    Args:
        key: API key string
        
    Returns:
        None
        
    Raises:
        ValueError: If API key format is invalid
        
    Example:
        >>> validate_api_key("a" * 32)  # Valid (32 chars)
    """
    if not isinstance(key, str):
        raise ValueError(f"API key must be string, got {type(key).__name__}")
    
    if len(key) < MIN_API_KEY_LENGTH:
        raise ValueError(
            f"API key too short (minimum {MIN_API_KEY_LENGTH} chars, "
            f"got {len(key)})"
        )
    
    if key != key.strip():
        raise ValueError(
            "API key contains leading or trailing whitespace"
        )
    
    if ' ' in key:
        raise ValueError("API key contains spaces")


def validate_photo_response(photo: Dict[str, Any]) -> None:
    """
    Validate photo object from Immich API response.
    
    Validates required fields:
    - id: Photo identifier
    - originalFileName: Original filename
    - exifInfo: EXIF metadata dictionary
    - exifInfo.dateTimeOriginal: Photo timestamp
    
    Args:
        photo: Photo dictionary from API
        
    Returns:
        None
        
    Raises:
        ValueError: If required fields missing or invalid
        
    Example:
        >>> photo = {'id': 'abc123', 'originalFileName': 'photo.jpg', 'exifInfo': {}}
        >>> validate_photo_response(photo)  # Will raise - missing dateTimeOriginal
    """
    if not isinstance(photo, dict):
        raise ValueError(f"Photo must be dict, got {type(photo).__name__}")
    
    # Check required fields
    required_fields = ['id', 'originalFileName', 'exifInfo']
    for field in required_fields:
        if field not in photo:
            raise ValueError(
                f"Photo missing required field: '{field}'"
            )
    
    # Validate exifInfo structure
    exif = photo.get('exifInfo')
    if not isinstance(exif, dict):
        raise ValueError(
            f"Photo exifInfo must be dict, got {type(exif).__name__}"
        )
    
    # Check dateTimeOriginal (may be None for photos without EXIF)
    if 'dateTimeOriginal' not in exif:
        raise ValueError(
            "Photo exifInfo missing dateTimeOriginal field"
        )


def validate_match_object(match: Dict[str, Any]) -> None:
    """
    Validate GPS match object structure.
    
    Validates required structure:
    - match['photo']: Photo dictionary with id, name
    - match['gps_point']: GPS point with latitude, longitude, time
    - match['distance_meters']: Distance as number
    - match['time_difference_seconds']: Time diff as number
    
    Args:
        match: Match dictionary
        
    Returns:
        None
        
    Raises:
        ValueError: If required structure missing
        
    Example:
        >>> match = {
        ...     'photo': {'id': 'abc', 'name': 'photo.jpg'},
        ...     'gps_point': {'latitude': 40.7, 'longitude': -74.0, 'time': datetime(2024, 1, 1)},
        ...     'distance_meters': 15.5,
        ...     'time_difference_seconds': 30
        ... }
        >>> validate_match_object(match)  # Valid
    """
    if not isinstance(match, dict):
        raise ValueError(f"Match must be dict, got {type(match).__name__}")
    
    # Check required keys
    required_keys = ['photo', 'gps_point', 'distance_meters', 'time_difference_seconds']
    for key in required_keys:
        if key not in match:
            raise ValueError(f"Match missing required key: '{key}'")
    
    # Validate photo structure
    photo = match['photo']
    if not isinstance(photo, dict):
        raise ValueError(f"Match photo must be dict")
    
    photo_required = ['id', 'name']
    for key in photo_required:
        if key not in photo:
            raise ValueError(f"Match photo missing '{key}'")
    
    # Validate gps_point structure
    gps = match['gps_point']
    if not isinstance(gps, dict):
        raise ValueError(f"Match gps_point must be dict")
    
    gps_required = ['latitude', 'longitude', 'time']
    for key in gps_required:
        if key not in gps:
            raise ValueError(f"Match gps_point missing '{key}'")
    
    # Validate numeric fields
    distance = match.get('distance_meters')
    if not isinstance(distance, (int, float)):
        raise ValueError(f"distance_meters must be number")
    
    if distance < 0:
        raise ValueError(f"distance_meters cannot be negative: {distance}")
    
    time_diff = match.get('time_difference_seconds')
    if not isinstance(time_diff, (int, float)):
        raise ValueError(f"time_difference_seconds must be number")
