"""
Tests for external library detection and XMP file handling.

Tests LibraryDetector for categorizing photos and XMPWriter for creating
sidecar files with GPS coordinates.
"""

import json
import logging
import pytest
from pathlib import Path
from immich_gpx.library_detector import LibraryDetector, LibraryInfo
from immich_gpx.xmp_writer import XMPWriter


@pytest.fixture
def logger():
    """Create a test logger."""
    return logging.getLogger("test")


@pytest.fixture
def temp_xmp_dir(tmp_path):
    """Create a temporary directory for XMP files."""
    return tmp_path / "xmp"


@pytest.fixture
def library_detector(logger):
    """Create a LibraryDetector instance."""
    return LibraryDetector(logger=logger)


@pytest.fixture
def xmp_writer(temp_xmp_dir, logger):
    """Create an XMPWriter instance with temp directory."""
    return XMPWriter(output_dir=temp_xmp_dir, logger=logger)


# ============================================================================
# Library Detector Tests
# ============================================================================


def test_is_external_library_main(library_detector):
    """Test detection of main library photos."""
    photo = {
        "id": "photo-123",
        "libraryId": "00000000-0000-0000-0000-000000000000",
    }
    assert not library_detector.is_external_library(photo)


def test_is_external_library_external(library_detector):
    """Test detection of external library photos."""
    photo = {
        "id": "photo-456",
        "libraryId": "12345678-1234-1234-1234-123456789abc",
    }
    assert library_detector.is_external_library(photo)


def test_is_external_library_no_library_id(library_detector):
    """Test photo without libraryId is assumed to be main library."""
    photo = {"id": "photo-789"}
    assert not library_detector.is_external_library(photo)


def test_categorize_photos(library_detector):
    """Test categorizing mixed photos."""
    photos = [
        {"id": "p1", "libraryId": "00000000-0000-0000-0000-000000000000"},  # Main
        {"id": "p2", "libraryId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},  # External
        {"id": "p3", "libraryId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},  # External
        {"id": "p4", "libraryId": "00000000-0000-0000-0000-000000000000"},  # Main
    ]

    result = library_detector.categorize_photos(photos)

    assert len(result["main_library"]) == 2
    assert len(result["external_libraries"]) == 2
    assert result["counts"]["main"] == 2
    assert result["counts"]["external"] == 2
    assert result["counts"]["total"] == 4


def test_categorize_photos_all_main(library_detector):
    """Test categorizing all main library photos."""
    photos = [
        {"id": "p1", "libraryId": "00000000-0000-0000-0000-000000000000"},
        {"id": "p2", "libraryId": "00000000-0000-0000-0000-000000000000"},
    ]

    result = library_detector.categorize_photos(photos)

    assert len(result["main_library"]) == 2
    assert len(result["external_libraries"]) == 0


def test_categorize_photos_all_external(library_detector):
    """Test categorizing all external library photos."""
    photos = [
        {"id": "p1", "libraryId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        {"id": "p2", "libraryId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},
    ]

    result = library_detector.categorize_photos(photos)

    assert len(result["main_library"]) == 0
    assert len(result["external_libraries"]) == 2


def test_get_library_id(library_detector):
    """Test extracting library ID from photo."""
    photo = {"id": "p1", "libraryId": "test-lib-id"}
    assert library_detector.get_library_id(photo) == "test-lib-id"


def test_get_library_id_missing(library_detector):
    """Test getting library ID when not present."""
    photo = {"id": "p1"}
    assert library_detector.get_library_id(photo) is None


# ============================================================================
# XMP Writer Tests
# ============================================================================


def test_xmp_writer_create_file(xmp_writer, temp_xmp_dir):
    """Test creating an XMP file."""
    success, msg = xmp_writer.create_xmp_file(
        "IMG_001.jpg", latitude=46.3999, longitude=12.0616
    )

    assert success is True
    assert "IMG_001.jpg.xmp" in msg
    assert (temp_xmp_dir / "IMG_001.jpg.xmp").exists()


def test_xmp_file_content(xmp_writer, temp_xmp_dir):
    """Test XMP file contains correct GPS coordinates."""
    xmp_writer.create_xmp_file("IMG_001.jpg", latitude=46.3999, longitude=12.0616)

    xmp_file = temp_xmp_dir / "IMG_001.jpg.xmp"
    content = xmp_file.read_text()

    assert "46.3999" in content
    assert "12.0616" in content
    assert "exif:GPSLatitude" in content
    assert "exif:GPSLongitude" in content


def test_xmp_file_negative_coordinates(xmp_writer, temp_xmp_dir):
    """Test XMP file with negative coordinates (Southern/Western hemisphere)."""
    xmp_writer.create_xmp_file("IMG_002.jpg", latitude=-33.8688, longitude=-151.2093)

    xmp_file = temp_xmp_dir / "IMG_002.jpg.xmp"
    content = xmp_file.read_text()

    assert "33.8688" in content  # Absolute value
    assert "151.2093" in content  # Absolute value
    assert "S" in content  # South latitude reference
    assert "W" in content  # West longitude reference


def test_xmp_file_with_photo_id(xmp_writer, temp_xmp_dir):
    """Test XMP file includes photo ID reference."""
    photo_id = "550e8400-e29b-41d4-a716-446655440000"
    xmp_writer.create_xmp_file(
        "IMG_003.jpg",
        latitude=40.7128,
        longitude=-74.0060,
        photo_id=photo_id,
    )

    xmp_file = temp_xmp_dir / "IMG_003.jpg.xmp"
    content = xmp_file.read_text()

    assert photo_id in content


def test_xmp_invalid_latitude(xmp_writer):
    """Test XMP writer rejects invalid latitude."""
    success, msg = xmp_writer.create_xmp_file("IMG_004.jpg", latitude=95.0, longitude=12.0)

    assert success is False
    assert "Invalid coordinates" in msg


def test_xmp_invalid_longitude(xmp_writer):
    """Test XMP writer rejects invalid longitude."""
    success, msg = xmp_writer.create_xmp_file("IMG_005.jpg", latitude=40.0, longitude=185.0)

    assert success is False
    assert "Invalid coordinates" in msg


def test_xmp_boundary_coordinates(xmp_writer, temp_xmp_dir):
    """Test XMP writer accepts boundary coordinates."""
    # North Pole
    success, _ = xmp_writer.create_xmp_file("IMG_north.jpg", latitude=90.0, longitude=0.0)
    assert success is True

    # South Pole
    success, _ = xmp_writer.create_xmp_file("IMG_south.jpg", latitude=-90.0, longitude=0.0)
    assert success is True

    # International Date Line
    success, _ = xmp_writer.create_xmp_file("IMG_dateline.jpg", latitude=0.0, longitude=180.0)
    assert success is True


def test_xmp_list_files(xmp_writer, temp_xmp_dir):
    """Test listing created XMP files."""
    xmp_writer.create_xmp_file("IMG_001.jpg", 40.7128, -74.0060)
    xmp_writer.create_xmp_file("IMG_002.jpg", 51.5074, -0.1278)
    xmp_writer.create_xmp_file("IMG_003.jpg", 48.8566, 2.3522)

    files = xmp_writer.list_xmp_files()

    assert len(files) == 3
    assert "IMG_001.jpg.xmp" in files
    assert "IMG_002.jpg.xmp" in files
    assert "IMG_003.jpg.xmp" in files


def test_xmp_delete_file(xmp_writer, temp_xmp_dir):
    """Test deleting an XMP file."""
    xmp_writer.create_xmp_file("IMG_001.jpg", 40.7128, -74.0060)
    assert (temp_xmp_dir / "IMG_001.jpg.xmp").exists()

    success, msg = xmp_writer.delete_xmp_file("IMG_001.jpg")

    assert success is True
    assert not (temp_xmp_dir / "IMG_001.jpg.xmp").exists()


def test_xmp_delete_nonexistent_file(xmp_writer):
    """Test deleting a nonexistent XMP file."""
    success, msg = xmp_writer.delete_xmp_file("IMG_nonexistent.jpg")

    assert success is False
    assert "not found" in msg


def test_xmp_directory_creation(temp_xmp_dir, logger):
    """Test XMP writer creates output directory."""
    nested_dir = temp_xmp_dir / "nested" / "path"
    xmp_writer = XMPWriter(output_dir=nested_dir, logger=logger)

    success, _ = xmp_writer.create_xmp_file("IMG_001.jpg", 40.7128, -74.0060)

    assert success is True
    assert nested_dir.exists()


def test_xmp_format_is_valid_xml(xmp_writer, temp_xmp_dir):
    """Test that generated XMP is valid XML."""
    xmp_writer.create_xmp_file("IMG_001.jpg", 40.7128, -74.0060)

    xmp_file = temp_xmp_dir / "IMG_001.jpg.xmp"
    content = xmp_file.read_text()

    # Check basic XML structure
    assert content.startswith("<?xml version=")
    assert "<x:xmpmeta" in content
    assert "<rdf:RDF" in content
    assert "</rdf:RDF>" in content
    assert "</x:xmpmeta>" in content
