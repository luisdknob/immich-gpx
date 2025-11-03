"""
High-level service API for immich-gpx-linker.

Provides a simple, clean interface for processing GPX files and matching photos.
This module decouples core logic from CLI and can be used as a library or in
microservices applications. Main classes:
    - ProcessResult: Data class containing results of a GPS matching operation
    - ImmichGPXService: High-level service for orchestrating the matching workflow

The service handles:
    - GPX file parsing and GPS point extraction
    - Querying Immich API for photos in matching time range
    - Matching photos to GPS points using distance/time thresholds
    - Categorizing matches by GPS status
    - Updating photo GPS coordinates

Usage examples:
    >>> service = ImmichGPXService('http://localhost:2283', 'api-key')
    >>> result = service.process_gpx_file('track.gpx')
    >>> print(f"Matched {result.matched_count} photos")
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config
from .errors import ConfigurationError, MatchingError
from .gpx_parser import GPXParser
from .gps_matcher import GPSMatcher
from .immich_client import ImmichAPI
from .validation import validate_match_object


class ProcessResult:
    """
    Encapsulates results from GPS file matching and photo query operation.
    
    Contains statistics and match data from a complete GPX-to-Immich matching workflow:
    - GPS points extracted from GPX file
    - Photos found in Immich database for matching time range
    - Successful matches between photos and GPS points
    - Categorization of matches by GPS status (with/without existing GPS)
    
    Attributes:
        matches (List[Dict]): List of matched photo-GPS point pairs
        gps_points_count (int): Total GPS points from GPX file
        photos_count (int): Total photos found in Immich time range
        matched_count (int): Number of successful photo-GPS matches
        with_gps_count (int): Photos in matches that already have GPS coordinates
        without_gps_count (int): Photos in matches with no existing GPS coordinates
        
    Example:
        >>> result = ProcessResult(matches=[...], gps_points_count=150, ...)
        >>> print(f"Efficiency: {result.matched_count}/{result.photos_count}")
    """
    
    def __init__(
        self,
        matches: List[Dict],
        gps_points_count: int,
        photos_count: int,
        matched_count: int,
        with_gps_count: int,
        without_gps_count: int,
    ) -> None:
        """
        Initialize process result with matching statistics.
        
        Args:
            matches: List of successful photo-GPS matches
            gps_points_count: Total GPS points from GPX file
            photos_count: Total photos found in Immich
            matched_count: Number of successful matches
            with_gps_count: Matches with existing GPS coordinates
            without_gps_count: Matches without existing GPS coordinates
            
        Returns:
            None
        """
        self.matches = matches
        self.gps_points_count = gps_points_count
        self.photos_count = photos_count
        self.matched_count = matched_count
        self.with_gps_count = with_gps_count
        self.without_gps_count = without_gps_count
    
    def __repr__(self) -> str:
        """Return string representation with matching statistics."""
        return (
            f"ProcessResult(gps_points={self.gps_points_count}, "
            f"photos={self.photos_count}, "
            f"matched={self.matched_count}, "
            f"with_gps={self.with_gps_count}, "
            f"without_gps={self.without_gps_count})"
        )


class ImmichGPXService:
    """
    High-level orchestration service for matching GPS data with Immich photos.
    
    Provides a clean, simple Python API for the complete GPS linking workflow:
    1. Parse GPX files to extract GPS points with timestamps
    2. Query Immich database for photos in matching time range
    3. Match photos to GPS points using distance and time thresholds
    4. Update photo GPS coordinates via Immich API
    
    Can be used as a library in Python applications or in microservices architectures.
    Handles all error cases, logging, and provides statistics on processing results.
    
    Attributes:
        url (str): Immich server URL
        api_key (str): API key for authentication
        immich (ImmichAPI): Low-level API client instance
        logger (logging.Logger): Logger for output
        
    Example:
        >>> service = ImmichGPXService('http://localhost:2283', 'api-key')
        >>> result = service.process_gpx_file('track.gpx')
        >>> print(f"Matched {result.matched_count} of {result.photos_count} photos")
    """
    
    def __init__(
        self,
        immich_url: str,
        immich_api_key: str,
        verify_ssl: bool = True,
        timeout: int = 10,
        threshold: float = 60,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the Immich GPS linking service.
        
        Args:
            immich_url: URL of the Immich server (e.g., 'http://localhost:2283')
            immich_api_key: API key for Immich authentication
            verify_ssl: Verify SSL certificates (default: True, disable for self-signed)
            timeout: API request timeout in seconds (default: 10)
            threshold: Time threshold in seconds for matching photos to GPS (default: 60)
            logger: Optional logger instance (defaults to 'immich_gpx')
            
        Returns:
            None
            
        Example:
            >>> service = ImmichGPXService(
            ...     'http://localhost:2283',
            ...     'abc123key',
            ...     verify_ssl=False,  # for self-signed certificates
            ...     timeout=20,
            ...     threshold=120
            ... )
        """
        self.immich_url = immich_url
        self.immich_api_key = immich_api_key
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.threshold = threshold
        self.logger = logger or logging.getLogger('immich_gpx')
        
        # Initialize API client
        self.immich_api = ImmichAPI(
            immich_url,
            immich_api_key,
            verify_ssl=verify_ssl,
            timeout=timeout,
            logger=self.logger
        )
        
        # Initialize matcher with time threshold
        self.matcher = GPSMatcher(threshold=threshold, logger=self.logger)
    
    def test_connection(self) -> bool:
        """
        Test connectivity and authentication to Immich server.
        
        Makes a lightweight test request to Immich API to verify:
        - Network connectivity (server is reachable)
        - API key is valid and has required permissions
        - Server is responding normally
        
        Returns:
            True if all connection tests pass
            
        Raises:
            ConnectionError: If server unreachable or network issues
            AuthenticationError: If API key invalid or insufficient permissions
            
        Example:
            >>> service = ImmichGPXService('http://localhost:2283', 'api-key')
            >>> try:
            ...     service.test_connection()
            ...     print("Immich server is ready")
            ... except (ConnectionError, AuthenticationError) as e:
            ...     print(f"Connection failed: {e}")
        """
        try:
            self.immich_api.test_connection()
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            raise
    
    def process_gpx_file(
        self,
        gpx_file: str,
        verbose: bool = False,
    ) -> ProcessResult:
        """
        Process GPX file and match GPS points with Immich photos.
        
        Complete workflow orchestration:
        1. Parses GPX file and extracts GPS points with timestamps
        2. Determines time range and adds 5-minute buffer on each side
        3. Queries Immich for photos taken in expanded time range
        4. Matches photos to GPS points using distance/time thresholds
        5. Categorizes matches by GPS status (already have GPS, or need GPS)
        
        Args:
            gpx_file: Path to GPX file to process
            verbose: Enable verbose logging of matching details (default: False)
            
        Returns:
            ProcessResult object containing:
                - matches: list of matched photo-GPS point dictionaries
                - gps_points_count: total GPS points from GPX
                - photos_count: total photos found in Immich
                - matched_count: successful matches
                - with_gps_count: matches for photos already having GPS
                - without_gps_count: matches for photos needing GPS
            
        Raises:
            ConfigurationError: If GPX file not found or has no timestamps
            GPXParsingError: If GPX file is invalid or corrupted
            ConnectionError: If Immich server unreachable
            MatchingError: If matching operation fails
            
        Example:
            >>> service = ImmichGPXService('http://localhost:2283', 'api-key')
            >>> result = service.process_gpx_file('track.gpx', verbose=True)
            >>> print(f"Matched {result.matched_count} photos")
            >>> for match in result.matches:
            ...     print(f"  {match['photo']['name']}: {match['distance_meters']}m away")
        """
        self.logger.info(f"Processing GPX file: {gpx_file}")
        
        # Validate GPX file exists
        gpx_path = Path(gpx_file)
        if not gpx_path.exists():
            raise ConfigurationError(f"GPX file not found: {gpx_file}")
        
        try:
            # Parse GPX file
            parser = GPXParser(gpx_file, logger=self.logger)
            gps_points = parser.parse()
            self.logger.info(f"Found {len(gps_points)} GPS points")
            
            # Get time range
            start_time, end_time = parser.get_time_range()
            if not start_time or not end_time:
                raise ConfigurationError("GPX file has no time information")
            
            # Add buffer to time range
            from datetime import timedelta
            before_buffer = timedelta(minutes=5)
            after_buffer = timedelta(minutes=5)
            start_time_query = start_time - before_buffer
            end_time_query = end_time + after_buffer
            
            # Query photos from Immich
            self.logger.info(f"Querying photos between {start_time_query} and {end_time_query}...")
            photos = self.immich_api.get_photos_in_range(start_time_query, end_time_query)
            self.logger.info(f"Found {len(photos)} photos in time range")
            
            # Match GPS with photos
            self.logger.info("Matching GPS points with photos...")
            matches = self.matcher.match_photos_to_points(
                gps_points, photos, verbose=verbose, logger=self.logger
            )
            self.logger.info(f"Found {len(matches)} matches")
            
            # Validate matches - basic structure check only
            valid_matches = []
            for match in matches:
                if isinstance(match, dict) and 'photo' in match and 'gps_point' in match:
                    valid_matches.append(match)
                else:
                    self.logger.debug(f"[VALIDATION] Skipping invalid match structure")
            
            # Categorize matches
            with_gps_count = sum(1 for m in valid_matches if m['photo'].get('latitude') is not None)
            without_gps_count = len(valid_matches) - with_gps_count
            
            result = ProcessResult(
                matches=valid_matches,
                gps_points_count=len(gps_points),
                photos_count=len(photos),
                matched_count=len(valid_matches),
                with_gps_count=with_gps_count,
                without_gps_count=without_gps_count
            )
            
            self.logger.info(f"Processing complete: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing GPX file: {e}")
            raise
    
    def update_photos(
        self,
        matches: List[Dict],
        mode: str = 'all'
    ) -> Dict:
        """
        Update photo GPS coordinates in Immich.
        
        Args:
            matches: List of matched results from process_gpx_file()
            mode: Update mode - 'all' or 'without-gps'
            
        Returns:
            Dictionary with update statistics:
                - updated_count: Number of photos updated
                - skipped_count: Number of photos skipped
                - failed_count: Number of failed updates
                - total: Total matches
                
        Raises:
            ValueError: If mode is invalid
        """
        if mode not in ['all', 'without-gps']:
            raise ValueError(f"Invalid update mode: {mode}. Must be 'all' or 'without-gps'")
        
        self.logger.info(f"Updating {len(matches)} photos in mode: {mode}")
        
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        
        for i, match in enumerate(matches, 1):
            photo = match['photo']
            gps = match['gps_point']
            photo_id = photo['id']
            
            # Skip photos with existing GPS if mode is 'without-gps'
            if mode == 'without-gps':
                lat = photo.get('latitude')
                lon = photo.get('longitude')
                if lat is not None and lon is not None:
                    self.logger.debug(
                        f"[SKIP] [{i}/{len(matches)}] {photo['name']} - "
                        f"Already has GPS: ({lat:.6f}, {lon:.6f})"
                    )
                    skipped_count += 1
                    continue
            
            try:
                # Update photo coordinates via API
                self.immich_api.update_photo_exif(
                    photo_id,
                    latitude=gps['latitude'],
                    longitude=gps['longitude']
                )
                self.logger.debug(
                    f"[OK] [{i}/{len(matches)}] {photo['name']} - "
                    f"Updated to ({gps['latitude']:.6f}, {gps['longitude']:.6f})"
                )
                updated_count += 1
                
            except Exception as e:
                self.logger.error(f"[FAIL] [{i}/{len(matches)}] {photo['name']} - {e}")
                failed_count += 1
        
        result = {
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'failed_count': failed_count,
            'total': len(matches)
        }
        
        self.logger.info(
            f"Update complete: {updated_count} updated, "
            f"{skipped_count} skipped, {failed_count} failed"
        )
        
        return result
