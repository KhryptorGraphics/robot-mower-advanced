#!/usr/bin/env python3
"""
Robot Mower Advanced - Main Entry Point

This is the main entry point for the Robot Mower Advanced software.
It initializes all necessary components and starts the system.
"""

import os
import sys
import logging
import argparse
import signal
import time
from typing import Dict, Any, Optional
import yaml

# Setup basic logging - will be enhanced once config is loaded
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('main')

# Global flag for stopping the program
running = True


def signal_handler(sig, frame):
    """Handle signals to properly shutdown the system"""
    global running
    logger.info(f"Received signal {sig}, initiating shutdown...")
    running = False


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Robot Mower Advanced Control System')
    
    parser.add_argument('--config', 
                        type=str, 
                        default='config/local_config.yaml',
                        help='Path to configuration file')
    
    parser.add_argument('--log-level', 
                        type=str, 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', 
                        help='Set logging level')
    
    parser.add_argument('--data-dir', 
                        type=str, 
                        default='data',
                        help='Data directory')
    
    parser.add_argument('--dev', 
                        action='store_true',
                        help='Run in development mode')
    
    parser.add_argument('--no-web', 
                        action='store_true',
                        help='Disable web interface')
    
    parser.add_argument('--sim', 
                        action='store_true',
                        help='Run in simulation mode (no hardware)')
    
    parser.add_argument('--test', 
                        action='store_true',
                        help='Run system test and exit')
    
    parser.add_argument('--update', 
                        action='store_true',
                        help='Update software from repository')
    
    parser.add_argument('--backup', 
                        action='store_true',
                        help='Create a backup of configuration and data')
    
    parser.add_argument('--restore', 
                        type=str,
                        help='Restore from a backup file')
    
    parser.add_argument('--reset-config', 
                        action='store_true',
                        help='Reset to default configuration')
    
    parser.add_argument('--calibrate', 
                        action='store_true',
                        help='Run sensor calibration routines')
    
    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary with configuration values
    """
    logger.info(f"Loading configuration from {config_path}")
    
    # Check if config path exists
    if not os.path.exists(config_path):
        # Try to find the default config
        default_config_path = os.path.join(
            os.path.dirname(config_path), 'default_config.yaml')
        
        if os.path.exists(default_config_path):
            logger.warning(f"Configuration file {config_path} not found, "
                          f"using default configuration at {default_config_path}")
            config_path = default_config_path
        else:
            logger.error(f"No configuration file found at {config_path} "
                        f"and no default configuration available.")
            sys.exit(1)
    
    # Load the config file
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.debug(f"Loaded configuration: {config}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        sys.exit(1)


def configure_logging(config: Dict[str, Any], args) -> None:
    """Configure logging based on configuration and command line args"""
    # Determine log level - command line args override config
    log_level_name = args.log_level
    if 'system' in config and 'log_level' in config['system']:
        log_level_name = config['system']['log_level']
    
    # Convert string to logging level
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Determine log file
    log_file = None
    if 'system' in config and 'log_file' in config['system']:
        log_file = config['system']['log_file']
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)
    
    # Add file handler if log file is specified
    if log_file:
        # Ensure the logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(file_handler)
    
    logger.debug(f"Logging configured with level {log_level_name}")


def handle_special_actions(args) -> bool:
    """
    Handle special command line actions like backup, restore, etc.
    
    Returns:
        True if a special action was performed, False otherwise
    """
    if args.update:
        logger.info("Updating software from repository")
        # Implement software update logic here
        # ...
        return True
    
    if args.backup:
        logger.info("Creating backup of configuration and data")
        # Implement backup logic here
        # ...
        return True
    
    if args.restore:
        logger.info(f"Restoring from backup file {args.restore}")
        # Implement restore logic here
        # ...
        return True
    
    if args.reset_config:
        logger.info("Resetting to default configuration")
        # Implement config reset logic here
        # ...
        return True
    
    if args.calibrate:
        logger.info("Running sensor calibration routines")
        # Implement calibration logic here
        # ...
        return True
    
    if args.test:
        logger.info("Running system test")
        # Implement system test logic here
        # ...
        return True
    
    return False


def initialize_system(config: Dict[str, Any], args) -> Dict[str, Any]:
    """
    Initialize the system components
    
    Args:
        config: System configuration
        args: Command line arguments
        
    Returns:
        Dictionary with initialized components
    """
    logger.info("Initializing system components")
    
    components = {}
    
    # Set simulation mode flag based on args
    simulation_mode = args.sim
    
    try:
        # Initialize components here - examples:
        
        # Initialize hardware interface
        # This would be replaced with actual implementations in a real system
        from hardware.sensors import UltrasonicSensor, MPU6050IMUSensor
        
        # Import navigation components
        from navigation.path_planning import PathPlanner, PathPlanningConfig, MowingPattern
        
        # Import perception components
        from perception.hailo_integration import ObstacleDetectionSystem
        
        # Create sensor instances
        # In simulation mode, sensors will use mock data
        if not simulation_mode:
            # Try to initialize real hardware
            try:
                # Example sensor initialization
                ultrasonic_sensor = UltrasonicSensor(
                    trigger_pin=config.get('hardware', {}).get('sensors', {})
                    .get('ultrasonic', {}).get('trigger_pin', 23),
                    echo_pin=config.get('hardware', {}).get('sensors', {})
                    .get('ultrasonic', {}).get('echo_pin', 24)
                )
                components['ultrasonic_sensor'] = ultrasonic_sensor
                
                imu_sensor = MPU6050IMUSensor(config)
                components['imu_sensor'] = imu_sensor
                
                # Initialize Hailo NPU-based obstacle detection if enabled
                hailo_enabled = config.get('hailo', {}).get('enabled', False)
                if hailo_enabled:
                    try:
                        logger.info("Initializing Hailo NPU-based obstacle detection...")
                        obstacle_system = ObstacleDetectionSystem(config)
                        if obstacle_system.initialized:
                            components['obstacle_detection'] = obstacle_system
                            logger.info("Hailo NPU obstacle detection initialized successfully")
                        else:
                            logger.warning("Hailo NPU obstacle detection failed to initialize")
                    except Exception as e:
                        logger.error(f"Error initializing Hailo NPU obstacle detection: {e}")
                
                logger.info("Hardware components initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing hardware: {e}")
                logger.info("Falling back to simulation mode")
                simulation_mode = True
        
        # If in simulation mode, use mock components
        if simulation_mode:
            logger.info("Running in simulation mode with mock hardware")
            # Initialize mock sensors and other components
            # ...
            
        # Initialize path planning
        mowing_pattern_str = config.get('navigation', {}).get('mowing_pattern', 'parallel_lines')
        try:
            mowing_pattern = MowingPattern(mowing_pattern_str)
        except ValueError:
            logger.warning(f"Invalid mowing pattern '{mowing_pattern_str}', using default")
            mowing_pattern = MowingPattern.PARALLEL_LINES
        
        path_planning_config = PathPlanningConfig(
            pattern=mowing_pattern,
            line_direction=config.get('navigation', {}).get('line_direction', 0.0),
            path_overlap_percent=config.get('navigation', {}).get('path_overlap_percent', 10.0),
            perimeter_passes=config.get('navigation', {}).get('perimeter_passes', 2)
        )
        
        # Mower width in meters
        mower_width = config.get('hardware', {}).get('mower_width', 0.3)
        
        path_planner = PathPlanner(mower_width=mower_width, config=path_planning_config)
        components['path_planner'] = path_planner
        
        # Initialize web interface if not disabled
        if not args.no_web:
            # We would import and initialize the web interface here
            # For now, just log that it would be initialized
            logger.info("Web interface would be initialized here")
        
        logger.info("System initialization complete")
        
    except Exception as e:
        logger.error(f"Error during system initialization: {e}")
        sys.exit(1)
    
    return components


def main():
    """Main entry point for the application"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config)
    
    # Configure logging
    configure_logging(config, args)
    
    # Handle special actions (if any)
    if handle_special_actions(args):
        return 0
    
    # Initialize system components
    components = initialize_system(config, args)
    
    logger.info("Robot Mower Advanced system starting...")
    
    # Main loop
    try:
        while running:
            # Perform system updates
            try:
                # Check for obstacles using Hailo NPU-based detection if available
                if 'obstacle_detection' in components and components['obstacle_detection'].initialized:
                    obstacle_system = components['obstacle_detection']
                    
                    # Start the detection system if not already running
                    if not obstacle_system.running:
                        obstacle_system.start()
                    
                    # Check for obstacles
                    if obstacle_system.is_emergency_stop_required():
                        logger.warning("EMERGENCY STOP: Safety critical obstacle detected!")
                        # Implement emergency stop here
                        # motors.emergency_stop()
                        
                    elif not obstacle_system.is_path_clear():
                        closest_distance = obstacle_system.get_closest_obstacle_distance()
                        logger.info(f"Obstacle detected at {closest_distance:.2f} meters, taking avoidance action")
                        # Implement obstacle avoidance here
                        # navigation.avoid_obstacle()
                        
                    # Get obstacle info for logging/debugging
                    obstacles = obstacle_system.get_obstacle_info()
                    if obstacles:
                        logger.debug(f"Detected {len(obstacles)} obstacles")
                
                # Regular sensor checks and navigation updates
                # ...
                
                # Sleep a short time to prevent CPU hogging
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in main loop processing: {e}")
                time.sleep(1)  # Sleep longer on error
            
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        return 1
    finally:
        # Clean up resources
        logger.info("Cleaning up resources...")
        
        # Clean up components
        for name, component in components.items():
            if hasattr(component, 'cleanup'):
                try:
                    logger.info(f"Cleaning up {name}...")
                    component.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up {name}: {e}")
        
        logger.info("System shutdown complete")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
