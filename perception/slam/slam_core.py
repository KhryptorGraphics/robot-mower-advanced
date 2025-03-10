"""
SLAM (Simultaneous Localization and Mapping) Core Module for Robot Mower Advanced

This module implements SLAM algorithms to provide precise mapping and localization 
for the robot mower, integrating data from RTK GPS, cameras, and other sensors.
"""

import os
import time
import logging
import threading
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional, Union, Any
import json
import math

# Optional dependencies - these will be installed via the installation script
try:
    import g2o  # Graph optimization for SLAM
    G2O_AVAILABLE = True
except ImportError:
    G2O_AVAILABLE = False
    logging.warning("g2o not found. Advanced SLAM graph optimization will be unavailable.")

# Try to import RTK GPS libraries
try:
    import rtklibpy
    RTKLIB_AVAILABLE = True
except ImportError:
    RTKLIB_AVAILABLE = False
    logging.warning("RTK GPS libraries not found. High-precision GPS data will not be available.")

# Import local modules
from perception.hailo_integration import EnvironmentalMap


class SlamMap:
    """Represents the SLAM-generated map of the environment."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SLAM map
        
        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Map dimensions and resolution
        self.map_resolution = config.get("slam", {}).get("map_resolution", 0.05)  # meters per pixel
        self.map_size_meters = config.get("slam", {}).get("map_size", 100.0)  # size in meters
        self.grid_size = int(self.map_size_meters / self.map_resolution)
        
        # Create occupancy grid map
        self.occupancy_grid = np.zeros((self.grid_size, self.grid_size), dtype=np.float32)
        
        # Create feature map (for visual features)
        self.feature_map = {}  # Keyed by feature ID
        
        # Create pose graph
        self.poses = []  # List of robot poses over time
        self.pose_graph_edges = []  # List of constraints between poses
        
        # Map origin in world coordinates
        self.origin_lat = config.get("slam", {}).get("origin_lat", 0.0)
        self.origin_lon = config.get("slam", {}).get("origin_lon", 0.0)
        self.origin_alt = config.get("slam", {}).get("origin_alt", 0.0)
        
        # Map transformation matrix (from local to world coordinates)
        self.transform_matrix = np.identity(4)
        
        # Local coordinate origin (in grid coordinates)
        self.origin_x = self.grid_size // 2
        self.origin_y = self.grid_size // 2
        
        # Persistence
        self.data_dir = config.get("system", {}).get("data_dir", "data")
        self.map_file = os.path.join(self.data_dir, "slam_map.json")
        self.loaded = self.load_map()
        
        self.logger.info("SLAM map initialized")
    
    def update_occupancy_grid(self, robot_pose: Tuple[float, float, float], 
                             measurements: List[Dict[str, Any]]) -> None:
        """
        Update the occupancy grid map with new sensor measurements
        
        Args:
            robot_pose: (x, y, theta) position and orientation of the robot in meters and radians
            measurements: List of sensor measurements (distances, angles, etc.)
        """
        # Convert robot position to grid coordinates
        grid_x = int(robot_pose[0] / self.map_resolution) + self.origin_x
        grid_y = int(robot_pose[1] / self.map_resolution) + self.origin_y
        theta = robot_pose[2]
        
        # Update occupancy grid using inverse sensor model
        for measurement in measurements:
            sensor_type = measurement.get("type", "unknown")
            
            if sensor_type == "sonar" or sensor_type == "ultrasonic":
                distance = measurement.get("distance", 0.0)
                angle = measurement.get("angle", 0.0)
                
                # Skip invalid measurements
                if distance <= 0.0:
                    continue
                
                # Calculate endpoint in world coordinates
                endpoint_x = robot_pose[0] + distance * math.cos(theta + angle)
                endpoint_y = robot_pose[1] + distance * math.sin(theta + angle)
                
                # Convert endpoint to grid coordinates
                endpoint_grid_x = int(endpoint_x / self.map_resolution) + self.origin_x
                endpoint_grid_y = int(endpoint_y / self.map_resolution) + self.origin_y
                
                # Ensure coordinates are within map bounds
                if (0 <= grid_x < self.grid_size and 0 <= grid_y < self.grid_size and
                    0 <= endpoint_grid_x < self.grid_size and 0 <= endpoint_grid_y < self.grid_size):
                    
                    # Apply Bresenham's line algorithm to trace the ray
                    self._update_grid_ray(grid_x, grid_y, endpoint_grid_x, endpoint_grid_y)
            
            elif sensor_type == "camera":
                # Process camera detection for occupancy grid update
                detections = measurement.get("detections", [])
                self._process_camera_detections(grid_x, grid_y, theta, detections)
    
    def _update_grid_ray(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """
        Update the occupancy grid along a ray using Bresenham's line algorithm
        
        Args:
            x0, y0: Starting point (robot position)
            x1, y1: Ending point (sensor reading)
        """
        # Constants for grid updating
        FREE_SPACE_PROB = 0.3  # Value to add for free space
        OCCUPIED_PROB = 0.7    # Value to add for occupied space
        MIN_PROB = 0.1         # Minimum probability
        MAX_PROB = 0.9         # Maximum probability
        
        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        
        while True:
            # Update grid cell
            if (x0, y0) != (x1, y1):  # Not the endpoint
                # Mark as free space
                self.occupancy_grid[y0, x0] = max(MIN_PROB, 
                                                 self.occupancy_grid[y0, x0] - FREE_SPACE_PROB)
            else:  # Endpoint
                # Mark as occupied
                self.occupancy_grid[y0, x0] = min(MAX_PROB, 
                                                 self.occupancy_grid[y0, x0] + OCCUPIED_PROB)
                break
            
            # Check if we've reached the endpoint
            if x0 == x1 and y0 == y1:
                break
            
            # Update position
            e2 = 2 * err
            if e2 >= dy:
                if x0 == x1:
                    break
                err += dy
                x0 += sx
            if e2 <= dx:
                if y0 == y1:
                    break
                err += dx
                y0 += sy
    
    def _process_camera_detections(self, 
                                  grid_x: int, 
                                  grid_y: int, 
                                  theta: float, 
                                  detections: List[Dict[str, Any]]) -> None:
        """
        Process camera-based object detections for occupancy grid update
        
        Args:
            grid_x, grid_y: Robot position in grid coordinates
            theta: Robot orientation in radians
            detections: List of detected objects
        """
        for detection in detections:
            obj_class = detection.get("class", "unknown")
            confidence = detection.get("confidence", 0.0)
            
            # Skip low-confidence detections
            if confidence < 0.5:
                continue
            
            # Calculate object distance and angle
            distance = detection.get("distance", 0.0)
            rel_angle = detection.get("angle", 0.0)
            
            # Skip invalid measurements
            if distance <= 0.0:
                continue
            
            # Calculate object position in grid coordinates
            angle = theta + rel_angle
            obj_x = int(grid_x + (distance / self.map_resolution) * math.cos(angle))
            obj_y = int(grid_y + (distance / self.map_resolution) * math.sin(angle))
            
            # Ensure coordinates are within map bounds
            if 0 <= obj_x < self.grid_size and 0 <= obj_y < self.grid_size:
                # Update grid with obstacle
                obstacle_radius = int(0.3 / self.map_resolution)  # 30cm radius
                for dx in range(-obstacle_radius, obstacle_radius + 1):
                    for dy in range(-obstacle_radius, obstacle_radius + 1):
                        if dx*dx + dy*dy <= obstacle_radius*obstacle_radius:
                            x = obj_x + dx
                            y = obj_y + dy
                            if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
                                # Mark as occupied with confidence-weighted probability
                                self.occupancy_grid[y, x] = min(0.9, 
                                                            self.occupancy_grid[y, x] + 0.7 * confidence)
            
            # Also update the ray to the object as free space
            self._update_grid_ray(grid_x, grid_y, obj_x, obj_y)
    
    def add_feature(self, feature_id: str, position: Tuple[float, float, float], 
                   descriptor: np.ndarray, visibility: List[int]) -> None:
        """
        Add a visual feature to the feature map
        
        Args:
            feature_id: Unique identifier for the feature
            position: (x, y, z) position in meters
            descriptor: Feature descriptor vector
            visibility: List of pose IDs where this feature is visible
        """
        self.feature_map[feature_id] = {
            "position": position,
            "descriptor": descriptor.tolist() if isinstance(descriptor, np.ndarray) else descriptor,
            "visibility": visibility
        }
    
    def add_pose(self, pose_id: int, position: Tuple[float, float, float], 
                orientation: Tuple[float, float, float, float], timestamp: float) -> int:
        """
        Add a robot pose to the pose graph
        
        Args:
            pose_id: Unique identifier for the pose
            position: (x, y, z) position in meters
            orientation: (qw, qx, qy, qz) quaternion orientation
            timestamp: Time when the pose was recorded
            
        Returns:
            The ID of the added pose
        """
        pose = {
            "id": pose_id,
            "position": position,
            "orientation": orientation,
            "timestamp": timestamp
        }
        self.poses.append(pose)
        return pose_id
    
    def add_edge(self, from_pose: int, to_pose: int, transform: np.ndarray, 
                information: np.ndarray) -> None:
        """
        Add an edge (constraint) to the pose graph
        
        Args:
            from_pose: Source pose ID
            to_pose: Target pose ID
            transform: 4x4 transformation matrix between poses
            information: Information matrix (inverse covariance)
        """
        edge = {
            "from": from_pose,
            "to": to_pose,
            "transform": transform.tolist() if isinstance(transform, np.ndarray) else transform,
            "information": information.tolist() if isinstance(information, np.ndarray) else information
        }
        self.pose_graph_edges.append(edge)
    
    def optimize_pose_graph(self) -> bool:
        """
        Optimize the pose graph using g2o
        
        Returns:
            True if optimization was successful, False otherwise
        """
        if not G2O_AVAILABLE:
            self.logger.warning("Cannot optimize pose graph: g2o not available")
            return False
        
        try:
            # Create a g2o optimizer
            optimizer = g2o.SparseOptimizer()
            solver = g2o.BlockSolverSE3(g2o.LinearSolverEigenSE3())
            algorithm = g2o.OptimizationAlgorithmLevenberg(solver)
            optimizer.set_algorithm(algorithm)
            
            # Add vertices (poses)
            for pose in self.poses:
                v_se3 = g2o.VertexSE3()
                v_se3.set_id(pose["id"])
                
                # Create isometry from pose
                position = pose["position"]
                orientation = pose["orientation"]
                
                # Convert to isometry (SE3 transform)
                isometry = g2o.Isometry3d(
                    g2o.Quaterniond(orientation[0], orientation[1], orientation[2], orientation[3]),
                    g2o.Vector3d(position[0], position[1], position[2])
                )
                
                v_se3.set_estimate(isometry)
                
                # Fix the first vertex
                if pose["id"] == 0:
                    v_se3.set_fixed(True)
                
                optimizer.add_vertex(v_se3)
            
            # Add edges
            for edge in self.pose_graph_edges:
                e_se3 = g2o.EdgeSE3()
                e_se3.set_vertex(0, optimizer.vertex(edge["from"]))
                e_se3.set_vertex(1, optimizer.vertex(edge["to"]))
                
                # Create measurement (transformation)
                transform = np.array(edge["transform"])
                rotation = transform[:3, :3]
                translation = transform[:3, 3]
                
                # Convert to isometry
                measurement = g2o.Isometry3d(
                    g2o.Quaterniond(rotation),
                    g2o.Vector3d(translation[0], translation[1], translation[2])
                )
                
                e_se3.set_measurement(measurement)
                
                # Set information matrix
                info = np.array(edge["information"])
                e_se3.set_information(info)
                
                optimizer.add_edge(e_se3)
            
            # Optimize
            optimizer.initialize_optimization()
            optimizer.optimize(20)  # 20 iterations
            
            # Update poses with optimized values
            for pose in self.poses:
                v_se3 = optimizer.vertex(pose["id"])
                if v_se3:
                    isometry = v_se3.estimate()
                    
                    # Extract position and orientation
                    translation = isometry.translation()
                    rotation = isometry.rotation()
                    
                    # Update pose
                    pose["position"] = (translation.x(), translation.y(), translation.z())
                    pose["orientation"] = (rotation.w(), rotation.x(), rotation.y(), rotation.z())
            
            self.logger.info("Pose graph optimization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error optimizing pose graph: {e}")
            return False
    
    def set_gps_origin(self, lat: float, lon: float, alt: float) -> None:
        """
        Set the GPS origin for the map
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters
        """
        self.origin_lat = lat
        self.origin_lon = lon
        self.origin_alt = alt
        
        # Reset the transformation matrix
        self.transform_matrix = np.identity(4)
    
    def gps_to_local(self, lat: float, lon: float, alt: float) -> Tuple[float, float, float]:
        """
        Convert GPS coordinates to local coordinates
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters
            
        Returns:
            (x, y, z) position in local coordinates (meters)
        """
        if not RTKLIB_AVAILABLE:
            # Simplified conversion for when RTK libraries are not available
            # Uses equirectangular approximation, which is suitable for small areas
            # Earth's radius in meters
            R = 6371000.0
            
            # Convert degrees to radians
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            lat_origin_rad = math.radians(self.origin_lat)
            lon_origin_rad = math.radians(self.origin_lon)
            
            # Calculate distances
            x = R * (lon_rad - lon_origin_rad) * math.cos(lat_origin_rad)
            y = R * (lat_rad - lat_origin_rad)
            z = alt - self.origin_alt
            
            return (x, y, z)
        else:
            # Use RTK library for more accurate conversion
            # This would be implemented using rtklibpy or similar
            pass
    
    def local_to_gps(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Convert local coordinates to GPS coordinates
        
        Args:
            x, y, z: Position in local coordinates (meters)
            
        Returns:
            (lat, lon, alt) position in GPS coordinates
        """
        if not RTKLIB_AVAILABLE:
            # Simplified conversion for when RTK libraries are not available
            # Uses equirectangular approximation, which is suitable for small areas
            # Earth's radius in meters
            R = 6371000.0
            
            # Convert origin to radians
            lat_origin_rad = math.radians(self.origin_lat)
            lon_origin_rad = math.radians(self.origin_lon)
            
            # Calculate GPS coordinates
            lat_rad = lat_origin_rad + y / R
            lon_rad = lon_origin_rad + x / (R * math.cos(lat_origin_rad))
            alt = z + self.origin_alt
            
            # Convert radians to degrees
            lat = math.degrees(lat_rad)
            lon = math.degrees(lon_rad)
            
            return (lat, lon, alt)
        else:
            # Use RTK library for more accurate conversion
            # This would be implemented using rtklibpy or similar
            pass
    
    def save_map(self) -> bool:
        """
        Save the SLAM map to disk
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.map_file), exist_ok=True)
            
            # Create map data structure
            map_data = {
                "occupancy_grid": self.occupancy_grid.tolist(),
                "feature_map": self.feature_map,
                "poses": self.poses,
                "pose_graph_edges": self.pose_graph_edges,
                "origin": {
                    "lat": self.origin_lat,
                    "lon": self.origin_lon,
                    "alt": self.origin_alt
                },
                "transform_matrix": self.transform_matrix.tolist(),
                "map_resolution": self.map_resolution,
                "map_size_meters": self.map_size_meters,
                "grid_size": self.grid_size,
                "local_origin": {
                    "x": self.origin_x,
                    "y": self.origin_y
                },
                "timestamp": time.time()
            }
            
            # Save to file
            with open(self.map_file, 'w') as f:
                json.dump(map_data, f)
            
            self.logger.info(f"SLAM map saved to {self.map_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving SLAM map: {e}")
            return False
    
    def load_map(self) -> bool:
        """
        Load the SLAM map from disk
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.map_file):
            self.logger.info("No existing SLAM map found, starting with blank map")
            return False
        
        try:
            with open(self.map_file, 'r') as f:
                map_data = json.load(f)
            
            # Load map data
            self.occupancy_grid = np.array(map_data["occupancy_grid"])
            self.feature_map = map_data["feature_map"]
            self.poses = map_data["poses"]
            self.pose_graph_edges = map_data["pose_graph_edges"]
            
            # Load origin and transform
            origin = map_data["origin"]
            self.origin_lat = origin["lat"]
            self.origin_lon = origin["lon"]
            self.origin_alt = origin["alt"]
            self.transform_matrix = np.array(map_data["transform_matrix"])
            
            # Load map parameters
            self.map_resolution = map_data["map_resolution"]
            self.map_size_meters = map_data["map_size_meters"]
            self.grid_size = map_data["grid_size"]
            
            # Load local origin
            local_origin = map_data["local_origin"]
            self.origin_x = local_origin["x"]
            self.origin_y = local_origin["y"]
            
            self.logger.info(f"SLAM map loaded from {self.map_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading SLAM map: {e}")
            return False
    
    def get_occupancy_grid(self) -> np.ndarray:
        """
        Get the occupancy grid map
        
        Returns:
            2D numpy array representing the occupancy grid
        """
        return self.occupancy_grid
    
    def get_features(self) -> Dict[str, Any]:
        """
        Get the feature map
        
        Returns:
            Dictionary of features
        """
        return self.feature_map
    
    def get_poses(self) -> List[Dict[str, Any]]:
        """
        Get the robot poses
        
        Returns:
            List of robot poses
        """
        return self.poses
    
    def visualize_map(self, output_path: Optional[str] = None) -> np.ndarray:
        """
        Create a visualization of the map
        
        Args:
            output_path: Optional path to save the visualization
            
        Returns:
            Visualization as a numpy array
        """
        # Create a color map for visualization
        colormap = np.zeros((self.grid_size, self.grid_size, 3), dtype=np.uint8)
        
        # Fill with occupancy grid data
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                prob = self.occupancy_grid[y, x]
                if prob > 0.7:  # Likely occupied
                    colormap[y, x] = [0, 0, 255]  # Red for obstacles
                elif prob < 0.3:  # Likely free
                    colormap[y, x] = [0, 255, 0]  # Green for free space
                else:  # Unknown
                    colormap[y, x] = [128, 128, 128]  # Gray for unknown
        
        # Add poses to the visualization
        for pose in self.poses:
            pos = pose["position"]
            grid_x = int(pos[0] / self.map_resolution) + self.origin_x
            grid_y = int(pos[1] / self.map_resolution) + self.origin_y
            
            # Ensure within bounds
            if 0 <= grid_x < self.grid_size and 0 <= grid_y < self.grid_size:
                # Draw a small circle for each pose
                cv2.circle(colormap, (grid_x, grid_y), 3, (255, 0, 0), -1)
        
        # Save the visualization if requested
        if output_path:
            try:
                cv2.imwrite(output_path, colormap)
                self.logger.info(f"Map visualization saved to {output_path}")
            except Exception as e:
                self.logger.error(f"Error saving map visualization: {e}")
        
        return colormap


class SlamSystem:
    """
    Main SLAM system for Robot Mower Advanced.
    Coordinates mapping, localization, and pose graph optimization.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SLAM system
        
        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize map
        self.map = SlamMap(config)
        
        # Initialize state
        self.current_pose = (0.0, 0.0, 0.0)  # (x, y, heading)
        self.current_pose_id = 0
        self.current_timestamp = time.time()
        
        # Sensor data
        self.latest_gps = None
        self.latest_imu = None
        self.latest_wheel_odometry = None
        self.latest_camera_frame = None
        
        # Feature tracking
        self.feature_detector = cv2.SIFT_create()
        self.feature_matcher = cv2.BFMatcher()
        self.tracked_features = {}
        
        # Threading and synchronization
        self.running = False
        self.mapping_thread = None
        self.localization_thread = None
        self.optimization_thread = None
        self.lock = threading.Lock()
        
        self.logger.info("SLAM system initialized")
    
    def start(self) -> bool:
        """
        Start the SLAM system
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            self.logger.warning("SLAM system already running")
            return True
        
        self.running = True
        
        # Start mapping thread
        self.mapping_thread = threading.Thread(target=self._mapping_loop)
        self.mapping_thread.daemon = True
        self.mapping_thread.start()
        
        # Start localization thread
        self.localization_thread = threading.Thread(target=self._localization_loop)
        self.localization_thread.daemon = True
        self.localization_thread.start()
        
        # Start optimization thread
        self.optimization_thread = threading.Thread(target=self._optimization_loop)
        self.optimization_thread.daemon = True
        self.optimization_thread.start()
        
        self.logger.info("SLAM system started")
        return True
    
    def stop(self) -> None:
        """Stop the SLAM system"""
        self.running = False
        
        # Wait for threads to terminate
        if self.mapping_thread and self.mapping_thread.is_alive():
            self.mapping_thread.join(timeout=2.0)
        
        if self.localization_thread and self.localization_thread.is_alive():
            self.localization_thread.join(timeout=2.0)
        
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=2.0)
        
        # Save map
        self.map.save_map()
        
        self.logger.info("SLAM system stopped")
    
    def _mapping_loop(self) -> None:
        """Main loop for mapping"""
        self.logger.info("Mapping loop started")
        
        mapping_interval = self.config.get("slam", {}).get("mapping_interval", 0.5)  # in seconds
        
        last_update_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Update at specified interval
            if current_time - last_update_time >= mapping_interval:
                with self.lock:
                    try:
                        # Check if we have necessary data
                        if self.latest_camera_frame is not None:
                            # Process camera frame for feature detection
                            self._process_camera_frame()
                        
                        # Update occupancy grid with latest sensor data
                        if self.latest_wheel_odometry is not None:
                            # Create measurement list from sensors
                            measurements = []
                            
                            # Add ultrasonic/lidar measurements if available
                            # ... (code would go here)
                            
                            # Add camera-based object detections if available
                            # ... (code would go here)
                            
                            # Update the map
                            self.map.update_occupancy_grid(self.current_pose, measurements)
                            
                        last_update_time = current_time
                    except Exception as e:
                        self.logger.error(f"Error in mapping loop: {e}")
            
            # Sleep to reduce CPU usage
            time.sleep(0.01)
    
    def _localization_loop(self) -> None:
        """Main loop for localization"""
        self.logger.info("Localization loop started")
        
        localization_interval = self.config.get("slam", {}).get("localization_interval", 0.1)  # in seconds
        
        last_update_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Update at specified interval
            if current_time - last_update_time >= localization_interval:
                with self.lock:
                    try:
                        # Perform localization using available sensor data
                        self._update_localization()
                        
                        last_update_time = current_time
                    except Exception as e:
                        self.logger.error(f"Error in localization loop: {e}")
            
            # Sleep to reduce CPU usage
            time.sleep(0.01)
    
    def _optimization_loop(self) -> None:
        """Main loop for pose graph optimization"""
        self.logger.info("Optimization loop started")
        
        optimization_interval = self.config.get("slam", {}).get("optimization_interval", 5.0)  # in seconds
        
        last_optimization_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Optimize at specified interval
            if current_time - last_optimization_time >= optimization_interval:
                with self.lock:
                    try:
                        # Optimize pose graph
                        self.map.optimize_pose_graph()
                        
                        last_optimization_time = current_time
                    except Exception as e:
                        self.logger.error(f"Error in optimization loop: {e}")
            
            # Sleep to reduce CPU usage
            time.sleep(0.1)
    
    def _process_camera_frame(self) -> None:
        """Process the latest camera frame for feature detection and tracking"""
        if self.latest_camera_frame is None:
            return
        
        frame = self.latest_camera_frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect keypoints and compute descriptors
        keypoints, descriptors = self.feature_detector.detectAndCompute(gray, None)
        
        if descriptors is None or len(keypoints) == 0:
            return
        
        # Track features from previous frames
        if self.tracked_features:
            matches = self.feature_matcher.knnMatch(descriptors, self.tracked_features["descriptors"], k=2)
            
            # Apply ratio test to filter good matches
            good_matches = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
            
            if len(good_matches) > 10:
                # Extract matched keypoints
                current_pts = np.float32([keypoints[m.queryIdx].pt for m in good_matches])
                prev_pts = np.float32([self.tracked_features["keypoints"][m.trainIdx].pt for m in good_matches])
                
                # Estimate transformation between frames
                H, mask = cv2.findHomography(prev_pts, current_pts, cv2.RANSAC, 5.0)
                
                if H is not None:
                    # Update robot pose based on transformation
                    self._update_pose_from_homography(H)
        
        # Store current features for future tracking
        self.tracked_features = {
            "keypoints": keypoints,
            "descriptors": descriptors,
            "timestamp": time.time()
        }
    
    def _update_pose_from_homography(self, H: np.ndarray) -> None:
        """
        Update the robot pose based on the homography between frames
        
        Args:
            H: 3x3 homography matrix
        """
        # Extract translation and rotation from homography
        # This is a simplified approximation
        translation = np.array([H[0, 2], H[1, 2]])
        rotation = np.arctan2(H[1, 0], H[0, 0])
        
        # Scale translation based on calibration
        scale_factor = self.config.get("slam", {}).get("visual_odometry_scale", 0.01)
        translation *= scale_factor
        
        # Update the robot pose (simple integration)
        # In a real implementation, this would be more sophisticated
        x, y, theta = self.current_pose
        
        # Apply rotation and translation in robot frame
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        dx = translation[0] * cos_theta - translation[1] * sin_theta
        dy = translation[0] * sin_theta + translation[1] * cos_theta
        
        # Update pose
        self.current_pose = (x + dx, y + dy, theta + rotation)
    
    def _update_localization(self) -> None:
        """Update the robot's localization based on sensor data"""
        # Use a sensor fusion approach to combine different sensor inputs
        
        # GPS-based localization (if available)
        if self.latest_gps is not None:
            lat = self.latest_gps.get("latitude", 0.0)
            lon = self.latest_gps.get("longitude", 0.0)
            alt = self.latest_gps.get("altitude", 0.0)
            
            # Convert GPS to local coordinates
            local_pos = self.map.gps_to_local(lat, lon, alt)
            
            # Integrate GPS data (with appropriate weighting)
            gps_weight = self.config.get("slam", {}).get("gps_weight", 0.7)
            self._integrate_position(local_pos, gps_weight)
        
        # IMU-based orientation (if available)
        if self.latest_imu is not None:
            # Extract orientation from IMU data
            orientation = self.latest_imu.get("orientation", (0.0, 0.0, 0.0))
            
            # Integrate orientation data
            imu_weight = self.config.get("slam", {}).get("imu_weight", 0.8)
            self._integrate_orientation(orientation, imu_weight)
        
        # Wheel odometry (if available)
        if self.latest_wheel_odometry is not None:
            # Extract odometry data
            odom_x = self.latest_wheel_odometry.get("x", 0.0)
            odom_y = self.latest_wheel_odometry.get("y", 0.0)
            odom_theta = self.latest_wheel_odometry.get("theta", 0.0)
            
            # Integrate odometry data
            odom_weight = self.config.get("slam", {}).get("odometry_weight", 0.5)
            self._integrate_odometry((odom_x, odom_y, odom_theta), odom_weight)
        
        # Add current pose to pose graph at regular intervals
        add_pose_interval = self.config.get("slam", {}).get("add_pose_interval", 1.0)  # In seconds
        if time.time() - self.current_timestamp > add_pose_interval:
            self._add_pose_to_graph()
    
    def _integrate_position(self, position: Tuple[float, float, float], weight: float) -> None:
        """
        Integrate a new position measurement with appropriate weighting
        
        Args:
            position: (x, y, z) position in meters
            weight: Weight for this measurement (0-1)
        """
        x, y, _ = self.current_pose  # Current position
        new_x, new_y, _ = position   # New measurement
        
        # Weighted average
        x = (1.0 - weight) * x + weight * new_x
        y = (1.0 - weight) * y + weight * new_y
        
        # Update position (keeping current orientation)
        _, _, theta = self.current_pose
        self.current_pose = (x, y, theta)
    
    def _integrate_orientation(self, orientation: Tuple[float, float, float], weight: float) -> None:
        """
        Integrate a new orientation measurement with appropriate weighting
        
        Args:
            orientation: (roll, pitch, yaw) orientation in radians
            weight: Weight for this measurement (0-1)
        """
        _, _, theta = self.current_pose  # Current orientation (yaw only)
        _, _, new_theta = orientation    # New measurement
        
        # Weighted average for orientation
        # Note: This is a simplification, real implementation would use quaternions
        # and handle wrap-around properly
        theta = (1.0 - weight) * theta + weight * new_theta
        
        # Update orientation (keeping current position)
        x, y, _ = self.current_pose
        self.current_pose = (x, y, theta)
    
    def _integrate_odometry(self, odometry: Tuple[float, float, float], weight: float) -> None:
        """
        Integrate odometry data with appropriate weighting
        
        Args:
            odometry: (x, y, theta) odometry measurement
            weight: Weight for this measurement (0-1)
        """
        x, y, theta = self.current_pose
        odom_x, odom_y, odom_theta = odometry
        
        # Apply odometry as a delta from the current position
        x += odom_x * weight
        y += odom_y * weight
        theta += odom_theta * weight
        
        # Update pose
        self.current_pose = (x, y, theta)
    
    def _add_pose_to_graph(self) -> None:
        """Add the current pose to the pose graph"""
        # Convert 2D pose to 3D pose
        x, y, theta = self.current_pose
        
        # Convert to 3D position
        position = (x, y, 0.0)
        
        # Convert to quaternion orientation (from yaw angle)
        # Simple conversion for 2D case (rotation around Z axis only)
        qw = np.cos(theta / 2.0)
        qx = 0.0
        qy = 0.0
        qz = np.sin(theta / 2.0)
        orientation = (qw, qx, qy, qz)
        
        # Add pose to the graph
        pose_id = self.current_pose_id
        self.map.add_pose(pose_id, position, orientation, time.time())
        
        # If this is not the first pose, add an edge to the previous pose
        if pose_id > 0:
            # Create transformation matrix between poses
            delta_x = x - self.previous_x
            delta_y = y - self.previous_y
            delta_theta = theta - self.previous_theta
            
            # Create SE(3) transformation matrix
            cos_theta = np.cos(delta_theta)
            sin_theta = np.sin(delta_theta)
            
            transform = np.identity(4)
            transform[0, 0] = cos_theta
            transform[0, 1] = -sin_theta
            transform[1, 0] = sin_theta
            transform[1, 1] = cos_theta
            transform[0, 3] = delta_x
            transform[1, 3] = delta_y
            
            # Information matrix (inverse covariance) - simplified
            # In a real implementation, this would depend on sensor uncertainties
            information = np.identity(6)
            
            # Add edge to the graph
            self.map.add_edge(pose_id - 1, pose_id, transform, information)
        
        # Store values for next time
        self.previous_x = x
        self.previous_y = y
        self.previous_theta = theta
        
        # Increment pose ID for next time
        self.current_pose_id += 1
        self.current_timestamp = time.time()
    
    def set_gps_data(self, gps_data: Dict[str, Any]) -> None:
        """
        Set the latest GPS data
        
        Args:
            gps_data: Dictionary with GPS data (latitude, longitude, altitude)
        """
        self.latest_gps = gps_data
    
    def set_imu_data(self, imu_data: Dict[str, Any]) -> None:
        """
        Set the latest IMU data
        
        Args:
            imu_data: Dictionary with IMU data (orientation, acceleration, etc.)
        """
        self.latest_imu = imu_data
    
    def set_wheel_odometry(self, odometry: Dict[str, Any]) -> None:
        """
        Set the latest wheel odometry data
        
        Args:
            odometry: Dictionary with odometry data (x, y, theta, etc.)
        """
        self.latest_wheel_odometry = odometry
    
    def set_camera_frame(self, frame: np.ndarray) -> None:
        """
        Set the latest camera frame
        
        Args:
            frame: Camera frame as numpy array
        """
        self.latest_camera_frame = frame
    
    def get_current_pose(self) -> Tuple[float, float, float]:
        """
        Get the current robot pose
        
        Returns:
            (x, y, theta) pose in meters and radians
        """
        return self.current_pose
    
    def get_map(self) -> SlamMap:
        """
        Get the SLAM map
        
        Returns:
            SlamMap object
        """
        return self.map
    
    def get_visualization(self, output_path: Optional[str] = None) -> np.ndarray:
        """
        Get a visualization of the current map and robot pose
        
        Args:
            output_path: Optional path to save the visualization
        
        Returns:
            Visualization as a numpy array
        """
        # Get base map visualization
        visualization = self.map.visualize_map()
        
        # Add current robot pose
        x, y, theta = self.current_pose
        grid_x = int(x / self.map.map_resolution) + self.map.origin_x
        grid_y = int(y / self.map.map_resolution) + self.map.origin_y
        
        # Ensure coordinates are within bounds
        if 0 <= grid_x < self.map.grid_size and 0 <= grid_y < self.map.grid_size:
            # Draw robot as a circle with a line indicating direction
            cv2.circle(visualization, (grid_x, grid_y), 5, (255, 255, 0), -1)
            
            # Draw direction line
            line_length = 15
            end_x = int(grid_x + line_length * np.cos(theta))
            end_y = int(grid_y + line_length * np.sin(theta))
            cv2.line(visualization, (grid_x, grid_y), (end_x, end_y), (255, 255, 0), 2)
        
        # Save the visualization if requested
        if output_path:
            try:
                cv2.imwrite(output_path, visualization)
                self.logger.info(f"Visualization saved to {output_path}")
            except Exception as e:
                self.logger.error(f"Error saving visualization: {e}")
        
        return visualization
