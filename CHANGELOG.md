# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
