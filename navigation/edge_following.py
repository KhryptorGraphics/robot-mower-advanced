"""
Edge Following Module

This module provides specialized functionality for precisely mowing along 
the edges of the lawn, providing a neater appearance and better finish.
"""

import logging
import math
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon, LineString, Point

from ..core.config import ConfigManager
from ..hardware.interfaces import MotorController, DistanceSensor
from .zone_management import Zone, EdgeHandlingMode


class EdgeFollowingError(Exception):
    """Exception raised for errors during edge following operations"""
    pass


class EdgeFollowingMode(Enum):
    """Enumeration of edge following modes"""
    PERIMETER = "perimeter"  # Follow the outer perimeter
    NO_MOW_ZONE = "no_mow_zone"  # Follow around no-mow zones
    OBSTACLE = "obstacle"  # Follow around detected obstacles


class EdgeState(Enum):
    """Enumeration of edge following states"""
    FINDING_EDGE = "finding_edge"
    FOLLOWING_EDGE = "following_edge"
    CORRECTING = "correcting"
    LOST_EDGE = "lost_edge"
    COMPLETED = "completed"


@dataclass
class EdgeTarget:
    """Data class representing an edge to follow"""
    name: str
    points: List[Tuple[float, float]]  # List of points defining the edge
    is_closed: bool = True  # Whether the edge forms a closed loop
    completion_distance: float = 0.2  # Distance in meters to consider edge complete
    direction: str = "clockwise"  # Direction to follow the edge
    overlap: float = 0.05  # Overlap between passes in meters
    

class EdgeFollower:
    """
    Edge following controller for precise edge mowing
    
    This class provides functionality for precisely following the edges of
    a lawn or no-mow zones, ensuring a neat finish along boundaries.
    """
    
    def __init__(self, 
                 config: ConfigManager, 
                 motor_controller: MotorController,
                 distance_sensors: Dict[str, DistanceSensor]):
        """
        Initialize the edge follower
        
        Args:
            config: Configuration manager
            motor_controller: Motor controller for movement
            distance_sensors: Distance sensors for edge detection
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.motor_controller = motor_controller
        self.distance_sensors = distance_sensors
        
        # Configuration parameters
        self.edge_following_speed = config.get("edge_following.speed", 0.4)  # 0-1 scale
        self.edge_distance = config.get("edge_following.distance", 0.15)  # Target distance from edge in meters
        self.correction_factor = config.get("edge_following.correction_factor", 1.2)  # Correction strength
        self.max_correction = config.get("edge_following.max_correction", 0.7)  # Maximum correction
        self.min_edge_detection_distance = config.get("edge_following.min_distance", 0.05)  # Minimum detectable edge distance
        self.max_edge_detection_distance = config.get("edge_following.max_distance", 0.5)  # Maximum detectable edge distance
        self.completion_threshold = config.get("edge_following.completion_threshold", 0.2)  # Distance to consider complete
        self.lost_edge_threshold = config.get("edge_following.lost_edge_threshold", 3)  # Seconds before considering edge lost
        self.max_lost_distance = config.get("edge_following.max_lost_distance", 1.0)  # Maximum meters to search when edge is lost
        
        # State
        self.current_target: Optional[EdgeTarget] = None
        self.state = EdgeState.FINDING_EDGE
        self.current_position: Tuple[float, float] = (0, 0)  # Current position (x, y) in meters
        self.current_heading: float = 0  # Current heading in degrees (0 = north, 90 = east)
        self.closest_edge_point: Optional[Tuple[float, float]] = None
        self.edge_distance_error: float = 0  # Error in distance from edge
        self.edge_progress: float = 0  # Progress along edge (0-1)
        
        # Initialize
        self.logger.info("Edge follower initialized")
    
    def set_position_and_heading(self, position: Tuple[float, float], heading: float) -> None:
        """
        Update the current position and heading
        
        Args:
            position: Current position (x, y) in meters
            heading: Current heading in degrees
        """
        self.current_position = position
        self.current_heading = heading
    
    def set_edge_target(self, target: EdgeTarget) -> None:
        """
        Set a new edge target to follow
        
        Args:
            target: Edge target to follow
        """
        self.current_target = target
        self.state = EdgeState.FINDING_EDGE
        self.edge_progress = 0.0
        self.logger.info(f"New edge target set: {target.name}")
    
    def create_perimeter_target(self, zone: Zone) -> EdgeTarget:
        """
        Create an edge target for the perimeter of a zone
        
        Args:
            zone: Zone to create perimeter target for
            
        Returns:
            EdgeTarget for the zone perimeter
        """
        return EdgeTarget(
            name=f"Perimeter of {zone.name}",
            points=zone.boundary,
            is_closed=True,
            direction="clockwise",
            overlap=0.1 if zone.settings.edge_mode == EdgeHandlingMode.OVERLAP else 0.05
        )
    
    def create_no_mow_target(self, zone: Zone, no_mow_index: int) -> EdgeTarget:
        """
        Create an edge target for a no-mow zone
        
        Args:
            zone: Zone containing the no-mow zone
            no_mow_index: Index of the no-mow zone
            
        Returns:
            EdgeTarget for the no-mow zone
        """
        if no_mow_index >= len(zone.no_mow_areas):
            raise EdgeFollowingError(f"No-mow zone index {no_mow_index} out of range")
        
        return EdgeTarget(
            name=f"No-mow zone {no_mow_index} in {zone.name}",
            points=zone.no_mow_areas[no_mow_index],
            is_closed=True,
            direction="counterclockwise",  # Counter-clockwise for no-mow zones
            overlap=0.05
        )
    
    def find_nearest_edge_point(self) -> Optional[Tuple[float, float]]:
        """
        Find the nearest point on the current edge target
        
        Returns:
            Nearest edge point or None if no target set
        """
        if not self.current_target or not self.current_target.points:
            return None
        
        # Create shapely LineString from target points
        if self.current_target.is_closed:
            # Add the first point at the end to close the loop
            points = self.current_target.points + [self.current_target.points[0]]
        else:
            points = self.current_target.points
        
        edge_line = LineString(points)
        current_point = Point(self.current_position)
        
        # Find nearest point on edge
        nearest_point = edge_line.interpolate(edge_line.project(current_point))
        
        return (nearest_point.x, nearest_point.y)
    
    def calculate_edge_distance(self) -> float:
        """
        Calculate the current distance to the edge
        
        Uses distance sensors or position data to calculate the distance
        to the nearest edge.
        
        Returns:
            Distance to edge in meters or -1 if edge not detected
        """
        # Priority 1: Use distance sensors if they can see the edge
        side_sensor = self.distance_sensors.get("left")
        if side_sensor and side_sensor.is_obstacle_detected(self.max_edge_detection_distance):
            distance = side_sensor.get_distance()
            if distance >= self.min_edge_detection_distance and distance <= self.max_edge_detection_distance:
                return distance
        
        # Priority 2: Use position data and target edge if available
        if self.current_target:
            nearest_point = self.find_nearest_edge_point()
            if nearest_point:
                self.closest_edge_point = nearest_point
                return math.sqrt((nearest_point[0] - self.current_position[0])**2 + 
                                 (nearest_point[1] - self.current_position[1])**2)
        
        # Edge not detected
        return -1
    
    def calculate_heading_to_edge(self) -> float:
        """
        Calculate the heading required to reach the edge
        
        Returns:
            Heading in degrees or current heading if edge not detected
        """
        if not self.closest_edge_point:
            nearest_point = self.find_nearest_edge_point()
            if not nearest_point:
                return self.current_heading
            self.closest_edge_point = nearest_point
        
        # Calculate angle to closest edge point
        dx = self.closest_edge_point[0] - self.current_position[0]
        dy = self.closest_edge_point[1] - self.current_position[1]
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # Convert to 0-360 range
        if angle_deg < 0:
            angle_deg += 360
        
        return angle_deg
    
    def calculate_edge_direction(self) -> float:
        """
        Calculate the direction to follow along the edge
        
        Returns:
            Direction heading in degrees
        """
        if not self.current_target or not self.closest_edge_point:
            return self.current_heading
        
        # Find the next point along the edge
        next_point = self._find_next_edge_point()
        if not next_point:
            return self.current_heading
        
        # Calculate direction vector along the edge
        edge_dx = next_point[0] - self.closest_edge_point[0]
        edge_dy = next_point[1] - self.closest_edge_point[1]
        
        # Calculate perpendicular direction (90 degrees offset for right side)
        if self.current_target.direction == "clockwise":
            perp_dx = -edge_dy
            perp_dy = edge_dx
        else:  # counterclockwise
            perp_dx = edge_dy
            perp_dy = -edge_dx
        
        # Normalize the perpendicular vector
        magnitude = math.sqrt(perp_dx**2 + perp_dy**2)
        if magnitude > 0:
            perp_dx /= magnitude
            perp_dy /= magnitude
        
        # Calculate the desired position (edge point + perpendicular vector * target distance)
        desired_x = self.closest_edge_point[0] + perp_dx * self.edge_distance
        desired_y = self.closest_edge_point[1] + perp_dy * self.edge_distance
        
        # Calculate direction from current position to desired position
        dx = desired_x - self.current_position[0]
        dy = desired_y - self.current_position[1]
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # Convert to 0-360 range
        if angle_deg < 0:
            angle_deg += 360
        
        return angle_deg
    
    def _find_next_edge_point(self) -> Optional[Tuple[float, float]]:
        """
        Find the next point along the edge
        
        Returns:
            Next edge point or None if not found
        """
        if not self.current_target or not self.closest_edge_point:
            return None
        
        # Create shapely LineString from target points
        if self.current_target.is_closed:
            # Add the first point at the end to close the loop
            points = self.current_target.points + [self.current_target.points[0]]
        else:
            points = self.current_target.points
        
        # Find the index of the closest segment
        min_distance = float('inf')
        closest_segment_idx = 0
        
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            # Check if closest_edge_point is on this segment
            line = LineString([p1, p2])
            point = Point(self.closest_edge_point)
            
            distance = line.distance(point)
            if distance < min_distance:
                min_distance = distance
                closest_segment_idx = i
        
        # Determine the next point based on direction
        if self.current_target.direction == "clockwise":
            next_idx = (closest_segment_idx + 1) % len(points)
        else:  # counterclockwise
            next_idx = (closest_segment_idx - 1) % len(points)
        
        return points[next_idx]
    
    def calculate_edge_progress(self) -> float:
        """
        Calculate progress along the edge (0-1)
        
        Returns:
            Progress as a fraction (0-1)
        """
        if not self.current_target or not self.closest_edge_point:
            return 0.0
        
        # Create shapely LineString from target points
        if self.current_target.is_closed:
            # Add the first point at the end to close the loop
            points = self.current_target.points + [self.current_target.points[0]]
        else:
            points = self.current_target.points
        
        edge_line = LineString(points)
        total_length = edge_line.length
        
        # Find the distance along the edge to the closest point
        project_distance = edge_line.project(Point(self.closest_edge_point))
        
        # Calculate progress
        return project_distance / total_length if total_length > 0 else 0.0
    
    def update(self) -> Dict[str, Any]:
        """
        Update the edge follower state
        
        Should be called regularly from the main control loop
        
        Returns:
            Status dictionary with current state
        """
        if not self.current_target:
            return {
                "state": EdgeState.FINDING_EDGE.value,
                "progress": 0.0,
                "message": "No edge target set"
            }
        
        # Update distances
        edge_distance = self.calculate_edge_distance()
        self.edge_distance_error = edge_distance - self.edge_distance if edge_distance >= 0 else 0
        
        # Update closest edge point
        self.closest_edge_point = self.find_nearest_edge_point()
        
        # Update state machine
        if self.state == EdgeState.FINDING_EDGE:
            if edge_distance >= 0 and edge_distance <= self.max_edge_detection_distance:
                self.state = EdgeState.FOLLOWING_EDGE
                self.logger.info("Edge found, transitioning to following")
            else:
                # Handle finding edge logic
                pass
                
        elif self.state == EdgeState.FOLLOWING_EDGE:
            if edge_distance < 0 or edge_distance > self.max_edge_detection_distance:
                self.state = EdgeState.LOST_EDGE
                self.logger.warning("Lost edge, attempting to recover")
            elif abs(self.edge_distance_error) > self.edge_distance * 0.5:
                self.state = EdgeState.CORRECTING
                self.logger.debug("Edge distance error too large, correcting")
            else:
                # Update progress
                self.edge_progress = self.calculate_edge_progress()
                
                # Check if completed
                if self.is_edge_complete():
                    self.state = EdgeState.COMPLETED
                    self.logger.info("Edge following completed")
                
        elif self.state == EdgeState.CORRECTING:
            if edge_distance < 0 or edge_distance > self.max_edge_detection_distance:
                self.state = EdgeState.LOST_EDGE
                self.logger.warning("Lost edge during correction, attempting to recover")
            elif abs(self.edge_distance_error) <= self.edge_distance * 0.2:
                self.state = EdgeState.FOLLOWING_EDGE
                self.logger.debug("Correction complete, resuming edge following")
                
        elif self.state == EdgeState.LOST_EDGE:
            if edge_distance >= 0 and edge_distance <= self.max_edge_detection_distance:
                self.state = EdgeState.FOLLOWING_EDGE
                self.logger.info("Edge recovered, resuming following")
                
        elif self.state == EdgeState.COMPLETED:
            # Nothing to do in completed state
            pass
        
        # Return status
        return {
            "state": self.state.value,
            "progress": self.edge_progress,
            "distance": edge_distance,
            "distance_error": self.edge_distance_error,
            "closest_point": self.closest_edge_point,
            "message": f"Edge following: {self.state.value}, progress: {self.edge_progress:.1%}"
        }
    
    def get_motor_commands(self) -> Tuple[float, float]:
        """
        Get motor commands for the current state
        
        Returns:
            Tuple of (left_speed, right_speed) in range -1 to 1
        """
        base_speed = self.edge_following_speed
        
        if self.state == EdgeState.FINDING_EDGE:
            # Head toward the edge
            target_heading = self.calculate_heading_to_edge()
            return self._heading_to_motor_commands(target_heading, base_speed)
            
        elif self.state == EdgeState.FOLLOWING_EDGE:
            # Follow along the edge
            following_heading = self.calculate_edge_direction()
            
            # Apply small correction based on distance error
            correction = self.edge_distance_error * self.correction_factor
            correction = max(-self.max_correction, min(correction, self.max_correction))
            
            # Apply the correction
            left_speed = base_speed
            right_speed = base_speed
            
            if correction > 0:  # Too far from edge, turn toward it
                right_speed -= correction
            else:  # Too close to edge, turn away from it
                left_speed += correction
                
            return (left_speed, right_speed)
            
        elif self.state == EdgeState.CORRECTING:
            # Strong correction to get back to the right distance
            correction = self.edge_distance_error * self.correction_factor * 1.5
            correction = max(-self.max_correction, min(correction, self.max_correction))
            
            # Apply the correction
            left_speed = base_speed * 0.8  # Slow down during correction
            right_speed = base_speed * 0.8
            
            if correction > 0:  # Too far from edge, turn toward it
                right_speed -= correction
            else:  # Too close to edge, turn away from it
                left_speed += correction
                
            return (left_speed, right_speed)
            
        elif self.state == EdgeState.LOST_EDGE:
            # Try to find the edge again
            # This is a simplistic approach - in a real system this would be more sophisticated
            # and might involve backtracking or other recovery behaviors
            target_heading = self.calculate_heading_to_edge()
            return self._heading_to_motor_commands(target_heading, base_speed * 0.6)  # Slow down when lost
            
        elif self.state == EdgeState.COMPLETED:
            # Stop when completed
            return (0.0, 0.0)
        
        # Default
        return (0.0, 0.0)
    
    def _heading_to_motor_commands(self, target_heading: float, base_speed: float) -> Tuple[float, float]:
        """
        Convert a target heading to motor commands
        
        Args:
            target_heading: Target heading in degrees (0-360)
            base_speed: Base speed for motors
            
        Returns:
            Tuple of (left_speed, right_speed)
        """
        # Calculate heading error
        heading_error = target_heading - self.current_heading
        
        # Normalize to -180 to 180
        if heading_error > 180:
            heading_error -= 360
        elif heading_error < -180:
            heading_error += 360
        
        # Scale by turning factor
        turning_factor = min(1.0, abs(heading_error) / 90.0) * 0.5
        
        # Apply turning adjustment
        if heading_error > 0:
            # Turn right
            left_speed = base_speed
            right_speed = base_speed * (1 - turning_factor * 2)
        else:
            # Turn left
            left_speed = base_speed * (1 - turning_factor * 2)
            right_speed = base_speed
        
        return (left_speed, right_speed)
    
    def is_edge_complete(self) -> bool:
        """
        Check if edge following is complete
        
        Returns:
            True if edge following is complete
        """
        if not self.current_target or self.edge_progress < 0.98:
            return False
        
        if not self.current_target.is_closed:
            # For non-closed edges, completing the path is enough
            return self.edge_progress >= 0.98
        
        # For closed edges, check if we're back near the starting point
        if self.closest_edge_point and len(self.current_target.points) > 0:
            start_point = self.current_target.points[0]
            distance_to_start = math.sqrt((self.closest_edge_point[0] - start_point[0])**2 + 
                                         (self.closest_edge_point[1] - start_point[1])**2)
            return distance_to_start <= self.current_target.completion_distance
        
        return False
    
    def execute_edge_following(self, 
                               update_position_callback: Callable[[], Tuple[float, float]],
                               update_heading_callback: Callable[[], float]) -> Dict[str, Any]:
        """
        Execute an edge following operation until completion
        
        Args:
            update_position_callback: Callback to get current position
            update_heading_callback: Callback to get current heading
            
        Returns:
            Status dictionary with results
        """
        if not self.current_target:
            return {
                "success": False,
                "message": "No edge target set"
            }
        
        self.logger.info(f"Starting edge following for {self.current_target.name}")
        self.state = EdgeState.FINDING_EDGE
        
        while self.state != EdgeState.COMPLETED:
            # Update position and heading
            self.current_position = update_position_callback()
            self.current_heading = update_heading_callback()
            
            # Update state
            status = self.update()
            
            # Get motor commands
            left_speed, right_speed = self.get_motor_commands()
            
            # Apply motor commands
            self.motor_controller.set_speed(left_speed, right_speed)
            
            # In a real system, you would wait for the next control cycle
            # We're simulating that here
            # time.sleep(0.1)
            
            # Break if operation takes too long (for safety)
            if self.state == EdgeState.LOST_EDGE and status.get("lost_time", 0) > 30:
                self.logger.error("Edge following failed: Edge lost for too long")
                return {
                    "success": False,
                    "message": "Edge following failed: Edge lost for too long"
                }
        
        # Stop motors
        self.motor_controller.stop()
        
        self.logger.info(f"Edge following completed for {self.current_target.name}")
        return {
            "success": True,
            "message": f"Edge following completed for {self.current_target.name}",
            "progress": self.edge_progress,
            "state": self.state.value
        }
