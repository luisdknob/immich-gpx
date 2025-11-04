"""
Tests for XMP sidecar file generation.

Tests GPS coordinate conversion and XMP file generation.
"""

import pytest
from pathlib import Path
from immich_gpx.xmp_writer import XMPWriter, convert_decimal_to_xmp_format


class TestGPSConversion:
    """Test GPS coordinate conversion to Immich XMP format."""
    
    def test_convert_positive_latitude_positive_longitude(self):
        """Test conversion of positive coordinates (Northern Hemisphere, Eastern Hemisphere)."""
        lat, lon = convert_decimal_to_xmp_format(46.495356, 12.061609)
        
        assert 'N' in lat  # North
        assert 'E' in lon  # East
        assert '46,' in lat  # Degrees
        assert '12,' in lon  # Degrees
    
    def test_convert_negative_latitude_negative_longitude(self):
        """Test conversion of negative coordinates (Southern Hemisphere, Western Hemisphere)."""
        lat, lon = convert_decimal_to_xmp_format(-41.199469, -71.826794)
        
        assert 'S' in lat  # South
        assert 'W' in lon  # West
        assert '41,' in lat
        assert '71,' in lon
    
    def test_convert_zero_coordinates(self):
        """Test conversion of zero coordinates (Equator, Prime Meridian)."""
        lat, lon = convert_decimal_to_xmp_format(0.0, 0.0)
        
        assert 'N' in lat or lat.startswith('0')  # 0 degrees is N
        assert 'E' in lon or lon.startswith('0')  # 0 degrees is E
    
    def test_convert_near_poles(self):
        """Test conversion near poles."""
        lat, lon = convert_decimal_to_xmp_format(89.999999, 179.999999)
        
        assert 'N' in lat
        assert 'E' in lon
        assert '89,' in lat
        assert '179,' in lon
    
    def test_convert_format_precision(self):
        """Test that conversion maintains proper decimal precision."""
        lat, lon = convert_decimal_to_xmp_format(46.495356, 12.061609)
        
        # Should have 8 decimal places for minutes
        parts = lat.split(',')
        assert len(parts) == 2
        minutes_part = parts[1][:-1]  # Remove direction letter
        # Should have multiple decimal places
        assert '.' in minutes_part


class TestXMPWriter:
    """Test XMP file generation and writing."""
    
    def test_xmp_content_generation(self, xmp_writer):
        """Test XMP content is generated with correct structure."""
        content = xmp_writer.generate_xmp_content(46.495356, 12.061609)
        
        assert '<?xpacket begin' in content
        assert '<x:xmpmeta' in content
        assert '<exif:GPSLatitude>' in content
        assert '<exif:GPSLongitude>' in content
        assert '<?xpacket end' in content
    
    def test_xmp_content_contains_coordinates(self, xmp_writer):
        """Test XMP content includes the GPS coordinates."""
        content = xmp_writer.generate_xmp_content(46.495356, 12.061609)
        
        # Should contain N and E for positive coordinates
        assert 'N' in content  # Latitude direction
        assert 'E' in content  # Longitude direction
    
    def test_write_xmp_file_creates_file(self, xmp_writer):
        """Test that XMP file is created."""
        xmp_path = xmp_writer.write_xmp_file(
            "IMG_1234.jpg",
            46.495356,
            12.061609
        )
        
        assert xmp_path.exists()
        assert xmp_path.name == "IMG_1234.jpg.xmp"
    
    def test_write_xmp_file_content(self, xmp_writer):
        """Test that written XMP file has correct content."""
        xmp_path = xmp_writer.write_xmp_file(
            "IMG_1234.jpg",
            46.495356,
            12.061609
        )
        
        with open(xmp_path, 'r') as f:
            content = f.read()
        
        assert '<?xpacket begin' in content
        assert '<exif:GPSLatitude>46,' in content
        assert '<exif:GPSLongitude>12,' in content
    
    def test_write_xmp_file_creates_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        xmp_dir = tmp_path / "nonexistent" / "xmp"
        writer = XMPWriter(output_directory=xmp_dir)
        
        xmp_path = writer.write_xmp_file("IMG_1234.jpg", 46.495356, 12.061609)
        
        assert xmp_dir.exists()
        assert xmp_path.exists()
    
    def test_write_xmp_file_negative_coordinates(self, xmp_writer):
        """Test XMP file for southern/western coordinates."""
        xmp_path = xmp_writer.write_xmp_file(
            "IMG_5678.jpg",
            -41.199469,
            -71.826794
        )
        
        with open(xmp_path, 'r') as f:
            content = f.read()
        
        assert '<exif:GPSLatitude>41,' in content
        assert 'S' in content  # South
        assert '<exif:GPSLongitude>71,' in content
        assert 'W' in content  # West
    
    def test_validate_xmp_format_valid(self, xmp_writer):
        """Test XMP format validation for valid content."""
        content = xmp_writer.generate_xmp_content(46.495356, 12.061609)
        
        assert xmp_writer.validate_xmp_format(content) is True
    
    def test_validate_xmp_format_invalid_missing_begin(self, xmp_writer):
        """Test validation fails for missing xpacket begin."""
        invalid_content = """<x:xmpmeta>
        <exif:GPSLatitude>46,29.71N</exif:GPSLatitude>
        </x:xmpmeta>"""
        
        assert xmp_writer.validate_xmp_format(invalid_content) is False
    
    def test_validate_xmp_format_invalid_missing_coordinates(self, xmp_writer):
        """Test validation fails for missing GPS coordinates."""
        invalid_content = """<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
        <x:xmpmeta xmlns:x='adobe:ns:meta/'>
        </x:xmpmeta>
        <?xpacket end='w'?>"""
        
        assert xmp_writer.validate_xmp_format(invalid_content) is False
    
    def test_write_multiple_xmp_files(self, xmp_writer):
        """Test writing multiple XMP files."""
        photos = [
            ("IMG_1234.jpg", 46.495356, 12.061609),
            ("IMG_5678.jpg", -41.199469, -71.826794),
            ("IMG_9999.jpg", 0.0, 0.0),
        ]
        
        paths = [xmp_writer.write_xmp_file(name, lat, lon) for name, lat, lon in photos]
        
        assert len(paths) == 3
        assert all(p.exists() for p in paths)
        assert xmp_writer.output_directory.exists()
    
    def test_xmp_file_overwrite(self, xmp_writer):
        """Test that writing to same filename overwrites existing file."""
        # Write first file
        xmp_writer.write_xmp_file("IMG_1234.jpg", 46.495356, 12.061609)
        
        # Write to same filename with different coordinates
        xmp_writer.write_xmp_file("IMG_1234.jpg", 50.0, 10.0)
        
        # Check that file has new coordinates
        xmp_path = xmp_writer.output_directory / "IMG_1234.jpg.xmp"
        with open(xmp_path, 'r') as f:
            content = f.read()
        
        assert '<exif:GPSLatitude>50,' in content
        assert '<exif:GPSLongitude>10,' in content
