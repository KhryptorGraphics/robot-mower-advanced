"""
Robot Mower Application

Main application class that bootstraps the system and manages services.
Acts as the entry point and manages the application lifecycle.
"""

import os
import sys
import signal
import traceback
import threading
from typing import Dict, List, Optional, Any, Callable, Set, Type
from pathlib import Path
import time
import atexit
from datetime import datetime

from .config import ConfigManager
from .logger import LogManager
from .dependency_injection import Container, DependencyError


class ApplicationError(Exception):
    """Exception raised for application-level errors"""
    pass


class ServiceStatus:
    """Represents the status of a service"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class Application:
    """
    Main application class that bootstraps and manages the Robot Mower system
    
    Features:
    - Configuration and logging initialization
    - Service registration and lifecycle management
    - Signal handling for graceful shutdown
    - Error handling and recovery
    - System diagnostics
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one Application instance"""
        if cls._instance is None:
            cls._instance = super(Application, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, 
                 app_name: str = "RobotMower",
                 config_dir: Optional[str] = None,
                 log_level: str = "INFO"):
        """Initialize the application"""
        # Skip re-initialization if already initialized
        if getattr(self, "_initialized", False):
            return
        
        self.app_name = app_name
        self.start_time = datetime.now()
        self.shutdown_event = threading.Event()
        self.service_statuses: Dict[str, str] = {}
        self.background_threads: List[threading.Thread] = []
        self._registered_services: Set[Type] = set()
        
        # Initialize configuration
        self.config_manager = ConfigManager(config_dir)
        
        # Initialize logging with configuration
        log_level = self.config_manager.get("system.log_level", log_level)
        self.log_manager = LogManager(log_level)
        self.logger = self.log_manager.get_logger("Application")
        
        # Initialize dependency injection container
        self.container = Container()
        
        # Register core services
        self._register_core_services()
        
        # Set initialized flag
        self._initialized = True
        self.logger.info(f"{self.app_name} application initialized")
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Register atexit handler
        atexit.register(self.shutdown)
    
    def _register_core_services(self) -> None:
        """Register core services with the dependency injection container"""
        # Register configuration manager
        self.container.register(
            ConfigManager,
            factory=lambda: self.config_manager,
            singleton=True
        )
        
        # Register logging manager
        self.container.register(
            LogManager,
            factory=lambda: self.log_manager,
            singleton=True
        )
        
        # Register application instance
        self.container.register(
            Application,
            factory=lambda: self,
            singleton=True
        )
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown"""
        # Handle Ctrl+C (SIGINT)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Handle termination (SIGTERM)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame) -> None:
        """Handle signals for graceful shutdown"""
        if sig == signal.SIGINT:
            self.logger.info("Received SIGINT (Ctrl+C), shutting down...")
        elif sig == signal.SIGTERM:
            self.logger.info("Received SIGTERM, shutting down...")
        
        # Initiate shutdown
        self.shutdown()
    
    def startup(self) -> None:
        """Start the application and all registered services"""
        self.logger.info(f"Starting {self.app_name} application")
        
        try:
            # Create data directories
            data_dir = self.config_manager.get("system.data_dir", str(Path(__file__).parent.parent / "data"))
            os.makedirs(data_dir, exist_ok=True)
            
            # Load plugins (future)
            
            # Start services
            self._start_services()
            
            self.logger.info(f"{self.app_name} application started successfully")
        except Exception as e:
            self.logger.error(f"Error during startup: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ApplicationError(f"Failed to start application: {str(e)}")
    
    def _start_services(self) -> None:
        """Start all registered services"""
        # This can be extended to start services in the correct dependency order
        # For now, we assume services are started when they are first resolved
        pass
    
    def shutdown(self) -> None:
        """Shut down the application gracefully"""
        if self.shutdown_event.is_set():
            # Already shutting down
            return
        
        self.logger.info(f"Shutting down {self.app_name} application")
        self.shutdown_event.set()
        
        # Stop background threads
        for thread in self.background_threads:
            if thread.is_alive():
                self.logger.debug(f"Waiting for thread {thread.name} to finish")
                thread.join(timeout=5)
        
        # Additional cleanup
        self.logger.info(f"{self.app_name} application shutdown complete")
    
    def is_shutting_down(self) -> bool:
        """Check if the application is in the process of shutting down"""
        return self.shutdown_event.is_set()
    
    def run_in_background(self, target: Callable, name: str = None, daemon: bool = True) -> threading.Thread:
        """Run a function in a background thread"""
        thread_name = name or f"background-thread-{len(self.background_threads) + 1}"
        thread = threading.Thread(target=target, name=thread_name, daemon=daemon)
        thread.start()
        self.background_threads.append(thread)
        return thread
    
    def register_service(self, service_type: Type, implementation: Type = None,
                        factory: Callable = None, singleton: bool = True) -> None:
        """Register a service with the container"""
        self.container.register(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            singleton=singleton
        )
        self._registered_services.add(service_type)
        self.service_statuses[service_type.__name__] = ServiceStatus.STOPPED
    
    def resolve_service(self, service_type: Type) -> Any:
        """Resolve a service from the container"""
        try:
            service = self.container.resolve(service_type)
            self.service_statuses[service_type.__name__] = ServiceStatus.RUNNING
            return service
        except DependencyError as e:
            self.service_statuses[service_type.__name__] = ServiceStatus.ERROR
            self.logger.error(f"Error resolving service {service_type.__name__}: {str(e)}")
            raise
    
    def get_uptime(self) -> float:
        """Get the application uptime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the application status"""
        return {
            "name": self.app_name,
            "version": self.config_manager.get("system.version", "unknown"),
            "uptime": self.get_uptime(),
            "start_time": self.start_time.isoformat(),
            "services": self.service_statuses.copy(),
            "shutting_down": self.is_shutting_down()
        }
    
    def wait_for_shutdown(self) -> None:
        """Wait until the application is shut down"""
        self.shutdown_event.wait()
