"""
Comprehensive tests for the validation module.

Tests all validation functions with valid and invalid inputs.
"""

import pytest
from datetime import datetime, timedelta, UTC
from pathlib import Path
from immich_gpx.core.validation import (
    validate_latitude,
    validate_longitude,
    validate_gps_point,
    validate_datetime,
    validate_gpx_file,
    validate_immich_url,
    validate_threshold,
    validate_timeout,
    validate_api_key,
    validate_photo_response,
    validate_match_object,
    GPS_ERA_START,
    LATITUDE_MIN,
    LATITUDE_MAX,
    LONGITUDE_MIN,
    LONGITUDE_MAX,
)


class TestLatitudeValidation:
    """Tests for validate_latitude function."""
    
    def test_valid_latitude_zero(self):
        """Test valid latitude at equator."""
        validate_latitude(0.0)  # Should not raise
    
    def test_valid_latitude_positive(self):
        """Test valid positive latitude."""
        validate_latitude(40.7128)  # NYC latitude
    
    def test_valid_latitude_negative(self):
        """Test valid negative latitude."""
        validate_latitude(-33.8688)  # Sydney latitude
    
    def test_valid_latitude_boundary_positive(self):
        """Test valid latitude at positive boundary."""
        validate_latitude(90.0)
    
    def test_valid_latitude_boundary_negative(self):
        """Test valid latitude at negative boundary."""
        validate_latitude(-90.0)
    
    def test_invalid_latitude_too_high(self):
        """Test invalid latitude above maximum."""
        with pytest.raises(ValueError, match="must be between"):
            validate_latitude(91.0)
    
    def test_invalid_latitude_too_low(self):
        """Test invalid latitude below minimum."""
        with pytest.raises(ValueError, match="must be between"):
            validate_latitude(-91.0)
    
    def test_invalid_latitude_string(self):
        """Test invalid latitude as string."""
        with pytest.raises(ValueError, match="must be a number"):
            validate_latitude("40.7128")
    
    def test_invalid_latitude_bool(self):
        """Test invalid latitude as boolean."""
        with pytest.raises(ValueError, match="must be a number"):
            validate_latitude(True)


class TestLongitudeValidation:
    """Tests for validate_longitude function."""
    
    def test_valid_longitude_zero(self):
        """Test valid longitude at prime meridian."""
        validate_longitude(0.0)
    
    def test_valid_longitude_positive(self):
        """Test valid positive longitude."""
        validate_longitude(-74.0060)  # NYC longitude
    
    def test_valid_longitude_negative(self):
        """Test valid negative longitude."""
        validate_longitude(151.2093)  # Sydney longitude
    
    def test_valid_longitude_boundary_positive(self):
        """Test valid longitude at positive boundary."""
        validate_longitude(180.0)
    
    def test_valid_longitude_boundary_negative(self):
        """Test valid longitude at negative boundary."""
        validate_longitude(-180.0)
    
    def test_invalid_longitude_too_high(self):
        """Test invalid longitude above maximum."""
        with pytest.raises(ValueError, match="must be between"):
            validate_longitude(181.0)
    
    def test_invalid_longitude_too_low(self):
        """Test invalid longitude below minimum."""
        with pytest.raises(ValueError, match="must be between"):
            validate_longitude(-181.0)


class TestGPSPointValidation:
    """Tests for validate_gps_point function."""
    
    def test_valid_gps_point_nyc(self):
        """Test valid GPS point for NYC."""
        validate_gps_point(40.7128, -74.0060)
    
    def test_valid_gps_point_sydney(self):
        """Test valid GPS point for Sydney."""
        validate_gps_point(-33.8688, 151.2093)
    
    def test_valid_gps_point_equator(self):
        """Test valid GPS point at equator."""
        validate_gps_point(0.0, 0.0)
    
    def test_invalid_gps_point_bad_latitude(self):
        """Test invalid GPS point with bad latitude."""
        with pytest.raises(ValueError, match="Latitude"):
            validate_gps_point(91.0, -74.0060)
    
    def test_invalid_gps_point_bad_longitude(self):
        """Test invalid GPS point with bad longitude."""
        with pytest.raises(ValueError, match="Longitude"):
            validate_gps_point(40.7128, 181.0)


class TestDatetimeValidation:
    """Tests for validate_datetime function."""
    
    def test_valid_datetime_iso8601_utc_z(self):
        """Test valid ISO 8601 datetime with Z suffix."""
        dt = validate_datetime("2024-01-15T12:30:00Z")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
    
    def test_valid_datetime_iso8601_with_offset(self):
        """Test valid ISO 8601 datetime with explicit offset."""
        dt = validate_datetime("2024-01-15T12:30:00+00:00")
        assert dt.year == 2024
    
    def test_valid_datetime_past(self):
        """Test valid datetime in the past."""
        past_date = "2020-01-15T12:30:00Z"
        dt = validate_datetime(past_date)
        assert dt.year == 2020
    
    def test_invalid_datetime_future(self):
        """Test invalid datetime in the future."""
        future_date = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="cannot be in the future"):
            validate_datetime(future_date)
    
    def test_invalid_datetime_before_gps_era(self):
        """Test invalid datetime before GPS era (1980-01-06)."""
        with pytest.raises(ValueError, match="cannot be before GPS era"):
            validate_datetime("1970-01-01T12:30:00Z")
    
    def test_invalid_datetime_format(self):
        """Test invalid datetime format."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            validate_datetime("01/15/2024")
    
    def test_invalid_datetime_empty_string(self):
        """Test invalid empty datetime string."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            validate_datetime("")


class TestGPXFileValidation:
    """Tests for validate_gpx_file function."""
    
    def test_valid_gpx_file_with_trackpoints(self, tmp_path):
        """Test valid GPX file with track points."""
        gpx_file = tmp_path / "test.gpx"
        gpx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="40.7128" lon="-74.0060">
        <time>2024-01-15T12:00:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>'''
        gpx_file.write_text(gpx_content)
        validate_gpx_file(str(gpx_file))
    
    def test_invalid_gpx_file_not_found(self):
        """Test invalid GPX file that doesn't exist."""
        with pytest.raises(ValueError, match="File not found"):
            validate_gpx_file("/nonexistent/file.gpx")
    
    def test_invalid_gpx_file_wrong_extension(self, tmp_path):
        """Test invalid file with wrong extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("some data")
        with pytest.raises(ValueError, match="must have .gpx extension"):
            validate_gpx_file(str(txt_file))
    
    def test_invalid_gpx_file_empty(self, tmp_path):
        """Test invalid empty GPX file."""
        gpx_file = tmp_path / "empty.gpx"
        gpx_file.write_text("")
        with pytest.raises(ValueError, match="File is empty"):
            validate_gpx_file(str(gpx_file))
    
    def test_invalid_gpx_file_invalid_xml(self, tmp_path):
        """Test invalid GPX file with malformed XML."""
        gpx_file = tmp_path / "invalid.gpx"
        gpx_file.write_text("<?xml version=\"1.0\"?><gpx><unclosed>")
        with pytest.raises(ValueError, match="Invalid XML"):
            validate_gpx_file(str(gpx_file))
    
    def test_invalid_gpx_file_no_trackpoints(self, tmp_path):
        """Test invalid GPX file with no track points."""
        gpx_file = tmp_path / "no_tracks.gpx"
        gpx_file.write_text("<?xml version=\"1.0\"?><gpx></gpx>")
        with pytest.raises(ValueError, match="no track points"):
            validate_gpx_file(str(gpx_file))


class TestURLValidation:
    """Tests for validate_immich_url function."""
    
    def test_valid_url_http_localhost(self):
        """Test valid HTTP localhost URL."""
        validate_immich_url("http://localhost:2283")
    
    def test_valid_url_https_domain(self):
        """Test valid HTTPS domain URL."""
        validate_immich_url("https://photos.example.com")
    
    def test_valid_url_with_path(self):
        """Test valid URL with path."""
        validate_immich_url("https://example.com/immich")
    
    def test_invalid_url_no_scheme(self):
        """Test invalid URL without scheme."""
        with pytest.raises(ValueError, match="http://|https://"):
            validate_immich_url("localhost:2283")
    
    def test_invalid_url_ftp_scheme(self):
        """Test invalid URL with unsupported scheme."""
        with pytest.raises(ValueError, match="http://|https://"):
            validate_immich_url("ftp://example.com")
    
    def test_invalid_url_empty_string(self):
        """Test invalid empty URL."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_immich_url("")
    
    def test_invalid_url_none(self):
        """Test invalid None URL."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_immich_url(None)


class TestThresholdValidation:
    """Tests for validate_threshold function."""
    
    def test_valid_threshold_minimum(self):
        """Test valid threshold at minimum."""
        validate_threshold(1)
    
    def test_valid_threshold_maximum(self):
        """Test valid threshold at maximum."""
        validate_threshold(3600)
    
    def test_valid_threshold_middle(self):
        """Test valid threshold in middle range."""
        validate_threshold(60)
    
    def test_invalid_threshold_zero(self):
        """Test invalid threshold at zero."""
        with pytest.raises(ValueError, match="Threshold must be"):
            validate_threshold(0)
    
    def test_invalid_threshold_negative(self):
        """Test invalid negative threshold."""
        with pytest.raises(ValueError, match="Threshold must be"):
            validate_threshold(-60)
    
    def test_invalid_threshold_too_high(self):
        """Test invalid threshold above maximum."""
        with pytest.raises(ValueError, match="Threshold must be"):
            validate_threshold(3601)
    
    def test_invalid_threshold_float(self):
        """Test invalid float threshold."""
        with pytest.raises(ValueError, match="must be integer"):
            validate_threshold(60.5)
    
    def test_invalid_threshold_string(self):
        """Test invalid string threshold."""
        with pytest.raises(ValueError, match="must be integer"):
            validate_threshold("60")


class TestTimeoutValidation:
    """Tests for validate_timeout function."""
    
    def test_valid_timeout_minimum(self):
        """Test valid timeout at minimum."""
        validate_timeout(1)
    
    def test_valid_timeout_maximum(self):
        """Test valid timeout at maximum."""
        validate_timeout(300)
    
    def test_valid_timeout_middle(self):
        """Test valid timeout in middle range."""
        validate_timeout(10)
    
    def test_invalid_timeout_zero(self):
        """Test invalid timeout at zero."""
        with pytest.raises(ValueError, match="Timeout must be"):
            validate_timeout(0)
    
    def test_invalid_timeout_negative(self):
        """Test invalid negative timeout."""
        with pytest.raises(ValueError, match="Timeout must be"):
            validate_timeout(-10)
    
    def test_invalid_timeout_too_high(self):
        """Test invalid timeout above maximum."""
        with pytest.raises(ValueError, match="Timeout must be"):
            validate_timeout(301)


class TestAPIKeyValidation:
    """Tests for validate_api_key function."""
    
    def test_valid_api_key_minimum_length(self):
        """Test valid API key at minimum length."""
        validate_api_key("a" * 20)
    
    def test_valid_api_key_long(self):
        """Test valid API key with long length."""
        validate_api_key("abcdefghijklmnopqrst_1234567890")
    
    def test_invalid_api_key_too_short(self):
        """Test invalid API key below minimum length."""
        with pytest.raises(ValueError, match="too short"):
            validate_api_key("short")
    
    def test_invalid_api_key_with_spaces(self):
        """Test invalid API key with spaces."""
        with pytest.raises(ValueError, match="whitespace|spaces"):
            validate_api_key("a" * 19 + " ")
    
    def test_invalid_api_key_empty(self):
        """Test invalid empty API key."""
        with pytest.raises(ValueError, match="too short"):
            validate_api_key("")


class TestPhotoResponseValidation:
    """Tests for validate_photo_response function."""
    
    def test_valid_photo_response_minimal(self):
        """Test valid photo with minimal required fields."""
        photo = {
            'id': 'photo-123',
            'originalFileName': 'photo.jpg',
            'exifInfo': {'dateTimeOriginal': '2024-01-15T12:00:00Z'}
        }
        validate_photo_response(photo)
    
    def test_valid_photo_response_complete(self):
        """Test valid photo with complete fields."""
        photo = {
            'id': 'photo-123',
            'originalFileName': 'photo.jpg',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'exifInfo': {'dateTimeOriginal': '2024-01-15T12:00:00Z'}
        }
        validate_photo_response(photo)
    
    def test_invalid_photo_response_no_id(self):
        """Test invalid photo without id."""
        photo = {'originalFileName': 'photo.jpg', 'exifInfo': {'dateTimeOriginal': '2024-01-15T12:00:00Z'}}
        with pytest.raises(ValueError, match="missing required field"):
            validate_photo_response(photo)
    
    def test_invalid_photo_response_not_dict(self):
        """Test invalid photo that is not dict."""
        with pytest.raises(ValueError, match="must be dict"):
            validate_photo_response("not a dict")
    
    def test_invalid_photo_response_empty(self):
        """Test invalid empty photo dict."""
        with pytest.raises(ValueError, match="missing required field"):
            validate_photo_response({})


class TestMatchObjectValidation:
    """Tests for validate_match_object function."""
    
    def test_valid_match_object_complete(self):
        """Test valid complete match object."""
        match = {
            'photo': {'id': 'p1', 'name': 'photo.jpg'},
            'gps_point': {
                'latitude': 40.7128,
                'longitude': -74.0060,
                'time': datetime.now()
            },
            'distance_meters': 15.5,
            'time_difference_seconds': 30
        }
        validate_match_object(match)
    
    def test_invalid_match_missing_photo(self):
        """Test invalid match missing photo."""
        match = {
            'gps_point': {'latitude': 40.7, 'longitude': -74.0, 'time': datetime.now()},
            'distance_meters': 15.5,
            'time_difference_seconds': 30
        }
        with pytest.raises(ValueError, match="missing required key"):
            validate_match_object(match)
    
    def test_invalid_match_missing_gps_point(self):
        """Test invalid match missing gps_point."""
        match = {
            'photo': {'id': 'p1', 'name': 'photo.jpg'},
            'distance_meters': 15.5,
            'time_difference_seconds': 30
        }
        with pytest.raises(ValueError, match="missing required key"):
            validate_match_object(match)
    
    def test_invalid_match_negative_distance(self):
        """Test invalid match with negative distance."""
        match = {
            'photo': {'id': 'p1', 'name': 'photo.jpg'},
            'gps_point': {
                'latitude': 40.7128,
                'longitude': -74.0060,
                'time': datetime.now()
            },
            'distance_meters': -15.5,
            'time_difference_seconds': 30
        }
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_match_object(match)
    
    def test_invalid_match_not_dict(self):
        """Test invalid match that is not dict."""
        with pytest.raises(ValueError, match="must be dict"):
            validate_match_object("not a dict")
