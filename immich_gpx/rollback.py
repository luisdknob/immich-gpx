"""
Rollback management for GPS coordinate updates.

Stores backup data before updates and restores original coordinates on demand.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Callable
from uuid import uuid4

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class RollbackSession:
    """Represents a single rollback session."""

    def __init__(
        self,
        session_id: str,
        gpx_file: str,
        update_mode: str = "all",
        rollback_dir: Path = None,
    ):
        """
        Initialize a rollback session.

        Args:
            session_id: Unique session identifier
            gpx_file: Name of GPX file used
            update_mode: Mode used for update (all, without-gps, prompt)
            rollback_dir: Directory to store rollback data
        """
        self.session_id = session_id
        self.gpx_file = gpx_file
        self.update_mode = update_mode
        self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.photos = []
        self.rollback_dir = rollback_dir or Path("./rollback")

    def add_photo(
        self,
        photo_id: str,
        filename: str,
        original_lat: Optional[float],
        original_lon: Optional[float],
        new_lat: float,
        new_lon: float,
    ) -> None:
        """
        Record a photo update for potential rollback.

        Args:
            photo_id: Immich photo ID
            filename: Photo filename
            original_lat: Original latitude (may be None)
            original_lon: Original longitude (may be None)
            new_lat: New latitude being set
            new_lon: New longitude being set
        """
        self.photos.append(
            {
                "id": photo_id,
                "filename": filename,
                "original_latitude": original_lat,
                "original_longitude": original_lon,
                "new_latitude": new_lat,
                "new_longitude": new_lon,
                "had_gps": original_lat is not None and original_lon is not None,
            }
        )

    def to_dict(self) -> Dict:
        """Convert session to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "gpx_file": self.gpx_file,
            "update_mode": self.update_mode,
            "photos": self.photos,
            "total_updated": len(self.photos),
        }

    def save(self) -> Path:
        """
        Save rollback session to JSON file.

        Returns:
            Path to saved rollback file
        """
        # Create rollback directory if it doesn't exist
        self.rollback_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp and session ID
        filename = f"rollback_{self.session_id}.json"
        filepath = self.rollback_dir / filename

        # Write rollback data
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath


class RollbackManager:
    """Manages rollback sessions and operations."""

    def __init__(
        self,
        rollback_dir: Path = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize rollback manager.

        Args:
            rollback_dir: Directory for storing rollback data
            logger: Logger instance
        """
        self.rollback_dir = Path(rollback_dir) if rollback_dir else Path("./rollback")
        self.logger = logger or logging.getLogger("immich-gpx")

    def create_session(self, gpx_file: str, update_mode: str = "all") -> RollbackSession:
        """
        Create a new rollback session.

        Args:
            gpx_file: Name of GPX file being used
            update_mode: Update mode (all, without-gps, prompt)

        Returns:
            New RollbackSession instance
        """
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + str(uuid4())[:8]
        return RollbackSession(
            session_id=session_id,
            gpx_file=gpx_file,
            update_mode=update_mode,
            rollback_dir=self.rollback_dir,
        )

    def list_sessions(self) -> List[Dict]:
        """
        List all available rollback sessions.

        Returns:
            List of session information dicts, sorted by timestamp (newest first)
        """
        if not self.rollback_dir.exists():
            return []

        sessions = []
        for filepath in sorted(self.rollback_dir.glob("rollback_*.json"), reverse=True):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    sessions.append(
                        {
                            "session_id": data.get("session_id"),
                            "timestamp": data.get("timestamp"),
                            "gpx_file": data.get("gpx_file"),
                            "total_updated": data.get("total_updated", 0),
                            "filepath": filepath,
                        }
                    )
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to read rollback file {filepath}: {e}")
                continue

        return sessions

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Load a specific rollback session by ID.

        Args:
            session_id: Session ID to load

        Returns:
            Session data dict or None if not found
        """
        if session_id == "latest":
            sessions = self.list_sessions()
            if not sessions:
                return None
            filepath = sessions[0]["filepath"]
        else:
            filepath = self.rollback_dir / f"rollback_{session_id}.json"

        if not filepath.exists():
            return None

        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load rollback session {session_id}: {e}")
            return None

    def cleanup_old_sessions(self, keep_count: int = 10) -> int:
        """
        Delete old rollback sessions, keeping only the most recent N.

        Args:
            keep_count: Number of recent sessions to keep

        Returns:
            Number of sessions deleted
        """
        if not self.rollback_dir.exists():
            return 0

        sessions = list(sorted(self.rollback_dir.glob("rollback_*.json"), reverse=True))
        deleted_count = 0

        for filepath in sessions[keep_count:]:
            try:
                filepath.unlink()
                deleted_count += 1
                self.logger.debug(f"Deleted old rollback file: {filepath.name}")
            except OSError as e:
                self.logger.warning(f"Failed to delete rollback file {filepath}: {e}")

        return deleted_count

    def create_progress_iterator(
        self,
        items: List,
        description: str = "Processing",
        disable: bool = False,
    ) -> Callable:
        """
        Create a progress iterator for processing items.

        Args:
            items: List of items to iterate
            description: Progress bar description
            disable: Disable progress bar (e.g., for non-interactive environments)

        Returns:
            Progress iterator (tqdm or plain list)
        """
        if not disable and TQDM_AVAILABLE:
            return tqdm(items, desc=description, unit="photo")
        return items

