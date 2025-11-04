"""
External library detection for Immich photos.

Detects which photos belong to external (read-only) libraries versus the
main Immich library, so they can be handled appropriately during updates.

Classes:
    LibraryDetector: Detect and categorize photos by library type
    LibraryInfo: Information about a library
    
External Libraries:
    - Read-only collections mounted from external sources
    - Cannot be updated via Immich API
    - Require XMP sidecar files for GPS coordinate updates
    - Have distinct libraryId field in photo metadata
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LibraryInfo:
    """Information about an Immich library."""

    library_id: str
    is_external: bool
    name: Optional[str] = None
    path: Optional[str] = None

    def __str__(self) -> str:
        return f"Library {self.library_id} (external={self.is_external})"


class LibraryDetector:
    """Detects external vs. main library photos from Immich."""

    # Main library UUID (standard Immich library)
    MAIN_LIBRARY_ID = "00000000-0000-0000-0000-000000000000"

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize library detector.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger("immich-gpx")
        self.library_cache: Dict[str, LibraryInfo] = {}

    def is_external_library(self, photo: Dict) -> bool:
        """
        Check if a photo belongs to an external library.

        Args:
            photo: Photo dict from Immich API with 'libraryId' field

        Returns:
            True if photo is in external library, False if in main library
        """
        library_id = photo.get("libraryId")

        if not library_id:
            # No library ID = main library (shouldn't happen in modern Immich)
            return False

        # Main library is writable, any other library is external/read-only
        return library_id != self.MAIN_LIBRARY_ID

    def categorize_photos(
        self, photos: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Categorize photos by library type.

        Args:
            photos: List of photo dicts from Immich API

        Returns:
            Dict with keys:
                - 'main_library': List of photos in main library (API updatable)
                - 'external_libraries': List of photos in external libraries (XMP needed)
                - 'counts': Dict with counts for each category
        """
        main_library = []
        external_libraries = []

        for photo in photos:
            if self.is_external_library(photo):
                external_libraries.append(photo)
            else:
                main_library.append(photo)

        return {
            "main_library": main_library,
            "external_libraries": external_libraries,
            "counts": {
                "main": len(main_library),
                "external": len(external_libraries),
                "total": len(photos),
            },
        }

    def get_library_id(self, photo: Dict) -> Optional[str]:
        """
        Get library ID from photo.

        Args:
            photo: Photo dict from Immich API

        Returns:
            Library ID or None
        """
        return photo.get("libraryId")

    def log_categorization(self, categorized: Dict) -> None:
        """Log categorization summary."""
        counts = categorized["counts"]
        self.logger.info(f"Photo library categorization:")
        self.logger.info(f"  Main library (API updatable): {counts['main']}")
        self.logger.info(f"  External libraries (XMP): {counts['external']}")
        self.logger.info(f"  Total: {counts['total']}")
