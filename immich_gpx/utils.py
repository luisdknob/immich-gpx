"""
Utility functions for printing results and handling user interactions.
"""

import logging
import os
import time
from typing import Dict, List, Optional

import requests
from tqdm import tqdm

from .core.validation import validate_match_object
from .xmp_writer import XMPWriter


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
            if distance is not None:
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
    rollback_session = None,
    enable_xmp: bool = False,
) -> Optional[List[Dict]]:
    """
    Update photo GPS coordinates in Immich via REST API.
    
    Applies GPS coordinates from matched GPX points to photos in Immich. Supports
    two update modes: update all photos (replacing existing GPS) or update only
    photos without GPS data (preserving existing coordinates).

    If rollback_session provided, captures original coordinates before update
    for potential rollback.
    
    Requires IMMICH_API_KEY environment variable for authentication. Reports
    detailed success/failure statistics for each update attempt.
    
    Args:
        matches: List of matched photo-GPS point dictionaries containing:
            - 'photo': dict with 'id', 'name', 'latitude', 'longitude'
            - 'gps_point': dict with 'latitude', 'longitude'
        immich_url: Base URL of Immich server (e.g., 'http://localhost:2283')
        logger: Logger instance for output and error reporting
        mode: Update strategy - 'all' (replace all GPS) or 'without-gps' (preserve existing)
        api_key: API key for authentication
        rollback_session: RollbackSession object to capture update history
        enable_xmp: Create XMP sidecar files for API failures (external libraries)
        
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
    xmp_count = 0
    failed_photos = []
    api_failed_photos = []  # Photos that failed API but might work with XMP
    
    # Initialize XMP writer if enabled
    xmp_writer = None
    if enable_xmp:
        xmp_writer = XMPWriter(logger=logger)
    
    # Update all photos via API
    logger.info("Updating photos via API")
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
            # Capture original coordinates for rollback if enabled
            if rollback_session:
                rollback_session.add_photo(
                    photo_id=photo_id,
                    filename=photo['name'],
                    original_lat=photo.get('latitude'),
                    original_lon=photo.get('longitude'),
                    new_lat=gps['latitude'],
                    new_lon=gps['longitude'],
                )
            
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
            # Store failed photo info for potential XMP handling
            api_failed_photos.append({
                'photo': photo,
                'gps': gps,
                'error': str(e)
            })
            failed_count += 1
        except Exception as e:
            api_failed_photos.append({
                'photo': photo,
                'gps': gps,
                'error': str(e)
            })
            failed_count += 1
    
    # Verify updates by re-fetching photo metadata
    logger.info("-" * 80)
    logger.info("Verify if updates were persisted")
    verified_count = 0
    verified_failed = []

    for match in tqdm(matches, desc="Verifying updates", unit="photo", leave=True, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
        photo = match['photo']
        gps = match['gps_point']
        
        # Skip if we already know it failed in Phase 1
        if any(item['photo']['id'] == photo['id'] for item in api_failed_photos):
            continue
        
        # Skip if mode is without-gps and photo already had GPS
        if mode == 'without-gps':
            lat = photo.get('latitude')
            lon = photo.get('longitude')
            if lat is not None and lon is not None:
                continue
        
        try:
            # Re-fetch photo metadata to verify coordinates were actually updated
            url = f"{immich_url}/api/assets/{photo['id']}"
            response = session.get(url, timeout=10)
            response.raise_for_status()
            updated_photo = response.json()
            
            # Check if coordinates match what we set
            new_lat = updated_photo.get('exifInfo', {}).get('latitude')
            new_lon = updated_photo.get('exifInfo', {}).get('longitude')
            
            if new_lat == gps['latitude'] and new_lon == gps['longitude']:
                # Verification successful - coordinates actually changed!
                verified_count += 1
            else:
                # Verification FAILED - coordinates didn't change (silent failure!)
                logger.debug(f"Verification failed for {photo['name']}: expected ({gps['latitude']}, {gps['longitude']}), got ({new_lat}, {new_lon})")
                verified_failed.append({
                    'photo': photo,
                    'gps': gps,
                    'error': 'Coordinates not updated (read-only or external library)'
                })
        except Exception as e:
            logger.debug(f"Failed to verify {photo['name']}: {e}")
            verified_failed.append({
                'photo': photo,
                'gps': gps,
                'error': f"Verification error: {str(e)}"
            })
    
    # Combine all failed photos (API failures + verification failures)
    all_failed = api_failed_photos + verified_failed
    
    # Log summary statistics with detailed breakdown
    logger.info("-" * 80)
    api_fail_count = len(api_failed_photos)
    verify_fail_count = len(verified_failed)
    
    # Create detailed summary
    summary_parts = [f"Complete!"]
    summary_parts.append(f"✓ {verified_count} verified")
    if skipped_count > 0:
        summary_parts.append(f"→ {skipped_count} skipped")
    if api_fail_count > 0:
        summary_parts.append(f"✗ {api_fail_count} failed (API)")
    if verify_fail_count > 0:
        summary_parts.append(f"⚠ {verify_fail_count} not persisted (read-only)")
    
    logger.info(" | ".join(summary_parts))
    
    # Handle unverified/failed photos
    if all_failed:
        logger.info("-" * 80)
        logger.error(f"⚠ {len(all_failed)} photo(s) could not be updated (read-only/external library)")
        
        if not enable_xmp:
            # XMP not enabled: just show error and suggestion
            logger.error("\nThese photos might be from read-only or external libraries.")
            logger.error("To create XMP sidecar files for these photos, use: --enable-xmp")
            logger.info("\nFailed photos:")
            for item in all_failed:
                logger.error(f"  ✗ {item['photo']['name']}: {item['error']}")
        else:
            # XMP enabled: run the full pipeline
            logger.info("-" * 80)
            logger.info("Creating XMP sidecar files for unverified photos...")
            
            xmp_writer = XMPWriter(logger=logger)
            xmp_created = 0
            xmp_failed = []
            
            for item in all_failed:
                photo = item['photo']
                gps = item['gps']
                try:
                    xmp_file = xmp_writer.write_xmp_file(
                        photo_path=photo['name'],
                        latitude=gps['latitude'],
                        longitude=gps['longitude']
                    )
                    logger.info(f"✓ Created XMP: {xmp_file}")
                    xmp_created += 1
                except Exception as e:
                    logger.warning(f"✗ Failed to create XMP for {photo['name']}: {e}")
                    xmp_failed.append(photo['name'])
            
            logger.info("-" * 80)
            logger.info(f"XMP files created: {xmp_created}/{len(all_failed)}")
            logger.info(f"XMP directory: {xmp_writer.output_directory.absolute()}")
            
            # Ask if user wants to trigger metadata rescan
            if xmp_created > 0:
                logger.info("-" * 80)
                try:
                    response = input("\nTrigger metadata rescan in Immich for these photos? (y/n): ").strip().lower()
                    if response == 'y':
                        logger.info("Waiting 3 seconds for Immich to detect new XMP files...")
                        time.sleep(3)
                        
                        logger.info("Retrying verification after rescan...")
                        retry_success = 0
                        for item in all_failed:
                            photo = item['photo']
                            gps = item['gps']
                            try:
                                url = f"{immich_url}/api/assets/{photo['id']}"
                                response = session.get(url, timeout=10)
                                response.raise_for_status()
                                updated_photo = response.json()
                                
                                new_lat = updated_photo.get('exifInfo', {}).get('latitude')
                                new_lon = updated_photo.get('exifInfo', {}).get('longitude')
                                
                                if new_lat == gps['latitude'] and new_lon == gps['longitude']:
                                    logger.debug(f"✓ Retry succeeded for {photo['name']}")
                                    retry_success += 1
                            except Exception as e:
                                logger.debug(f"✗ Retry failed for {photo['name']}: {e}")
                        
                        if retry_success > 0:
                            logger.info(f"✓ Successfully verified {retry_success} photos after XMP rescan")
                except EOFError:
                    logger.info("(Running in non-interactive mode, skipping rescan prompt)")
    
    logger.info("=" * 80)
    
    return matches
