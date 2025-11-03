"""Tests for GPXParser class."""
import pytest
from pathlib import Path
from immich_gpx import GPXParser, GPXValidationError, GPXParsingError


def test_parse_valid_gpx(tmp_gpx_file):
    """Test parsing valid GPX file."""
    parser = GPXParser(str(tmp_gpx_file))
    points = parser.parse()
    
    assert len(points) == 3
    assert points[0]['latitude'] == 41.0
    assert points[0]['longitude'] == -71.0
    assert points[0]['elevation'] == 100
    assert points[0]['time'] is not None


def test_parse_nonexistent_file():
    """Test handling of missing file."""
    parser = GPXParser("nonexistent.gpx")
    
    with pytest.raises(GPXValidationError, match="GPX file not found"):
        parser.parse()


def test_parse_empty_gpx(tmp_path, empty_gpx_content):
    """Test parsing empty GPX file."""
    gpx_file = tmp_path / "empty.gpx"
    gpx_file.write_text(empty_gpx_content)
    
    parser = GPXParser(str(gpx_file))
    points = parser.parse()
    
    assert len(points) == 0


def test_get_time_range(tmp_gpx_file):
    """Test extracting time range."""
    parser = GPXParser(str(tmp_gpx_file))
    points = parser.parse()
    
    start_time, end_time = parser.get_time_range()
    
    assert start_time is not None
    assert end_time is not None
    assert start_time < end_time
    assert (end_time - start_time).total_seconds() == 120.0


def test_get_time_range_no_points(tmp_path, empty_gpx_content):
    """Test time range with no points."""
    gpx_file = tmp_path / "empty.gpx"
    gpx_file.write_text(empty_gpx_content)
    
    parser = GPXParser(str(gpx_file))
    parser.parse()
    
    start_time, end_time = parser.get_time_range()
    
    assert start_time is None
    assert end_time is None


def test_points_sorted_by_time(tmp_path):
    """Test that points are sorted by time."""
    unsorted_gpx = '''<?xml version="1.0"?>
<gpx version="1.1">
    <trk><trkseg>
        <trkpt lat="41.3" lon="-71.3">
            <time>2022-02-16T12:08:29Z</time>
        </trkpt>
        <trkpt lat="41.1" lon="-71.1">
            <time>2022-02-16T12:06:29Z</time>
        </trkpt>
        <trkpt lat="41.2" lon="-71.2">
            <time>2022-02-16T12:07:29Z</time>
        </trkpt>
    </trkseg></trk>
</gpx>'''
    
    gpx_file = tmp_path / "unsorted.gpx"
    gpx_file.write_text(unsorted_gpx)
    
    parser = GPXParser(str(gpx_file))
    points = parser.parse()
    
    times = [p['time'] for p in points if p['time']]
    assert times == sorted(times)


def test_parse_waypoints(tmp_path, gpx_with_waypoints):
    """Test parsing waypoints."""
    gpx_file = tmp_path / "waypoints.gpx"
    gpx_file.write_text(gpx_with_waypoints)
    
    parser = GPXParser(str(gpx_file))
    points = parser.parse()
    
    assert len(points) == 1
    assert points[0]['latitude'] == 41.5
    assert points[0]['longitude'] == -71.5


def test_parse_invalid_xml(tmp_path):
    """Test handling of invalid XML."""
    invalid_gpx = "not valid xml"
    gpx_file = tmp_path / "invalid.gpx"
    gpx_file.write_text(invalid_gpx)
    
    parser = GPXParser(str(gpx_file))
    
    with pytest.raises(GPXParsingError, match="Invalid GPX format"):
        parser.parse()


def test_parse_with_logger(tmp_gpx_file):
    """Test parsing with logger parameter."""
    import logging
    logger = logging.getLogger('test_logger')
    
    parser = GPXParser(str(tmp_gpx_file), logger=logger)
    points = parser.parse()
    
    assert len(points) == 3
