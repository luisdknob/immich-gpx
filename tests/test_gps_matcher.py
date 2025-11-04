"""Tests for GPSMatcher class."""
import pytest
from datetime import datetime, timezone
from immich_gpx import GPSMatcher


def test_haversine_distance():
    """Test Haversine distance calculation."""
    matcher = GPSMatcher()
    
    # Distance between two known points
    distance = matcher.haversine_distance(
        41.0, -71.0,
        41.1, -71.1
    )
    
    # Should be approximately 14,000 meters
    assert 13000 < distance < 15000


def test_haversine_distance_same_point():
    """Test Haversine distance for same point."""
    matcher = GPSMatcher()
    
    distance = matcher.haversine_distance(41.0, -71.0, 41.0, -71.0)
    
    assert distance == 0


def test_match_photos_to_points(gps_points):
    """Test photo matching."""
    matcher = GPSMatcher(threshold=60)
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test1.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30+00:00',
                'latitude': None,
                'longitude': None
            }
        },
        {
            'id': 'photo2',
            'originalFileName': 'test2.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:07:30+00:00',
                'latitude': None,
                'longitude': None
            }
        }
    ]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    assert len(matches) == 2
    assert matches[0]['photo']['id'] == 'photo1'
    assert matches[0]['gps_point']['latitude'] == 41.0


def test_no_matches_exceeds_threshold(gps_points):
    """Test when no matches due to time threshold."""
    matcher = GPSMatcher(threshold=1)  # Very strict - 1 second threshold
    
    photos = [{
        'id': 'photo1',
        'originalFileName': 'test1.jpg',
        'exifInfo': {
            'dateTimeOriginal': '2022-02-16T12:10:00+00:00',  # Way too far from GPS points (last at 12:08:29)
            'latitude': None,
            'longitude': None
        }
    }]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    assert len(matches) == 0


def test_match_closest_point(gps_points):
    """Test matching to closest GPS point."""
    matcher = GPSMatcher(threshold=120)
    
    photos = [{
        'id': 'photo1',
        'originalFileName': 'test1.jpg',
        'exifInfo': {
            'dateTimeOriginal': '2022-02-16T12:06:35+00:00',  # Between two points
            'latitude': None,
            'longitude': None
        }
    }]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    # Should match to first point (6 seconds away) not second (54 seconds away)
    assert len(matches) == 1
    assert matches[0]['gps_point']['latitude'] == 41.0
    assert matches[0]['time_difference_seconds'] == 6


def test_skip_photo_no_timestamp(gps_points):
    """Test skipping photos without timestamps."""
    matcher = GPSMatcher()
    
    photos = [{
        'id': 'photo1',
        'originalFileName': 'test1.jpg',
        'exifInfo': {
            'dateTimeOriginal': None,  # No timestamp
            'latitude': None,
            'longitude': None
        }
    }]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    assert len(matches) == 0


def test_match_with_logger():
    """Test matching with logger parameter."""
    import logging
    logger = logging.getLogger('test_matcher_logger')
    
    matcher = GPSMatcher(logger=logger)
    assert matcher.logger is logger


def test_empty_gps_points():
    """Test matching with empty GPS points."""
    matcher = GPSMatcher()
    
    photos = [{
        'id': 'photo1',
        'originalFileName': 'test1.jpg',
        'exifInfo': {
            'dateTimeOriginal': '2022-02-16T12:06:30+00:00',
            'latitude': None,
            'longitude': None
        }
    }]
    
    matches = matcher.match_photos_to_points([], photos)
    
    assert len(matches) == 0


def test_empty_photos():
    """Test matching with empty photos."""
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29, tzinfo=timezone.utc)
        }
    ]
    
    matcher = GPSMatcher()
    matches = matcher.match_photos_to_points(gps_points, [])
    
    assert len(matches) == 0


def test_multiple_matches_same_photo(gps_points):
    """Test that each photo matches only to one closest point."""
    matcher = GPSMatcher(threshold=120)
    
    gps_points_test = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 0, tzinfo=timezone.utc)
        },
        {
            'latitude': 41.05,
            'longitude': -71.05,
            'elevation': 102,
            'time': datetime(2022, 2, 16, 12, 7, 0, tzinfo=timezone.utc)
        },
        {
            'latitude': 41.1,
            'longitude': -71.1,
            'elevation': 105,
            'time': datetime(2022, 2, 16, 12, 8, 0, tzinfo=timezone.utc)
        }
    ]
    
    photos = [{
        'id': 'photo1',
        'originalFileName': 'test1.jpg',
        'exifInfo': {
            'dateTimeOriginal': '2022-02-16T12:06:30+00:00',
            'latitude': None,
            'longitude': None
        }
    }]
    
    matches = matcher.match_photos_to_points(gps_points_test, photos)
    
    # Should match to exactly one point
    assert len(matches) == 1
    # gps_point['time'] is returned as ISO string in the match
    assert matches[0]['gps_point']['time'] == '2022-02-16T12:06:00+00:00'


def test_matches_sorted_oldest_first(gps_points):
    """Test that matches are sorted by photo timestamp (oldest first)."""
    matcher = GPSMatcher(threshold=120)
    
    # Create photos with different timestamps (not in chronological order)
    photos = [
        {
            'id': 'photo3',
            'originalFileName': 'test3.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:09:00Z',  # Third
                'latitude': 41.0,
                'longitude': -71.0
            }
        },
        {
            'id': 'photo1',
            'originalFileName': 'test1.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:05:00Z',  # First (oldest)
                'latitude': 41.0,
                'longitude': -71.0
            }
        },
        {
            'id': 'photo2',
            'originalFileName': 'test2.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:07:00Z',  # Second
                'latitude': 41.0,
                'longitude': -71.0
            }
        }
    ]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    # Should have all 3 matches
    assert len(matches) == 3
    
    # Verify matches are sorted by time (oldest first)
    assert matches[0]['photo']['id'] == 'photo1'
    assert matches[0]['photo']['time'] == '2022-02-16T12:05:00Z'
    
    assert matches[1]['photo']['id'] == 'photo2'
    assert matches[1]['photo']['time'] == '2022-02-16T12:07:00Z'
    
    assert matches[2]['photo']['id'] == 'photo3'
    assert matches[2]['photo']['time'] == '2022-02-16T12:09:00Z'


def test_match_numbering_follows_order():
    """Test that match numbering (#1, #2, etc.) follows chronological order."""
    matcher = GPSMatcher(threshold=120)
    
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 0, tzinfo=timezone.utc)
        }
    ]
    
    photos = [
        {
            'id': 'photo2',
            'originalFileName': 'newer.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',  # Newer
                'latitude': 41.0,
                'longitude': -71.0
            }
        },
        {
            'id': 'photo1',
            'originalFileName': 'older.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:00Z',  # Older
                'latitude': 41.0,
                'longitude': -71.0
            }
        }
    ]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    # Older photo should be first (match #1)
    assert matches[0]['photo']['name'] == 'older.jpg'
    assert matches[1]['photo']['name'] == 'newer.jpg'


def test_single_match_no_sort_error():
    """Test that single match doesn't cause sorting errors."""
    matcher = GPSMatcher(threshold=120)
    
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 0, tzinfo=timezone.utc)
        }
    ]
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:00Z',
                'latitude': 41.0,
                'longitude': -71.0
            }
        }
    ]
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    # Should have exactly one match
    assert len(matches) == 1
    assert matches[0]['photo']['name'] == 'test.jpg'


def test_empty_matches_no_sort_error():
    """Test that empty matches list doesn't cause sorting errors."""
    matcher = GPSMatcher(threshold=120)
    
    gps_points = []
    photos = []
    
    matches = matcher.match_photos_to_points(gps_points, photos)
    
    # Should have empty list
    assert len(matches) == 0
