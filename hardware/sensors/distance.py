"""
Distance Sensor Implementations

Provides concrete implementations of distance sensors including
ultrasonic and other proximity detection sensors.
"""

import time
import threading
import logging
from typing import Dict, List, Tuple, Optional, Any

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from ..interfaces import DistanceSensor
