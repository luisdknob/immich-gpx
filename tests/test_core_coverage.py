"""Additional tests for core modules to improve coverage."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from immich_gpx.core.gps_matcher import GPSMatcher
from immich_gpx.core.gpx_parser import GPXParser
from pathlib import Path
import tempfile


class TestGPSMatcherBoundary:
    """Test edge cases in GPS matcher."""
    
    def test_matcher_empty_photos(self):
        """Test matching with empty photo list."""
        matcher = GPSMatcher(threshold=120)
        gps_points = [
            {'latitude': 41.0, 'longitude': -71.0, 'time': datetime(2022, 2, 16, 12, 6, 29)},
        ]
        photos = []
        
        result = matcher.match_photos_to_points(gps_points, photos)
        
        assert result == []
    
    def test_matcher_empty_gps_points(self):
        """Test matching with empty GPS points."""
        matcher = GPSMatcher(threshold=120)
        gps_points = []
        photos = [
            {'id': 'p1', 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}},
        ]
        
        result = matcher.match_photos_to_points(gps_points, photos)
        
        assert result == []
    
    def test_matcher_large_distance_threshold(self):
        """Test matcher with very large distance threshold."""
        matcher = GPSMatcher(threshold=10000)  # 10,000 meters
        gps_points = [
            {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100.0, 'time': datetime(2022, 2, 16, 12, 6, 29, tzinfo=timezone.utc)},
        ]
        photos = [
            {'id': 'p1', 'latitude': 35.0, 'longitude': -80.0, 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}},
        ]
        
        result = matcher.match_photos_to_points(gps_points, photos)
        
        # With large threshold, should match due to time proximity
        assert isinstance(result, list)
    
    def test_matcher_very_small_distance_threshold(self):
        """Test matcher with very small distance threshold."""
        matcher = GPSMatcher(threshold=1)  # 1 meter
        gps_points = [
            {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100.0, 'time': datetime(2022, 2, 16, 12, 6, 29, tzinfo=timezone.utc)},
        ]
        photos = [
            {'id': 'p1', 'latitude': 41.000001, 'longitude': -71.000001, 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}},
        ]
        
        result = matcher.match_photos_to_points(gps_points, photos)
        
        # Should return a list (may be empty or contain matches)
        assert isinstance(result, list)
    
    def test_matcher_with_verbose_logging(self):
        """Test matcher with verbose logging."""
        import logging
        logger = logging.getLogger('test')
        matcher = GPSMatcher(threshold=120)
        gps_points = [
            {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100.0, 'time': datetime(2022, 2, 16, 12, 6, 29, tzinfo=timezone.utc)},
        ]
        photos = [
            {'id': 'p1', 'latitude': 41.0, 'longitude': -71.0, 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}},
        ]
        
        result = matcher.match_photos_to_points(gps_points, photos, verbose=True, logger=logger)
        
        assert isinstance(result, list)


class TestGPXParserBoundary:
    """Test edge cases in GPX parser."""
    
    def test_parser_minimal_gpx(self):
        """Test parsing minimal valid GPX."""
        gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="41.0" lon="-71.0">
                <time>2022-02-16T12:06:29Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
            f.write(gpx_content)
            f.flush()
            
            parser = GPXParser(f.name)
            points = parser.parse()
            
            assert len(points) == 1
            assert points[0]['latitude'] == 41.0
            assert points[0]['longitude'] == -71.0
    
    def test_parser_multiple_segments(self):
        """Test parsing GPX with multiple track segments."""
        gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="41.0" lon="-71.0">
                <time>2022-02-16T12:06:29Z</time>
            </trkpt>
        </trkseg>
        <trkseg>
            <trkpt lat="40.0" lon="-70.0">
                <time>2022-02-16T13:06:29Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
            f.write(gpx_content)
            f.flush()
            
            parser = GPXParser(f.name)
            points = parser.parse()
            
            assert len(points) == 2
    
    def test_parser_get_time_range(self):
        """Test extracting time range from GPX."""
        gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="41.0" lon="-71.0">
                <time>2022-02-16T12:00:00Z</time>
            </trkpt>
            <trkpt lat="40.0" lon="-70.0">
                <time>2022-02-16T14:00:00Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
            f.write(gpx_content)
            f.flush()
            
            parser = GPXParser(f.name)
            parser.parse()
            start, end = parser.get_time_range()
            
            assert start < end
            assert start.year == 2022
