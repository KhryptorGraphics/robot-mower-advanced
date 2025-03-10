"""
Hailo NPU Integration Module for Robot Mower Advanced

This module provides integration with the Hailo NPU HAT for Raspberry Pi,
allowing real-time object detection and avoidance using deep learning models.
"""

import os
import time
import logging
import threading
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional, Union, Any

# Import Hailo SDK - this will be installed via the installation script
try:
    import hailo
    import hailort
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False
    logging.warning("Hailo SDK not found. Object detection using Hailo NPU will be unavailable.")

# Define object detection classes (COCO dataset by default)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book",
    "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Obstacle categories (classes that should be avoided)
OBSTACLE_CATEGORIES = [
    "person", "bicycle", "car", "motorcycle", "dog", "cat", "potted plant", 
    "chair", "bench", "backpack", "suitcase", "sports ball", "bottle"
]

# Safety critical obstacles (require immediate stopping)
SAFETY_CRITICAL = ["person", "dog", "cat"]


class HailoObjectDetector:
    """
    Hailo NPU-based object detection for the Robot Mower.
    
    This class handles the integration with the Hailo NPU HAT to perform
    real-time object detection on video frames from the mower's camera.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Hailo object detector
        
        Args:
            config: Configuration dictionary containing Hailo settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.model_path = config.get("hailo", {}).get("model_path", "/opt/hailo/models/yolov5m.hef")
        self.confidence_threshold = config.get("hailo", {}).get("confidence_threshold", 0.5)
        self.device_id = config.get("hailo", {}).get("device_id", None)
        self.input_shape = config.get("hailo", {}).get("input_shape", (640, 640))
        self.class_filter = config.get("hailo", {}).get("class_filter", None)
        
        # Initialize state variables
        self.initialized = False
        self.running = False
        self.latest_detections = []
        self.latest_frame = None
        self.detection_lock = threading.Lock()
        
        # Performance metrics
        self.inference_times = []
        self.avg_inference_time = 0
        self.fps = 0
        
        # Initialize Hailo NPU if available
        if HAILO_AVAILABLE:
            self._initialize_hailo()
    
    def _initialize_hailo(self) -> None:
        """Initialize the Hailo NPU device and load model"""
        try:
            self.logger.info("Initializing Hailo NPU...")
            
            # Create device and load network
            if self.device_id:
                self.device = hailo.Device(device_id=self.device_id)
            else:
                self.device = hailo.Device()
            
            self.logger.info(f"Hailo device initialized: {self.device.device_id}")
            
            # Load the model (HEF file)
            if not os.path.exists(self.model_path):
                self.logger.error(f"Model file not found: {self.model_path}")
                return
            
            self.logger.info(f"Loading model: {self.model_path}")
            self.network = hailo.Network(self.device, self.model_path)
            
            # Get input and output layers
            self.input_vstream = hailo.InputVStream(self.network)
            self.output_vstream = hailo.OutputVStream(self.network)
            
            # Start the network
            self.input_vstream.start()
            self.output_vstream.start()
            
            self.logger.info("Hailo NPU initialization completed successfully")
            self.initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Hailo NPU: {e}")
            self.initialized = False
    
    def start(self) -> bool:
        """
        Start the object detection processing loop
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start object detection: Hailo NPU not initialized")
            return False
        
        if self.running:
            self.logger.warning("Object detection already running")
            return True
        
        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        self.logger.info("Object detection started")
        
        return True
    
    def stop(self) -> None:
        """Stop the object detection processing loop"""
        self.running = False
        if hasattr(self, 'detection_thread') and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2.0)
        self.logger.info("Object detection stopped")
    
    def _detection_loop(self) -> None:
        """Main detection loop that processes frames from the camera"""
        self.logger.info("Detection loop started")
        
        while self.running:
            # Skip if no frame is available
            if self.latest_frame is None:
                time.sleep(0.01)
                continue
            
            try:
                # Process the current frame
                detections = self.process_frame(self.latest_frame)
                
                # Update the latest detections
                with self.detection_lock:
                    self.latest_detections = detections
                    
            except Exception as e:
                self.logger.error(f"Error in detection loop: {e}")
                time.sleep(0.1)
    
    def process_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process a video frame through the Hailo NPU for object detection
        
        Args:
            frame: Input video frame (BGR format)
            
        Returns:
            List of detection dictionaries containing class, confidence, and bounding box
        """
        if not self.initialized:
            return []
        
        start_time = time.time()
        
        # Prepare the frame for the model
        preprocessed = self._preprocess_frame(frame)
        
        # Run inference
        try:
            # Send input to the NPU
            self.input_vstream.send(preprocessed)
            
            # Get the output from the NPU
            output = self.output_vstream.recv()
            
            # Post-process the output to get detections
            detections = self._postprocess_output(output, frame.shape)
            
        except Exception as e:
            self.logger.error(f"Inference error: {e}")
            return []
        
        # Calculate performance metrics
        inference_time = time.time() - start_time
        self.inference_times.append(inference_time)
        
        # Keep only the last 100 inference times
        if len(self.inference_times) > 100:
            self.inference_times.pop(0)
        
        # Update average inference time and fps
        self.avg_inference_time = sum(self.inference_times) / len(self.inference_times)
        self.fps = 1.0 / self.avg_inference_time if self.avg_inference_time > 0 else 0
        
        return detections
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess the frame for the Hailo NPU
        
        Args:
            frame: Input BGR frame
            
        Returns:
            Preprocessed frame ready for the Hailo NPU
        """
        # Resize the frame to the input shape expected by the model
        input_width, input_height = self.input_shape
        resized = cv2.resize(frame, (input_width, input_height))
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize the image (0-255 -> 0-1)
        normalized = rgb.astype(np.float32) / 255.0
        
        # Transpose to the format expected by the model (batch, channels, height, width)
        transposed = np.transpose(normalized, (2, 0, 1))
        
        # Add batch dimension
        batched = np.expand_dims(transposed, axis=0)
        
        return batched
    
    def _postprocess_output(self, output: np.ndarray, original_shape: Tuple[int, int, int]) -> List[Dict[str, Any]]:
        """
        Post-process the model output to extract detections
        
        Args:
            output: Raw output from the Hailo NPU
            original_shape: Original shape of the input frame (height, width, channels)
            
        Returns:
            List of detection dictionaries
        """
        # This will need to be adjusted based on the specific model format
        # For YOLOv5, the output is typically [batch, num_detections, 5+num_classes]
        # where the first 5 values are [x, y, width, height, confidence]
        
        # Extract detections from the output
        detections = []
        
        # Example implementation for YOLOv5 output format
        # Actual implementation depends on the model and output format
        boxes = output[..., :4]  # x, y, width, height
        scores = output[..., 4]  # confidence
        class_probs = output[..., 5:]  # class probabilities
        
        # Get original dimensions
        height, width, _ = original_shape
        
        # Process each detection
        for i in range(len(scores)):
            confidence = scores[i]
            
            # Skip low confidence detections
            if confidence < self.confidence_threshold:
                continue
            
            # Get the class with highest probability
            class_id = np.argmax(class_probs[i])
            class_name = COCO_CLASSES[class_id]
            
            # Filter by class if specified
            if self.class_filter and class_name not in self.class_filter:
                continue
            
            # Extract bounding box coordinates
            x, y, w, h = boxes[i]
            
            # Convert normalized coordinates to pixel coordinates
            x1 = int(x * width)
            y1 = int(y * height)
            x2 = int((x + w) * width)
            y2 = int((y + h) * height)
            
            # Create detection dictionary
            detection = {
                "class": class_name,
                "confidence": float(confidence),
                "bbox": [x1, y1, x2, y2],
                "is_obstacle": class_name in OBSTACLE_CATEGORIES,
                "is_safety_critical": class_name in SAFETY_CRITICAL
            }
            
            detections.append(detection)
        
        return detections
    
    def get_latest_detections(self) -> List[Dict[str, Any]]:
        """
        Get the latest object detections
        
        Returns:
            List of detection dictionaries
        """
        with self.detection_lock:
            return self.latest_detections.copy()
    
    def set_frame(self, frame: np.ndarray) -> None:
        """
        Set a new frame to be processed
        
        Args:
            frame: New video frame
        """
        self.latest_frame = frame
    
    def get_performance_stats(self) -> Dict[str, float]:
        """
        Get performance statistics
        
        Returns:
            Dictionary with inference time and FPS
        """
        return {
            "inference_time_ms": self.avg_inference_time * 1000,
            "fps": self.fps
        }
    
    def cleanup(self) -> None:
        """Clean up resources when shutting down"""
        self.stop()
        
        if self.initialized:
            try:
                self.input_vstream.stop()
                self.output_vstream.stop()
                del self.network
                self.device.close()
                self.logger.info("Hailo NPU resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error cleaning up Hailo NPU: {e}")


class ObstacleDetectionSystem:
    """
    Main obstacle detection system that uses the Hailo NPU for object detection.
    This class coordinates the detection process and provides an interface for
    other system components to get obstacle information.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the obstacle detection system
        
        Args:
            config: System configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Configure camera settings
        camera_config = config.get("camera", {})
        self.camera_enabled = camera_config.get("enabled", True)
        self.camera_width = camera_config.get("width", 640)
        self.camera_height = camera_config.get("height", 480)
        self.camera_fps = camera_config.get("fps", 30)
        self.camera_index = camera_config.get("index", 0)
        
        # Configure object detection
        detection_config = config.get("object_detection", {})
        self.detection_enabled = detection_config.get("enabled", True)
        
        # Safety zones (in meters)
        self.safety_critical_zone = detection_config.get("safety_critical_zone", 1.5)  # meters
        self.obstacle_zone = detection_config.get("obstacle_zone", 3.0)  # meters
        
        # Initialize state
        self.initialized = False
        self.running = False
        self.camera = None
        self.detector = None
        self.frame_thread = None
        
        # Safety state
        self.obstacles_detected = False
        self.safety_critical_detected = False
        self.latest_obstacle_distance = float('inf')
        self.latest_obstacles = []
        
        # Initialize camera and detector if enabled
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize camera and Hailo detector"""
        try:
            # Initialize the camera if enabled
            if self.camera_enabled:
                self._init_camera()
            
            # Initialize the Hailo detector if enabled and available
            if self.detection_enabled and HAILO_AVAILABLE:
                self.detector = HailoObjectDetector(self.config)
                if not self.detector.initialized:
                    self.logger.warning("Hailo detector failed to initialize")
            elif self.detection_enabled:
                self.logger.warning("Hailo SDK not available, object detection disabled")
            
            self.initialized = True
            self.logger.info("Obstacle detection system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize obstacle detection system: {e}")
            self.initialized = False
    
    def _init_camera(self) -> None:
        """Initialize the camera for video capture"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.camera_fps)
            
            if not self.camera.isOpened():
                self.logger.error("Failed to open camera")
                self.camera_enabled = False
                return
            
            self.logger.info(f"Camera initialized: {self.camera_width}x{self.camera_height} @ {self.camera_fps}fps")
            
        except Exception as e:
            self.logger.error(f"Camera initialization error: {e}")
            self.camera_enabled = False
    
    def start(self) -> bool:
        """
        Start the obstacle detection system
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: System not initialized")
            return False
        
        if self.running:
            self.logger.warning("System already running")
            return True
        
        self.running = True
        
        # Start the frame processing thread if camera is enabled
        if self.camera_enabled and self.camera and self.camera.isOpened():
            self.frame_thread = threading.Thread(target=self._frame_loop)
            self.frame_thread.daemon = True
            self.frame_thread.start()
        
        # Start the Hailo detector if available
        if self.detector and self.detector.initialized:
            self.detector.start()
        
        self.logger.info("Obstacle detection system started")
        return True
    
    def stop(self) -> None:
        """Stop the obstacle detection system"""
        self.running = False
        
        # Stop the Hailo detector
        if self.detector:
            self.detector.stop()
        
        # Stop the frame processing thread
        if hasattr(self, 'frame_thread') and self.frame_thread and self.frame_thread.is_alive():
            self.frame_thread.join(timeout=2.0)
        
        # Release the camera
        if self.camera and self.camera.isOpened():
            self.camera.release()
        
        self.logger.info("Obstacle detection system stopped")
    
    def _frame_loop(self) -> None:
        """Main loop for capturing and processing camera frames"""
        self.logger.info("Frame processing loop started")
        
        while self.running:
            try:
                # Capture a frame from the camera
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    self.logger.warning("Failed to capture frame from camera")
                    time.sleep(0.1)
                    continue
                
                # If detector is available, send the frame for processing
                if self.detector:
                    self.detector.set_frame(frame)
                
                # Process obstacle detections
                self._process_detections()
                
            except Exception as e:
                self.logger.error(f"Error in frame processing loop: {e}")
                time.sleep(0.1)
    
    def _process_detections(self) -> None:
        """Process the latest detections to update obstacle status"""
        if not self.detector:
            return
        
        # Get the latest detections
        detections = self.detector.get_latest_detections()
        
        # Reset detection flags
        self.obstacles_detected = False
        self.safety_critical_detected = False
        self.latest_obstacle_distance = float('inf')
        obstacles = []
        
        # Process each detection
        for detection in detections:
            if detection["is_obstacle"]:
                self.obstacles_detected = True
                
                # Calculate approximate distance based on bounding box size
                bbox = detection["bbox"]
                bbox_height = bbox[3] - bbox[1]
                # This is a simple approximation - actual distance calculation
                # would need camera calibration and object size models
                estimated_distance = self._estimate_distance(detection)
                
                obstacle = {
                    "class": detection["class"],
                    "confidence": detection["confidence"],
                    "bbox": detection["bbox"],
                    "distance": estimated_distance,
                    "is_safety_critical": detection["is_safety_critical"]
                }
                
                obstacles.append(obstacle)
                
                # Update minimum distance
                if estimated_distance < self.latest_obstacle_distance:
                    self.latest_obstacle_distance = estimated_distance
                
                # Check if this is a safety critical obstacle
                if detection["is_safety_critical"] and estimated_distance <= self.safety_critical_zone:
                    self.safety_critical_detected = True
        
        # Update the latest obstacles list
        self.latest_obstacles = obstacles
    
    def _estimate_distance(self, detection: Dict[str, Any]) -> float:
        """
        Estimate the distance to an object based on its bounding box
        
        Args:
            detection: Detection dictionary
            
        Returns:
            Estimated distance in meters
        """
        # This is a simplified model and would need calibration for accurate results
        # A proper implementation would use camera parameters and known object sizes
        
        bbox = detection["bbox"]
        bbox_height = bbox[3] - bbox[1]
        bbox_width = bbox[2] - bbox[0]
        
        # The larger dimension is likely more reliable for distance estimation
        dimension = max(bbox_height, bbox_width)
        
        # Get estimated object physical size (in meters)
        object_size = self._get_object_size(detection["class"])
        
        # Simple pinhole camera model for distance estimation
        # focal_length * real_size / perceived_size
        # This would need proper calibration in a real implementation
        focal_length = self.camera_width  # A very rough approximation
        
        if dimension > 0:
            distance = (focal_length * object_size) / dimension
        else:
            distance = float('inf')
        
        return distance
    
    def _get_object_size(self, class_name: str) -> float:
        """
        Get the typical size of an object in meters
        
        Args:
            class_name: Object class name
            
        Returns:
            Estimated object size in meters
        """
        # These are rough estimates and would need to be refined
        sizes = {
            "person": 1.7,      # Average height
            "bicycle": 1.0,     # Average height
            "car": 1.5,         # Average height
            "motorcycle": 1.2,  # Average height
            "dog": 0.5,         # Average height
            "cat": 0.3,         # Average height
            "potted plant": 0.5,# Average height
            "chair": 0.8,       # Average height
            "bench": 0.5,       # Average height
            # Add more objects as needed
        }
        
        # Default to 1 meter if class not found
        return sizes.get(class_name, 1.0)
    
    def is_path_clear(self) -> bool:
        """
        Check if the path ahead is clear of obstacles
        
        Returns:
            bool: True if path is clear, False if obstacles detected
        """
        return not self.obstacles_detected
    
    def is_emergency_stop_required(self) -> bool:
        """
        Check if an emergency stop is required due to safety critical obstacles
        
        Returns:
            bool: True if emergency stop is required, False otherwise
        """
        return self.safety_critical_detected
    
    def get_closest_obstacle_distance(self) -> float:
        """
        Get the distance to the closest detected obstacle
        
        Returns:
            float: Distance in meters, or inf if no obstacles detected
        """
        return self.latest_obstacle_distance
    
    def get_obstacle_info(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about detected obstacles
        
        Returns:
            List of obstacle dictionaries
        """
        return self.latest_obstacles
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the obstacle detection system
        
        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "obstacles_detected": self.obstacles_detected,
            "safety_critical_detected": self.safety_critical_detected,
            "closest_obstacle_distance": self.latest_obstacle_distance,
            "obstacle_count": len(self.latest_obstacles),
            "performance": self.detector.get_performance_stats() if self.detector else {}
        }
    
    def cleanup(self) -> None:
        """Clean up resources when shutting down"""
        self.stop()
        
        if self.detector:
            self.detector.cleanup()
        
        self.logger.info("Obstacle detection system cleaned up")
