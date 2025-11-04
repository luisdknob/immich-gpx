"""
Immich API client for photo queries and GPS coordinate updates.

Handles connection testing, photo queries by date range, and GPS coordinate updates.
Uses API key authentication via 'x-api-key' header.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests
from tqdm import tqdm

from .errors import AuthenticationError, ConnectionError
from .validation import validate_photo_response
from immich_gpx.error_handling import UpdateResult
from immich_gpx.cache import APIResponseCache
from immich_gpx.rate_limiter import RateLimiter


class ImmichAPI:
    """
    REST API client for Immich photo management server.
    
    Handles authentication, connection management, and HTTP requests to Immich API.
    Provides methods for querying photos by date range, extracting EXIF GPS data,
    and updating photo metadata with GPS coordinates.
    
    Attributes:
        url (str): Base URL of Immich server (trailing slash removed)
        api_key (str): API key for authentication
        verbose (bool): Enable debug logging for requests
        verify_ssl (bool): Verify SSL certificates (disable for self-signed)
        timeout (int): Request timeout in seconds
        session (requests.Session): Persistent HTTP session with authentication
        logger (logging.Logger): Logger instance for output
        
    Example:
        >>> api = ImmichAPI('http://localhost:2283', 'your-api-key')
        >>> api.test_connection()
        >>> photos = api.get_photos_in_range(start_time, end_time)
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        verbose: bool = False,
        verify_ssl: bool = True,
        timeout: int = 10,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize Immich API client with connection parameters.
        
        Args:
            url: Base URL of Immich server (e.g., 'http://localhost:2283')
            api_key: API key for authentication (generate in Immich settings)
            verbose: Enable debug logging for API requests (default: False)
            verify_ssl: Verify SSL certificates (set False for self-signed, default: True)
            timeout: Request timeout in seconds (default: 10)
            logger: Optional logger instance (defaults to 'immich-gpx')
            
        Returns:
            None
            
        Example:
            >>> api = ImmichAPI('http://localhost:2283', 'abc123key')
            >>> api_with_custom = ImmichAPI('https://photos.example.com', 'key', 
            ...                              verify_ssl=False, timeout=20, logger=my_logger)
        """
        # Store connection parameters
        self.url = url.rstrip('/')  # Remove trailing slash for consistent URL building
        self.api_key = api_key
        self.verbose = verbose
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        
        # Set logger instance
        self.logger = logger or logging.getLogger('immich-gpx')
        
        # Log the URL being used (helps debug protocol issues)
        self.logger.debug(f"ImmichAPI initialized with URL: {self.url}")
        
        # Initialize HTTP session with authentication header
        self.session = requests.Session()
        self.session.headers.update({'x-api-key': api_key})
        self.session.verify = verify_ssl
        
        # Initialize production features
        self.response_cache = APIResponseCache(ttl_seconds=3600)  # Cache responses for 1 hour
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 req/min
        
        # Set logger instance
        self.logger = logger or logging.getLogger('immich-gpx')

    def _log(self, message: str) -> None:
        """
        Log debug message if verbose mode enabled.
        
        Args:
            message: Debug message to log
            
        Returns:
            None
        """
        if self.verbose:
            self.logger.debug(message)

    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with proper redirect handling.
        
        Detects and handles redirects by updating the base URL if a redirect
        is detected. This ensures that subsequent requests use the correct
        protocol (e.g., if server redirects HTTP -> HTTPS).
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            url: Full URL to request
            **kwargs: Additional arguments passed to session request
            
        Returns:
            requests.Response object
            
        Raises:
            requests.exceptions.RequestException: If request fails
        """
        # Make request with allow_redirects=True to follow redirects
        response = self.session.request(method, url, allow_redirects=True, **kwargs)
        
        # Check if a redirect occurred by examining response.history
        # response.history contains the list of Response objects from the history of the request
        if response.history:
            # A redirect occurred - the final URL might have a different protocol
            # Extract the new base URL from the final URL
            final_url = response.url
            
            # Parse the URL to get base (scheme + netloc)
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(final_url)
            new_base_url = urlunparse((parsed.scheme, parsed.netloc, '', '', '', ''))
            
            # If the protocol or host changed, update self.url
            if new_base_url != self.url.rstrip('/'):
                self.logger.debug(f"Redirect detected: {self.url} -> {new_base_url}")
                self.url = new_base_url
        
        return response

    def test_connection(self) -> bool:
        """
        Test connection to Immich API and verify authentication.
        
        Makes a test request to /api/server/version endpoint to verify:
        - Network connectivity to server
        - API key authentication
        - Server is responsive and running
        
        Returns:
            True if connection test successful
            
        Raises:
            ConnectionError: If server unreachable or network issues
            AuthenticationError: If API key invalid or insufficient permissions
            
        Example:
            >>> api = ImmichAPI('http://localhost:2283', 'api-key')
            >>> try:
            ...     api.test_connection()
            ...     print("Connected successfully")
            ... except ConnectionError as e:
            ...     print(f"Connection failed: {e}")
        """
        try:
            # Log connection attempt
            self.logger.debug(f"Testing connection to {self.url}")
            
            # Request server version (lightweight, read-only endpoint)
            self.rate_limiter.wait_if_needed()  # Respect rate limit
            response = self._make_request(
                'GET',
                f"{self.url}/api/server/version",
                timeout=self.timeout
            )
            
            # Check for authentication failure (401 Unauthorized)
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Check your IMMICH_API_KEY."
                )
            
            # Raise exception for other HTTP errors
            response.raise_for_status()
            
            # Log successful connection with version
            version_data = response.json()
            # Extract version from API response: {major, minor, patch}
            major = version_data.get('major', '?')
            minor = version_data.get('minor', '?')
            patch = version_data.get('patch', '?')
            version_string = f"{major}.{minor}.{patch}"
            self.logger.info(f"Connected to Immich server version: {version_string}")
            return True
            
        except requests.exceptions.Timeout:
            raise ConnectionError(
                f"Connection timeout after {self.timeout}s. Server may be down or unreachable."
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to {self.url}. Check URL and network connectivity."
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Connection failed: {e}")

    def get_photos_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict]:
        """
        Query Immich for all photos with EXIF data within a time range.
        
        Performs paginated search through Immich database for non-archived photos
        taken between start_time and end_time. Automatically handles pagination
        and fetches EXIF data (including GPS, timestamps, etc.) for each photo.
        
        Args:
            start_time: Start of time range (inclusive) as datetime object
            end_time: End of time range (inclusive) as datetime object
            
        Returns:
            List of photo dictionaries, each containing:
                - 'id': str, unique photo ID
                - 'fileCreatedAt': datetime, when file was created
                - 'exifInfo': dict, EXIF metadata including GPS (if available)
                - Other photo metadata fields
                
        Raises:
            RuntimeError: If API request fails or photo retrieval encounters errors
            
        Example:
            >>> from datetime import datetime, timedelta
            >>> api = ImmichAPI('http://localhost:2283', 'api-key')
            >>> start = datetime(2024, 1, 1)
            >>> end = start + timedelta(days=1)
            >>> photos = api.get_photos_in_range(start, end)
            >>> print(f"Found {len(photos)} photos")
        """
        # Log query parameters
        self._log(f"Fetching photos from {start_time} to {end_time}")

        # Check cache first
        cache_key = f"photos:{start_time.isoformat()}:{end_time.isoformat()}"
        cached_photos = self.response_cache.get(cache_key)
        if cached_photos is not None:
            self._log(f"Cache hit for {cache_key}, returning {len(cached_photos)} photos")
            return cached_photos

        all_photos = []
        skip = 0
        limit = 100  # Photos per page (Immich API limit)

        # Convert to ISO format strings (Immich v2 expects ISO date strings)
        # Replace timezone info with 'Z' for UTC (ISO 8601 format)
        start_iso = start_time.isoformat().replace('+00:00', 'Z')
        end_iso = end_time.isoformat().replace('+00:00', 'Z')

        try:
            # Paginate through all photos in time range
            while True:
                endpoint = f"{self.url}/api/search/metadata"
                
                # Build search query payload
                payload = {
                    'takenAfter': start_iso,      # Filter: photos after start time
                    'takenBefore': end_iso,       # Filter: photos before end time
                    'isArchived': False,          # Filter: exclude archived photos
                    'skip': skip,                 # Pagination: offset
                    'take': limit,                # Pagination: result limit
                }

                self._log(f"Querying {endpoint} with payload {payload}")
                self.rate_limiter.wait_if_needed()  # Respect rate limit
                response = self._make_request('POST', endpoint, json=payload, timeout=self.timeout)
                response.raise_for_status()

                # Parse response (API returns nested structure)
                data = response.json()
                assets_data = data.get('assets', {})
                assets_list = assets_data.get('items', []) if isinstance(assets_data, dict) else assets_data
                
                # Stop if no more results
                if not assets_list:
                    break

                # Accumulate all photos
                all_photos.extend(assets_list)
                self._log(f"Retrieved {len(assets_list)} photos, total: {len(all_photos)}")

                # Check if there are more pages to fetch
                if not assets_data.get('nextPage'):
                    break

                skip += limit

            # Fetch complete EXIF data for each photo
            self._log(f"Fetching EXIF data for {len(all_photos)} photos")
            photos_with_exif = []
            for photo in tqdm(all_photos, desc="Fetching EXIF data", unit="photo", leave=False, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
                asset_id = photo.get('id')
                if asset_id:
                    # Retrieve full asset data including EXIF
                    exif_data = self.get_photo_exif(asset_id)
                    if exif_data:
                        photo['exifInfo'] = exif_data
                    
                    # Validate photo structure after EXIF data is fetched
                    try:
                        validate_photo_response(photo)
                        photos_with_exif.append(photo)
                    except ValueError as e:
                        self._log(f"[VALIDATION] Skipping invalid photo: {e}")
                        continue

            # Cache the results
            self.response_cache.set(cache_key, photos_with_exif, ttl_seconds=3600)
            self._log(f"Cached {len(photos_with_exif)} photos for {cache_key}")
            
            return photos_with_exif

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse status: {e.response.status_code}"
                try:
                    error_msg += f"\nResponse body: {e.response.text}"
                except:
                    pass
            raise RuntimeError(f"Error fetching photos from Immich: {error_msg}")

        except Exception as e:
            raise RuntimeError(f"Error fetching EXIF data: {e}")

    def get_photo_exif(self, asset_id: str) -> Optional[Dict]:
        """
        Retrieve full EXIF data for a specific photo from Immich.
        
        Fetches complete asset details including EXIF metadata (GPS, timestamps,
        camera model, etc.). EXIF data is stored in the 'exifInfo' field.
        
        Args:
            asset_id: Unique Immich asset ID (UUID string)
            
        Returns:
            Dictionary containing EXIF metadata, or None if fetch fails. Typical keys:
                - 'latitude': float, GPS latitude (-90 to 90)
                - 'longitude': float, GPS longitude (-180 to 180)
                - 'exifImageWidth': int, image width in pixels
                - 'exifImageHeight': int, image height in pixels
                - 'make': str, camera manufacturer
                - 'model': str, camera model
                - 'dateTaken': datetime, photo timestamp
                
        Example:
            >>> api = ImmichAPI('http://localhost:2283', 'api-key')
            >>> exif = api.get_photo_exif('550e8400-e29b-41d4-a716-446655440000')
            >>> if exif:
            ...     print(f"GPS: {exif.get('latitude')}, {exif.get('longitude')}")
        """
        try:
            url = f"{self.url}/api/assets/{asset_id}"
            self._log(f"Fetching asset details for {asset_id}")
            self.rate_limiter.wait_if_needed()  # Respect rate limit
            response = self._make_request('GET', url, timeout=self.timeout)
            response.raise_for_status()
            asset = response.json()
            return asset.get('exifInfo')
        except requests.exceptions.RequestException as e:
            self._log(f"Error fetching asset data: {e}")
            return None
    
    def update_photo_exif(
        self,
        asset_id: str,
        latitude: float,
        longitude: float,
        **kwargs
    ) -> bool:
        """
        Update photo GPS coordinates (EXIF data).
        
        Args:
            asset_id: The asset ID of the photo
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            **kwargs: Additional EXIF fields to update
            
        Returns:
            True if update successful
            
        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        try:
            url = f"{self.url}/api/assets/{asset_id}"
            payload = {
                'latitude': latitude,
                'longitude': longitude,
                **kwargs
            }
            self._log(f"Updating EXIF for {asset_id}: ({latitude}, {longitude})")
            self.rate_limiter.wait_if_needed()  # Respect rate limit
            response = self._make_request('PUT', url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            self._log(f"Error updating asset EXIF: {e}")
            raise

    def batch_update_photos(
        self,
        matches: List[Dict],
        dry_run: bool = False,
    ) -> UpdateResult:
        """
        Update multiple photos with GPS coordinates in batch.
        
        Continues processing on individual failures, providing partial success.
        Useful for updating many photos when some may fail due to permissions,
        concurrent updates, or temporary errors.
        
        Args:
            matches: List of matched photo-GPS point dictionaries, each containing:
                    - 'photo': {'id': str, 'originalFileName': str}
                    - 'gps_point': {'latitude': float, 'longitude': float}
            dry_run: If True, log what would be updated without actual updates
            
        Returns:
            UpdateResult with counts of successful/failed/skipped updates
            
        Example:
            >>> matches = [
            ...     {
            ...         'photo': {'id': 'abc123', 'originalFileName': 'photo.jpg'},
            ...         'gps_point': {'latitude': 40.7128, 'longitude': -74.0060}
            ...     },
            ...     ...
            ... ]
            >>> result = api.batch_update_photos(matches, dry_run=False)
            >>> print(result.summary())
            'Processed 100 photos: 95 updated, 3 failed, 2 skipped (95.0% success rate)'
        """
        result = UpdateResult()
        
        for match in matches:
            photo = match.get('photo', {})
            photo_id = photo.get('id', 'unknown')
            photo_name = photo.get('originalFileName', 'unknown')
            
            try:
                gps_point = match.get('gps_point', {})
                latitude = gps_point.get('latitude')
                longitude = gps_point.get('longitude')
                
                if dry_run:
                    self._log(f"[DRY-RUN] Would update {photo_name} with GPS: ({latitude}, {longitude})")
                    result.skipped += 1
                else:
                    # Update the photo
                    self.update_photo_exif(photo_id, latitude, longitude)
                    self.logger.info(f"Updated {photo_name} with GPS: ({latitude}, {longitude})")
                    result.successful += 1
            
            except Exception as e:
                # Log error but continue with next photo
                self.logger.error(
                    f"Failed to update {photo_name} (ID: {photo_id}): {e}",
                    exc_info=False,
                )
                result.add_error(photo_id, e)
        
        return result
