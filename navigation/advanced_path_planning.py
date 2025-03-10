"""
Advanced Path Planning Module for Robot Mower Advanced

This module implements sophisticated path planning algorithms for efficient lawn mowing,
including various patterns, dynamic obstacle avoidance, and integration with SLAM.
"""

import os
import time
import logging
import numpy as np
import math
import cv2
from typing import List, Dict, Tuple, Optional, Union, Any
from enum import Enum
from dataclasses import dataclass
import threading
import json

# Import local modules
from perception.slam.slam_core import SlamMap, SlamSystem


class MowingPattern(Enum):
    """Enumeration of available mowing patterns"""
    PARALLEL = "parallel"
    SPIRAL = "spiral"
    ZIGZAG = "zigzag"
    PERIMETER_FIRST = "perimeter_first"
    ADAPTIVE = "adaptive"
    CUSTOM = "custom"


@dataclass
class PathSegment:
    """Represents a segment of a planned path"""
    start: Tuple[float, float]
    end: Tuple[float, float]
    type: str = "straight"  # "straight", "curve", "rotate"
    radius: float = 0.0  # Used for curved segments
    speed: float = 1.0  # Relative speed (0.0-1.0)
    mowing_active: bool = True  # Whether the mower blades should be active


@dataclass
class Zone:
    """Represents a mowing zone with specific parameters"""
    id: str
    name: str
    perimeter: List[Tuple[float, float]]  # Boundary points (clockwise order)
    pattern: MowingPattern = MowingPattern.PARALLEL
    direction_degrees: float = 0.0  # Pattern orientation (for parallel/zigzag)
    overlap_percent: float = 10.0  # Overlap between adjacent passes
    cutting_height_mm: int = 50
    priority: int = 1  # Higher value = higher priority
    avoid_obstacles: bool = True
    schedule: Dict[str, Any] = None  # Custom scheduling for this zone
    custom_parameters: Dict[str, Any] = None  # Pattern-specific parameters


class ObstacleType(Enum):
    """Types of obstacles with different avoidance behaviors"""
    UNKNOWN = 0
    STATIC = 1  # Permanent obstacles (trees, garden beds)
    DYNAMIC = 2  # Moving obstacles (people, animals)
    TEMPORARY = 3  # Temporary obstacles (toys, tools)
    RESTRICTED = 4  # No-go areas (flower beds)


@dataclass
class Obstacle:
    """Represents an obstacle in the environment"""
    id: str
    position: Tuple[float, float]
    radius: float  # Simplified as circular obstacles
    type: ObstacleType = ObstacleType.UNKNOWN
    confidence: float = 1.0  # Detection confidence (0.0-1.0)
    last_seen: float = 0.0  # Timestamp
    velocity: Optional[Tuple[float, float]] = None  # For dynamic obstacles


class PathPlanner:
    """
    Advanced path planning system for the robot mower.
    Generates efficient mowing paths based on zone definition, detected obstacles, and SLAM data.
    """
    
    def __init__(self, config: Dict[str, Any], slam_system: Optional[SlamSystem] = None):
        """Initialize the path planner"""
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.slam_system = slam_system
        
        # Path planning parameters
        self.mower_width = config.get("mower", {}).get("cutting_width_mm", 320) / 1000.0  # Convert to meters
        self.safety_margin = config.get("navigation", {}).get("safety_margin_m", 0.2)  # Meters
        self.min_turning_radius = config.get("mower", {}).get("min_turning_radius_m", 0.5)  # Meters
        
        # Load zones from configuration
        self.zones = self._load_zones()
        
        # Obstacle management
        self.obstacles = []  # List of known obstacles
        self.obstacle_lock = threading.Lock()
        
        # Current plan
        self.current_path = []  # List of PathSegment objects
        self.current_zone = None
        self.current_segment_index = 0
        self.plan_lock = threading.Lock()
        
        # Edge detection parameters
        self.edge_detection_enabled = config.get("navigation", {}).get("edge_detection_enabled", True)
        self.edge_follow_distance = config.get("navigation", {}).get("edge_follow_distance_m", 0.1)  # Meters
        
        # Progress tracking
        self.mowed_areas = []  # List of paths already mowed
        self.mowed_percentage = 0.0
        
        # Persistence
        self.data_dir = config.get("system", {}).get("data_dir", "data")
        self.zone_file = os.path.join(self.data_dir, "zone_definitions", "zones.json")
        self.coverage_file = os.path.join(self.data_dir, "coverage_history.json")
        
        # Initialize previous position values for pose graph
        self.previous_x = 0.0
        self.previous_y = 0.0
        self.previous_theta = 0.0
        
        self.logger.info("Path planner initialized")
    
    def _load_zones(self) -> List[Zone]:
        """Load zone definitions from configuration or file"""
        zones = []
        
        # Check if zone definitions file exists
        zone_file = os.path.join(self.data_dir, "zone_definitions", "zones.json")
        if os.path.exists(zone_file):
            try:
                with open(zone_file, 'r') as f:
                    zone_data = json.load(f)
                
                for zone_info in zone_data:
                    try:
                        # Parse zone data
                        zone_id = zone_info.get("id", str(len(zones)))
                        name = zone_info.get("name", f"Zone {zone_id}")
                        perimeter = zone_info.get("perimeter", [])
                        
                        # Convert perimeter string points to tuples if needed
                        if perimeter and isinstance(perimeter[0], str):
                            perimeter = [tuple(map(float, p.split(','))) for p in perimeter]
                        
                        # Get pattern type
                        pattern_str = zone_info.get("pattern", "parallel").lower()
                        try:
                            pattern = MowingPattern(pattern_str)
                        except ValueError:
                            pattern = MowingPattern.PARALLEL
                            self.logger.warning(f"Unknown mowing pattern '{pattern_str}', defaulting to PARALLEL")
                        
                        # Create zone object
                        zone = Zone(
                            id=zone_id,
                            name=name,
                            perimeter=perimeter,
                            pattern=pattern,
                            direction_degrees=zone_info.get("direction_degrees", 0.0),
                            overlap_percent=zone_info.get("overlap_percent", 10.0),
                            cutting_height_mm=zone_info.get("cutting_height_mm", 50),
                            priority=zone_info.get("priority", 1),
                            avoid_obstacles=zone_info.get("avoid_obstacles", True),
                            schedule=zone_info.get("schedule", {}),
                            custom_parameters=zone_info.get("custom_parameters", {})
                        )
                        
                        zones.append(zone)
                    except Exception as e:
                        self.logger.error(f"Error parsing zone data: {e}")
                
                self.logger.info(f"Loaded {len(zones)} zones from {zone_file}")
            except Exception as e:
                self.logger.error(f"Error loading zone definitions: {e}")
        
        # If no zones were loaded, create a default zone
        if not zones:
            self.logger.warning("No zones defined, creating default zone")
            
            # Default square zone (10m x 10m)
            default_perimeter = [
                (0.0, 0.0),
                (10.0, 0.0),
                (10.0, 10.0),
                (0.0, 10.0)
            ]
            
            zones.append(Zone(
                id="default",
                name="Default Zone",
                perimeter=default_perimeter,
                pattern=MowingPattern.PARALLEL
            ))
        
        return zones
    
    def save_zones(self) -> bool:
        """Save zone definitions to file"""
        try:
            os.makedirs(os.path.dirname(self.zone_file), exist_ok=True)
            zone_data = []
            for zone in self.zones:
                zone_dict = {
                    "id": zone.id,
                    "name": zone.name,
                    "perimeter": zone.perimeter,
                    "pattern": zone.pattern.value,
                    "direction_degrees": zone.direction_degrees,
                    "overlap_percent": zone.overlap_percent,
                    "cutting_height_mm": zone.cutting_height_mm,
                    "priority": zone.priority,
                    "avoid_obstacles": zone.avoid_obstacles,
                    "schedule": zone.schedule,
                    "custom_parameters": zone.custom_parameters
                }
                zone_data.append(zone_dict)
            
            with open(self.zone_file, 'w') as f:
                json.dump(zone_data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.zones)} zones to {self.zone_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving zone definitions: {e}")
            return False
    
    def add_zone(self, zone: Zone) -> bool:
        """Add a new zone definition"""
        for existing_zone in self.zones:
            if existing_zone.id == zone.id:
                self.logger.warning(f"Zone ID '{zone.id}' already exists")
                return False
        
        self.zones.append(zone)
        self.save_zones()
        return True
    
    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone by ID"""
        for i, zone in enumerate(self.zones):
            if zone.id == zone_id:
                self.zones.pop(i)
                self.save_zones()
                return True
        return False
    
    def update_zone(self, zone: Zone) -> bool:
        """Update an existing zone"""
        for i, existing_zone in enumerate(self.zones):
            if existing_zone.id == zone.id:
                self.zones[i] = zone
                self.save_zones()
                return True
        return False
    
    def get_zones(self) -> List[Zone]:
        """Get all defined zones"""
        return self.zones
    
    def get_zone_by_id(self, zone_id: str) -> Optional[Zone]:
        """Get a zone by ID"""
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        return None
    
    def add_obstacle(self, obstacle: Obstacle) -> None:
        """Add or update an obstacle"""
        with self.obstacle_lock:
            for i, existing_obstacle in enumerate(self.obstacles):
                if existing_obstacle.id == obstacle.id:
                    self.obstacles[i] = obstacle
                    return
            self.obstacles.append(obstacle)
    
    def remove_obstacle(self, obstacle_id: str) -> bool:
        """Remove an obstacle by ID"""
        with self.obstacle_lock:
            for i, obstacle in enumerate(self.obstacles):
                if obstacle.id == obstacle_id:
                    self.obstacles.pop(i)
                    return True
            return False
    
    def get_obstacles(self) -> List[Obstacle]:
        """Get all known obstacles"""
        with self.obstacle_lock:
            return self.obstacles.copy()
    
    def get_obstacle_by_id(self, obstacle_id: str) -> Optional[Obstacle]:
        """Get an obstacle by ID"""
        with self.obstacle_lock:
            for obstacle in self.obstacles:
                if obstacle.id == obstacle_id:
                    return obstacle
            return None
    
    def clear_obstacles(self) -> None:
        """Clear all obstacles"""
        with self.obstacle_lock:
            self.obstacles = []
    
    def plan_path_for_zone(self, zone_id: str) -> List[PathSegment]:
        """Plan a path for a specific zone"""
        zone = self.get_zone_by_id(zone_id)
        if zone is None:
            self.logger.error(f"Zone ID '{zone_id}' not found")
            return []
        
        obstacles = self.get_obstacles()
        
        with self.plan_lock:
            if zone.pattern == MowingPattern.PARALLEL:
                path = self._plan_parallel_path(zone, obstacles)
            elif zone.pattern == MowingPattern.SPIRAL:
                path = self._plan_spiral_path(zone, obstacles)
            elif zone.pattern == MowingPattern.ZIGZAG:
                path = self._plan_zigzag_path(zone, obstacles)
            elif zone.pattern == MowingPattern.PERIMETER_FIRST:
                path = self._plan_perimeter_first_path(zone, obstacles)
            elif zone.pattern == MowingPattern.ADAPTIVE:
                path = self._plan_adaptive_path(zone, obstacles)
            elif zone.pattern == MowingPattern.CUSTOM:
                path = self._plan_custom_path(zone, obstacles)
            else:
                path = self._plan_parallel_path(zone, obstacles)
            
            self.current_path = path
            self.current_zone = zone
            self.current_segment_index = 0
            
            return path
    
    def _plan_parallel_path(self, zone: Zone, obstacles: List[Obstacle]) -> List[PathSegment]:
        """Plan a parallel path pattern for the zone"""
        self.logger.info(f"Planning parallel path for zone: {zone.name}")
        
        path_segments = []
        
        # Get zone bounds
        x_coords = [p[0] for p in zone.perimeter]
        y_coords = [p[1] for p in zone.perimeter]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Get pattern direction in radians
        direction_rad = math.radians(zone.direction_degrees)
        
        # Calculate spacing between passes (cutting width minus overlap)
        overlap_meters = (zone.overlap_percent / 100.0) * self.mower_width
        spacing = self.mower_width - overlap_meters
        
        # Find perpendicular direction
        perp_direction_rad = direction_rad + math.pi / 2
        
        # Extend zone boundaries to ensure full coverage
        extension = self.mower_width / 2
        
        # Calculate axis-aligned bounding box of the zone
        aabb_width = max_x - min_x + 2 * extension
        aabb_height = max_y - min_y + 2 * extension
        
        # Number of parallel passes
        num_passes = max(2, int(math.ceil(max(aabb_width, aabb_height) / spacing)))
        
        # Generate parallel lines
        for i in range(num_passes):
            # Calculate offset from starting edge
            offset = i * spacing
            
            # Calculate endpoints of this pass
            if i % 2 == 0:
                # Even passes go in the original direction
                start_x = min_x - extension * math.cos(direction_rad) + offset * math.cos(perp_direction_rad)
                start_y = min_y - extension * math.sin(direction_rad) + offset * math.sin(perp_direction_rad)
                end_x = start_x + aabb_width * math.cos(direction_rad)
                end_y = start_y + aabb_width * math.sin(direction_rad)
            else:
                # Odd passes go in the opposite direction
                end_x = min_x - extension * math.cos(direction_rad) + offset * math.cos(perp_direction_rad)
                end_y = min_y - extension * math.sin(direction_rad) + offset * math.sin(perp_direction_rad)
                start_x = end_x + aabb_width * math.cos(direction_rad)
                start_y = end_y + aabb_width * math.sin(direction_rad)
            
            segment = PathSegment(
                start=(start_x, start_y),
                end=(end_x, end_y),
                type="straight",
                speed=1.0,
                mowing_active=True
            )
            
            path_segments.append(segment)
            
            # Add connecting segment to the next pass if needed
            if i < num_passes - 1:
                # Calculate start of next pass
                next_offset = (i + 1) * spacing
                if (i + 1) % 2 == 0:
                    next_start_x = min_x - extension * math.cos(direction_rad) + next_offset * math.cos(perp_direction_rad)
                    next_start_y = min_y - extension * math.sin(direction_rad) + next_offset * math.sin(perp_direction_rad)
                else:
                    next_start_x = min_x - extension * math.cos(direction_rad) + next_offset * math.cos(perp_direction_rad) + aabb_width * math.cos(direction_rad)
                    next_start_y = min_y - extension * math.sin(direction_rad) + next_offset * math.sin(perp_direction_rad) + aabb_width * math.sin(direction_rad)
                
                connector = PathSegment(
                    start=(end_x, end_y),
                    end=(next_start_x, next_start_y),
                    type="straight",
                    speed=1.0,
                    mowing_active=False  # Turn off mowing for transitions
                )
                
                path_segments.append(connector)
        
        # If obstacles are present and should be avoided, modify the path
        if zone.avoid_obstacles and obstacles:
            path_segments = self._avoid_obstacles(path_segments, obstacles)
        
        return path_segments
    
    def _plan_spiral_path(self, zone: Zone, obstacles: List[Obstacle]) -> List[PathSegment]:
        """Plan a spiral path pattern for the zone"""
        self.logger.info(f"Planning spiral path for zone: {zone.name}")
        
        path_segments = []
        
        # Get zone centroid
        x_coords = [p[0] for p in zone.perimeter]
        y_coords = [p[1] for p in zone.perimeter]
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        
        # Calculate zone radius (distance from centroid to furthest point)
        max_radius = 0
        for x, y in zone.perimeter:
            distance = math.sqrt((x - centroid_x)**2 + (y - centroid_y)**2)
            max_radius = max(max_radius, distance)
        
        # Calculate spacing between spiral turns
        overlap_meters = (zone.overlap_percent / 100.0) * self.mower_width
        spacing = self.mower_width - overlap_meters
        
        # Calculate number of spiral turns needed
        num_turns = math.ceil(max_radius / spacing)
        
        # Calculate spiral parameters
        # For an Archimedean spiral: r = a + b*theta
        a = spacing  # Starting radius
        b = spacing / (2 * math.pi)  # Spacing between successive turns
        
        # Generate points along the spiral
        theta_step = math.pi / 36  # 5 degrees in radians
        max_theta = 2 * math.pi * num_turns
        
        spiral_points = []
        for theta in np.arange(0, max_theta, theta_step):
            r = a + b * theta
            x = centroid_x + r * math.cos(theta)
            y = centroid_y + r * math.sin(theta)
            spiral_points.append((x, y))
        
        # Convert points to path segments
        for i in range(len(spiral_points) - 1):
            segment = PathSegment(
                start=spiral_points[i],
                end=spiral_points[i + 1],
                type="straight",  # Approximation with short straight segments
                speed=1.0,
                mowing_active=True
            )
            path_segments.append(segment)
        
        # If obstacles are present and should be avoided, modify the path
        if zone.avoid_obstacles and obstacles:
            path_segments = self._avoid_obstacles(path_segments, obstacles)
        
        return path_segments
    
    def _plan_zigzag_path(self, zone: Zone, obstacles: List[Obstacle]) -> List[PathSegment]:
        """Plan a zigzag path pattern for the zone"""
        # Simplified implementation - in real application, implement a true zigzag pattern
        self.logger.info(f"Planning zigzag path for zone: {zone.name} (simplified)")
        return self._plan_parallel_path(zone, obstacles)
    
    def _plan_perimeter_first_path(self, zone: Zone, obstacles: List[Obstacle]) -> List[PathSegment]:
        """Plan a perimeter-first path pattern (follow boundary, then fill interior)"""
        self.logger.info(f"Planning perimeter-first path for zone: {zone.name} (simplified)")
        path_segments = []
        
        # Get perimeter
        perimeter = zone.perimeter
        
        # Add extra point to close the loop if needed
        if perimeter[0] != perimeter[-1]:
            perimeter = perimeter + [perimeter[0]]
        
        # Create segments to follow the perimeter (clockwise)
        for i in range(len(perimeter) - 1):
            segment = PathSegment(
                start=perimeter[i],
                end=perimeter[i + 1],
                type="straight",
                speed=0.8,  # Slower speed for edge following
                mowing_active=True
            )
            path_segments.append(segment)
        
        # Then add parallel path for interior (simplified approach)
        interior_path = self._plan_parallel_path(zone, obstacles)
        
        if interior_path:
            # Add connecting segment between perimeter and interior path
            connector = PathSegment(
                start=perimeter[-1],
                end=interior_path[0].start,
                type="straight",
                speed=0.8,
                mowing_active=False
            )
            path_segments.append(connector)
            
            # Add interior path segments
            path_segments.extend(interior_path)
        
        # If obstacles are present and should be avoided, modify the path
        if zone.avoid_obstacles and obstacles:
            path_segments = self._avoid_obstacles(path_segments, obstacles)
        
        return path_segments
    
    def _plan_adaptive_path(self, zone: Zone, obstacles: List[Obstacle]) -> List[PathSegment]:
        """Plan an adaptive path pattern based on terrain and obstacles"""
        self.logger.info(f"Planning adaptive path for zone: {zone.name} (simplified)")
        
        # Get zone properties
        perimeter = zone.perimeter
        x_coords = [p[0] for p in perimeter]
        y_coords = [p[1] for p in perimeter]
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
        
        # Choose pattern based on shape
        if width > 2 * height or height > 2 * width:
            # Long and narrow - use parallel along long axis
            direction = 0.0 if width > height else 90.0
            
            # Create a parallel zone with optimized direction
            parallel_zone = Zone(
                id=zone.id,
                name=zone.name,
                perimeter=perimeter,
                pattern=MowingPattern.PARALLEL,
                direction_degrees=direction,
                overlap_percent=zone.overlap_percent,
                cutting_height_mm=zone.cutting_height_mm,
                avoid_obstacles=zone.avoid_obstacles
            )
            
            return self._plan_parallel_path(parallel_zone, obstacles)
        else:
            # Use perimeter-first for balanced shape
            return self._plan_perimeter_first_path(zone, obstacles)
    
    def _plan_custom_path(self, zone: Zone, obstacles: List[Obstacle]) -> List[PathSegment]:
        """Plan a custom path based on user-defined parameters"""
        # Default to parallel for simplicity
        self.logger.info(f"Planning custom path for zone: {zone.name} (simplified)")
        return self._plan_parallel_path(zone, obstacles)
    
    def _avoid_obstacles(self, path_segments: List[PathSegment], obstacles: List[Obstacle]) -> List[PathSegment]:
        """
        Modify path segments to avoid obstacles
        
        Args:
            path_segments: Original path segments
            obstacles: List of obstacles to avoid
            
        Returns:
            Modified path segments
        """
        if not obstacles:
            return path_segments
        
        self.logger.info(f"Avoiding {len(obstacles)} obstacles")
        
        # Simple implementation - just skip segments that intersect with obstacles
        new_path = []
        
        for segment in path_segments:
            start_x, start_y = segment.start
            end_x, end_y = segment.end
            
            # Check if this segment intersects with any obstacle
            intersects_obstacle = False
            for obstacle in obstacles:
                if obstacle.confidence < 0.5:  # Skip low-confidence obstacles
                    continue
                
                # Get obstacle data
                obs_x, obs_y = obstacle.position
                obs_radius = obstacle.radius + self.safety_margin
                
                # Check if line segment intersects with obstacle circle
                # Vector from start to end
                dx = end_x - start_x
                dy = end_y - start_y
                
                # Skip zero-length segments
                if dx*dx + dy*dy < 0.0001:
                    continue
                
                # Vector from start to obstacle
                ox = obs_x - start_x
                oy = obs_y - start_y
                
                # Project obstacle onto line segment
                t = max(0, min(1, (ox*dx + oy*dy) / (dx*dx + dy*dy)))
                
                # Closest point on line segment to obstacle
                closest_x = start_x + t * dx
                closest_y = start_y + t * dy
                
                # Distance from obstacle to closest point
                dist = math.sqrt((closest_x - obs_x)**2 + (closest_y - obs_y)**2)
                
                if dist < obs_radius:
                    intersects_obstacle = True
                    break
            
            if not intersects_obstacle:
                # Keep segments that don't intersect with obstacles
                new_path.append(segment)
        
        return new_path
    
    def get_current_path(self) -> List[PathSegment]:
        """Get the currently planned path"""
        with self.plan_lock:
            return self.current_path.copy()
    
    def get_next_segment(self) -> Optional[PathSegment]:
        """Get the next path segment to follow"""
        with self.plan_lock:
            if not self.current_path or self.current_segment_index >= len(self.current_path):
                return None
            
            return self.current_path[self.current_segment_index]
    
    def advance_to_next_segment(self) -> bool:
        """Advance to the next segment in the current path"""
        with self.plan_lock:
            if not self.current_path or self.current_segment_index >= len(self.current_path) - 1:
                return False
            
            self.current_segment_index += 1
            return True
    
    def get_mowing_progress(self) -> float:
        """Get the current mowing progress as a percentage"""
        return self.mowed_percentage
    
    def update_mowing_progress(self, completed_segment: PathSegment) -> None:
        """Update the mowing progress tracking"""
        # Add to list of completed segments
        if completed_segment.mowing_active:
            self.mowed_areas.append(completed_segment)
            
            # Update progress percentage (simplified calculation)
            if self.current_path:
                # Count how many mowing segments we've completed
                completed_count = sum(1 for i, segment in enumerate(self.current_path) 
                                    if i <= self.current_segment_index and segment.mowing_active)
                total_count = sum(1 for segment in self.current_path if segment.mowing_active)
                
                if total_count > 0:
                    self.mowed_percentage = 100.0 * completed_count / total_count
    
    def reset_path(self) -> None:
        """Reset the current path"""
        with self.plan_lock:
            self.current_path = []
            self.current_segment_index = 0
            self.mowed_percentage = 0.0
