"""
Path Planning Module for Robot Mower Advanced

This module implements advanced path planning algorithms for efficient lawn mowing.
Various patterns are supported including grid, spiral, parallel lines, perimeter-first,
zigzag, and adaptive patterns based on lawn characteristics.
"""

import math
import numpy as np
import logging
from enum import Enum
from typing import List, Tuple, Dict, Optional, Any, Union
from dataclasses import dataclass

# Import helper functions
from .path_planning_helper import (
    compute_convex_hull, is_point_in_polygon, is_point_in_any_polygon,
    clip_line_to_boundary, offset_polygon_inward, is_simple_polygon,
    polygon_area, is_roughly_circular
)

# Types for type hints
Point = Tuple[float, float]  # (x, y)
Path = List[Point]           # List of points forming a path
Polygon = List[Point]        # List of points forming a polygon


class MowingPattern(Enum):
    """Supported mowing patterns for different terrain and efficiency needs"""
    GRID = "grid"                  # Grid pattern (perpendicular lines in both directions)
    PARALLEL_LINES = "lines"       # Simple back and forth parallel lines
    SPIRAL = "spiral"              # Spiral from outside to inside (or reverse)
    PERIMETER_FIRST = "perimeter"  # Mow perimeter, then fill in the middle
    ZIGZAG = "zigzag"              # Zigzag pattern (efficient for rectangular areas)
    ADAPTIVE = "adaptive"          # Adjust pattern based on lawn shape and obstacles
    RANDOM = "random"              # Random coverage (useful for certain scenarios)


@dataclass
class PathPlanningConfig:
    """Configuration for path planning parameters"""
    pattern: MowingPattern = MowingPattern.PARALLEL_LINES
    
    # Direction for parallel lines (degrees, 0 = East, 90 = North)
    line_direction: float = 0.0
    
    # Path generation parameters
    path_overlap_percent: float = 10.0    # Percentage of mower width to overlap
    reverse_direction: bool = False       # Start from inside instead of outside for spiral
    
    # Perimeter settings
    perimeter_passes: int = 2             # Number of passes around perimeter
    
    # Adaptive pattern settings
    adaptivity_weight: float = 0.5        # 0-1, how much to adapt to lawn shape
    obstacle_buffer: float = 0.2          # Buffer around obstacles (meters)
    
    # Completion metrics
    target_coverage: float = 98.0         # Target coverage percentage
    timeout_minutes: int = 120            # Maximum time allowed for complete mowing


class PathPlanner:
    """
    Path planner for robotic lawn mower that generates efficient
    mowing paths based on lawn boundaries, obstacles, and other constraints.
    """
    
    def __init__(self, mower_width: float, config: Optional[PathPlanningConfig] = None):
        """
        Initialize the path planner
        
        Args:
            mower_width: Width of the mower blade/cutting area in meters
            config: Configuration for path planning (optional)
        """
        self.logger = logging.getLogger("PathPlanner")
        self.mower_width = mower_width
        self.config = config or PathPlanningConfig()
        
        # Calculate the effective path width considering overlap
        overlap_meters = self.mower_width * (self.config.path_overlap_percent / 100.0)
        self.effective_width = self.mower_width - overlap_meters
        
        self.logger.debug(f"Initialized path planner with mower width {mower_width}m "
                          f"and effective width {self.effective_width}m")
    
    def plan_path(self, boundary: Polygon, 
                 obstacles: List[Polygon] = None, 
                 dock_position: Point = None) -> Path:
        """
        Generate a mowing path based on lawn boundary and obstacles
        
        Args:
            boundary: List of (x,y) points defining the lawn boundary
            obstacles: List of polygons defining obstacles within the lawn
            dock_position: Starting/ending position (x,y) for the mower
            
        Returns:
            List of (x,y) points defining the mowing path
        """
        obstacles = obstacles or []
        
        self.logger.info(f"Planning path with pattern {self.config.pattern.value}")
        self.logger.debug(f"Boundary has {len(boundary)} points, "
                          f"{len(obstacles)} obstacles defined")
        
        if dock_position:
            self.logger.debug(f"Dock position: {dock_position}")
        
        # Select and execute the appropriate path planning algorithm based on pattern
        if self.config.pattern == MowingPattern.GRID:
            path = self._plan_grid_pattern(boundary, obstacles)
        elif self.config.pattern == MowingPattern.PARALLEL_LINES:
            path = self._plan_parallel_lines(boundary, obstacles)
        elif self.config.pattern == MowingPattern.SPIRAL:
            path = self._plan_spiral_pattern(boundary, obstacles)
        elif self.config.pattern == MowingPattern.PERIMETER_FIRST:
            path = self._plan_perimeter_first(boundary, obstacles)
        elif self.config.pattern == MowingPattern.ZIGZAG:
            path = self._plan_zigzag_pattern(boundary, obstacles)
        elif self.config.pattern == MowingPattern.ADAPTIVE:
            path = self._plan_adaptive_pattern(boundary, obstacles)
        elif self.config.pattern == MowingPattern.RANDOM:
            path = self._plan_random_pattern(boundary, obstacles)
        else:
            self.logger.warning(f"Unknown pattern {self.config.pattern}, falling back to parallel lines")
            path = self._plan_parallel_lines(boundary, obstacles)
        
        # Optimize the path
        path = self._optimize_path(path, dock_position)
        
        self.logger.info(f"Generated path with {len(path)} points")
        return path
    
    def _optimize_path(self, path: Path, dock_position: Optional[Point] = None) -> Path:
        """
        Optimize the path for efficiency and ensure it starts/ends at dock position
        
        Args:
            path: The initial path generated
            dock_position: The dock position to start/end at
            
        Returns:
            Optimized path
        """
        if not path:
            return path
        
        # If a dock position is specified, ensure the path starts and ends there
        if dock_position:
            # Insert dock position at start if it's not already there
            if path[0] != dock_position:
                path.insert(0, dock_position)
            
            # Append dock position at end if it's not already there
            if path[-1] != dock_position:
                path.append(dock_position)
        
        # Remove unnecessary zigzags or turns
        path = self._smooth_path(path)
        
        # Remove points that are too close together
        path = self._simplify_path(path)
        
        return path
    
    def _smooth_path(self, path: Path) -> Path:
        """Smooth the path by removing unnecessary turns"""
        if len(path) < 3:
            return path
        
        smoothed_path = [path[0]]
        
        # Define a tolerance for collinearity (in radians)
        # If angle between segments is less than this, consider them collinear
        collinearity_tolerance = math.radians(5)
        
        for i in range(1, len(path) - 1):
            # Calculate vectors between points
            v1 = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
            v2 = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
            
            # Calculate magnitudes
            mag_v1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag_v2 = math.sqrt(v2[0]**2 + v2[1]**2)
            
            # Avoid division by zero
            if mag_v1 == 0 or mag_v2 == 0:
                smoothed_path.append(path[i])
                continue
            
            # Calculate dot product and angle between vectors
            dot_product = v1[0]*v2[0] + v1[1]*v2[1]
            cos_angle = dot_product / (mag_v1 * mag_v2)
            
            # Clamp cos_angle to [-1, 1] to avoid domain errors in acos
            cos_angle = max(-1, min(1, cos_angle))
            angle = math.acos(cos_angle)
            
            # If the angle is greater than our tolerance (not collinear), keep the point
            if angle > collinearity_tolerance:
                smoothed_path.append(path[i])
        
        # Always include the last point
        smoothed_path.append(path[-1])
        return smoothed_path
    
    def _simplify_path(self, path: Path) -> Path:
        """Remove redundant points that are too close together"""
        if len(path) < 2:
            return path
        
        # Define a minimum distance between points
        min_distance = self.mower_width / 10
        min_distance_squared = min_distance ** 2
        
        simplified_path = [path[0]]
        
        for i in range(1, len(path)):
            # Calculate squared distance between current point and last point in simplified path
            dx = path[i][0] - simplified_path[-1][0]
            dy = path[i][1] - simplified_path[-1][1]
            distance_squared = dx**2 + dy**2
            
            # If distance is greater than our threshold, add the point
            if distance_squared > min_distance_squared:
                simplified_path.append(path[i])
        
        # Make sure we include the last point
        if simplified_path[-1] != path[-1]:
            simplified_path.append(path[-1])
            
        return simplified_path
    
    def _plan_grid_pattern(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """Generate a grid pattern (horizontal then vertical passes)"""
        # First create a path with horizontal lines
        horizontal_path = self._plan_parallel_lines(boundary, obstacles, direction_deg=0)
        
        # Then create a path with vertical lines
        vertical_path = self._plan_parallel_lines(boundary, obstacles, direction_deg=90)
        
        # Combine the paths
        return horizontal_path + vertical_path
    
    def _plan_parallel_lines(self, boundary: Polygon, obstacles: List[Polygon], 
                            direction_deg: Optional[float] = None) -> Path:
        """Generate parallel lines pattern with specified or configured direction"""
        if direction_deg is None:
            direction_deg = self.config.line_direction
        
        # Convert boundary to numpy array for easier manipulation
        boundary_np = np.array(boundary)
        
        # Get bounding box of the boundary
        min_x, min_y = np.min(boundary_np, axis=0)
        max_x, max_y = np.max(boundary_np, axis=0)
        
        # Convert direction to radians
        direction_rad = math.radians(direction_deg)
        
        # Calculate perpendicular direction for the lines
        perp_direction_rad = direction_rad + math.pi/2
        perp_vector = (math.cos(perp_direction_rad), math.sin(perp_direction_rad))
        
        # Calculate line direction vector
        line_vector = (math.cos(direction_rad), math.sin(direction_rad))
        
        # Determine the diagonal length of the bounding box
        diagonal_length = math.sqrt((max_x - min_x)**2 + (max_y - min_y)**2)
        
        # Calculate center of the boundary for starting the pattern
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center = (center_x, center_y)
        
        # Calculate number of lines (assuming diagonal distance in both directions)
        num_lines = math.ceil(diagonal_length / self.effective_width) * 2 + 1
        
        # Generate the lines
        path = []
        for i in range(-num_lines//2, num_lines//2 + 1):
            # Calculate offset from center for this line
            offset = i * self.effective_width
            
            # Calculate start and end points for this line
            # Make lines longer than diagonal to ensure coverage
            line_length = diagonal_length * 1.5
            
            # Calculate the offset perpendicular to the line direction
            offset_x = perp_vector[0] * offset
            offset_y = perp_vector[1] * offset
            
            # Calculate the line start and end points
            start_x = center_x + offset_x - line_vector[0] * line_length/2
            start_y = center_y + offset_y - line_vector[1] * line_length/2
            end_x = center_x + offset_x + line_vector[0] * line_length/2
            end_y = center_y + offset_y + line_vector[1] * line_length/2
            
            # Clip the line to the boundary and add to path
            line_points = self._clip_line_to_boundary(
                (start_x, start_y), (end_x, end_y), boundary, obstacles)
            
            # If we have valid line points and they form a line (not just a point)
            if line_points and len(line_points) >= 2:
                # Alternate the direction of each line (for efficient back-and-forth)
                if i % 2 == 0:
                    path.extend(line_points)
                else:
                    path.extend(reversed(line_points))
                
                # If this isn't the last line, add a connecting segment to the next line
                if i < num_lines//2 and path:
                    # If we have a valid next line, connect to its starting point
                    next_i = i + 1
                    next_offset = next_i * self.effective_width
                    next_offset_x = perp_vector[0] * next_offset
                    next_offset_y = perp_vector[1] * next_offset
                    next_start_x = center_x + next_offset_x - line_vector[0] * line_length/2
                    next_start_y = center_y + next_offset_y - line_vector[1] * line_length/2
                    next_end_x = center_x + next_offset_x + line_vector[0] * line_length/2
                    next_end_y = center_y + next_offset_y + line_vector[1] * line_length/2
                    
                    next_line_points = self._clip_line_to_boundary(
                        (next_start_x, next_start_y), (next_end_x, next_end_y), boundary, obstacles)
                    
                    if next_line_points and len(next_line_points) >= 2:
                        # Get the start point of the next line (possibly reversed)
                        if next_i % 2 == 0:
                            next_start = next_line_points[0]
                        else:
                            next_start = next_line_points[-1]
                        
                        # Add a connecting point to the path
                        path.append(next_start)
        
        return path
    
    def _plan_spiral_pattern(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """Generate a spiral pattern from outside to inside or vice versa"""
        # Convert boundary to numpy array for easier manipulation
        boundary_np = np.array(boundary)
        
        # Get bounding box and center of the boundary
        min_x, min_y = np.min(boundary_np, axis=0)
        max_x, max_y = np.max(boundary_np, axis=0)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Calculate the maximum radius needed
        width = max_x - min_x
        height = max_y - min_y
        max_radius = math.sqrt(width**2 + height**2) / 2
        
        # Calculate number of spiral loops
        num_loops = math.ceil(max_radius / self.effective_width)
        
        # Generate points along the spiral
        path = []
        theta_step = math.pi / 36  # 5 degrees in radians
        
        # Direction of spiral (inward or outward)
        reverse = self.config.reverse_direction
        
        for i in range(num_loops * 72 + 1):  # 72 steps for 360 degrees
            theta = theta_step * i
            
            # Calculate radius that gradually increases/decreases
            if reverse:
                # Start from inside and spiral outward
                radius = (i / (num_loops * 72)) * max_radius
            else:
                # Start from outside and spiral inward
                radius = max_radius - (i / (num_loops * 72)) * max_radius
            
            # Calculate point coordinates
            x = center_x + radius * math.cos(theta)
            y = center_y + radius * math.sin(theta)
            
            # Add point to path if it's within the boundary
            if self._is_point_in_polygon((x, y), boundary):
                path.append((x, y))
        
        return path
    
    def _plan_perimeter_first(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """Generate a perimeter-first pattern, then fill in with parallel lines"""
        path = []
        
        # First, mow the perimeter multiple times
        for i in range(self.config.perimeter_passes):
            # Create an offset boundary (moving inward)
            offset_dist = i * self.effective_width
            offset_boundary = self._offset_polygon_inward(boundary, offset_dist)
            
            # Skip if the offset boundary is invalid
            if not offset_boundary or len(offset_boundary) < 3:
                continue
            
            # Add the perimeter path (and return to start)
            perimeter_path = offset_boundary.copy()
            perimeter_path.append(offset_boundary[0])  # Close the loop
            
            # Add to the overall path
            if i == 0 or not path:
                # First perimeter or if path is empty
                path.extend(perimeter_path)
            else:
                # Connect from the end of previous path to this perimeter
                path.append(perimeter_path[0])
                path.extend(perimeter_path)
        
        # Calculate the inner area offset from the boundary
        inner_offset = self.config.perimeter_passes * self.effective_width
        inner_boundary = self._offset_polygon_inward(boundary, inner_offset)
        
        # If we still have a valid inner area, fill it with parallel lines
        if inner_boundary and len(inner_boundary) >= 3:
            # Fill the inner area with parallel lines
            inner_path = self._plan_parallel_lines(inner_boundary, obstacles)
            
            # Connect the perimeter path with the inner path
            if path and inner_path:
                # Add a connecting point from last perimeter point to first inner path point
                path.append(inner_path[0])
                # Add the rest of the inner path
                path.extend(inner_path[1:])
        
        return path
    
    def _plan_zigzag_pattern(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """Generate a zigzag pattern which is efficient for rectangular areas"""
        # This is essentially a variation of parallel lines with a different connection strategy
        # between lines
        
        # Choose the dominant direction based on the shape of the lawn
        boundary_np = np.array(boundary)
        min_x, min_y = np.min(boundary_np, axis=0)
        max_x, max_y = np.max(boundary_np, axis=0)
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Choose line direction perpendicular to the longest side
        direction_deg = 0 if width < height else 90
        
        # Generate base parallel lines
        return self._plan_parallel_lines(boundary, obstacles, direction_deg=direction_deg)
    
    def _plan_adaptive_pattern(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """
        Generate an adaptive pattern that adjusts based on lawn shape.
        For complex lawns, this combines multiple approaches.
        """
        # Analyze lawn shape to determine the best approach
        boundary_np = np.array(boundary)
        
        # Calculate convex hull ratio as a measure of complexity
        convex_hull = self._compute_convex_hull(boundary)
        
        if len(convex_hull) == 0 or len(boundary) == 0:
            return self._plan_parallel_lines(boundary, obstacles)
            
        # Calculate areas
        hull_area = self._polygon_area(convex_hull)
        boundary_area = self._polygon_area(boundary)
        
        if hull_area == 0:
            # Fallback to standard pattern if calculation fails
            return self._plan_parallel_lines(boundary, obstacles)
        
        # Ratio of actual area to convex hull area (1.0 = convex, <1.0 = complex)
        convexity_ratio = boundary_area / hull_area
        
        # Choose pattern based on shape analysis
        if convexity_ratio > 0.9:
            # Near-convex shape: Good for spiral or simple parallel lines
            if self._is_roughly_circular(boundary):
                return self._plan_spiral_pattern(boundary, obstacles)
            else:
                return self._plan_parallel_lines(boundary, obstacles)
        elif convexity_ratio > 0.7:
            # Moderately complex: Perimeter first then fill
            return self._plan_perimeter_first(boundary, obstacles)
        else:
            # Very complex shape: Divide and conquer
            return self._plan_divide_and_conquer(boundary, obstacles)
    
    def _plan_random_pattern(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """
        Generate a random coverage pattern.
        This can be useful for certain scenarios, especially in smaller spaces.
        """
        # Convert boundary to numpy array for easier manipulation
        boundary_np = np.array(boundary)
        
        # Get bounding box of the boundary
        min_x, min_y = np.min(boundary_np, axis=0)
        max_x, max_y = np.max(boundary_np, axis=0)
        
        # Calculate the area of the bounding box
        width = max_x - min_x
        height = max_y - min_y
        
        # Estimate the area of the lawn
        lawn_area = self._polygon_area(boundary)
        
        # Estimate how many points we need to ensure coverage
        # Each point represents a position, and we'll create paths between them
        points_needed = int(lawn_area / (self.mower_width**2)) * 2
        points_needed = max(points_needed, 50)  # Ensure minimum number of points
        
        # Generate random points within the boundary
        valid_points = []
        attempts = 0
        max_attempts = points_needed * 10  # Limit attempts to avoid infinite loop
        
        while len(valid_points) < points_needed and attempts < max_attempts:
            # Generate a random point within the bounding box
            x = min_x + np.random.rand() * width
            y = min_y + np.random.rand() * height
            
            # Check if the point is within the boundary and not in an obstacle
            if self._is_point_in_polygon((x, y), boundary) and not self._is_point_in_any_polygon((x, y), obstacles):
                valid_points.append((x, y))
            
            attempts += 1
        
        # If we couldn't generate enough points, fall back to a simpler pattern
        if len(valid_points) < 10:
            self.logger.warning("Not enough valid points for random pattern, falling back to parallel lines")
            return self._plan_parallel_lines(boundary, obstacles)
        
        # Create a path that visits these points using a nearest neighbor approach
        path = [valid_points[0]]
        remaining_points = valid_points[1:]
        
        while remaining_points:
            # Find the closest point to the last point in the path
            curr_point = path[-1]
            min_dist = float('inf')
            closest_idx = -1
            
            for i, point in enumerate(remaining_points):
                dist = math.sqrt((point[0] - curr_point[0])**2 + (point[1] - curr_point[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            
            # Add the closest point to the path
            path.append(remaining_points[closest_idx])
            # Remove it from remaining points
            remaining_points.pop(closest_idx)
        
        return path
    
    def _plan_divide_and_conquer(self, boundary: Polygon, obstacles: List[Polygon]) -> Path:
        """
        Divide complex lawns into simpler regions and plan paths for each.
        This is a more advanced algorithm for handling complex shapes.
        """
        # For now, we'll use a simplified approximation
        # In a real implementation, this would use clustering or Voronoi diagrams
        
        # Use parallel lines with alternating directions as a simplification
        path1 = self._plan_parallel_lines(boundary, obstacles, direction_deg=0)
        path2 = self._plan_parallel_lines(boundary, obstacles, direction_deg=90)
        
        # Combine the paths
        # We take half of each to ensure good coverage without excessive redundancy
        half_len1 = len(path1) // 2
        half_len2 = len(path2) // 2
        
        # Alternate between horizontal and vertical paths
        combined_path = path1[:half_len1]
        
        # Add a transition point if needed
        if combined_path and path2:
            combined_path.append(path2[0])
        
        combined_path.extend(path2[:half_len2])
        
        return combined_path
    
    def _offset_polygon_inward(self, polygon: Polygon, offset_distance: float) -> Polygon:
        """Create an inward offset of a polygon boundary"""
        if offset_distance <= 0:
            return polygon
        
        # Convert to numpy for easier vector operations
        poly_np = np.array(polygon)
        
        # If the polygon doesn't have enough points, return empty
        if len(poly_np) < 3:
            return []
        
        # Create a new polygon with offset edges
        offset_polygon = []
        
        for i in range(len(poly_np)):
            # Get current, previous, and next points
            curr = poly_np[i]
            prev = poly_np[i-1]  # Wraps to last point when i=0
            next_point = poly_np[(i+1) % len(poly_np)]
            
            # Calculate normal vectors for previous and next edges
            prev_edge = curr - prev
            next_edge = next_point - curr
            
            # Normalize the edge vectors
            prev_len = np.linalg.norm(prev_edge)
            next_len = np.linalg.norm(next_edge)
            
            if prev_len > 0 and next_len > 0:
                prev_norm = prev_edge / prev_len
                next_norm = next_edge / next_len
                
                # Calculate normal vectors (90 degrees clockwise rotation for inward offset)
                prev_normal = np.array([-prev_norm[1], prev_norm[0]])
                next_normal = np.array([-next_norm[1], next_norm[0]])
                
                # Average the normals for a smooth offset
                avg_normal = (prev_normal + next_normal) / 2
                
                # Normalize the average normal
                avg_normal_len = np.linalg.norm(avg_normal)
                if avg_normal_len > 0:
                    avg_normal = avg_normal / avg_normal_len
                    
                    # Calculate offset point
                    offset_point = curr + avg_normal * offset_distance
                    offset_polygon.append((offset_point[0], offset_point[1]))
        
        # Check if resulting polygon has enough points and is not self-intersecting
        if len(offset_polygon) >= 3:
            # Simple check for self-intersection (more sophisticated checks would be used in production)
            if not self._is_simple_polygon(offset_polygon):
                return []
            return offset_polygon
        else:
            return []
    
    def _is_simple_polygon(self, polygon: Polygon) -> bool:
        """
        Check if a polygon is simple (non-self-intersecting).
        This is a simplified check - a real implementation would use more sophisticated algorithms.
        """
        # For now, calculate the area as a rough check
        area = self._polygon_area(polygon)
        return area > 0
    
    def _polygon_area(self, polygon: Polygon) -> float:
        """Calculate the area of a polygon using the Shoelace formula"""
        if len(polygon) < 3:
            return 0
        
        area = 0.0
        for i in range(len(polygon)):
            j = (i + 1) % len(polygon)
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        
        return abs(area) / 2.0
    
    def _is_roughly_circular(self, polygon: Polygon) -> bool:
        """Determine if a polygon is roughly circular in shape"""
        # Calculate centroid
        centroid_x = sum(p[0] for p in polygon) / len(polygon)
        centroid_y = sum(p[1] for p in polygon) / len(polygon)
        
        # Calculate average distance from centroid to boundary points
        avg_distance = sum(math.sqrt((p[0] - centroid_x)**2 + (p[1] - centroid_y)**2) for p in polygon) / len(polygon)
        
        # Calculate standard deviation of distances
        variance = sum((math.sqrt((p[0] - centroid_x)**2 + (p[1] - centroid_y)**2) - avg_distance)**2 for p in polygon) / len(polygon)
        std_dev = math.sqrt(variance)
        
        # If standard deviation is small relative to average distance, it's roughly circular
        circularity = std_dev / avg_distance if avg_distance > 0 else float('inf')
        return circularity < 0.2  # Threshold can be adjusted
    
    def _compute_convex_hull(self, polygon: Polygon) -> Polygon:
        """
        Compute the convex hull of a polygon using the Graham scan algorithm.
        """
        return compute_convex_hull(polygon)
    
    def _is_point_in_polygon(self, point: Point, polygon: Polygon) -> bool:
        """Check if a point is inside a polygon"""
        return is_point_in_polygon(point, polygon)
    
    def _is_point_in_any_polygon(self, point: Point, polygons: List[Polygon]) -> bool:
        """Check if a point is inside any of a list of polygons"""
        return is_point_in_any_polygon(point, polygons)
    
    def _clip_line_to_boundary(self, start: Point, end: Point, boundary: Polygon, obstacles: List[Polygon] = None) -> List[Point]:
        """Clip a line to a boundary polygon"""
        return clip_line_to_boundary(start, end, boundary, obstacles)
