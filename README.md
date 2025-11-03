# Immich GPX

Link GPS coordinates from GPX tracks to photos in Immich based on timestamp proximity.

## Features

- Parse GPX files and extract GPS coordinates with timestamps
- Query Immich for photos within the GPS track time range
- Match photos to GPS points by time proximity (closest point wins)
- Update photo GPS coordinates in Immich
- Interactive preview before applying updates
- Support for HTTPS with SSL verification options
- YAML configuration support
- Performance metrics and logging
- 89%+ test coverage with 280 passing tests

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
| `--gpx-file` | Path to GPX file (required) | - |
| `--immich-url` | Immich server URL | config file |
| `--immich-api-key` | Immich API key | config file |
| `--threshold` | Time threshold in seconds | 60 |
| `--timeout` | API request timeout (seconds) | 10 |
| `--no-verify-ssl` | Disable SSL verification | false |
| `--verbose` | Enable debug output | false |
| `--config` | Path to YAML config file | auto-search |
| `--update-mode` | `all`, `without-gps`, or `prompt` | prompt |
| `--version` | Show version | - |

## How It Works

1. **Parse GPX**: Extract GPS points and timestamps from GPX file
2. **Query Immich**: Fetch photos taken within the GPX time range
3. **Match**: For each photo, find the GPS point closest in time
4. **Preview**: Show matches and ask for confirmation
5. **Update**: Apply GPS coordinates to matched photos in Immich

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

**Connection errors**: Verify URL, server is running, network connectivity. Use `--no-verify-ssl` for self-signed certificates.

**No photos found**: Check photos exist in GPX time range. Try `--verbose` to debug.

**No matches found**: Increase `--threshold` value. Ensure photos have valid timestamps.

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

