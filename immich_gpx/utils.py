"""
Utility functions for printing results and handling user interactions.
"""

import logging
from typing import Dict, List, Optional

import requests
from tqdm import tqdm

from .core.validation import validate_match_object


def categorize_matches(matches: List[Dict]) -> Dict[str, any]:
    """
    Categorize matched photos by GPS status.
    
    Separates matched photo-GPS pairs into two categories based on whether
    the photo already contains GPS coordinate data.
    
    Args:
        matches: List of matched photo-GPS pair dictionaries, each containing
                'photo' and 'gps' keys with coordinate and metadata information
        
    Returns:
        Dictionary containing:
            - 'all': All matches provided
            - 'with_gps': Matches where photo has existing GPS coordinates
            - 'without_gps': Matches where photo lacks GPS coordinates  
            - 'counts': Dictionary with total, with_gps, without_gps counts
    
    Examples:
        >>> matches = [{'photo': {'id': 'p1', 'latitude': 41.0}, 'gps': {...}}]
        >>> result = categorize_matches(matches)
        >>> result['counts']['with_gps']
        1
    """
    with_gps = []
    without_gps = []
    
    for match in matches:
        # Basic structure validation - must have photo key
        if not isinstance(match, dict) or 'photo' not in match:
            logger = logging.getLogger(__name__)
            logger.debug(f"[VALIDATION] Skipping invalid match structure")
            continue
        
        photo = match['photo']
        latitude = photo.get('latitude')
        longitude = photo.get('longitude')
        
        # Photo has GPS if both latitude and longitude are not None
        if latitude is not None and longitude is not None:
            with_gps.append(match)
        else:
            without_gps.append(match)
    
    return {
        'all': matches,
        'with_gps': with_gps,
        'without_gps': without_gps,
        'counts': {
            'total': len(matches),
            'with_gps': len(with_gps),
            'without_gps': len(without_gps)
        }
    }


def print_results(
    gps_points: List[Dict],
    photos: List[Dict],
    matches: List[Dict],
    immich_url: str = "",
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Pretty print GPS matching results to console and logger.
    
    Displays comprehensive matching summary including GPS point information,
    photos found, matches discovered, and provides a clickable link to view
    matches in the Immich web interface.
    
    Args:
        gps_points: List of GPS points extracted from GPX file
        photos: List of photos retrieved from Immich server
        matches: List of photo-GPS matches discovered
        immich_url: Immich server URL for constructing view links (optional)
        logger: Logger instance for output (defaults to 'immich-gpx')
    
    Returns:
        None
    
    Example:
        >>> print_results(gps_pts, immich_photos, matched_pairs, 
        ...               immich_url='http://localhost:2283')
    """
    if logger is None:
        logger = logging.getLogger('immich-gpx')
    
    logger.info("=" * 80)
    logger.info("IMMICH GPX - RESULTS")
    logger.info("=" * 80)
    logger.info("GPX Track Information:")
    logger.info(f"  • Total GPS points: {len(gps_points)}")
    if gps_points:
        start_time, end_time = None, None
        times = [p['time'] for p in gps_points if p['time']]
        if times:
            start_time, end_time = min(times), max(times)
            logger.info(f"  • Time range: {start_time} to {end_time}")
            logger.info(f"  • Duration: {end_time - start_time}")
    logger.info("Immich Photos:")
    logger.info(f"  • Total photos in time range: {len(photos)}")
    logger.info("Matched Results:")
    logger.info(f"  • Total matches: {len(matches)}")

    if matches:
        logger.info("-" * 80)
        for i, match in enumerate(matches, 1):
            photo = match['photo']
            gps = match['gps_point']
            distance = match['distance_meters']
            time_diff = match['time_difference_seconds']

            # Generate links
            osm_link = f"https://www.openstreetmap.org/?mlat={gps['latitude']}&mlon={gps['longitude']}&zoom=15"
            immich_link = f"{immich_url}/photos/{photo['id']}" if immich_url else ""

            logger.info(f"Match #{i}:")
            logger.info(f"  Photo: {photo['name']}")
            if immich_link:
                logger.info(f"  Immich: {immich_link}")
            if photo['latitude'] is not None and photo['longitude'] is not None:
                logger.info(f"  Photo location: ({photo['latitude']:.6f}, {photo['longitude']:.6f})")
            else:
                logger.info(f"  Photo location: (No EXIF GPS data)")
            logger.info(f"  Photo time: {photo['time']}")
            logger.info(f"  OpenStreetMap: {osm_link}")
            logger.info(f"  GPS point location: ({gps['latitude']:.6f}, {gps['longitude']:.6f})")
            logger.info(f"  GPS point time: {gps['time']}")
            logger.info(f"  Distance: {distance} meters")
            if time_diff:
                logger.info(f"  Time difference: {time_diff} seconds")
        logger.info("-" * 80)
    else:
        logger.info("No matches found. Try adjusting thresholds or check your data.")

    logger.info("=" * 80)


def prompt_update_mode(
    categorized: Dict[str, any],
    logger: logging.Logger,
) -> str:
    """
    Prompt user to select GPS update mode with validation and confirmation.
    
    Displays categorized match statistics and presents three options:
    1. Update all photos (replace existing GPS coordinates)
    2. Update only photos without GPS (preserve existing)
    3. Cancel operation
    
    Handles user input validation, confirmation prompts, and graceful cancellation
    via Ctrl+C or EOF signals.
    
    Args:
        categorized: Dictionary from categorize_matches() containing:
            - 'counts': dict with 'total', 'with_gps', 'without_gps' keys
            - 'matches': list of matched photo-GPS point dictionaries
        logger: Logger instance for informational and error output
        
    Returns:
        str: One of 'all', 'without-gps', or 'cancel' indicating selected mode
        
    Example:
        >>> categorized = categorize_matches(matches)
        >>> mode = prompt_update_mode(categorized, logger)
        >>> if mode == 'all':
        ...     update_all_photos(categorized['matches'], logger)
    """
    # Extract match count statistics
    counts = categorized['counts']
    
    # Display update options with formatted output
    logger.info("")
    logger.info("=" * 80)
    logger.info("GPS Update Options")
    logger.info("=" * 80)
    logger.info(f"Found {counts['total']} photo(s) with GPS matches:")
    
    if counts['with_gps'] > 0:
        logger.info(f"  ✓ {counts['with_gps']} photo(s) already have GPS coordinates")
    if counts['without_gps'] > 0:
        logger.info(f"  ✗ {counts['without_gps']} photo(s) have no GPS coordinates")
    
    logger.info("")
    logger.info("Update options:")
    logger.info(f"  [1] Update all {counts['total']} photos (replace existing GPS)")
    if counts['without_gps'] > 0:
        logger.info(f"  [2] Update only {counts['without_gps']} photos without GPS (preserve existing)")
    else:
        logger.info(f"  [2] Update only photos without GPS (no photos available)")
    logger.info("  [3] Cancel (no changes)")
    logger.info("")
    
    # Loop until valid choice with confirmation
    while True:
        try:
            choice = input("Your choice [1/2/3]: ").strip()
            
            if choice == '1':
                logger.info("Selected: Update all photos")
                confirm = input(f"This will update {counts['total']} photos. Continue? [y/N]: ").strip().lower()
                if confirm == 'y':
                    return 'all'
                else:
                    logger.info("Cancelled by user")
                    continue
                    
            elif choice == '2':
                if counts['without_gps'] == 0:
                    logger.warning("No photos without GPS to update!")
                    return 'cancel'
                logger.info(f"Selected: Update only {counts['without_gps']} photos without GPS")
                return 'without-gps'
                
            elif choice == '3':
                logger.info("Update cancelled by user")
                return 'cancel'
                
            else:
                logger.warning(f"Invalid choice: {choice}. Please enter 1, 2, or 3.")
                
        except EOFError:
            logger.info("\nInput cancelled (EOF)")
            return 'cancel'
        except KeyboardInterrupt:
            logger.info("\nInterrupted by user")
            return 'cancel'


def print_position_update_preview(
    matches: List[Dict],
    logger: logging.Logger,
) -> None:
    """
    Display a formatted preview of GPS coordinate updates to be applied.
    
    Shows current GPS coordinates (if available) and new coordinates from GPX matches
    for each photo. Helps user review changes before confirmation.
    
    Args:
        matches: List of matched photo-GPS point dictionaries containing:
            - 'photo': dict with 'id', 'name', 'latitude', 'longitude'
            - 'gps_point': dict with 'latitude', 'longitude'
        logger: Logger instance for preview output
        
    Returns:
        None
        
    Example:
        >>> matches = [{'photo': {...}, 'gps_point': {...}}]
        >>> print_position_update_preview(matches, logger)
    """
    logger.info("=" * 80)
    logger.info("UPDATING PHOTOS WITH GPS COORDINATES")
    logger.info("=" * 80)
    
    for i, match in enumerate(matches, 1):
        photo = match['photo']
        gps = match['gps_point']
        
        # Format current GPS info
        if photo['latitude'] is not None and photo['longitude'] is not None:
            current_gps = f"({photo['latitude']:.4f}, {photo['longitude']:.4f})"
        else:
            current_gps = "(no GPS)"
        
        # Format new GPS info
        new_gps = f"({gps['latitude']:.4f}, {gps['longitude']:.4f})"
        
        # Compact single-line format
        logger.info(f"{i:3}. {photo['name']:40} {current_gps:20} → {new_gps}")


def update_photo_positions(
    matches: List[Dict],
    immich_url: str,
    logger: logging.Logger,
    mode: str = 'all',
    api_key: str = None,
) -> Optional[List[Dict]]:
    """
    Update photo GPS coordinates in Immich via REST API.
    
    Applies GPS coordinates from matched GPX points to photos in Immich. Supports
    two update modes: update all photos (replacing existing GPS) or update only
    photos without GPS data (preserving existing coordinates).
    
    Requires IMMICH_API_KEY environment variable for authentication. Reports
    detailed success/failure statistics for each update attempt.
    
    Args:
        matches: List of matched photo-GPS point dictionaries containing:
            - 'photo': dict with 'id', 'name', 'latitude', 'longitude'
            - 'gps_point': dict with 'latitude', 'longitude'
        immich_url: Base URL of Immich server (e.g., 'http://localhost:2283')
        logger: Logger instance for output and error reporting
        mode: Update strategy - 'all' (replace all GPS) or 'without-gps' (preserve existing)
        
    Returns:
        List of updated matches if successful, None if API key missing or invalid mode
        
    Raises:
        Logs exceptions but returns None on critical errors (missing API key)
        
    Example:
        >>> os.environ['IMMICH_API_KEY'] = 'my-api-key'
        >>> matches = [{'photo': {...}, 'gps_point': {...}}]
        >>> result = update_photo_positions(matches, 'http://localhost:2283', logger)
        >>> if result:
        ...     print(f"Updated {len(result)} photos")
    """
    # Validate update mode parameter
    if mode not in ['all', 'without-gps']:
        logger.error(f"Invalid update mode: {mode}. Must be 'all' or 'without-gps'")
        return None
    
    logger.info("-" * 80)
    
    # Retrieve API key
    if not api_key:
        logger.error("Error: API key not provided")
        return None
    
    # Create authenticated session for API requests
    session = requests.Session()
    session.headers.update({'x-api-key': api_key})
    
    # Initialize update statistics counters
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    failed_photos = []
    
    # Process each matched photo with tqdm progress bar
    for match in tqdm(matches, desc="Updating photos", unit="photo", leave=True, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
        photo = match['photo']
        gps = match['gps_point']
        photo_id = photo['id']
        
        # Skip photos with existing GPS if mode is 'without-gps'
        if mode == 'without-gps':
            lat = photo.get('latitude')
            lon = photo.get('longitude')
            if lat is not None and lon is not None:
                skipped_count += 1
                continue
        
        try:
            # Update photo with new GPS coordinates using Immich API PUT endpoint
            url = f"{immich_url}/api/assets/{photo_id}"
            
            # Prepare GPS coordinate payload
            payload = {
                'latitude': gps['latitude'],
                'longitude': gps['longitude'],
            }
            
            # Submit API request with timeout protection
            response = session.put(url, json=payload, timeout=10)
            response.raise_for_status()
            
            updated_count += 1
            
        except requests.exceptions.RequestException as e:
            failed_photos.append({'name': photo['name'], 'error': str(e)})
            failed_count += 1
        except Exception as e:
            failed_photos.append({'name': photo['name'], 'error': str(e)})
            failed_count += 1
    
    # Log summary statistics
    logger.info("-" * 80)
    logger.info(f"Complete! ✓ {updated_count} updated | → {skipped_count} skipped | ✗ {failed_count} failed")
    
    # Show failed photos details only if there were failures
    if failed_count > 0:
        logger.info("-" * 80)
        logger.error("Failed updates:")
        for photo in failed_photos:
            logger.error(f"  • {photo['name']}: {photo['error']}")
    
    logger.info("=" * 80)
    
    return matches
