"""
Path Planning Helper Methods for Robot Mower Advanced

This module contains helper methods for the path planning algorithms.
"""

import math
import numpy as np
from typing import List, Tuple, Optional

# Types for type hints
Point = Tuple[float, float]  # (x, y)
Vector = Tuple[float, float]  # (x, y)
Path = List[Point]           # List of points forming a path
Polygon = List[Point]        # List of points forming a polygon


def compute_convex_hull(points: List[Point]) -> Polygon:
    """
    Compute the convex hull of a set of points using the Graham scan algorithm.
    
    Args:
        points: List of points
        
    Returns:
        Convex hull as a list of points
    """
    # Need at least 3 points for a convex hull
    if len(points) < 3:
        return points
    
    # Find the point with the lowest y-coordinate (and leftmost if tied)
    lowest_point = min(points, key=lambda p: (p[1], p[0]))
    
    # Sort points by polar angle with respect to the lowest point
    def polar_angle(p):
        return math.atan2(p[1] - lowest_point[1], p[0] - lowest_point[0])
    
    sorted_points = sorted(points, key=polar_angle)
    
    # Initialize the hull with the first three points
    hull = [sorted_points[0], sorted_points[1], sorted_points[2]]
    
    # Process the remaining points
    for i in range(3, len(sorted_points)):
        # Remove points that make a non-left turn
        while len(hull) > 1 and not is_left_turn(hull[-2], hull[-1], sorted_points[i]):
            hull.pop()
        
        hull.append(sorted_points[i])
    
    return hull


def is_left_turn(p1: Point, p2: Point, p3: Point) -> bool:
    """
    Determine if three points make a left turn.
    
    Args:
        p1, p2, p3: Three points
        
    Returns:
        True if the points make a left turn, False otherwise
    """
    return ((p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])) > 0


def clip_line_to_boundary(start: Point, end: Point, boundary: Polygon, 
                          obstacles: List[Polygon] = None) -> List[Point]:
    """
    Clip a line to a boundary polygon, including obstacles.
    
    Args:
        start: Starting point of the line
        end: Ending point of the line
        boundary: Boundary polygon
        obstacles: List of obstacle polygons
        
    Returns:
        Clipped line as a list of points
    """
    obstacles = obstacles or []
    
    # Check if start and end are inside the boundary
    start_inside = is_point_in_polygon(start, boundary)
    end_inside = is_point_in_polygon(end, boundary)
    
    # If both points are outside, check if the line intersects the boundary
    if not start_inside and not end_inside:
        intersections = find_line_polygon_intersections(start, end, boundary)
        if len(intersections) >= 2:
            # Line passes through the boundary at least twice
            # Sort intersections by distance from start point
            intersections.sort(key=lambda p: (p[0] - start[0])**2 + (p[1] - start[1])**2)
            
            # Take the first and last intersections as the clipped line
            return [intersections[0], intersections[-1]]
        elif len(intersections) == 1:
            # Line touches the boundary at one point
            return [intersections[0]]
        else:
            # Line is completely outside
            return []
    
    # If one point is inside and one is outside, find the intersection
    if start_inside != end_inside:
        intersections = find_line_polygon_intersections(start, end, boundary)
        if intersections:
            if start_inside:
                return [start, intersections[0]]
            else:
                return [intersections[0], end]
        else:
            # No intersections, something's wrong
            return []
    
    # Both points are inside the boundary
    
    # Check if the line passes through any obstacles
    for obstacle in obstacles:
        intersections = find_line_polygon_intersections(start, end, obstacle)
        if intersections:
            # Line goes through an obstacle
            # In a real implementation, we'd route around the obstacle
            # Here, we'll just clip the line to avoid the obstacle
            
            # Sort intersections by distance from start point
            intersections.sort(key=lambda p: (p[0] - start[0])**2 + (p[1] - start[1])**2)
            
            # Check if start is in the obstacle
            start_in_obstacle = is_point_in_polygon(start, obstacle)
            end_in_obstacle = is_point_in_polygon(end, obstacle)
            
            if start_in_obstacle and end_in_obstacle:
                # Both start and end are inside obstacle, skip this line
                return []
            elif start_in_obstacle:
                # Start is in obstacle, move to first exit point
                return [intersections[0], end]
            elif end_in_obstacle:
                # End is in obstacle, move to last entry point
                return [start, intersections[0]]
            else:
                # Neither start nor end is in obstacle, but line passes through
                # Return segments before and after obstacle
                return [start, intersections[0], intersections[1], end]
    
    # No obstacles, return the original line
    return [start, end]


def find_line_polygon_intersections(start: Point, end: Point, polygon: Polygon) -> List[Point]:
    """
    Find all intersections of a line with a polygon.
    
    Args:
        start: Starting point of the line
        end: Ending point of the line
        polygon: Polygon to check for intersections
        
    Returns:
        List of intersection points
    """
    intersections = []
    
    # Check each edge of the polygon
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        
        # Get edge points
        edge_start = polygon[i]
        edge_end = polygon[j]
        
        # Find intersection of the line and this edge
        intersection = find_line_intersection(start, end, edge_start, edge_end)
        if intersection:
            intersections.append(intersection)
    
    return intersections


def find_line_intersection(line1_start: Point, line1_end: Point, 
                          line2_start: Point, line2_end: Point) -> Optional[Point]:
    """
    Find the intersection point of two line segments.
    
    Args:
        line1_start, line1_end: Points defining the first line segment
        line2_start, line2_end: Points defining the second line segment
        
    Returns:
        Intersection point, or None if the lines don't intersect
    """
    # Get line parameters
    x1, y1 = line1_start
    x2, y2 = line1_end
    x3, y3 = line2_start
    x4, y4 = line2_end
    
    # Calculate denominator
    denominator = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    
    # Check if lines are parallel
    if denominator == 0:
        return None
    
    # Calculate ua and ub
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denominator
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denominator
    
    # Check if intersection is on both line segments
    if 0 <= ua <= 1 and 0 <= ub <= 1:
        # Calculate intersection point
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)
    
    return None


def is_point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """
    Determine if a point is inside a polygon using the ray casting algorithm.
    
    Args:
        point: Point to check
        polygon: Polygon to check against
        
    Returns:
        True if the point is inside the polygon, False otherwise
    """
    # Empty polygon - cannot contain any points
    if len(polygon) < 3:
        return False
    
    # Get point coordinates
    x, y = point
    
    # Initialize counter
    inside = False
    
    # Loop through polygon vertices
    j = len(polygon) - 1
    for i in range(len(polygon)):
        # Get current vertex and previous vertex
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        # Check if ray intersects edge
        intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        
        # If ray intersects, toggle inside flag
        if intersect:
            inside = not inside
        
        # Move to next vertex
        j = i
    
    return inside


def is_point_in_any_polygon(point: Point, polygons: List[Polygon]) -> bool:
    """
    Determine if a point is inside any of a list of polygons.
    
    Args:
        point: Point to check
        polygons: List of polygons to check against
        
    Returns:
        True if the point is inside any polygon, False otherwise
    """
    return any(is_point_in_polygon(point, polygon) for polygon in polygons)


def offset_polygon_inward(polygon: Polygon, offset_distance: float) -> Polygon:
    """
    Create an inward offset of a polygon boundary.
    
    Args:
        polygon: Polygon to offset
        offset_distance: Distance to offset
        
    Returns:
        Offset polygon
    """
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
        
        # Calculate edge vectors
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
        if not is_simple_polygon(offset_polygon):
            return []
        return offset_polygon
    else:
        return []


def is_simple_polygon(polygon: Polygon) -> bool:
    """
    Check if a polygon is simple (non-self-intersecting).
    This is a simplified check - a real implementation would use more sophisticated algorithms.
    
    Args:
        polygon: Polygon to check
        
    Returns:
        True if the polygon is simple, False otherwise
    """
    # For now, calculate the area as a rough check
    area = polygon_area(polygon)
    return area > 0


def polygon_area(polygon: Polygon) -> float:
    """
    Calculate the area of a polygon using the Shoelace formula.
    
    Args:
        polygon: Polygon to calculate area for
        
    Returns:
        Area of the polygon
    """
    if len(polygon) < 3:
        return 0
    
    area = 0.0
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        area += polygon[i][0] * polygon[j][1]
        area -= polygon[j][0] * polygon[i][1]
    
    return abs(area) / 2.0


def is_roughly_circular(polygon: Polygon) -> bool:
    """
    Determine if a polygon is roughly circular in shape.
    
    Args:
        polygon: Polygon to check
        
    Returns:
        True if the polygon is roughly circular, False otherwise
    """
    # Calculate centroid
    centroid_x = sum(p[0] for p in polygon) / len(polygon)
    centroid_y = sum(p[1] for p in polygon) / len(polygon)
    
    # Calculate average distance from centroid to boundary points
    avg_distance = sum(math.sqrt((p[0] - centroid_x)**2 + (p[1] - centroid_y)**2) 
                       for p in polygon) / len(polygon)
    
    # Calculate standard deviation of distances
    variance = sum((math.sqrt((p[0] - centroid_x)**2 + (p[1] - centroid_y)**2) - avg_distance)**2 
                   for p in polygon) / len(polygon)
    std_dev = math.sqrt(variance)
    
    # If standard deviation is small relative to average distance, it's roughly circular
    circularity = std_dev / avg_distance if avg_distance > 0 else float('inf')
    return circularity < 0.2  # Threshold can be adjusted
