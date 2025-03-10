"""
Test module for the path planning algorithms.
This module demonstrates the usage of the PathPlanner class with different patterns.
"""

import matplotlib.pyplot as plt
import numpy as np
import math
from typing import List, Tuple
import logging

from .path_planning import PathPlanner, PathPlanningConfig, MowingPattern

# Setup logging
logging.basicConfig(level=logging.INFO)


def generate_test_boundary() -> List[Tuple[float, float]]:
    """Generate a test lawn boundary (simple polygon)"""
    # Create a simple rectangular boundary
    return [
        (0, 0),     # Bottom-left
        (10, 0),    # Bottom-right
        (10, 8),    # Top-right
        (0, 8)      # Top-left
    ]


def generate_complex_boundary() -> List[Tuple[float, float]]:
    """Generate a more complex boundary with irregular shape"""
    # L-shaped yard
    return [
        (0, 0),     # Bottom-left
        (10, 0),    # Bottom-right
        (10, 3),    # Middle-right-1
        (5, 3),     # Middle-middle
        (5, 8),     # Top-middle
        (0, 8)      # Top-left
    ]


def generate_test_obstacles() -> List[List[Tuple[float, float]]]:
    """Generate some test obstacles in the lawn"""
    # A circular-ish obstacle (approximated as polygon)
    circle_points = []
    center_x, center_y = 7, 4
    radius = 1
    num_points = 8
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        circle_points.append((x, y))
    
    # A rectangular obstacle
    rectangle = [
        (2, 2),
        (3, 2),
        (3, 3),
        (2, 3)
    ]
    
    return [circle_points, rectangle]


def plot_lawn(boundary, obstacles=None, path=None, title="Lawn Map"):
    """Plot the lawn boundary, obstacles, and mowing path"""
    plt.figure(figsize=(10, 8))
    
    # Plot boundary
    boundary_x = [p[0] for p in boundary] + [boundary[0][0]]  # Close the loop
    boundary_y = [p[1] for p in boundary] + [boundary[0][1]]
    plt.plot(boundary_x, boundary_y, 'b-', linewidth=2, label='Lawn Boundary')
    
    # Plot obstacles
    if obstacles:
        for i, obstacle in enumerate(obstacles):
            obstacle_x = [p[0] for p in obstacle] + [obstacle[0][0]]  # Close the loop
            obstacle_y = [p[1] for p in obstacle] + [obstacle[0][1]]
            plt.plot(obstacle_x, obstacle_y, 'r-', linewidth=2, label='Obstacle' if i == 0 else "")
            plt.fill(obstacle_x, obstacle_y, 'r', alpha=0.3)
    
    # Plot path
    if path:
        path_x = [p[0] for p in path]
        path_y = [p[1] for p in path]
        plt.plot(path_x, path_y, 'g-', linewidth=1, label='Mowing Path')
        
        # Mark start/end points
        plt.plot(path_x[0], path_y[0], 'go', markersize=8, label='Start')
        plt.plot(path_x[-1], path_y[-1], 'rx', markersize=8, label='End')
    
    plt.title(title)
    plt.xlabel('X (meters)')
    plt.ylabel('Y (meters)')
    plt.grid(True)
    plt.axis('equal')
    plt.legend()
    
    # Save the plot to a file
    output_file = f"lawn_path_{title.replace(' ', '_').lower()}.png"
    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")
    
    # Uncomment to show plot interactively
    # plt.show()


def test_path_planning():
    """Test various path planning patterns"""
    # Create a path planner with default configuration
    mower_width = 0.3  # 30 cm mower width
    
    # Define test cases with different patterns
    test_cases = [
        ("Parallel Lines", MowingPattern.PARALLEL_LINES, generate_test_boundary()),
        ("Spiral", MowingPattern.SPIRAL, generate_test_boundary()),
        ("Grid", MowingPattern.GRID, generate_test_boundary()),
        ("Perimeter First", MowingPattern.PERIMETER_FIRST, generate_test_boundary()),
        ("ZigZag", MowingPattern.ZIGZAG, generate_test_boundary()),
        ("Complex Shape - Adaptive", MowingPattern.ADAPTIVE, generate_complex_boundary()),
        ("Complex Shape - Perimeter First", MowingPattern.PERIMETER_FIRST, generate_complex_boundary()),
    ]
    
    # Generate obstacles
    obstacles = generate_test_obstacles()
    
    # Run tests for each pattern
    for title, pattern, boundary in test_cases:
        print(f"\nTesting {title} pattern...")
        
        # Create configuration for this pattern
        config = PathPlanningConfig(pattern=pattern)
        
        # Create path planner with this configuration
        planner = PathPlanner(mower_width=mower_width, config=config)
        
        # Define docking station position (bottom left of the lawn)
        dock_position = (0.5, 0.5)
        
        # Generate the path
        path = planner.plan_path(boundary, obstacles, dock_position)
        
        print(f"Generated path with {len(path)} points")
        
        # Plot the result
        plot_lawn(boundary, obstacles, path, title=title)


if __name__ == "__main__":
    test_path_planning()
