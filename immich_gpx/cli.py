"""
Command-line interface for immich-gpx-linker.

Provides CLI argument parsing and orchestrates the GPS photo linking workflow:
1. Parse GPX file to extract GPS points with timestamps
2. Query Immich API for photos in matching time range
3. Match photos to GPS points using distance and time thresholds
4. Update photo metadata with GPS coordinates

Main entry point: main()
"""

import argparse
import os
import sys
from datetime import timedelta

from immich_gpx.config_loader import ConfigLoader

# CLI Configuration Constants
DEFAULT_TIME_THRESHOLD_SECONDS = 60
DEFAULT_API_TIMEOUT_SECONDS = 10
DEFAULT_UPDATE_MODE = 'prompt'
TIME_BUFFER_MINUTES = 5
DEFAULT_CONFIG_FILES = ['config.yaml', 'config-example.yaml']

UPDATE_MODE_ALL = 'all'
UPDATE_MODE_WITHOUT_GPS = 'without-gps'
UPDATE_MODE_PROMPT = 'prompt'

from immich_gpx.core.config import Config
from immich_gpx.core.errors import (
    AuthenticationError,
    ConfigurationError,
    ErrorCodes,
    GPXParsingError,
    GPXValidationError,
    ImmichGPXLinkerError,
    MatchingError,
    UpdateError,
)
from immich_gpx.core.gpx_parser import GPXParser
from immich_gpx.core.gps_matcher import GPSMatcher
from immich_gpx.core.immich_client import ImmichAPI
from immich_gpx.core.logger import setup_logging
from immich_gpx.utils import print_results
from immich_gpx.metrics import PerformanceMetrics
from immich_gpx.rollback import RollbackManager
from immich_gpx import __version__


def main() -> None:
    """
    Main entry point for the immich-gpx-linker CLI application.
    
    Orchestrates the complete GPS photo linking workflow:
    1. Parses command-line arguments and environment configuration
    2. Extracts GPS points from GPX file with timestamps
    3. Connects to Immich server and retrieves photos in matching time range
    4. Matches photos to GPS points using distance and time thresholds
    5. Updates photo GPS coordinates based on matches
    
    Configuration sources (in order of precedence):
    - Command-line arguments (highest priority)
    - Environment variables (IMMICH_URL, IMMICH_API_KEY, etc.)
    - Default values (lowest priority)
    
    Exits with appropriate error code on failure:
    - 1: Configuration/credentials error
    - 2-8: Various processing errors (see ErrorCodes)
    - Other: Unexpected exceptions
    
    Args:
        None - Arguments provided via sys.argv
        
    Returns:
        None - Exits with appropriate exit code
        
    Raises:
        Logs exceptions but doesn't re-raise; exits with error code instead
        
    Example:
        >>> # Called from CLI entry point
        >>> python -m immich_gpx.cli --gpx-file track.gpx --immich-url http://localhost:2283
    """
    parser = argparse.ArgumentParser(
        prog='immich-gpx',
        description='Link GPS points from GPX files with Immich photos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --gpx-file track.gpx --config config.yaml
  %(prog)s --gpx-file track.gpx --immich-url http://localhost:2283 --immich-api-key YOUR_KEY --threshold 120
        """,
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
        help='Show version number and exit',
    )
    parser.add_argument(
        '--config',
        help='Path to YAML config file (searches for config.yaml or config-example.yaml if not specified)',
    )
    parser.add_argument(
        '--gpx-file',
        required=True,
        help='Path to the GPX file to parse',
    )
    parser.add_argument(
        '--immich-url',
        help='URL of the Immich server (e.g., http://localhost:2283)',
    )
    parser.add_argument(
        '--immich-api-key',
        help='API key for Immich authentication',
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=DEFAULT_TIME_THRESHOLD_SECONDS,
        help=f'Time threshold in seconds for matching photos to GPS points (default: {DEFAULT_TIME_THRESHOLD_SECONDS})',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output',
    )
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL verification (use for self-signed certificates)',
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_API_TIMEOUT_SECONDS,
        help=f'API request timeout in seconds (default: {DEFAULT_API_TIMEOUT_SECONDS})',
    )
    parser.add_argument(
        '--update-mode',
        choices=[UPDATE_MODE_ALL, UPDATE_MODE_WITHOUT_GPS, UPDATE_MODE_PROMPT],
        default=DEFAULT_UPDATE_MODE,
        help='Update mode: all (update all photos), without-gps (only photos without GPS), '
             'prompt (ask user, default)',
    )
    parser.add_argument(
        '--rollback',
        metavar='SESSION_ID',
        default=None,
        help='Rollback GPS updates for a specific session (use "latest" for most recent)',
    )

    args = parser.parse_args()

    # Load configuration from YAML file if available (BEFORE initializing logger)
    config = {}
    config_file = args.config
    
    # If no config file specified, search for default files
    if not config_file:
        for default_file in DEFAULT_CONFIG_FILES:
            if os.path.exists(default_file):
                config_file = default_file
                break
    
    # Load config from file if found
    if config_file:
        try:
            loader = ConfigLoader(config_file)
            config = loader.load()
        except Exception as e:
            # Can't use logger yet since it's not initialized
            print(f"Error loading config file {config_file}: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Initialize logging with config log_dir if available
    log_dir = None
    if config:
        log_dir = config.get('logging', {}).get('log_file')
    logger = setup_logging(verbose=args.verbose, log_dir=log_dir)
    
    if config_file:
        logger.info(f"Found config file: {config_file}")
        logger.info(f"Loaded configuration from {config_file}")

    # Handle rollback command
    if args.rollback:
        from tqdm import tqdm
        immich_url = args.immich_url or config.get('immich', {}).get('url')
        immich_api_key = args.immich_api_key or config.get('immich', {}).get('api_key')
        verify_ssl = config.get('immich', {}).get('verify_ssl', True)
        if args.no_verify_ssl:
            verify_ssl = False
        
        if not immich_url or not immich_api_key:
            logger.error("Error: Missing Immich credentials for rollback.")
            sys.exit(1)
        
        # List available sessions if user wants latest but none exist
        rollback_mgr = RollbackManager(logger=logger)
        session_data = rollback_mgr.get_session(args.rollback)
        
        if not session_data:
            logger.error(f"Rollback session '{args.rollback}' not found.")
            logger.info("Available sessions:")
            for sess in rollback_mgr.list_sessions():
                logger.info(f"  {sess['session_id']}: {sess['total_updated']} photos ({sess['timestamp']})")
            sys.exit(1)
        
        # Perform rollback
        logger.info(f"Rolling back session {session_data['session_id']}")
        immich = ImmichAPI(immich_url, immich_api_key, verify_ssl=verify_ssl, timeout=args.timeout, logger=logger)
        
        try:
            immich.test_connection()
        except (AuthenticationError, ConnectionError) as e:
            logger.error(f"Failed to connect to Immich: {e}")
            sys.exit(1)
        
        # Restore coordinates for each photo
        success_count = 0
        fail_count = 0
        for photo in tqdm(session_data['photos'], desc="Restoring coordinates", unit="photo"):
            try:
                if photo['had_gps']:
                    # Restore original coordinates
                    immich.update_photo_exif(
                        photo['id'],
                        photo['original_latitude'],
                        photo['original_longitude']
                    )
                else:
                    # Remove GPS data that was added
                    immich.update_photo_exif(photo['id'], None, None)
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to restore {photo['filename']}: {e}")
                fail_count += 1
        
        logger.info(f"Rollback complete: {success_count} restored, {fail_count} failed")
        sys.exit(0)
    
    # Extract config values (command-line args take precedence over config file)
    immich_url = args.immich_url or config.get('immich', {}).get('url')
    immich_api_key = args.immich_api_key or config.get('immich', {}).get('api_key')
    
    # Get optional config values
    verify_ssl = config.get('immich', {}).get('verify_ssl', True)
    timeout = args.timeout if args.timeout != DEFAULT_API_TIMEOUT_SECONDS else config.get('immich', {}).get('timeout', DEFAULT_API_TIMEOUT_SECONDS)
    time_threshold = args.threshold if args.threshold != DEFAULT_TIME_THRESHOLD_SECONDS else config.get('matching', {}).get('threshold', DEFAULT_TIME_THRESHOLD_SECONDS)
    
    # Override with command-line args if provided
    if args.no_verify_ssl:
        verify_ssl = False
    
    if not immich_url or not immich_api_key:
        logger.error("Error: Missing Immich credentials.")
        logger.error("Provide via --immich-url and --immich-api-key, or in the YAML config file.")
        sys.exit(1)

    try:
        # Create metrics for tracking operations
        parse_metrics = PerformanceMetrics("Parse GPX")
        
        # Parse GPX file
        logger.info(f"Parsing GPX file: {args.gpx_file}")
        gpx_parser = GPXParser(args.gpx_file)
        gps_points = gpx_parser.parse()
        parse_metrics.complete(items_processed=len(gps_points), errors=0)
        logger.info(f"Found {len(gps_points)} GPS points - {parse_metrics.summary()}")

        # Get time range
        start_time, end_time = gpx_parser.get_time_range()
        if not start_time or not end_time:
            logger.warning("Warning: GPX file has no time information")
            sys.exit(1)

        # Add buffer to time range to capture nearby photos
        # (photos slightly before/after the GPX track)
        before_buffer = timedelta(minutes=TIME_BUFFER_MINUTES)
        after_buffer = timedelta(minutes=TIME_BUFFER_MINUTES)
        start_time_query = start_time - before_buffer
        end_time_query = end_time + after_buffer

        # Connect to Immich
        logger.info(f"Connecting to Immich API: {immich_url}")
        immich = ImmichAPI(
            immich_url,
            immich_api_key,
            verbose=args.verbose,
            verify_ssl=verify_ssl,
            timeout=timeout,
            logger=logger,
        )
        
        # Test connection
        try:
            immich.test_connection()
        except (ConnectionError, AuthenticationError):
            raise

        # Fetch photos from Immich with metrics
        fetch_metrics = PerformanceMetrics("Fetch Photos")
        logger.info(f"Querying for photos between {start_time_query} and {end_time_query}...")
        photos = immich.get_photos_in_range(start_time_query, end_time_query)
        fetch_metrics.complete(items_processed=len(photos), errors=0)
        logger.info(f"Found {len(photos)} photos - {fetch_metrics.summary()}")

        if not photos:
            logger.warning("Warning: No photos found in the time range")
            logger.warning("  Try adjusting the time buffer or check your Immich library")

        # Match GPS points with photos with metrics
        match_metrics = PerformanceMetrics("Match Photos to GPS")
        logger.info(f"Matching GPS points with photos...")
        matcher = GPSMatcher(
            threshold=time_threshold,
        )
        matches = matcher.match_photos_to_points(gps_points, photos, verbose=args.verbose, logger=logger)
        match_metrics.complete(items_processed=len(photos), errors=len(photos) - len(matches))
        logger.info(f"Found {len(matches)} matches - {match_metrics.summary()}")

        # Print results
        print_results(gps_points, photos, matches, immich_url=immich_url, logger=logger)

        # Handle selective update
        if matches:
            from .utils import categorize_matches, prompt_update_mode, update_photo_positions, print_position_update_preview
            
            # Categorize matches by GPS status
            categorized = categorize_matches(matches)
            
            # Determine update mode from arguments or prompt user
            if args.update_mode == UPDATE_MODE_PROMPT:
                # Interactive mode - prompt user for choice
                update_mode = prompt_update_mode(categorized, logger)
                if update_mode == 'cancel':
                    logger.info("Update cancelled. No changes made.")
                    return
            else:
                # Non-interactive mode - use selected mode directly
                update_mode = args.update_mode
                counts = categorized['counts']
                logger.info(f"Non-interactive mode: {update_mode}")
                logger.info(f"  Total matches: {counts['total']}")
                logger.info(f"  With GPS: {counts['with_gps']}")
                logger.info(f"  Without GPS: {counts['without_gps']}")
            
            # Select matches to update based on mode
            if update_mode == UPDATE_MODE_ALL:
                matches_to_update = categorized['all']
            elif update_mode == UPDATE_MODE_WITHOUT_GPS:
                matches_to_update = categorized['without_gps']
                if not matches_to_update:
                    logger.warning("No photos without GPS to update!")
                    return
            
            # Preview
            print_position_update_preview(matches_to_update, logger)
            
            # Update with metrics
            update_metrics = PerformanceMetrics("Update Photos")
            
            # Create rollback session to capture update history
            rollback_mgr = RollbackManager(logger=logger)
            rollback_session = rollback_mgr.create_session(
                gpx_file=args.gpx_file,
                update_mode=update_mode
            )
            
            update_photo_positions(
                matches_to_update,
                immich_url,
                logger,
                mode=update_mode,
                api_key=immich_api_key,
                rollback_session=rollback_session
            )
            
            # Save rollback session and cleanup old ones
            rollback_session.save()
            rollback_mgr.cleanup_old_sessions(keep_count=10)
            logger.info(f"Rollback data saved: {rollback_session.session_id}")
            
            update_metrics.complete(items_processed=len(matches_to_update), errors=0)
            logger.info(f"Update complete - {update_metrics.detailed_summary()}")

    except ConfigurationError as e:
        logger.error(f"Configuration Error: {e}")
        logger.error("Troubleshooting:")
        logger.error("  1. Check environment variables: IMMICH_URL, IMMICH_API_KEY")
        logger.error("  2. Verify command-line arguments are correct")
        logger.error("  3. Ensure GPX file exists and is readable")
        sys.exit(ErrorCodes.CONFIG_ERROR)
    except GPXValidationError as e:
        logger.error(f"GPX File Error: {e}")
        logger.error("Troubleshooting:")
        logger.error("  1. Verify the GPX file path is correct")
        logger.error("  2. Check that the file exists and is readable")
        logger.error("  3. Ensure sufficient disk space and permissions")
        sys.exit(ErrorCodes.FILE_NOT_FOUND)
    except GPXParsingError as e:
        logger.error(f"GPX Parsing Error: {e}")
        logger.error("Troubleshooting:")
        logger.error("  1. Verify the GPX file is valid XML format")
        logger.error("  2. Check for corrupted or incomplete GPX data")
        logger.error("  3. Try opening the file in a GPX editor to validate")
        sys.exit(ErrorCodes.PARSE_ERROR)
    except ConnectionError as e:
        logger.error(f"Connection Error: {e}")
        logger.error("Troubleshooting:")
        logger.error("  1. Verify the Immich URL is correct (e.g., http://localhost:2283)")
        logger.error("  2. Check that the Immich server is running and accessible")
        logger.error("  3. Verify network connectivity to the server")
        logger.error("  4. Check firewall rules and port access")
        logger.error("  5. If using HTTPS, verify SSL/TLS certificates are valid")
        sys.exit(ErrorCodes.CONNECTION_ERROR)
    except AuthenticationError as e:
        logger.error(f"Authentication Error: {e}")
        logger.error("Troubleshooting:")
        logger.error("  1. Verify the API key is correct and not expired")
        logger.error("  2. Check that the API key has sufficient permissions")
        logger.error("  3. Try generating a new API key in Immich settings")
        logger.error("  4. Verify the API key format is correct")
        sys.exit(ErrorCodes.AUTH_ERROR)
    except (MatchingError, UpdateError) as e:
        logger.error(f"Processing Error: {e}")
        logger.error("Troubleshooting:")
        logger.error("  1. Check the verbose output for more details")
        logger.error("  2. Verify photo and GPS data format")
        logger.error("  3. Try adjusting distance/time thresholds")
        if isinstance(e, MatchingError):
            sys.exit(ErrorCodes.MATCH_ERROR)
        else:
            sys.exit(ErrorCodes.UPDATE_ERROR)
    except ImmichGPXLinkerError as e:
        logger.error(f"Application Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(e.error_code if hasattr(e, 'error_code') else ErrorCodes.UNKNOWN_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(ErrorCodes.UNKNOWN_ERROR)


if __name__ == '__main__':
    main()
