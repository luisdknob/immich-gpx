"""
XMP sidecar file generation for GPS coordinates.

Generates XMP sidecar files in Immich-compatible format for external library photos.
GPS coordinates are converted from decimal format to Immich's XMP format
(Degrees, Decimal Minutes).

Classes:
    XMPWriter: Generate and write XMP files with GPS data
    
Functions:
    convert_decimal_to_xmp_format(): Convert decimal GPS to DD,MM.MMMMMMM[N/S/E/W]
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from xml.etree import ElementTree as ET


def convert_decimal_to_xmp_format(latitude: float, longitude: float) -> Tuple[str, str]:
    """
    Convert decimal GPS coordinates to Immich XMP format.
    
    Immich XMP format: DD,MM.MMMMMMM[N/S/E/W]
    Example: 46,29.71342201N (46 degrees, 29.71342201 decimal minutes North)
    
    Args:
        latitude: Decimal latitude (-90 to 90)
        longitude: Decimal longitude (-180 to 180)
        
    Returns:
        Tuple of (latitude_xmp, longitude_xmp) in Immich format
        
    Example:
        >>> lat, lon = convert_decimal_to_xmp_format(46.495356, 12.061609)
        >>> lat
        '46,29.71342201N'
        >>> lon
        '12,3.69654540E'
    """
    # Convert latitude
    lat_degrees = int(latitude)
    lat_minutes = (abs(latitude) - abs(lat_degrees)) * 60
    lat_direction = 'N' if latitude >= 0 else 'S'
    latitude_xmp = f"{abs(lat_degrees)},{lat_minutes:.8f}{lat_direction}"
    
    # Convert longitude
    lon_degrees = int(longitude)
    lon_minutes = (abs(longitude) - abs(lon_degrees)) * 60
    lon_direction = 'E' if longitude >= 0 else 'W'
    longitude_xmp = f"{abs(lon_degrees)},{lon_minutes:.8f}{lon_direction}"
    
    return latitude_xmp, longitude_xmp


class XMPWriter:
    """Generate and write XMP sidecar files with GPS data."""
    
    # Immich XMP template
    XMP_TEMPLATE = """<?xpacket begin='﻿' id=''?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='immich-gpx v.1.1.0'>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>

 <rdf:Description rdf:about=''
  xmlns:exif='http://ns.adobe.com/exif/1.0/'>
  <exif:GPSLatitude>{latitude}</exif:GPSLatitude>
  <exif:GPSLongitude>{longitude}</exif:GPSLongitude>
 </rdf:Description>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
    
    def __init__(
        self,
        output_directory: Path = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize XMP writer.
        
        Args:
            output_directory: Directory to write XMP files (default: ./xmp/)
            logger: Logger instance
        """
        self.output_directory = Path(output_directory) if output_directory else Path("./xmp")
        self.logger = logger or logging.getLogger("immich-gpx")
    
    def generate_xmp_content(self, latitude: float, longitude: float) -> str:
        """
        Generate XMP file content with GPS coordinates.
        
        Args:
            latitude: Decimal latitude
            longitude: Decimal longitude
            
        Returns:
            XMP file content as string
        """
        lat_xmp, lon_xmp = convert_decimal_to_xmp_format(latitude, longitude)
        return self.XMP_TEMPLATE.format(latitude=lat_xmp, longitude=lon_xmp)
    
    def write_xmp_file(
        self,
        photo_filename: str,
        latitude: float,
        longitude: float,
    ) -> Path:
        """
        Write XMP sidecar file for a photo.
        
        Args:
            photo_filename: Original photo filename
            latitude: Decimal latitude
            longitude: Decimal longitude
            
        Returns:
            Path to created XMP file
            
        Raises:
            OSError: If file write fails
        """
        # Create output directory if needed
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Generate XMP filename (add .xmp extension)
        xmp_filename = f"{photo_filename}.xmp"
        xmp_filepath = self.output_directory / xmp_filename
        
        # Generate XMP content
        xmp_content = self.generate_xmp_content(latitude, longitude)
        
        # Write file
        try:
            with open(xmp_filepath, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
            self.logger.debug(f"Created XMP file: {xmp_filepath}")
            return xmp_filepath
        except OSError as e:
            self.logger.error(f"Failed to write XMP file {xmp_filepath}: {e}")
            raise
    
    def validate_xmp_format(self, xmp_content: str) -> bool:
        """
        Validate XMP file format.
        
        Args:
            xmp_content: XMP file content
            
        Returns:
            True if valid XMP format
        """
        try:
            # Check for required XML elements
            if '<?xpacket begin' not in xmp_content:
                return False
            if '<x:xmpmeta' not in xmp_content:
                return False
            if '<exif:GPSLatitude>' not in xmp_content:
                return False
            if '<exif:GPSLongitude>' not in xmp_content:
                return False
            if '<?xpacket end' not in xmp_content:
                return False
            return True
        except Exception as e:
            self.logger.error(f"XMP validation error: {e}")
            return False
