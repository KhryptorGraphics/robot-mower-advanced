"""
GPS Sensor Implementations

Provides concrete implementations of GPS sensors for
position and navigation capabilities.
"""

import time
import threading
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    # Use a mock for development without serial
    from unittest.mock import MagicMock
    serial = MagicMock()

from ..interfaces import GPSSensor, GPSPosition
from ...core.config import ConfigManager


class NMEAGPSSensor(GPSSensor):
    """Implementation of a GPS sensor that uses NMEA protocol over serial"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the GPS sensor"""
        self.config = config
        self.logger = logging.getLogger("GPSSensor")
        self._is_initialized = False
        
        # Get configuration
        self._port = config.get("hardware.sensors.gps.uart_port", "/dev/ttyS0")
        self._baud_rate = config.get("hardware.sensors.gps.baud_rate", 9600)
        self._update_rate = config.get("hardware.sensors.gps.update_rate", 1)  # Hz
        
        # State
        self._serial = None
        self._running = False
        self._read_thread = None
        self._position = None
        self._speed = 0.0
        self._heading = 0.0
        self._satellites = 0
        self._has_fix = False
        self._last_update = 0.0
        self._data_lock = threading.Lock()
    
    def initialize(self) -> bool:
        """Initialize the GPS sensor"""
        if not SERIAL_AVAILABLE:
            self.logger.error("pyserial is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Initialize serial port
            self._serial = serial.Serial(
                self._port,
                self._baud_rate,
                timeout=1.0
            )
            
            # Start the read thread
            self._start_read_thread()
            
            self._is_initialized = True
            self.logger.info("GPS sensor initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing GPS sensor: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def _start_read_thread(self) -> None:
        """Start the thread that continuously reads data from the GPS"""
        if self._running:
            return
        
        self._running = True
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name="GPS_ReadThread"
        )
        self._read_thread.start()
    
    def _stop_read_thread(self) -> None:
        """Stop the read thread"""
        self._running = False
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)
    
    def _read_loop(self) -> None:
        """Loop that continuously reads data from the GPS"""
        while self._running and self._is_initialized:
            try:
                if not self._serial or not self._serial.is_open:
                    time.sleep(1.0)
                    continue
                
                # Read a line from the GPS
                line = self._serial.readline().decode('ascii', errors='ignore').strip()
                
                if line.startswith('$'):
                    # Parse NMEA sentence
                    self._parse_nmea(line)
                
                # Sleep to control read rate
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error reading from GPS: {str(e)}")
                time.sleep(1.0)  # Longer delay on error
    
    def _parse_nmea(self, sentence: str) -> None:
        """Parse an NMEA sentence from the GPS"""
        try:
            # Check for checksum
            if '*' in sentence:
                # Strip the checksum for now (could validate it in a real implementation)
                sentence = sentence.split('*')[0]
            
            # Split the sentence into fields
            fields = sentence.split(',')
            
            # Check the sentence type
            if fields[0] == '$GPGGA':
                # Global Positioning System Fix Data
                return self._parse_gpgga(fields)
            elif fields[0] == '$GPRMC':
                # Recommended Minimum Specific GPS/Transit Data
                return self._parse_gprmc(fields)
            elif fields[0] == '$GPVTG':
                # Track Made Good and Ground Speed
                return self._parse_gpvtg(fields)
            elif fields[0] == '$GPGSA':
                # GPS DOP and active satellites
                return self._parse_gpgsa(fields)
                
        except Exception as e:
            self.logger.debug(f"Error parsing NMEA sentence: {str(e)} - {sentence}")
    
    def _parse_gpgga(self, fields: List[str]) -> None:
        """Parse a GPGGA sentence (position data)"""
        if len(fields) < 15:
            return
        
        # Extract timestamp
        try:
            time_str = fields[1]
            hours = int(time_str[0:2]) if len(time_str) >= 2 else 0
            minutes = int(time_str[2:4]) if len(time_str) >= 4 else 0
            seconds = float(time_str[4:]) if len(time_str) > 4 else 0.0
            
            timestamp = hours * 3600 + minutes * 60 + seconds
        except:
            timestamp = time.time()
        
        # Extract position
        try:
            # Check if we have a fix
            fix_quality = int(fields[6]) if fields[6] else 0
            
            with self._data_lock:
                self._has_fix = (fix_quality > 0)
                self._satellites = int(fields[7]) if fields[7] else 0
            
            if self._has_fix:
                lat_str = fields[2]
                lat_dir = fields[3]
                lon_str = fields[4]
                lon_dir = fields[5]
                
                if lat_str and lon_str:
                    # Convert DDMM.MMMM to decimal degrees
                    lat_deg = float(lat_str[0:2])
                    lat_min = float(lat_str[2:])
                    latitude = lat_deg + (lat_min / 60.0)
                    
                    lon_deg = float(lon_str[0:3])
                    lon_min = float(lon_str[3:])
                    longitude = lon_deg + (lon_min / 60.0)
                    
                    # Apply direction
                    if lat_dir == 'S':
                        latitude = -latitude
                    if lon_dir == 'W':
                        longitude = -longitude
                    
                    # Extract altitude
                    altitude = float(fields[9]) if fields[9] else 0.0
                    
                    # Create position object
                    with self._data_lock:
                        self._position = GPSPosition(
                            latitude=latitude,
                            longitude=longitude,
                            altitude=altitude,
                            accuracy=0.0,  # No accuracy info in GPGGA
                            timestamp=timestamp
                        )
                        self._last_update = time.time()
        except Exception as e:
            self.logger.debug(f"Error parsing GPGGA position: {str(e)} - {fields}")
    
    def _parse_gprmc(self, fields: List[str]) -> None:
        """Parse a GPRMC sentence (position and velocity)"""
        if len(fields) < 12:
            return
        
        try:
            # Check if we have a valid fix
            status = fields[2]
            
            with self._data_lock:
                self._has_fix = (status == 'A')  # 'A' = Active, 'V' = Void
            
            if self._has_fix:
                # Extract speed (in knots) and convert to m/s
                speed_knots = float(fields[7]) if fields[7] else 0.0
                speed_ms = speed_knots * 0.51444  # 1 knot = 0.51444 m/s
                
                # Extract heading (track angle in degrees)
                heading = float(fields[8]) if fields[8] else 0.0
                
                with self._data_lock:
                    self._speed = speed_ms
                    self._heading = heading
                
                # Extract position
                lat_str = fields[3]
                lat_dir = fields[4]
                lon_str = fields[5]
                lon_dir = fields[6]
                
                if lat_str and lon_str:
                    # Convert DDMM.MMMM to decimal degrees
                    lat_deg = float(lat_str[0:2])
                    lat_min = float(lat_str[2:])
                    latitude = lat_deg + (lat_min / 60.0)
                    
                    lon_deg = float(lon_str[0:3])
                    lon_min = float(lon_str[3:])
                    longitude = lon_deg + (lon_min / 60.0)
                    
                    # Apply direction
                    if lat_dir == 'S':
                        latitude = -latitude
                    if lon_dir == 'W':
                        longitude = -longitude
                    
                    # Extract timestamp
                    time_str = fields[1]
                    date_str = fields[9]
                    
                    if time_str and date_str:
                        hours = int(time_str[0:2]) if len(time_str) >= 2 else 0
                        minutes = int(time_str[2:4]) if len(time_str) >= 4 else 0
                        seconds = float(time_str[4:]) if len(time_str) > 4 else 0.0
                        
                        day = int(date_str[0:2]) if len(date_str) >= 2 else 0
                        month = int(date_str[2:4]) if len(date_str) >= 4 else 0
                        year = 2000 + int(date_str[4:]) if len(date_str) > 4 else 2000
                        
                        # Create a timestamp from the date and time
                        dt = datetime(year, month, day, hours, minutes, int(seconds))
                        timestamp = dt.timestamp()
                    else:
                        timestamp = time.time()
                    
                    # Create position object (with more accurate time)
                    with self._data_lock:
                        self._position = GPSPosition(
                            latitude=latitude,
                            longitude=longitude,
                            altitude=0.0,  # GPRMC doesn't have altitude
                            accuracy=0.0,  # No accuracy info in GPRMC
                            timestamp=timestamp
                        )
                        self._last_update = time.time()
        except Exception as e:
            self.logger.debug(f"Error parsing GPRMC position: {str(e)} - {fields}")
    
    def _parse_gpvtg(self, fields: List[str]) -> None:
        """Parse a GPVTG sentence (track and speed data)"""
        if len(fields) < 10:
            return
        
        try:
            # Extract true heading
            heading = float(fields[1]) if fields[1] else 0.0
            
            # Extract speed
            # Field 7 is speed in km/h
            speed_kmh = float(fields[7]) if fields[7] else 0.0
            speed_ms = speed_kmh / 3.6  # Convert km/h to m/s
            
            with self._data_lock:
                self._heading = heading
                self._speed = speed_ms
        except Exception as e:
            self.logger.debug(f"Error parsing GPVTG data: {str(e)} - {fields}")
    
    def _parse_gpgsa(self, fields: List[str]) -> None:
        """Parse a GPGSA sentence (satellite data)"""
        if len(fields) < 18:
            return
        
        try:
            # Check fix type (1 = no fix, 2 = 2D fix, 3 = 3D fix)
            fix_type = int(fields[2]) if fields[2] else 0
            
            with self._data_lock:
                self._has_fix = (fix_type > 1)
                
                # Could also extract PDOP, HDOP, VDOP from fields 15-17
                # for more accurate position quality assessment
        except Exception as e:
            self.logger.debug(f"Error parsing GPGSA data: {str(e)} - {fields}")
    
    def get_position(self) -> Optional[GPSPosition]:
        """Get the current GPS position"""
        with self._data_lock:
            if not self._has_fix or self._position is None:
                return None
            return self._position
    
    def has_fix(self) -> bool:
        """Check if the GPS has a fix"""
        with self._data_lock:
            # Also check if the fix is recent (within 10 seconds)
            if time.time() - self._last_update > 10.0:
                return False
            return self._has_fix
    
    def get_speed(self) -> float:
        """Get the current speed from GPS in m/s"""
        with self._data_lock:
            return self._speed
    
    def get_heading(self) -> float:
        """Get the current heading from GPS in degrees"""
        with self._data_lock:
            return self._heading
    
    def get_num_satellites(self) -> int:
        """Get the number of satellites in view"""
        with self._data_lock:
            return self._satellites
    
    def cleanup(self) -> None:
        """Clean up resources used by the GPS sensor"""
        self._stop_read_thread()
        
        if self._serial:
            self._serial.close()
            self._serial = None
        
        self._is_initialized = False
        self.logger.info("GPS sensor cleaned up")
