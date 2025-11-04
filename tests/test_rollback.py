"""
Tests for rollback functionality.

Tests the RollbackManager and RollbackSession classes for managing
GPS coordinate update rollback data.
"""

import json
import logging
import pytest
from pathlib import Path
from datetime import datetime
from immich_gpx.rollback import RollbackManager, RollbackSession


@pytest.fixture
def temp_rollback_dir(tmp_path):
    """Create a temporary rollback directory."""
    rollback_dir = tmp_path / "rollback"
    return rollback_dir


@pytest.fixture
def rollback_manager(temp_rollback_dir):
    """Create a RollbackManager instance with temp directory."""
    logger = logging.getLogger("test")
    return RollbackManager(rollback_dir=temp_rollback_dir, logger=logger)


def test_create_rollback_session(rollback_manager):
    """Test creating a new rollback session."""
    session = rollback_manager.create_session(gpx_file="track.gpx", update_mode="all")

    assert session is not None
    assert session.gpx_file == "track.gpx"
    assert session.update_mode == "all"
    assert len(session.session_id) > 0
    assert session.timestamp is not None


def test_add_photo_to_session():
    """Test adding a photo to rollback session."""
    session = RollbackSession(
        session_id="test_session",
        gpx_file="track.gpx",
        rollback_dir=Path("/tmp"),
    )

    session.add_photo(
        photo_id="photo_123",
        filename="IMG_001.jpg",
        original_lat=41.0,
        original_lon=-71.0,
        new_lat=41.1,
        new_lon=-71.1,
    )

    assert len(session.photos) == 1
    assert session.photos[0]["id"] == "photo_123"
    assert session.photos[0]["filename"] == "IMG_001.jpg"
    assert session.photos[0]["original_latitude"] == 41.0
    assert session.photos[0]["new_latitude"] == 41.1
    assert session.photos[0]["had_gps"] is True


def test_add_photo_without_original_gps():
    """Test adding a photo that had no original GPS."""
    session = RollbackSession(
        session_id="test_session",
        gpx_file="track.gpx",
        rollback_dir=Path("/tmp"),
    )

    session.add_photo(
        photo_id="photo_456",
        filename="IMG_002.jpg",
        original_lat=None,
        original_lon=None,
        new_lat=41.1,
        new_lon=-71.1,
    )

    assert len(session.photos) == 1
    assert session.photos[0]["had_gps"] is False
    assert session.photos[0]["original_latitude"] is None


def test_save_rollback_session(rollback_manager, temp_rollback_dir):
    """Test saving rollback session to file."""
    session = rollback_manager.create_session(gpx_file="track.gpx", update_mode="all")

    session.add_photo(
        photo_id="photo_123",
        filename="IMG_001.jpg",
        original_lat=41.0,
        original_lon=-71.0,
        new_lat=41.1,
        new_lon=-71.1,
    )

    filepath = session.save()

    assert filepath.exists()
    assert filepath.parent == temp_rollback_dir
    assert filepath.name.startswith("rollback_")
    assert filepath.suffix == ".json"

    # Verify file contents
    with open(filepath, "r") as f:
        data = json.load(f)

    assert data["gpx_file"] == "track.gpx"
    assert data["update_mode"] == "all"
    assert len(data["photos"]) == 1
    assert data["total_updated"] == 1


def test_rollback_directory_created_automatically(rollback_manager, temp_rollback_dir):
    """Test that rollback directory is created if it doesn't exist."""
    assert not temp_rollback_dir.exists()

    session = rollback_manager.create_session(gpx_file="track.gpx")
    session.save()

    assert temp_rollback_dir.exists()
    assert temp_rollback_dir.is_dir()


def test_list_rollback_sessions(rollback_manager):
    """Test listing all available rollback sessions."""
    # Create multiple sessions
    session1 = rollback_manager.create_session(gpx_file="track1.gpx")
    session1.add_photo("p1", "img1.jpg", 41.0, -71.0, 41.1, -71.1)
    session1.save()

    session2 = rollback_manager.create_session(gpx_file="track2.gpx")
    session2.add_photo("p2", "img2.jpg", 42.0, -72.0, 42.1, -72.1)
    session2.add_photo("p3", "img3.jpg", 42.0, -72.0, 42.1, -72.1)
    session2.save()

    sessions = rollback_manager.list_sessions()

    assert len(sessions) == 2
    assert sessions[0]["gpx_file"] in ["track1.gpx", "track2.gpx"]
    assert sessions[1]["gpx_file"] in ["track1.gpx", "track2.gpx"]
    assert sessions[0]["total_updated"] in [1, 2]
    assert sessions[1]["total_updated"] in [1, 2]


def test_get_session_by_id(rollback_manager):
    """Test retrieving a specific session by ID."""
    session = rollback_manager.create_session(gpx_file="track.gpx", update_mode="all")
    session.add_photo("p1", "img1.jpg", 41.0, -71.0, 41.1, -71.1)
    session.save()

    retrieved = rollback_manager.get_session(session.session_id)

    assert retrieved is not None
    assert retrieved["session_id"] == session.session_id
    assert retrieved["gpx_file"] == "track.gpx"
    assert len(retrieved["photos"]) == 1


def test_get_latest_session(rollback_manager):
    """Test retrieving the latest session with 'latest' keyword."""
    session1 = rollback_manager.create_session(gpx_file="track1.gpx")
    session1.add_photo("p1", "img1.jpg", 41.0, -71.0, 41.1, -71.1)
    session1.save()

    session2 = rollback_manager.create_session(gpx_file="track2.gpx")
    session2.add_photo("p2", "img2.jpg", 42.0, -72.0, 42.1, -72.1)
    session2.save()

    latest = rollback_manager.get_session("latest")

    assert latest is not None
    # Latest should be one of the two sessions we created
    assert latest["gpx_file"] in ["track1.gpx", "track2.gpx"]


def test_get_nonexistent_session(rollback_manager):
    """Test retrieving a nonexistent session returns None."""
    result = rollback_manager.get_session("nonexistent_id")
    assert result is None


def test_cleanup_old_sessions(rollback_manager):
    """Test cleanup removes old sessions keeping only recent ones."""
    # Create 15 sessions
    for i in range(15):
        session = rollback_manager.create_session(gpx_file=f"track{i}.gpx")
        session.add_photo(f"p{i}", f"img{i}.jpg", 41.0, -71.0, 41.1, -71.1)
        session.save()

    # Verify all 15 exist
    sessions_before = rollback_manager.list_sessions()
    assert len(sessions_before) == 15

    # Cleanup, keeping only 10
    deleted = rollback_manager.cleanup_old_sessions(keep_count=10)

    assert deleted == 5

    # Verify only 10 remain
    sessions_after = rollback_manager.list_sessions()
    assert len(sessions_after) == 10


def test_session_to_dict():
    """Test converting session to dictionary."""
    session = RollbackSession(
        session_id="test_123",
        gpx_file="track.gpx",
        update_mode="prompt",
        rollback_dir=Path("/tmp"),
    )

    session.add_photo("p1", "img1.jpg", 41.0, -71.0, 41.1, -71.1)
    session.add_photo("p2", "img2.jpg", None, None, 42.0, -72.0)

    data = session.to_dict()

    assert data["session_id"] == "test_123"
    assert data["gpx_file"] == "track.gpx"
    assert data["update_mode"] == "prompt"
    assert data["total_updated"] == 2
    assert len(data["photos"]) == 2


def test_empty_session_list(rollback_manager):
    """Test listing sessions when none exist."""
    sessions = rollback_manager.list_sessions()
    assert sessions == []


def test_cleanup_with_no_sessions(rollback_manager):
    """Test cleanup when no sessions exist."""
    deleted = rollback_manager.cleanup_old_sessions(keep_count=10)
    assert deleted == 0


def test_rollback_file_json_format(temp_rollback_dir):
    """Test that rollback file has valid JSON format."""
    session = RollbackSession(
        session_id="test_format",
        gpx_file="track.gpx",
        update_mode="all",
        rollback_dir=temp_rollback_dir,
    )

    session.add_photo("p1", "img.jpg", 41.0, -71.0, 41.5, -71.5)
    filepath = session.save()

    # Verify valid JSON
    with open(filepath, "r") as f:
        data = json.load(f)

    # Verify structure
    assert "session_id" in data
    assert "timestamp" in data
    assert "gpx_file" in data
    assert "update_mode" in data
    assert "photos" in data
    assert "total_updated" in data

    assert isinstance(data["photos"], list)
    assert isinstance(data["total_updated"], int)
