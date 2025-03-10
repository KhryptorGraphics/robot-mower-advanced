"""
Perception package for Robot Mower Advanced.

This package contains modules for environmental perception, including
object detection, obstacle avoidance, and vision-based navigation.
"""

from .hailo_integration import HailoObjectDetector, ObstacleDetectionSystem

__all__ = ['HailoObjectDetector', 'ObstacleDetectionSystem']
