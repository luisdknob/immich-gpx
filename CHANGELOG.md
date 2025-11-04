# Changelog

All notable changes documented here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - 2025-11-04

### Added

- **Rollback system**: Undo GPS updates with `--rollback latest` or `--rollback SESSION_ID`
  - Session-based with automatic cleanup (keeps 10 most recent)
  - Stores original coordinates before updates
- **XMP sidecar support**: Generate XMP files for external/read-only libraries via `--enable-xmp`
  - Auto-detects when API fails to persist coordinates
  - Creates XMP files for Immich metadata rescan
  - Interactive verification pipeline with retry option
- **Update verification**: Re-fetches photos after update to confirm persistence
  - Detects silent failures from read-only or external libraries
  - Clear error reporting for API vs persistence failures
- HTTP redirect handling: Auto-updates base URL on HTTP→HTTPS redirects
- Match sorting: Photos sorted by timestamp (oldest first)

### Changed

- Enhanced output with status indicators:
  - `✓ X verified` - Update successful and confirmed
  - `→ X skipped` - Existing GPS preserved
  - `✗ X failed` - API error
  - `⚠ X not persisted` - Read-only library detected
- Distance no longer displays 'None' when unavailable
- Improved docstrings and removed verbose comments

### Fixed

- HTTP/HTTPS protocol mismatch on redirects
- Integration test mocking for session.request()
- Python 3.13+ compatibility (datetime.UTC → zoneinfo.UTC)

## [1.0.0] - 2025-11-03

### Added

- GPS point matching based on time proximity
- Photo GPS coordinate updates in Immich
- YAML configuration file support
- Docker support
- CLI with configurable thresholds and timeouts
- Input validation for coordinates, timestamps, URLs, and file paths
- Automatic retry with exponential backoff
- Response caching with TTL
- Rate limiting
- Performance metrics

### Dependencies

- requests >= 2.28.0
- gpxpy >= 1.5.0
- python-dotenv >= 0.20.0
- PyYAML >= 6.0
- tqdm >= 4.66.0

### Limitations

- Single-threaded
- In-memory cache only
- No rollback for bulk updates

[1.0.0]: https://github.com/luisdknob/immich-gpx/releases/tag/v1.0.0
