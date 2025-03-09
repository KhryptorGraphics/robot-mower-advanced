"""
Camera Implementations

Provides concrete implementations of camera interfaces for
video streaming, image capture, and computer vision.
"""

import time
import threading
import logging
import numpy as np
from typing import Dict, Tuple, Optional, Any

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    # Use a mock for development without PiCamera
    from unittest.mock import MagicMock
    Picamera2 = MagicMock()

from ..interfaces import Camera
from ...core.config import ConfigManager


class RaspberryPiCamera(Camera):
    """Implementation of a camera using Raspberry Pi Camera Module"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the camera"""
        self.config = config
        self.logger = logging.getLogger("Camera")
        self._is_initialized = False
        
        # Get configuration
        self._width = config.get("hardware.sensors.camera.width", 1280)
        self._height = config.get("hardware.sensors.camera.height", 720)
        self._fps = config.get("hardware.sensors.camera.fps", 30)
        self._format = config.get("hardware.sensors.camera.format", "RGB")
        
        # State
        self._camera = None
        self._streaming = False
        self._last_frame = None
        self._frame_lock = threading.Lock()
    
    def initialize(self) -> bool:
        """Initialize the camera hardware"""
        if not PICAMERA_AVAILABLE:
            self.logger.error("picamera2 is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Initialize camera
            self._camera = Picamera2()
            
            # Configure camera
            self._configure_camera()
            
            self._is_initialized = True
            self.logger.info("Camera initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing camera: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def _configure_camera(self) -> None:
        """Configure the camera with current settings"""
        if not self._camera:
            return
        
        # Create configuration
        config = self._camera.create_preview_configuration(
            main={"size": (self._width, self._height)},
            lores={"size": (640, 480), "format": "YUV420"}
        )
        
        # Apply configuration
        self._camera.configure(config)
    
    def capture_image(self) -> np.ndarray:
        """Capture a still image"""
        if not self._is_initialized or not self._camera:
            self.logger.error("Camera not initialized")
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        try:
            # If streaming, return the latest frame
            if self._streaming:
                with self._frame_lock:
                    if self._last_frame is not None:
                        return self._last_frame.copy()
            
            # Otherwise, capture a new image
            self._camera.start()
            time.sleep(0.5)  # Give the camera time to adjust
            
            # Capture image
            image = self._camera.capture_array()
            
            # Stop the camera if not streaming
            if not self._streaming:
                self._camera.stop()
            
            return image
            
        except Exception as e:
            self.logger.error(f"Error capturing image: {str(e)}")
            return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def start_video_stream(self) -> bool:
        """Start the video stream"""
        if not self._is_initialized or not self._camera:
            self.logger.error("Camera not initialized")
            return False
        
        if self._streaming:
            return True
        
        try:
            # Start the camera
            self._camera.start()
            self._streaming = True
            
            # Start a thread to update the frame buffer
            threading.Thread(
                target=self._frame_update_loop,
                daemon=True,
                name="CameraUpdateThread"
            ).start()
            
            self.logger.info("Video stream started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting video stream: {str(e)}")
            return False
    
    def _frame_update_loop(self) -> None:
        """Loop to update the frame buffer"""
        while self._streaming and self._camera:
            try:
                # Capture a frame
                frame = self._camera.capture_array()
                
                # Update the frame buffer
                with self._frame_lock:
                    self._last_frame = frame
                
                # Sleep to control frame rate
                time.sleep(1.0 / self._fps)
                
            except Exception as e:
                self.logger.error(f"Error in frame update loop: {str(e)}")
                time.sleep(0.1)
    
    def stop_video_stream(self) -> None:
        """Stop the video stream"""
        self._streaming = False
        
        if self._camera:
            self._camera.stop()
        
        self.logger.info("Video stream stopped")
    
    def get_frame(self) -> np.ndarray:
        """Get the latest frame from the video stream"""
        if not self._streaming:
            self.logger.warning("Video stream not started")
            return self.capture_image()
        
        with self._frame_lock:
            if self._last_frame is not None:
                return self._last_frame.copy()
            else:
                return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def set_resolution(self, width: int, height: int) -> bool:
        """Set the camera resolution"""
        if not self._is_initialized:
            self.logger.error("Camera not initialized")
            return False
        
        # Store current streaming state
        was_streaming = self._streaming
        
        # Stop streaming if active
        if was_streaming:
            self.stop_video_stream()
        
        # Update resolution
        self._width = width
        self._height = height
        
        # Reconfigure camera
        self._configure_camera()
        
        # Restart streaming if it was active
        if was_streaming:
            self.start_video_stream()
        
        self.logger.info(f"Camera resolution set to {width}x{height}")
        return True
    
    def get_resolution(self) -> Tuple[int, int]:
        """Get the current camera resolution"""
        return (self._width, self._height)
    
    def cleanup(self) -> None:
        """Clean up resources used by the camera"""
        if self._streaming:
            self.stop_video_stream()
        
        if self._camera:
            try:
                self._camera.close()
            except:
                pass
            self._camera = None
        
        self._is_initialized = False
        self.logger.info("Camera cleaned up")
