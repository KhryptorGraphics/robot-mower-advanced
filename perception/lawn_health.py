"""
Lawn Health Analysis Module

This module provides functionality for analyzing the health of the lawn using
computer vision and machine learning techniques to identify problems such as
brown patches, overgrowth, and other issues.
"""

import os
import time
import logging
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ..hardware.interfaces import Camera


class GrassHealthStatus(Enum):
    """Enumeration of grass health statuses"""
    HEALTHY = "healthy"
    NEEDS_WATER = "needs_water"
    OVERGROWN = "overgrown"
    DISEASED = "diseased"
    WEED_INFESTED = "weed_infested"
    DAMAGED = "damaged"
    UNKNOWN = "unknown"


@dataclass
class LawnHealthReport:
    """Class for representing lawn health analysis results"""
    timestamp: datetime
    overall_health: float  # 0-1 score
    health_status: GrassHealthStatus
    issues: List[Dict[str, Any]]
    coverage_map: Optional[np.ndarray] = None
    recommendations: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a dictionary for storage/transmission"""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "overall_health": self.overall_health,
            "health_status": self.health_status.value,
            "issues": self.issues,
            "recommendations": self.recommendations or []
        }
        
        # Don't include the coverage map in the dict (too large)
        # But indicate if it exists
        result["has_coverage_map"] = self.coverage_map is not None
        
        return result


class LawnHealthAnalyzer:
    """
    Class for analyzing lawn health using computer vision
    
    This analyzer processes camera images to detect grass health issues and
    provides recommendations for lawn care.
    """
    
    def __init__(self, config: Dict[str, Any], sensors: Dict[str, Any]):
        """
        Initialize the lawn health analyzer
        
        Args:
            config: Configuration dictionary
            sensors: Dictionary of sensors
        """
        self.logger = logging.getLogger(__name__)
        self.sensors = sensors
        self.camera = sensors.get("camera") if sensors else None
        
        # Configuration
        self.config = config
        self.analysis_interval = config.get("analysis_interval", 3600)  # Default: 1 hour
        self.save_images = config.get("save_images", True)
        self.image_save_path = config.get("image_save_path", "data/lawn_images")
        self.report_save_path = config.get("report_save_path", "data/lawn_reports")
        self.model_path = config.get("model_path", "models/lawn_health_model.h5")
        
        # Create necessary directories
        os.makedirs(self.image_save_path, exist_ok=True)
        os.makedirs(self.report_save_path, exist_ok=True)
        
        # State
        self.last_analysis_time = 0
        self.last_report = None
        self.healthy_grass_reference = None
        self.health_history = []
        
        # Load healthy grass reference if available
        reference_path = os.path.join(self.image_save_path, "healthy_reference.jpg")
        if os.path.exists(reference_path):
            try:
                self.healthy_grass_reference = cv2.imread(reference_path)
                self.logger.info("Loaded healthy grass reference image")
            except Exception as e:
                self.logger.warning(f"Failed to load healthy grass reference: {e}")
        
        self.logger.info("Lawn health analyzer initialized")
    
    def should_run_analysis(self) -> bool:
        """Determine if it's time to run a new analysis"""
        current_time = time.time()
        return (current_time - self.last_analysis_time) >= self.analysis_interval
    
    def analyze_health(self, force: bool = False) -> Optional[LawnHealthReport]:
        """
        Analyze the health of the lawn
        
        Args:
            force: If True, run analysis regardless of the interval
            
        Returns:
            LawnHealthReport if analysis was performed, None otherwise
        """
        if not force and not self.should_run_analysis():
            return None
        
        self.logger.info("Starting lawn health analysis")
        self.last_analysis_time = time.time()
        
        try:
            # Capture an image from the camera
            image = self.camera.capture_image()
            
            # Save the image if configured to do so
            if self.save_images:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join(self.image_save_path, f"lawn_{timestamp}.jpg")
                cv2.imwrite(image_path, image)
                self.logger.debug(f"Saved lawn image to {image_path}")
            
            # Process the image
            # In a real implementation, this would use more sophisticated 
            # computer vision and ML techniques
            report = self._analyze_image(image)
            
            # Save the report
            report_path = os.path.join(
                self.report_save_path, 
                f"report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # In a real implementation, save the report to JSON
            # import json
            # with open(report_path, 'w') as f:
            #     json.dump(report.to_dict(), f, indent=2)
            
            # Keep track of history (limited to 10 entries for memory)
            self.health_history.append(report)
            if len(self.health_history) > 10:
                self.health_history.pop(0)
            
            self.last_report = report
            return report
            
        except Exception as e:
            self.logger.error(f"Error during lawn health analysis: {e}")
            return None
    
    def _analyze_image(self, image: np.ndarray) -> LawnHealthReport:
        """
        Analyze a lawn image to determine health
        
        Args:
            image: Image as numpy array
            
        Returns:
            LawnHealthReport with analysis results
        """
        # This is a simplified simulation of grass health analysis
        # A real implementation would use computer vision and ML techniques
        
        # Convert to HSV for better color analysis
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Extract the green channel (hue around 60 in HSV)
        # This is a simplistic approach - real systems would be more sophisticated
        green_mask = cv2.inRange(hsv_image, (40, 50, 50), (80, 255, 255))
        brown_mask = cv2.inRange(hsv_image, (10, 50, 50), (30, 255, 255))
        
        # Calculate coverage percentages
        total_pixels = image.shape[0] * image.shape[1]
        green_pixels = cv2.countNonZero(green_mask)
        brown_pixels = cv2.countNonZero(brown_mask)
        
        green_percentage = green_pixels / total_pixels
        brown_percentage = brown_pixels / total_pixels
        
        # Determine overall health score (0-1)
        overall_health = max(0, min(1, green_percentage / 0.7))
        
        # Create a coverage map
        coverage_map = np.zeros(image.shape[:2], dtype=np.uint8)
        coverage_map[green_mask > 0] = 2  # Healthy
        coverage_map[brown_mask > 0] = 1  # Unhealthy
        
        # Determine health status
        health_status = GrassHealthStatus.UNKNOWN
        issues = []
        recommendations = []
        
        if overall_health > 0.8:
            health_status = GrassHealthStatus.HEALTHY
            issues = []
            recommendations = ["Maintain current lawn care routine"]
        elif brown_percentage > 0.3:
            health_status = GrassHealthStatus.NEEDS_WATER
            issues = [{
                "type": "brown_patches",
                "severity": brown_percentage,
                "coverage": f"{brown_percentage:.1%}"
            }]
            recommendations = ["Increase watering schedule", "Consider checking soil nutrients"]
        elif green_percentage < 0.5:
            health_status = GrassHealthStatus.DAMAGED
            issues = [{
                "type": "sparse_coverage",
                "severity": 1 - green_percentage,
                "coverage": f"{green_percentage:.1%}"
            }]
            recommendations = ["Consider reseeding sparse areas", "Check for soil compaction"]
        else:
            health_status = GrassHealthStatus.OVERGROWN
            issues = [{
                "type": "overgrowth",
                "severity": 0.5,
                "coverage": "General"
            }]
            recommendations = ["Schedule more frequent mowing"]
        
        # Create the report
        return LawnHealthReport(
            timestamp=datetime.now(),
            overall_health=overall_health,
            health_status=health_status,
            issues=issues,
            coverage_map=coverage_map,
            recommendations=recommendations
        )
    
    def set_healthy_reference(self, image: np.ndarray) -> bool:
        """
        Set a reference image for healthy grass
        
        Args:
            image: Image of healthy grass as numpy array
            
        Returns:
            Success or failure
        """
        try:
            self.healthy_grass_reference = image.copy()
            
            # Save the reference image
            reference_path = os.path.join(self.image_save_path, "healthy_reference.jpg")
            cv2.imwrite(reference_path, image)
            
            self.logger.info("Set new healthy grass reference image")
            return True
        except Exception as e:
            self.logger.error(f"Error setting healthy grass reference: {e}")
            return False
    
    def get_lawn_health_trend(self) -> Dict[str, Any]:
        """
        Get the trend of lawn health over time
        
        Returns:
            Dictionary with trend information
        """
        if not self.health_history:
            return {
                "available": False,
                "message": "No health history available"
            }
        
        # Calculate average health over time
        timestamps = [report.timestamp.isoformat() for report in self.health_history]
        health_scores = [report.overall_health for report in self.health_history]
        
        # Calculate trend (positive or negative)
        trend = 0
        if len(health_scores) >= 2:
            # Simple linear trend
            trend = health_scores[-1] - health_scores[0]
        
        return {
            "available": True,
            "timestamps": timestamps,
            "health_scores": health_scores,
            "trend": trend,
            "trend_description": "improving" if trend > 0 else "declining" if trend < 0 else "stable",
            "current_health": health_scores[-1] if health_scores else None
        }
    
    def get_problem_areas(self) -> List[Dict[str, Any]]:
        """
        Identify problem areas in the lawn
        
        Returns:
            List of problem areas with position and severity
        """
        if self.last_report is None or self.last_report.coverage_map is None:
            return []
        
        # This would use computer vision to identify regions of unhealthy grass
        # For this simplified implementation, we'll just return mock data
        
        # In a real implementation, we would:
        # 1. Use connected component analysis on the coverage map
        # 2. Filter to find significant brown/unhealthy regions
        # 3. Map these to real-world coordinates using the mower's position
        
        # Mock data for demonstration purposes
        return [
            {
                "id": 1,
                "type": "brown_patch",
                "center_position": [2.5, 3.2],  # x, y coordinates in meters
                "size": 0.8,  # approximate size in sq meters
                "severity": 0.7,  # 0-1 score
                "first_detected": (datetime.now().isoformat())
            },
            {
                "id": 2,
                "type": "weed_patch",
                "center_position": [5.1, 1.8],
                "size": 0.3,
                "severity": 0.5,
                "first_detected": (datetime.now().isoformat())
            }
        ]
