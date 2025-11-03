"""
GPX file parsing and GPS point extraction module.

Provides GPXParser class for parsing GPX (GPS Exchange Format) files and extracting
GPS track points with timestamps, coordinates, and elevation data. Handles error
cases (missing files, invalid formats) and provides time range queries.

Classes:
    GPXParser: Main parser class for reading and extracting GPS data from GPX files
    
Main entry point: GPXParser.parse()
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import gpxpy
    import gpxpy.gpx
except ImportError:
    gpxpy = None

from .errors import GPXParsingError, GPXValidationError


class GPXParser:
    """
    Parse and extract GPS points from GPX (GPS Exchange Format) files.
    
    Handles GPX file validation, parsing, and point extraction from both tracks
    and waypoints. Provides time range queries and sorts points chronologically.
    
    Attributes:
        gpx_file (Path): Path to the GPX file
        gpx_data: Parsed GPX object from gpxpy
        points (List[Dict]): Extracted GPS points with coordinates and timestamps
        logger (logging.Logger): Logger instance for output
        
    Example:
        >>> parser = GPXParser('track.gpx')
        >>> points = parser.parse()
        >>> start, end = parser.get_time_range()
    """

    def __init__(
        self,
        gpx_file: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize GPX parser with file path and optional logger.
        
        Args:
            gpx_file: Path to GPX file (string or Path object)
            logger: Optional logger instance (defaults to 'immich-gpx')
            
        Returns:
            None
            
        Example:
            >>> parser = GPXParser('my_track.gpx')
            >>> parser_with_logger = GPXParser('track.gpx', logger=custom_logger)
        """
        self.gpx_file = Path(gpx_file)
        self.gpx_data = None
        self.points: List[Dict] = []
        self.logger = logger or logging.getLogger('immich-gpx')

    def parse(self) -> List[Dict]:
        """
        Parse GPX file and extract all GPS points with timestamps and elevation.
        
        Validates file existence, parses XML format, and extracts coordinates from
        both GPX tracks (recorded routes) and waypoints (marked locations). Sorts
        all points chronologically by timestamp.
        
        Returns:
            List of GPS point dictionaries, each containing:
                - 'latitude': float, GPS latitude (-90 to 90)
                - 'longitude': float, GPS longitude (-180 to 180)
                - 'elevation': float or None, altitude in meters
                - 'time': datetime or None, timestamp of the point
                
        Raises:
            GPXValidationError: If file not found or cannot be read
            GPXParsingError: If GPX XML format is invalid or corrupted
            
        Example:
            >>> parser = GPXParser('track.gpx')
            >>> points = parser.parse()
            >>> print(f"Extracted {len(points)} GPS points")
            >>> for point in points[:3]:
            ...     print(f"Lat: {point['latitude']}, Lon: {point['longitude']}")
        """
        # Validate file existence
        if not self.gpx_file.exists():
            raise GPXValidationError(f"GPX file not found: {self.gpx_file}")

        try:
            # Parse GPX XML file
            with open(self.gpx_file, 'r', encoding='utf-8') as gpx_file:
                self.gpx_data = gpxpy.parse(gpx_file)
        except (IOError, OSError) as e:
            raise GPXValidationError(f"Cannot read GPX file: {e}")
        except gpxpy.gpx.GPXException as e:
            raise GPXParsingError(f"Invalid GPX format: {e}")
        except Exception as e:
            raise GPXParsingError(f"Unexpected error parsing GPX: {e}")

        # Initialize points list
        self.points = []

        # Extract points from tracks (recorded route segments)
        for track in self.gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    self.points.append({
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'elevation': point.elevation,
                        'time': point.time,
                    })

        # Extract points from waypoints (named locations)
        for waypoint in self.gpx_data.waypoints:
            self.points.append({
                'latitude': waypoint.latitude,
                'longitude': waypoint.longitude,
                'elevation': waypoint.elevation,
                'time': waypoint.time,
            })

        # Sort all points chronologically by timestamp
        # Points without timestamps sort to beginning (datetime.min)
        self.points.sort(key=lambda p: p['time'] or datetime.min)

        return self.points

    def get_time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Get the minimum and maximum timestamps from all GPS points.
        
        Useful for querying Immich for photos taken during the recorded track,
        with optional time buffers added for photos taken slightly before/after.
        
        Returns:
            Tuple of (start_time, end_time) as datetime objects, or (None, None)
            if no points have timestamps
            
        Example:
            >>> parser = GPXParser('track.gpx')
            >>> points = parser.parse()
            >>> start_time, end_time = parser.get_time_range()
            >>> if start_time:
            ...     duration = end_time - start_time
            ...     print(f"Track duration: {duration}")
        """
        # Return None if no points available
        if not self.points:
            return None, None

        # Filter points with valid timestamps
        times = [p['time'] for p in self.points if p['time']]
        if not times:
            return None, None

        # Return min and max timestamps
        return min(times), max(times)
