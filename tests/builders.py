"""
Test data builders for creating consistent test data.

Builder classes and convenience functions:
- photo(): Create photo in Immich API format
- gps_point(): Create GPS point with coordinates
- match(): Create photo-GPS match structure
"""

from datetime import datetime
from typing import Dict, Optional


class PhotoBuilder:
    """Builder for test photo data in Immich API format."""
    
    def __init__(self):
        self.data = {
            'id': 'photo1',
            'originalFileName': 'IMG_001.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',
                'latitude': None,
                'longitude': None
            }
        }
    
    def with_id(self, photo_id: str):
        """Set photo ID."""
        self.data['id'] = photo_id
        return self
    
    def with_name(self, name: str):
        """Set photo filename."""
        self.data['originalFileName'] = name
        return self
    
    def with_gps(self, lat: float, lon: float):
        """Set GPS coordinates."""
        self.data['exifInfo']['latitude'] = lat
        self.data['exifInfo']['longitude'] = lon
        return self
    
    def without_gps(self):
        """Remove GPS coordinates."""
        self.data['exifInfo']['latitude'] = None
        self.data['exifInfo']['longitude'] = None
        return self
    
    def with_time(self, time_str: str):
        """Set photo timestamp."""
        self.data['exifInfo']['dateTimeOriginal'] = time_str
        return self
    
    def build(self) -> Dict:
        """Build and return photo dict in Immich API format."""
        return self.data.copy()


class GPSPointBuilder:
    """Builder for GPS point data."""
    
    def __init__(self):
        self.data = {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29)
        }
    
    def at(self, lat: float, lon: float):
        """Set GPS coordinates."""
        self.data['latitude'] = lat
        self.data['longitude'] = lon
        return self
    
    def with_elevation(self, elevation: float):
        """Set elevation."""
        self.data['elevation'] = elevation
        return self
    
    def with_time(self, time):
        """Set GPS timestamp."""
        self.data['time'] = time
        return self
    
    def build(self) -> Dict:
        """Build and return GPS point dict."""
        return self.data.copy()


class MatchBuilder:
    """Builder for match data (photo + GPS point)."""
    
    def __init__(self):
        self._photo = None
        self._gps = None
        self._distance = 10.5
        self._time_diff = 1
    
    def with_photo(self, photo: Dict):
        """Set photo data."""
        self._photo = photo
        return self
    
    def with_gps(self, gps: Dict):
        """Set GPS point data."""
        self._gps = gps
        return self
    
    def with_distance(self, distance: float):
        """Set distance in meters."""
        self._distance = distance
        return self
    
    def with_time_diff(self, seconds: int):
        """Set time difference in seconds."""
        self._time_diff = seconds
        return self
    
    def build(self) -> Dict:
        """Build and return match dict with photo in match format."""
        photo_data = self._photo if self._photo else PhotoBuilder().build()
        gps_data = self._gps if self._gps else GPSPointBuilder().build()
        
        # Transform photo from Immich API format to match format
        # (mimics what GPSMatcher does in gps_matcher.py line 207)
        match_photo = {
            'id': photo_data.get('id'),
            'name': photo_data.get('originalFileName'),
            'time': photo_data.get('exifInfo', {}).get('dateTimeOriginal'),
            'latitude': photo_data.get('exifInfo', {}).get('latitude'),
            'longitude': photo_data.get('exifInfo', {}).get('longitude')
        }
        
        # Transform GPS point time to ISO string if it's a datetime object
        match_gps = gps_data.copy()
        if hasattr(match_gps.get('time'), 'isoformat'):
            match_gps['time'] = match_gps['time'].isoformat().replace('+00:00', 'Z')
        
        return {
            'photo': match_photo,
            'gps_point': match_gps,
            'distance_meters': self._distance,
            'time_difference_seconds': self._time_diff
        }


# Convenience functions for quick test data creation

def photo(photo_id: str = 'photo1', lat: Optional[float] = None, lon: Optional[float] = None, 
          name: str = 'IMG_001.jpg', timestamp: Optional[str] = '2022-02-16T12:06:30Z') -> Dict:
    """
    Quick photo builder for Immich API format.
    
    Args:
        photo_id: Photo ID
        lat: Latitude (None for no GPS)
        lon: Longitude (None for no GPS)
        name: Filename
        timestamp: ISO format timestamp (default: '2022-02-16T12:06:30Z', None to omit)
    
    Returns:
        Photo dict in Immich API format
    
    Examples:
        >>> photo('p1')  # No GPS, default timestamp
        >>> photo('p2', 41.0, -71.0)  # With GPS
        >>> photo('p3', timestamp='2022-02-16T12:00:00Z')
    """
    builder = PhotoBuilder().with_id(photo_id).with_name(name)
    if lat is not None and lon is not None:
        builder.with_gps(lat, lon)
    if timestamp is not None:
        builder.with_time(timestamp)
    return builder.build()


def gps_point(lat: float = 41.0, lon: float = -71.0, elevation: float = 100) -> Dict:
    """
    Quick GPS point builder.
    
    Args:
        lat: Latitude
        lon: Longitude
        elevation: Elevation in meters
    
    Returns:
        GPS point dict
    
    Examples:
        >>> gps_point()  # Default coords
        >>> gps_point(46.5, 12.0)  # Custom coords
    """
    return GPSPointBuilder().at(lat, lon).with_elevation(elevation).build()


def match(photo_data: Optional[Dict] = None, gps_data: Optional[Dict] = None) -> Dict:
    """
    Quick match builder.
    
    Args:
        photo_data: Photo dict (uses default if None)
        gps_data: GPS point dict (uses default if None)
    
    Returns:
        Match dict
    
    Examples:
        >>> match()  # Default photo and GPS
        >>> match(photo('p1'), gps_point(41.0, -71.0))
    """
    builder = MatchBuilder()
    if photo_data:
        builder.with_photo(photo_data)
    if gps_data:
        builder.with_gps(gps_data)
    return builder.build()
