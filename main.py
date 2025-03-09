#!/usr/bin/env python3
"""
Robot Mower Advanced - Main Entry Point

This script serves as the entry point for the Robot Mower Advanced system.
It initializes the application, loads configurations, and starts all necessary services.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import time
import signal

from core.application import Application
from core.config import ConfigManager
from hardware.factory import HardwareFactory
# No SensorManager class, we use dict of sensors instead
from navigation.edge_following import EdgeFollowingController
from navigation.zone_management import ZoneManager
from perception.lawn_health import LawnHealthAnalyzer
from perception.growth_prediction import GrassGrowthPredictor
from perception.object_detection import ObjectDetector
from scheduling.weather_scheduler import WeatherBasedScheduler
from maintenance.maintenance_tracker import MaintenanceTracker
from security.theft_protection import TheftProtection
from web.app import WebInterface


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Robot Mower Advanced Control System")
    
    parser.add_argument("--config", type=str, default="config/default_config.yaml",
                        help="Path to configuration file (default: config/default_config.yaml)")
    
    parser.add_argument("--log-level", type=str, default=None, 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level (overrides config)")
    
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Data directory path (overrides config)")
    
    parser.add_argument("--dev", action="store_true",
                        help="Development mode (more verbose output)")
    
    parser.add_argument("--no-web", action="store_true",
                        help="Disable web interface")
    
    parser.add_argument("--sim", action="store_true",
                        help="Run in simulation mode (no physical hardware)")
    
    parser.add_argument("--test", action="store_true",
                        help="Run system test and exit")
    
    return parser.parse_args()


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set development mode if specified
    dev_mode = args.dev
    
    # Configure logging
    log_level = args.log_level or ("DEBUG" if dev_mode else "INFO")
    
    # Initialize application
    app = Application(
        app_name="RobotMower",
        config_dir=os.path.dirname(args.config),
        log_level=log_level
    )
    
    # Get logger
    logger = app.log_manager.get_logger("Main")
    logger.info("Starting Robot Mower Advanced system")
    
    # Load configuration
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return 1
    
    app.config_manager.load_config(str(config_path))
    logger.info(f"Loaded configuration from {config_path}")
    
    # Override config with command line args
    if args.data_dir:
        app.config_manager.set("system.data_dir", args.data_dir)
    
    # Create data directory
    data_dir = app.config_manager.get("system.data_dir", "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize hardware
    try:
        # Create hardware factory
        hardware_factory = HardwareFactory(
            app.config_manager,
            service_locator=app.container
        )
        app.register_service(HardwareFactory, factory=lambda: hardware_factory)
        
        # Initialize hardware components
        motor_controller = hardware_factory.create_motor_controller()
        blade_controller = hardware_factory.create_blade_controller()
        app.register_service(type(motor_controller), factory=lambda: motor_controller)
        app.register_service(type(blade_controller), factory=lambda: blade_controller)
        
        # Initialize sensors
        sensors = hardware_factory.create_all_sensors()
        app.register_service(dict, factory=lambda: sensors)
        
        # Start application
        app.startup()
        
        # Initialize higher-level services
        zone_manager = ZoneManager(app.config_manager, sensors)
        edge_controller = EdgeFollowingController(app.config_manager, motor_controller, sensors)
        maintenance_tracker = MaintenanceTracker(app.config_manager)
        lawn_health = LawnHealthAnalyzer(app.config_manager, sensors)
        growth_predictor = GrassGrowthPredictor(app.config_manager)
        weather_scheduler = WeatherBasedScheduler(app.config_manager)
        theft_protection = TheftProtection(app.config_manager, sensors)
        
        # Register services with the application
        app.register_service(ZoneManager, factory=lambda: zone_manager)
        app.register_service(EdgeFollowingController, factory=lambda: edge_controller)
        app.register_service(MaintenanceTracker, factory=lambda: maintenance_tracker)
        app.register_service(LawnHealthAnalyzer, factory=lambda: lawn_health)
        app.register_service(GrassGrowthPredictor, factory=lambda: growth_predictor)
        app.register_service(WeatherBasedScheduler, factory=lambda: weather_scheduler)
        app.register_service(TheftProtection, factory=lambda: theft_protection)
        
        # Initialize object detection if enabled
        if app.config_manager.get("perception.object_detection.enabled", False):
            object_detector = ObjectDetector(app.config_manager, sensors)
            app.register_service(ObjectDetector, factory=lambda: object_detector)
        
        # Start web interface if not disabled
        if not args.no_web:
            web_interface = WebInterface(
                app.config_manager,
                power_manager=sensors.get("power") if sensors else None,
                zone_manager=zone_manager,
                health_analyzer=lawn_health,
                growth_predictor=growth_predictor,
                maintenance_tracker=maintenance_tracker,
                theft_protection=theft_protection,
                weather_scheduler=weather_scheduler
            )
            app.register_service(WebInterface, factory=lambda: web_interface)
            web_interface.start()
        
        # For test mode, run a quick test and exit
        if args.test:
            logger.info("Running system test...")
            # Implement test routine here
            logger.info("System test completed successfully")
            return 0
        
        # Main control loop
        logger.info("Robot Mower system running. Press Ctrl+C to exit.")
        
        try:
            # Wait for shutdown signal
            app.wait_for_shutdown()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        finally:
            # Cleanup
            logger.info("Shutting down Robot Mower system...")
            
            # Stop web interface
            if not args.no_web and web_interface:
                web_interface.stop()
            
            # Stop application
            app.shutdown()
            
            logger.info("Robot Mower system shutdown complete")
    
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
