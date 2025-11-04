# Immich GPX

Add GPS coordinates from GPX tracks to photos in Immich based on timestamp matching.

## Features

- Match photos to GPS points by timestamp proximity
- Update photo GPS coordinates in Immich
- **Rollback system**: Undo GPS updates with `--rollback latest`
- **XMP sidecar support**: Handle external/read-only libraries with `--enable-xmp`
- **Update verification**: Detect when coordinates don't persist
- Interactive preview before updates
- YAML configuration support
- HTTP redirect handling and SSL options

## Prerequisites

### Immich API Key

Create an API key in Immich: **Settings** → **Account Settings** → **API Keys** → **New API Key**

Enable permissions: `asset.read` and `asset.update`

Store securely in `config.yaml` or pass via `--immich-api-key`.

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Basic Usage

```bash
python -m immich_gpx.cli --gpx-file track.gpx
```

With options:

```bash
python -m immich_gpx.cli \
  --gpx-file track.gpx \
  --immich-url https://photos.example.com \
  --immich-api-key YOUR_API_KEY \
  --threshold 120
```

### Configuration File (optional)

Copy and edit `config-example.yaml`:

```bash
cp config-example.yaml config.yaml
```

```yaml
immich:
  url: https://photos.example.com
  api_key: your-api-key
  verify_ssl: true
  timeout: 10

matching:
  threshold: 60  # seconds
```

The tool auto-searches for `config.yaml` in the current directory.

## Command-line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--gpx-file` | Path to GPX file (required for GPS updates) | - |
| `--immich-url` | Immich server URL | config file |
| `--immich-api-key` | Immich API key | config file |
| `--threshold` | Time threshold in seconds | 60 |
| `--timeout` | API request timeout (seconds) | 10 |
| `--no-verify-ssl` | Disable SSL verification | false |
| `--verbose` | Enable debug output | false |
| `--config` | Path to YAML config file | auto-search |
| `--update-mode` | `all`, `without-gps`, or `prompt` | prompt |
| `--rollback` | Restore GPS from session: `latest` or SESSION_ID | - |
| `--enable-xmp` | Create XMP sidecars for external libraries | false |
| `--version` | Show version | - |

## How It Works

1. **Parse GPX**: Extract GPS points with timestamps
2. **Query Immich**: Fetch photos in GPX time range
3. **Match**: Find closest GPS point for each photo by time
4. **Verify**: Confirm coordinates persisted after update
5. **Preview**: Show matches and request confirmation
6. **Update**: Apply coordinates to Immich

### Rollback

Undo coordinate changes:

```bash
# Restore most recent session
python -m immich_gpx.cli --rollback latest

# Restore specific session
python -m immich_gpx.cli --rollback abc123-def456
```

Sessions stored in `./rollback/` (auto-cleaned, keeps 10 most recent).

### External Libraries / Read-Only Storage

For external or read-only libraries where Immich can't write EXIF directly:

```bash
python -m immich_gpx.cli --gpx-file track.gpx --enable-xmp
```

Creates XMP sidecar files for Immich to import on metadata rescan.

## Configuration Priority

Settings are applied in order (highest → lowest):
1. Command-line arguments
2. YAML config file
3. Default values

## Docker

```bash
docker build -t immich-gpx .

docker run --rm \
  -v $(pwd):/data \
  immich-gpx \
  --gpx-file /data/track.gpx \
  --immich-url https://photos.example.com \
  --immich-api-key YOUR_KEY
```

## Troubleshooting

**Permission errors (403/401)**: Verify your API key has `asset.read` and `asset.update` permissions enabled in Immich settings.

**Connection errors**: Verify URL and network connectivity. Use `--no-verify-ssl` for self-signed certificates.

**No photos found**: Check photos exist in GPX time range. Use `--verbose` to debug.

**No matches found**: Try increasing `--threshold` value (default: 60 seconds).

## Development

Run tests:

```bash
python -m pytest tests/ -v
```

## Disclaimer

**USE AT YOUR OWN RISK**

This software is provided "as is" without warranty of any kind. The author:
- Takes **zero responsibility** for any data loss, corruption, or issues
- Provides **no guarantees** that it will work for your use case
- Offers **no official support** (though issues/PRs are welcome)

This was coded during vibe sessions. It works for me, might work for you. I did my best to ensure that everything functions properly and that the code is well-written. However, make sure to test it thoroughly before using it on production data.

**Always backup your Immich database before running update operations.**

## License

Apache License 2.0 - See LICENSE file

