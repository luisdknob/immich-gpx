# Test Helper Infrastructure

This directory contains standardized test helpers for creating consistent, maintainable tests.

## Files

### `builders.py` - Test Data Builders
Provides builder classes and convenience functions for creating test data.

**Usage:**
```python
from tests.builders import photo, gps_point, match

# Quick builders
p = photo('photo1', lat=41.0, lon=-71.0)
g = gps_point(41.0, -71.0)
m = match(p, g)

# Builder pattern for complex cases
p = PhotoBuilder().with_id('photo1').with_gps(41.0, -71.0).with_name('test.jpg').build()
```

**Classes:**
- `PhotoBuilder` - Build photo dicts
- `GPSPointBuilder` - Build GPS point dicts  
- `MatchBuilder` - Build match dicts (photo + GPS)

**Functions:**
- `photo(photo_id, lat, lon, name)` - Quick photo creation
- `gps_point(lat, lon, elevation)` - Quick GPS point creation
- `match(photo_data, gps_data)` - Quick match creation

### `mocks.py` - Standardized Mock Patterns
Provides reusable mock builders for consistent API mocking.

**Usage:**
```python
from tests.mocks import MockRequestsSession

@patch('requests.Session')
def test_something(mock_session_class, logger):
    mock_session_class.return_value = MockRequestsSession.with_photo_update('photo1', 41.0, -71.0)
    # Test code here
```

**Classes:**
- `MockRequestsSession` - Standard patterns for requests.Session mocking
  - `.with_success()` - Generic successful API calls
  - `.with_photo_update(id, lat, lon)` - Successful GPS update with verification
  - `.with_silent_failure(id)` - API success but coordinates don't persist (read-only library)
  - `.with_api_failure(message)` - Connection/timeout errors
  - `.with_http_redirect(from_url, to_url)` - HTTP redirect handling

**Functions:**
- `mock_api_response(data, status_code)` - Create mock API response
- `mock_immich_photos(count)` - Generate list of mock photo responses

### `conftest.py` - Centralized Fixtures
All pytest fixtures are centralized here for reuse across tests.

**Available Fixtures:**
- `logger` - Test logger instance
- `temp_rollback_dir` - Temporary rollback directory
- `rollback_manager` - RollbackManager instance with temp dir
- `temp_xmp_dir` - Temporary XMP output directory
- `xmp_writer` - XMPWriter instance with temp dir
- `sample_gpx_content` - Sample GPX file content
- `tmp_gpx_file` - Temporary GPX file
- `gps_points` - Sample GPS points list
- Plus all existing fixtures...

## Migration Guide

### Before (Bloated)
```python
def test_update_verification_success(mock_put, mock_get):
    logger = logging.getLogger('test')
    
    # 20 lines of mock setup...
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {'id': 'photo1', 'exifInfo': {...}}
    mock_get.return_value = mock_get_response
    
    matches = [
        {'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
         'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}}
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
```

### After (Clean)
```python
from tests.builders import photo, gps_point, match
from tests.mocks import MockRequestsSession

@patch('requests.Session')
def test_update_verification_success(mock_session_class, logger):
    mock_session_class.return_value = MockRequestsSession.with_photo_update('photo1', 41.0, -71.0)
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
    assert result is not None
```

## Benefits

1. **75% less code** - Eliminates repetitive mock setup
2. **Clearer intent** - `MockRequestsSession.with_photo_update()` vs 15 lines of Mock()
3. **Consistent patterns** - All tests use same mocking approach
4. **Easy to extend** - Add new mock patterns in one place
5. **Faster test writing** - Reuse builders instead of recreating data structures

## Status

**Completed:**
- ✅ `builders.py` created with Photo/GPS/Match builders
- ✅ `mocks.py` created with MockRequestsSession patterns
- ✅ `conftest.py` updated with centralized fixtures
- ✅ Duplicate fixtures removed from test_rollback.py and test_xmp_writer.py
- ✅ Infrastructure validated (39 tests passing)

**Remaining Work:**
Individual test files need gradual migration to use new helpers. This should be done file-by-file:
1. Import builders and mocks at top of file
2. Replace inline dicts with builder calls
3. Replace verbose mocking with MockRequestsSession patterns
4. Use logger fixture instead of logging.getLogger()
5. Run tests to validate

## Examples

See refactored tests in:
- `test_rollback.py` - Uses centralized fixtures
- `test_xmp_writer.py` - Uses centralized fixtures
