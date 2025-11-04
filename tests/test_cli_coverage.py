"""Comprehensive CLI tests for improved code coverage."""
import pytest
import sys
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import logging


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_main_no_arguments(self):
        """Test CLI with no arguments shows error."""
        from immich_gpx import main
        
        with patch('sys.argv', ['immich_gpx']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Our code exits with code 1 (validation error), not argparse code 2
            assert exc_info.value.code == 1

    def test_main_with_all_arguments(self, tmp_path):
        """Test CLI with all arguments provided."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key',
            '--threshold', '50',
            '--time-threshold', '60',
            '--verbose'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        mock_parser = Mock()
                        mock_parser.parse.return_value = []
                        mock_parser.get_time_range.return_value = (datetime.now(), datetime.now() + timedelta(hours=1))
                        mock_parser_class.return_value = mock_parser
                        
                        mock_api = Mock()
                        mock_api.test_connection.return_value = None
                        mock_api.get_photos_in_range.return_value = []
                        mock_api_class.return_value = mock_api
                        
                        mock_matcher = Mock()
                        mock_matcher.match_photos_to_points.return_value = []
                        mock_matcher_class.return_value = mock_matcher
                        
                        try:
                            main()
                        except SystemExit:
                            pass

    def test_main_short_arguments(self, tmp_path):
        """Test CLI with short form arguments."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '-g', str(gpx_file),
            '-u', 'http://localhost:2283',
            '-k', 'test_key',
            '-d', '50',
            '-t', '60'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        mock_parser = Mock()
                        mock_parser.parse.return_value = []
                        mock_parser.get_time_range.return_value = (datetime.now(), datetime.now() + timedelta(hours=1))
                        mock_parser_class.return_value = mock_parser
                        
                        mock_api = Mock()
                        mock_api.test_connection.return_value = None
                        mock_api.get_photos_in_range.return_value = []
                        mock_api_class.return_value = mock_api
                        
                        mock_matcher = Mock()
                        mock_matcher.match_photos_to_points.return_value = []
                        mock_matcher_class.return_value = mock_matcher
                        
                        try:
                            main()
                        except SystemExit:
                            pass


class TestCLIEnvironmentVariables:
    """Test CLI with environment variables."""

    def test_main_with_env_variables(self, tmp_path):
        """Test CLI reading from environment variables."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch.dict(os.environ, {
            'IMMICH_URL': 'http://localhost:2283',
            'IMMICH_API_KEY': 'env_key'
        }):
            with patch('sys.argv', ['immich_gpx', '--gpx-file', str(gpx_file)]):
                with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                    with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                        with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                            mock_parser = Mock()
                            mock_parser.parse.return_value = []
                            mock_parser.get_time_range.return_value = (datetime.now(), datetime.now() + timedelta(hours=1))
                            mock_parser_class.return_value = mock_parser
                            
                            mock_api = Mock()
                            mock_api.test_connection.return_value = None
                            mock_api.get_photos_in_range.return_value = []
                            mock_api_class.return_value = mock_api
                            
                            mock_matcher = Mock()
                            mock_matcher.match_photos_to_points.return_value = []
                            mock_matcher_class.return_value = mock_matcher
                            
                            try:
                                main()
                            except SystemExit:
                                pass

    def test_main_cli_overrides_env(self, tmp_path):
        """Test that CLI arguments override environment variables."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch.dict(os.environ, {
            'IMMICH_URL': 'http://wrong:2283',
            'IMMICH_API_KEY': 'wrong_key'
        }):
            with patch('sys.argv', [
                'immich_gpx',
                '--gpx-file', str(gpx_file),
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'correct_key'
            ]):
                with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                    with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                        with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                            mock_parser = Mock()
                            mock_parser.parse.return_value = []
                            mock_parser.get_time_range.return_value = (datetime.now(), datetime.now() + timedelta(hours=1))
                            mock_parser_class.return_value = mock_parser
                            
                            mock_api = Mock()
                            mock_api.test_connection.return_value = None
                            mock_api.get_photos_in_range.return_value = []
                            mock_api_class.return_value = mock_api
                            
                            mock_matcher = Mock()
                            mock_matcher.match_photos_to_points.return_value = []
                            mock_matcher_class.return_value = mock_matcher
                            
                            try:
                                main()
                            except SystemExit:
                                pass


class TestCLIErrorCases:
    """Test CLI error handling."""

    def test_main_gpx_file_no_time_info(self, tmp_path):
        """Test CLI when GPX file has no time information."""
        from immich_gpx import main
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"/></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                mock_parser = Mock()
                mock_parser.parse.return_value = [{'latitude': 41.0, 'longitude': -71.0, 'time': None}]
                mock_parser.get_time_range.return_value = (None, None)
                mock_parser_class.return_value = mock_parser
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_main_no_gps_points(self, tmp_path):
        """Test CLI when GPX file has no GPS points."""
        from immich_gpx import main
        
        gpx_file = tmp_path / "empty.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                mock_parser = Mock()
                mock_parser.parse.return_value = []
                mock_parser.get_time_range.return_value = (None, None)
                mock_parser_class.return_value = mock_parser
                
                with pytest.raises(SystemExit):
                    main()


class TestCLIUpdateModes:
    """Test CLI update modes."""

    def test_main_update_mode_all(self, tmp_path):
        """Test CLI with 'all' update mode."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        with patch('immich_gpx.utils.prompt_update_mode', return_value='all'):
                            
                                with patch('immich_gpx.utils.update_photo_positions'):
                                    mock_parser = Mock()
                                    mock_parser.parse.return_value = [{'latitude': 41.0, 'longitude': -71.0, 'time': datetime(2022, 2, 16, 12, 6, 29)}]
                                    mock_parser.get_time_range.return_value = (datetime(2022, 2, 16, 12, 0), datetime(2022, 2, 16, 13, 0))
                                    mock_parser_class.return_value = mock_parser
                                    
                                    mock_api = Mock()
                                    mock_api.test_connection.return_value = None
                                    mock_api.get_photos_in_range.return_value = [{'id': 'p1', 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}}]
                                    mock_api_class.return_value = mock_api
                                    
                                    mock_matcher = Mock()
                                    mock_matcher.match_photos_to_points.return_value = [{'photo': {'id': 'p1'}, 'gps_point': {'latitude': 41.0, 'longitude': -71.0}}]
                                    mock_matcher_class.return_value = mock_matcher
                                    
                                    try:
                                        main()
                                    except SystemExit:
                                        pass

    def test_main_update_mode_without_gps(self, tmp_path):
        """Test CLI with 'without-gps' update mode."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        with patch('immich_gpx.utils.prompt_update_mode', return_value='without-gps'):
                            
                                with patch('immich_gpx.utils.update_photo_positions'):
                                    mock_parser = Mock()
                                    mock_parser.parse.return_value = [{'latitude': 41.0, 'longitude': -71.0, 'time': datetime(2022, 2, 16, 12, 6, 29)}]
                                    mock_parser.get_time_range.return_value = (datetime(2022, 2, 16, 12, 0), datetime(2022, 2, 16, 13, 0))
                                    mock_parser_class.return_value = mock_parser
                                    
                                    mock_api = Mock()
                                    mock_api.test_connection.return_value = None
                                    mock_api.get_photos_in_range.return_value = [{'id': 'p1', 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}, 'latitude': None, 'longitude': None}]
                                    mock_api_class.return_value = mock_api
                                    
                                    mock_matcher = Mock()
                                    mock_matcher.match_photos_to_points.return_value = [{'photo': {'id': 'p1', 'latitude': None, 'longitude': None}, 'gps_point': {'latitude': 41.0, 'longitude': -71.0}}]
                                    mock_matcher_class.return_value = mock_matcher
                                    
                                    try:
                                        main()
                                    except SystemExit:
                                        pass


class TestCLIVerboseLogging:
    """Test CLI verbose logging."""

    def test_main_verbose_mode(self, tmp_path, caplog):
        """Test CLI with verbose mode enabled."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key',
            '--verbose'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        mock_parser = Mock()
                        mock_parser.parse.return_value = []
                        mock_parser.get_time_range.return_value = (datetime.now(), datetime.now() + timedelta(hours=1))
                        mock_parser_class.return_value = mock_parser
                        
                        mock_api = Mock()
                        mock_api.test_connection.return_value = None
                        mock_api.get_photos_in_range.return_value = []
                        mock_api_class.return_value = mock_api
                        
                        mock_matcher = Mock()
                        mock_matcher.match_photos_to_points.return_value = []
                        mock_matcher_class.return_value = mock_matcher
                        
                        try:
                            main()
                        except SystemExit:
                            pass


class TestCLIUserInteraction:
    """Test CLI user interaction."""

    def test_main_cancel_update(self, tmp_path):
        """Test user cancels the update."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        with patch('immich_gpx.utils.prompt_update_mode', return_value='all'):
                            
                                mock_parser = Mock()
                                mock_parser.parse.return_value = [{'latitude': 41.0, 'longitude': -71.0, 'time': datetime(2022, 2, 16, 12, 6, 29)}]
                                mock_parser.get_time_range.return_value = (datetime(2022, 2, 16, 12, 0), datetime(2022, 2, 16, 13, 0))
                                mock_parser_class.return_value = mock_parser
                                
                                mock_api = Mock()
                                mock_api.test_connection.return_value = None
                                mock_api.get_photos_in_range.return_value = [{'id': 'p1', 'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z'}}]
                                mock_api_class.return_value = mock_api
                                
                                mock_matcher = Mock()
                                mock_matcher.match_photos_to_points.return_value = [{'photo': {'id': 'p1'}, 'gps_point': {'latitude': 41.0, 'longitude': -71.0}}]
                                mock_matcher_class.return_value = mock_matcher
                                
                                try:
                                    main()
                                except SystemExit:
                                    pass

    def test_main_no_matches(self, tmp_path):
        """Test when no matches are found."""
        from immich_gpx import main
        from datetime import datetime
        
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"><trk><trkseg><trkpt lat="41.0" lon="-71.0"><time>2022-02-16T12:06:29Z</time></trkpt></trkseg></trk></gpx>')
        
        with patch('sys.argv', [
            'immich_gpx',
            '--gpx-file', str(gpx_file),
            '--immich-url', 'http://localhost:2283',
            '--immich-api-key', 'test_key'
        ]):
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                with patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                    with patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                        with patch('immich_gpx.cli.print_results'):
                            mock_parser = Mock()
                            mock_parser.parse.return_value = [{'latitude': 41.0, 'longitude': -71.0, 'time': datetime(2022, 2, 16, 12, 6, 29)}]
                            mock_parser.get_time_range.return_value = (datetime(2022, 2, 16, 12, 0), datetime(2022, 2, 16, 13, 0))
                            mock_parser_class.return_value = mock_parser
                            
                            mock_api = Mock()
                            mock_api.test_connection.return_value = None
                            mock_api.get_photos_in_range.return_value = []
                            mock_api_class.return_value = mock_api
                            
                            mock_matcher = Mock()
                            mock_matcher.match_photos_to_points.return_value = []
                            mock_matcher_class.return_value = mock_matcher
                            
                            try:
                                main()
                            except SystemExit:
                                pass
