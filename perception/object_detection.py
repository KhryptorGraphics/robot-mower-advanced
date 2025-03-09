"""
Object Detection Module

This module provides functionality for detecting and classifying objects
in the robot's surroundings, with special attention to safety-critical
objects like people, children, and animals.
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
import threading

from ..core.config import ConfigManager
from ..hardware.interfaces import Camera


class ObjectCategory(Enum):
    """Enumeration of object categories"""
    PERSON = "person"
    CHILD = "child"
    PET = "pet"
    VEHICLE = "vehicle"
    OBSTACLE = "obstacle"
    UNKNOWN = "unknown"


class SafetyLevel(Enum):
    """Enumeration of safety levels"""
    CRITICAL = "critical"  # Immediate stop required (e.g., child, pet)
    HIGH = "high"  # Requires significant avoidance (e.g., person)
    MEDIUM = "medium"  # Requires some avoidance (e.g., obstacle)
    LOW = "low"  # Can be safely navigated around
    NONE = "none"  # No safety concerns


@dataclass
class DetectedObject:
    """Class representing a detected object"""
    id: int
    category: ObjectCategory
    confidence: float  # 0-1 confidence score
    bounding_box: Tuple[int, int, int, int]  # (x, y, width, height)
    safety_level: SafetyLevel
    distance: Optional[float] = None  # Estimated distance in meters, if available
    velocity: Optional[Tuple[float, float]] = None  # (vx, vy) in m/s, if available
    timestamp: datetime = datetime.now()
    image: Optional[np.ndarray] = None  # Cropped image of the object, if available
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the object to a dictionary (without image data)"""
        return {
            "id": self.id,
            "category": self.category.value,
            "confidence": self.confidence,
            "bounding_box": list(self.bounding_box),
            "safety_level": self.safety_level.value,
            "distance": self.distance,
            "velocity": list(self.velocity) if self.velocity else None,
            "timestamp": self.timestamp.isoformat()
        }


class ObjectDetector:
    """
    Class for detecting and classifying objects in camera images
    
    Uses computer vision and machine learning to identify safety-critical
    objects such as people, children, and pets.
    """
    
    def __init__(self, config: ConfigManager, camera: Camera):
        """
        Initialize the object detector
        
        Args:
            config: Configuration manager
            camera: Camera instance for capturing images
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.camera = camera
        
        # Configuration
        self.detection_interval = config.get("object_detection.interval", 0.2)  # Seconds
        self.confidence_threshold = config.get("object_detection.confidence_threshold", 0.5)
        self.iou_threshold = config.get("object_detection.iou_threshold", 0.5)  # For NMS
        self.max_detection_distance = config.get("object_detection.max_distance", 5.0)  # Meters
        self.safety_radius = config.get("object_detection.safety_radius", 2.0)  # Meters
        self.child_safety_radius = config.get("object_detection.child_safety_radius", 4.0)  # Meters
        self.pet_safety_radius = config.get("object_detection.pet_safety_radius", 3.0)  # Meters
        self.save_detections = config.get("object_detection.save_detections", True)
        self.detection_history_limit = config.get("object_detection.history_limit", 100)
        
        # Model settings
        model_dir = os.path.join(config.get("system.data_dir", "data"), "models")
        self.model_path = config.get("object_detection.model_path", os.path.join(model_dir, "detection_model.onnx"))
        self.classes = config.get("object_detection.classes", [
            "person", "bicycle", "car", "motorcycle", "bus", "truck", 
            "cat", "dog", "horse", "cow", "elephant", "bear", "zebra", "giraffe",
            "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", 
            "sports ball", "kite", "baseball glove", "skateboard", "surfboard", 
            "tennis racket", "bottle", "cup", "fork", "knife", "spoon", "bowl"
        ])
        self.safety_critical_classes = config.get("object_detection.safety_critical_classes", [
            "person", "cat", "dog"
        ])
        
        # State
        self.running = False
        self.detection_thread = None
        self.last_detection_time = 0
        self.current_detections: List[DetectedObject] = []
        self.detection_history: List[DetectedObject] = []
        self.next_object_id = 1
        self.detection_count = 0
        
        # Initialize model
        self._init_model()
        
        # Create save directory if needed
        if self.save_detections:
            save_dir = os.path.join(config.get("system.data_dir", "data"), "detections")
            os.makedirs(save_dir, exist_ok=True)
            self.detection_save_path = save_dir
        
        self.logger.info("Object detector initialized")
    
    def _init_model(self) -> None:
        """Initialize the detection model"""
        try:
            # In a real implementation, this would load a proper object detection model
            # For this example, we'll just set up a mock model
            self.logger.info(f"Initializing object detection model (mock implementation)")
            
            # Ensure the model directory exists
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Check if the real model exists, if not we'll use our mock implementation
            if not os.path.exists(self.model_path):
                self.logger.warning(f"Model file not found at {self.model_path}, using mock detection")
            
            # In a real implementation we would load the model here:
            # Using OpenCV's DNN module for example:
            # self.model = cv2.dnn.readNetFromONNX(self.model_path)
            # or TensorFlow:
            # import tensorflow as tf
            # self.model = tf.saved_model.load(self.model_path)
            
            # For our mock implementation, we'll use a simple flag
            self.model_loaded = True
            
        except Exception as e:
            self.logger.error(f"Error initializing detection model: {e}")
            self.model_loaded = False
    
    def start(self) -> bool:
        """
        Start the object detector
        
        Returns:
            Success or failure
        """
        if self.running:
            self.logger.warning("Object detector already running")
            return True
        
        if not self.model_loaded:
            self.logger.error("Cannot start: Model not initialized")
            return False
        
        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.detection_thread.start()
        
        self.logger.info("Object detector started")
        return True
    
    def stop(self) -> None:
        """Stop the object detector"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=3.0)
        self.logger.info("Object detector stopped")
    
    def _detection_loop(self) -> None:
        """Main detection loop running in a separate thread"""
        while self.running:
            current_time = time.time()
            
            # Only run detection at the specified interval
            if current_time - self.last_detection_time >= self.detection_interval:
                try:
                    # Capture an image
                    image = self.camera.capture_image()
                    
                    # Run detection on the image
                    detections = self.detect_objects(image)
                    
                    # Update state
                    self.current_detections = detections
                    self.last_detection_time = current_time
                    
                    # Log detections
                    if detections:
                        safety_critical = any(d.safety_level in [SafetyLevel.CRITICAL, SafetyLevel.HIGH] for d in detections)
                        if safety_critical:
                            self.logger.warning(f"Detected {len(detections)} objects, including safety-critical objects")
                        else:
                            self.logger.debug(f"Detected {len(detections)} objects")
                
                except Exception as e:
                    self.logger.error(f"Error in detection loop: {e}")
            
            # Sleep a bit to avoid hammering the CPU
            time.sleep(0.05)
    
    def detect_objects(self, image: np.ndarray) -> List[DetectedObject]:
        """
        Detect objects in an image
        
        Args:
            image: Image as numpy array
            
        Returns:
            List of detected objects
        """
        if not self.model_loaded:
            return []
        
        # In a real implementation, this would use the loaded model to detect objects
        # For this example, we'll use a mock implementation that randomly generates detections
        
        # Get image dimensions
        height, width = image.shape[:2]
        
        # Generate random number of detections (0-3)
        num_detections = np.random.randint(0, 4)
        detections = []
        
        for _ in range(num_detections):
            # Generate random bounding box
            box_width = np.random.randint(50, width // 3)
            box_height = np.random.randint(50, height // 3)
            x = np.random.randint(0, width - box_width)
            y = np.random.randint(0, height - box_height)
            bbox = (x, y, box_width, box_height)
            
            # Randomly select a class
            class_idx = np.random.randint(0, len(self.classes))
            class_name = self.classes[class_idx]
            
            # Generate confidence score
            confidence = np.random.uniform(0.5, 0.95)
            
            # Determine object category
            if class_name == "person":
                # Small bounding boxes are more likely to be children
                if box_height < 100:
                    category = ObjectCategory.CHILD
                    safety_level = SafetyLevel.CRITICAL
                else:
                    category = ObjectCategory.PERSON
                    safety_level = SafetyLevel.HIGH
            elif class_name in ["cat", "dog"]:
                category = ObjectCategory.PET
                safety_level = SafetyLevel.CRITICAL
            elif class_name in ["car", "motorcycle", "bus", "truck", "bicycle"]:
                category = ObjectCategory.VEHICLE
                safety_level = SafetyLevel.HIGH
            else:
                category = ObjectCategory.OBSTACLE
                safety_level = SafetyLevel.MEDIUM
            
            # Estimate distance (mock implementation)
            # In a real system, this would use depth sensors or other methods
            distance = np.random.uniform(1.0, 8.0)
            
            # Only include if confidence is above threshold and within detection range
            if confidence >= self.confidence_threshold and distance <= self.max_detection_distance:
                object_id = self.next_object_id
                self.next_object_id += 1
                
                # Create detection object
                detection = DetectedObject(
                    id=object_id,
                    category=category,
                    confidence=confidence,
                    bounding_box=bbox,
                    safety_level=safety_level,
                    distance=distance,
                    velocity=None,  # No velocity estimation in this mock implementation
                    timestamp=datetime.now()
                )
                
                # Extract image crop
                x, y, w, h = bbox
                crop = image[y:y+h, x:x+w].copy() if 0 <= y < y+h <= height and 0 <= x < x+w <= width else None
                detection.image = crop
                
                detections.append(detection)
                
                # Save detection if configured
                if self.save_detections and crop is not None:
                    self._save_detection(detection, crop)
                
                # Add to history
                self.detection_history.append(detection)
                
                # Limit history size
                if len(self.detection_history) > self.detection_history_limit:
                    self.detection_history = self.detection_history[-self.detection_history_limit:]
        
        self.detection_count += len(detections)
        return detections
    
    def _save_detection(self, detection: DetectedObject, crop: np.ndarray) -> None:
        """
        Save a detection image to disk
        
        Args:
            detection: The detection object
            crop: Cropped image of the detected object
        """
        try:
            # Create filename
            timestamp = detection.timestamp.strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{detection.category.value}_{detection.id}_{timestamp}.jpg"
            filepath = os.path.join(self.detection_save_path, filename)
            
            # Save image
            cv2.imwrite(filepath, crop)
        except Exception as e:
            self.logger.error(f"Error saving detection: {e}")
    
    def get_safety_critical_objects(self) -> List[DetectedObject]:
        """
        Get a list of safety-critical objects from current detections
        
        Returns:
            List of safety-critical detected objects
        """
        return [obj for obj in self.current_detections 
                if obj.safety_level in [SafetyLevel.CRITICAL, SafetyLevel.HIGH]]
    
    def is_path_clear(self, direction_vector: Tuple[float, float], distance: float = 2.0) -> bool:
        """
        Check if a path in a given direction is clear of obstacles
        
        Args:
            direction_vector: Direction vector (x, y) to check
            distance: Distance to check in meters
            
        Returns:
            True if path is clear, False if obstacles are present
        """
        # Normalize direction vector
        magnitude = (direction_vector[0]**2 + direction_vector[1]**2)**0.5
        if magnitude == 0:
            return True  # No direction, so no movement
        
        direction = (direction_vector[0] / magnitude, direction_vector[1] / magnitude)
        
        for obj in self.current_detections:
            if obj.distance is None:
                continue
            
            # Skip objects that are too far away
            if obj.distance > distance + self.safety_radius:
                continue
            
            # For safety-critical objects, use a larger safety radius
            safety_radius = self.safety_radius
            if obj.category == ObjectCategory.CHILD:
                safety_radius = self.child_safety_radius
            elif obj.category == ObjectCategory.PET:
                safety_radius = self.pet_safety_radius
            
            # Simple path collision check
            # This is a simplistic approach - a real implementation would be more sophisticated
            # We're approximating objects as circles and checking for ray-circle intersection
            
            # Direction to object (assuming mower is at (0,0))
            obj_direction = (obj.distance, 0)  # Mock direction - real system would use actual position
            
            # Distance from path to object
            dot_product = obj_direction[0] * direction[0] + obj_direction[1] * direction[1]
            projection = (dot_product * direction[0], dot_product * direction[1])
            closest_point = (projection[0], projection[1])
            
            # Distance squared from closest point to object
            dist_sq = (obj_direction[0] - closest_point[0])**2 + (obj_direction[1] - closest_point[1])**2
            
            # Check if path is too close to object
            if dist_sq < safety_radius**2:
                # Projected point is within safety radius of object
                # Check if the point is within our forward path of interest
                if 0 <= dot_product <= distance:
                    return False  # Path is not clear
        
        return True  # No obstacles found in path
    
    def get_safe_directions(self, num_directions: int = 8) -> List[Tuple[float, Tuple[float, float]]]:
        """
        Get a list of safe directions to travel, ranked by safety score
        
        Args:
            num_directions: Number of directions to check
            
        Returns:
            List of (safety_score, direction_vector) tuples, sorted by safety score (higher is safer)
        """
        directions = []
        
        # Generate evenly spaced directions
        for i in range(num_directions):
            angle = 2 * np.pi * i / num_directions
            direction = (np.cos(angle), np.sin(angle))
            
            # Calculate safety score for this direction
            score = self._calculate_direction_safety(direction)
            directions.append((score, direction))
        
        # Sort by safety score, highest first
        return sorted(directions, key=lambda x: x[0], reverse=True)
    
    def _calculate_direction_safety(self, direction: Tuple[float, float]) -> float:
        """
        Calculate a safety score for a given direction
        
        Args:
            direction: Direction vector (x, y) to check
            
        Returns:
            Safety score (higher is safer)
        """
        score = 1.0  # Base score
        
        for obj in self.current_detections:
            if obj.distance is None:
                continue
            
            # Calculate safety radius based on object type
            safety_radius = self.safety_radius
            if obj.category == ObjectCategory.CHILD:
                safety_radius = self.child_safety_radius
            elif obj.category == ObjectCategory.PET:
                safety_radius = self.pet_safety_radius
            
            # Similar geometric calculation as in is_path_clear, but we use the distance
            # to generate a score instead of a binary result
            
            # Direction to object (assuming mower is at (0,0))
            obj_direction = (obj.distance, 0)  # Mock direction - real system would use actual position
            
            # Calculate dot product to find how far along our direction the closest point is
            dot_product = obj_direction[0] * direction[0] + obj_direction[1] * direction[1]
            
            # Only consider objects that are ahead of us
            if dot_product <= 0:
                continue
                
            projection = (dot_product * direction[0], dot_product * direction[1])
            
            # Distance squared from closest point to object
            dist_sq = (obj_direction[0] - projection[0])**2 + (obj_direction[1] - projection[1])**2
            
            # Calculate safety reduction based on proximity to the object
            # Objects directly in the path cause more score reduction
            if dist_sq < safety_radius**2:
                # The closer we are to the center of the object, the lower the score
                proximity_factor = dist_sq / (safety_radius**2) if safety_radius > 0 else 0
                
                # Scale by object safety level
                safety_factor = 1.0
                if obj.safety_level == SafetyLevel.CRITICAL:
                    safety_factor = 0.1  # Critical objects cause major score reduction
                elif obj.safety_level == SafetyLevel.HIGH:
                    safety_factor = 0.3
                elif obj.safety_level == SafetyLevel.MEDIUM:
                    safety_factor = 0.5
                
                # Reduce score based on proximity and safety level
                score_reduction = (1 - proximity_factor) * (1 - safety_factor)
                score -= score_reduction
        
        # Ensure score is in range [0, 1]
        return max(0.0, min(1.0, score))
    
    def get_object_stats(self) -> Dict[str, Any]:
        """
        Get statistics about detected objects
        
        Returns:
            Dictionary with object statistics
        """
        # Count objects by category and safety level
        categories = {cat.value: 0 for cat in ObjectCategory}
        safety_levels = {level.value: 0 for level in SafetyLevel}
        
        for obj in self.detection_history:
            categories[obj.category.value] += 1
            safety_levels[obj.safety_level.value] += 1
        
        return {
            "total_detections": self.detection_count,
            "current_detections": len(self.current_detections),
            "by_category": categories,
            "by_safety_level": safety_levels,
            "has_safety_critical": any(obj.safety_level in [SafetyLevel.CRITICAL, SafetyLevel.HIGH] 
                                     for obj in self.current_detections)
        }


class ChildAnimalDetector(ObjectDetector):
    """
    Specialized object detector focused on children and animals
    
    This detector has higher sensitivity and more conservative safety settings
    for detecting and avoiding children and animals.
    """
    
    def __init__(self, config: ConfigManager, camera: Camera):
        """
        Initialize the child and animal detector
        
        Args:
            config: Configuration manager
            camera: Camera instance for capturing images
        """
        # Modify configuration for specialized detection
        # First, get a copy of the configuration to not modify the original
        child_config = ConfigManager({})
        for key, value in config.__dict__.items():
            if hasattr(config, key) and not key.startswith('_'):
                setattr(child_config, key, value)
        
        # Override specific settings for child and animal detection
        child_config.set("object_detection.confidence_threshold", 0.4)  # Lower threshold to increase sensitivity
        child_config.set("object_detection.interval", 0.1)  # More frequent detection
        child_config.set("object_detection.child_safety_radius", 5.0)  # Larger safety radius
        child_config.set("object_detection.pet_safety_radius", 4.0)  # Larger safety radius
        
        # Initialize the base object detector with modified config
        super().__init__(child_config, camera)
        
        # Additional state for persistent tracking
        self.child_detected_time = None
        self.last_child_position = None
        self.stop_duration = config.get("child_detection.stop_duration", 30)  # Seconds to stop after child detection
        
        self.logger.info("Child and animal detector initialized with enhanced safety settings")
    
    def detect_objects(self, image: np.ndarray) -> List[DetectedObject]:
        """
        Detect objects with special focus on children and animals
        
        Args:
            image: Image as numpy array
            
        Returns:
            List of detected objects
        """
        # Get base detections
        detections = super().detect_objects(image)
        
        # Apply additional processing for child/animal detection
        for detection in detections:
            # For children, lower the distance estimate to increase safety margin
            if detection.category == ObjectCategory.CHILD and detection.distance is not None:
                # Reduce estimated distance by 20% to create a larger safety buffer
                detection.distance *= 0.8
            
            # For pets, apply similar adjustment
            if detection.category == ObjectCategory.PET and detection.distance is not None:
                # Reduce estimated distance by 15%
                detection.distance *= 0.85
        
        # Track child detections over time
        child_detections = [d for d in detections if d.category == ObjectCategory.CHILD]
        if child_detections:
            self.child_detected_time = time.time()
            # In a real implementation, we would track the child's position over time
            self.last_child_position = child_detections[0].bounding_box
        
        return detections
    
    def is_safe_to_move(self) -> bool:
        """
        Check if it's safe to move or if the mower should stop
        
        Returns:
            True if safe to move, False if the mower should stop
        """
        # If a child has been detected recently, stop moving for a safety period
        if self.child_detected_time is not None:
            elapsed_time = time.time() - self.child_detected_time
            if elapsed_time < self.stop_duration:
                return False
        
        # Check current detections
        for obj in self.current_detections:
            if obj.safety_level == SafetyLevel.CRITICAL:
                return False
        
        return True
    
    def get_safe_retreat_direction(self) -> Optional[Tuple[float, float]]:
        """
        Get a safe direction to retreat if unsafe conditions are detected
        
        Returns:
            Direction vector or None if no retreat is needed
        """
        if not self.is_safe_to_move():
            # Find the direction with the highest safety score
            safe_directions = self.get_safe_directions(num_directions=16)
            if safe_directions and safe_directions[0][0] > 0.7:
                # Return the safest direction
                return safe_directions[0][1]
            
            # If no direction is very safe, move backward
            return (-1.0, 0.0)  # Backward direction
        
        return None  # No need to retreat
