# Test Infrastructure

Standardized helpers for consistent, maintainable tests.

## Files

### `builders.py`
Create test data with builder pattern.

```python
from tests.builders import photo, gps_point, match

# Quick creation
p = photo('photo1', 41.0, -71.0, name='test.jpg')
g = gps_point(41.0, -71.0, elevation=100)
m = match(p, g)

# Builder pattern
p = PhotoBuilder().with_id('photo1').with_gps(41.0, -71.0).build()
```

**Classes:**
- `PhotoBuilder` - Immich API photo format
- `GPSPointBuilder` - GPS coordinates with time
- `MatchBuilder` - Photo-GPS match structure

**Functions:**
- `photo(id, lat, lon, name, timestamp)` - Create photo dict
- `gps_point(lat, lon, elevation)` - Create GPS point dict
- `match(photo_data, gps_data)` - Create match dict

### `mocks.py`
Reusable mock patterns for API testing.

```python
from tests.mocks import MockRequestsSession

@patch('requests.Session')
def test_something(mock_session_class):
    mock_session_class.return_value = MockRequestsSession.with_photo_update('photo1', 41.0, -71.0)
```

**Patterns:**
- `.with_success()` - Generic successful API calls
- `.with_photo_update(id, lat, lon)` - GPS update with verification
- `.with_silent_failure(id)` - API success but no persistence
- `.with_api_failure(message)` - Connection/timeout errors
- `.with_http_redirect(from_url, to_url)` - Redirect handling

**Functions:**
- `mock_api_response(data, status)` - Create mock response
- `mock_immich_photos(count)` - Generate photo list

### `conftest.py`
Centralized pytest fixtures.

**Fixtures:**
- `logger` - Test logger
- `rollback_manager` - RollbackManager with temp dir
- `xmp_writer` - XMPWriter with temp dir
- `tmp_gpx_file` - Temporary GPX file
- `gps_points` - Sample GPS points

## Migration Example

**Before (Bloated):**
```python
def test_update_verification(mock_put, mock_get):
    logger = logging.getLogger('test')
    
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    mock_get_response = Mock()
    mock_get_response.json.return_value = {'id': 'photo1', 'exifInfo': {...}}
    mock_get.return_value = mock_get_response
    
    matches = [{'photo': {'id': 'photo1', ...}, 'gps_point': {...}}]
```

**After (Clean):**
```python
from tests.builders import photo, gps_point, match
from tests.mocks import MockRequestsSession

@patch('requests.Session')
def test_update_verification(mock_session_class, logger):
    mock_session_class.return_value = MockRequestsSession.with_photo_update('photo1', 41.0, -71.0)
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
```

## Benefits

- **75% less code** per test
- **Consistent patterns** across test suite
- **Single source of truth** for test data structures
- **Easier maintenance** - update builders, not every test

## Status

✅ Infrastructure complete (333/333 tests passing, 82.70% coverage)
✅ Migrated files: test_update_verification.py, test_utilities.py, test_gps_matcher.py, test_validation.py
