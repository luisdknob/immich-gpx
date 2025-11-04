"""
GPS point to photo matching logic.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from tqdm import tqdm

from .validation import validate_gps_point, validate_photo_response

# Earth radius constant used in distance calculations
EARTH_RADIUS_METERS = 6371000


class GPSMatcher:
    """Match GPS points with photos based on proximity and time."""

    def __init__(
        self,
        threshold: float = 60,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize GPS matcher.
        
        Args:
            threshold: Time in seconds to consider a match
            logger: Logger instance
        """
        self.threshold = threshold
        self.logger = logger or logging.getLogger('immich-gpx')

    @staticmethod
    def haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate great-circle distance between two GPS coordinates using Haversine formula.
        
        Args:
            lat1: Latitude of first point in degrees
            lon1: Longitude of first point in degrees
            lat2: Latitude of second point in degrees
            lon2: Longitude of second point in degrees
        
        Returns:
            Distance in meters
        """
        from math import radians, cos, sin, asin, sqrt

        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        lon_diff = lon2 - lon1
        lat_diff = lat2 - lat1
        
        angular_distance = (
            sin(lat_diff / 2) ** 2 +
            cos(lat1) * cos(lat2) * sin(lon_diff / 2) ** 2
        )
        
        # Convert angular distance to central angle
        central_angle = 2 * asin(sqrt(angular_distance))
        
        # Convert to meters using Earth's radius
        distance_meters = central_angle * EARTH_RADIUS_METERS
        return distance_meters

    def match_photos_to_points(
        self,
        gps_points: List[Dict],
        photos: List[Dict],
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> List[Dict]:
        """
        Match GPS points with photos based on time proximity only.
        
        Validates GPS coordinates and photo structure before matching.
        Only includes photos and GPS points with valid coordinates and timestamps.
        
        Args:
            gps_points: List of GPS point dictionaries with latitude, longitude, time
            photos: List of photo dictionaries from Immich API
            verbose: Enable verbose logging of matching process
            logger: Logger instance for output
            
        Returns:
            List of matched results with photo, gps_point, distance, time_difference
            
        Raises:
            Logs validation errors but continues (non-critical for matching)
        """
        if logger is None:
            logger = logging.getLogger('immich-gpx')
        
        matches = []

        for photo in tqdm(photos, desc="Matching photos to GPS points", unit="photo", leave=False, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
            # Validate photo structure (logs errors but continues)
            try:
                validate_photo_response(photo)
            except ValueError as e:
                if verbose:
                    logger.debug(f"[VALIDATION] Photo validation error: {e}")
                continue
            
            photo_time_str = photo.get('exifInfo', {}).get('dateTimeOriginal')
            photo_lat = photo.get('exifInfo', {}).get('latitude')
            photo_lon = photo.get('exifInfo', {}).get('longitude')
            
            if verbose:
                logger.debug(f"[MATCHER] Photo: {photo.get('originalFileName')}")
                logger.debug(f"  Location: ({photo_lat}, {photo_lon})")
                logger.debug(f"  Time: {photo_time_str}")

            if not photo_time_str:
                if verbose:
                    print(f"  → Skipped: No timestamp")
                continue

            try:
                photo_time = datetime.fromisoformat(
                    photo_time_str.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                if verbose:
                    print(f"  → Skipped: Invalid timestamp")
                continue

            # Find the closest GPS point in time
            closest_gps_point = None
            min_time_diff = float('inf')
            
            for gps_point in gps_points:
                gps_time = gps_point['time']
                
                if not gps_time:
                    continue
                
                # Validate GPS coordinates (logs errors but continues)
                gps_lat = gps_point.get('latitude')
                gps_lon = gps_point.get('longitude')
                if gps_lat is not None and gps_lon is not None:
                    try:
                        validate_gps_point(gps_lat, gps_lon)
                    except ValueError as e:
                        if verbose:
                            logger.debug(f"[VALIDATION] GPS point validation error: {e}")
                        continue
                
                time_diff = abs((photo_time - gps_time).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_gps_point = gps_point
            
            if closest_gps_point is None:
                if verbose:
                    print(f"  → Skipped: No GPS points with timestamps")
                continue
            
            if verbose:
                print(f"  Closest GPS point time diff: {min_time_diff:.1f}s (threshold: {self.threshold}s)")
            
            if min_time_diff > self.threshold:
                if verbose:
                    print(f"  → Skipped: Closest point exceeds time threshold")
                continue
            
            # Create match for the closest GPS point
            gps_point = closest_gps_point
            
            # Calculate distance for informational purposes
            if photo_lat and photo_lon:
                distance = self.haversine_distance(
                    gps_point['latitude'],
                    gps_point['longitude'],
                    photo_lat,
                    photo_lon,
                )
            else:
                distance = None
            
            matches.append({
                'photo': {
                    'id': photo.get('id'),
                    'name': photo.get('originalFileName'),
                    'latitude': photo_lat,
                    'longitude': photo_lon,
                    'time': photo_time_str,
                },
                'gps_point': {
                    'latitude': gps_point['latitude'],
                    'longitude': gps_point['longitude'],
                    'elevation': gps_point['elevation'],
                    'time': gps_point['time'].isoformat() if gps_point['time'] else None,
                },
                'distance_meters': round(distance, 2) if distance else None,
                'time_difference_seconds': round(min_time_diff),
            })
            
            if verbose:
                logger.debug(f"  Matched: Time diff {min_time_diff:.0f}s, Distance {distance:.0f}m" if distance else f"  Matched: Time diff {min_time_diff:.0f}s")

        # Sort matches by photo timestamp (oldest first)
        matches.sort(key=lambda m: m['photo']['time'])

        return matches
