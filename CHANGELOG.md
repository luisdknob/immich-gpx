# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - 2025-11-04

### Added

- **Rollback system**: Full undo capability for GPS updates via `--rollback` flag
  - Session-based rollback with automatic cleanup (keeps 10 most recent)
  - `--rollback latest` or `--rollback SESSION_ID` to restore changes
  - Stores original coordinates before updates
- **XMP sidecar support**: Generate XMP files for external/read-only libraries via `--enable-xmp`
  - Auto-detects when Immich API fails to persist coordinates
  - Creates XMP files that Immich can import on metadata rescan
  - Interactive pipeline with verification retry
- **Update verification**: Re-fetches photos after update to confirm persistence
  - Catches silent failures from read-only or external libraries
  - Clear error reporting distinguishing API vs persistence failures
- HTTP redirect handling: Auto-updates base URL when HTTP redirects to HTTPS
- Match sorting: Photos now sorted by timestamp (oldest first) for consistent processing

### Changed

- Enhanced output formatting with detailed status indicators:
  - ✓ X verified (update successful and confirmed)
  - → X skipped (existing GPS preserved)
  - ✗ X failed (API error)
  - ⚠ X not persisted (read-only library detected)
- Distance display no longer shows 'None' when unavailable

### Fixed

- HTTP/HTTPS protocol mismatch when server redirects
- Integration tests properly mock session.request()

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
