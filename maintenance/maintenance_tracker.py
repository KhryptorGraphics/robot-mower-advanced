"""
Maintenance Tracking Module

This module provides functionality for tracking and scheduling maintenance tasks
for the robot mower, including blade replacement, cleaning, and other periodic maintenance.
"""

import os
import json
import logging
import threading
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta

from ..core.config import ConfigManager
from ..hardware.interfaces import BladeController, MotorController, PowerManagement


class MaintenanceStatus(Enum):
    """Enumeration of maintenance item statuses"""
    OK = "ok"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    UNKNOWN = "unknown"


class MaintenanceItem:
    """Class representing a maintenance item to be tracked"""
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 interval_hours: float, 
                 warning_threshold: float = 0.9,
                 last_maintenance: Optional[datetime] = None,
                 total_runtime_hours: float = 0.0):
        """
        Initialize a maintenance item
        
        Args:
            name: Name of the maintenance item
            description: Description of what needs to be maintained
            interval_hours: Hours between maintenance
            warning_threshold: Percentage of interval to trigger warning (0.0-1.0)
            last_maintenance: Last time maintenance was performed
            total_runtime_hours: Total runtime hours on this item
        """
        self.name = name
        self.description = description
        self.interval_hours = interval_hours
        self.warning_threshold = warning_threshold
        self.last_maintenance = last_maintenance or datetime.now()
        self.total_runtime_hours = total_runtime_hours
        self.runtime_at_last_maintenance = total_runtime_hours
    
    def update_runtime(self, hours: float) -> None:
        """
        Update the total runtime hours
        
        Args:
            hours: Hours to add to total runtime
        """
        self.total_runtime_hours += hours
    
    def perform_maintenance(self) -> None:
        """Record that maintenance has been performed"""
        self.last_maintenance = datetime.now()
        self.runtime_at_last_maintenance = self.total_runtime_hours
    
    def get_runtime_since_maintenance(self) -> float:
        """
        Get runtime hours since last maintenance
        
        Returns:
            Runtime hours since last maintenance
        """
        return self.total_runtime_hours - self.runtime_at_last_maintenance
    
    def get_status(self) -> MaintenanceStatus:
        """
        Get the current maintenance status
        
        Returns:
            MaintenanceStatus enum value
        """
        runtime_since_maintenance = self.get_runtime_since_maintenance()
        
        if runtime_since_maintenance >= self.interval_hours:
            return MaintenanceStatus.OVERDUE
        elif runtime_since_maintenance >= self.interval_hours * self.warning_threshold:
            return MaintenanceStatus.DUE_SOON
        else:
            return MaintenanceStatus.OK
    
    def get_time_until_maintenance(self) -> Optional[float]:
        """
        Get hours until maintenance is due
        
        Returns:
            Hours until maintenance or None if already overdue
        """
        runtime_since_maintenance = self.get_runtime_since_maintenance()
        remaining = self.interval_hours - runtime_since_maintenance
        
        return max(0.0, remaining) if remaining > 0 else None
    
    def get_percentage_until_maintenance(self) -> float:
        """
        Get percentage until maintenance is due (0-100)
        
        Returns:
            Percentage until maintenance (> 100 if overdue)
        """
        runtime_since_maintenance = self.get_runtime_since_maintenance()
        percentage = (runtime_since_maintenance / self.interval_hours) * 100.0
        
        return percentage
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert maintenance item to dictionary for storage
        
        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "interval_hours": self.interval_hours,
            "warning_threshold": self.warning_threshold,
            "last_maintenance": self.last_maintenance.isoformat() if self.last_maintenance else None,
            "total_runtime_hours": self.total_runtime_hours,
            "runtime_at_last_maintenance": self.runtime_at_last_maintenance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaintenanceItem':
        """
        Create maintenance item from dictionary
        
        Args:
            data: Dictionary representation
            
        Returns:
            MaintenanceItem instance
        """
        return cls(
            name=data["name"],
            description=data["description"],
            interval_hours=data["interval_hours"],
            warning_threshold=data.get("warning_threshold", 0.9),
            last_maintenance=datetime.fromisoformat(data["last_maintenance"]) if data.get("last_maintenance") else None,
            total_runtime_hours=data.get("total_runtime_hours", 0.0)
        )


class MaintenanceTracker:
    """
    Class for tracking maintenance on the robot mower
    
    Tracks runtime and schedules maintenance for various components.
    """
    
    def __init__(self, 
                 config: ConfigManager, 
                 blade_controller: Optional[BladeController] = None,
                 motor_controller: Optional[MotorController] = None,
                 power_manager: Optional[PowerManagement] = None):
        """
        Initialize the maintenance tracker
        
        Args:
            config: Configuration manager
            blade_controller: Blade controller for tracking blade runtime
            motor_controller: Motor controller for tracking drive motor runtime
            power_manager: Power manager for tracking battery cycles
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.blade_controller = blade_controller
        self.motor_controller = motor_controller
        self.power_manager = power_manager
        
        # Configuration
        self.enabled = config.get("maintenance.enabled", True)
        self.update_interval = config.get("maintenance.update_interval", 60.0)  # seconds
        self.notify_overdue = config.get("maintenance.notify_overdue", True)
        self.auto_schedule = config.get("maintenance.auto_schedule", False)
        
        # State
        self.maintenance_items: Dict[str, MaintenanceItem] = {}
        self.running = False
        self.tracking_thread = None
        self.last_update_time = datetime.now()
        self.runtime_since_last_update: Dict[str, float] = {}
        self.last_status_check = datetime.now()
        self.status_check_interval = timedelta(hours=1)  # Check status every hour
        
        # Paths
        data_dir = config.get("system.data_dir", "data")
        self.data_file = os.path.join(data_dir, "maintenance_data.json")
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        # Initialize standard maintenance items
        self._initialize_maintenance_items()
        
        # Load maintenance data
        self._load_maintenance_data()
        
        self.logger.info("Maintenance tracker initialized")
    
    def _initialize_maintenance_items(self) -> None:
        """Initialize standard maintenance items"""
        # Blade replacement
        blade_hours = self.config.get("maintenance.blade_replacement.interval_hours", 50.0)
        self.maintenance_items["blade_replacement"] = MaintenanceItem(
            name="Blade Replacement",
            description="Replace or sharpen the cutting blade",
            interval_hours=blade_hours,
            warning_threshold=0.9
        )
        
        # Filter cleaning
        filter_hours = self.config.get("maintenance.filter_cleaning.interval_hours", 20.0)
        self.maintenance_items["filter_cleaning"] = MaintenanceItem(
            name="Filter Cleaning",
            description="Clean or replace the air filter",
            interval_hours=filter_hours,
            warning_threshold=0.8
        )
        
        # General inspection
        inspection_hours = self.config.get("maintenance.general_inspection.interval_hours", 100.0)
        self.maintenance_items["general_inspection"] = MaintenanceItem(
            name="General Inspection",
            description="Perform a general inspection of the mower",
            interval_hours=inspection_hours,
            warning_threshold=0.9
        )
        
        # Drive motors maintenance
        motor_hours = self.config.get("maintenance.motor_maintenance.interval_hours", 200.0)
        self.maintenance_items["motor_maintenance"] = MaintenanceItem(
            name="Drive Motors Maintenance",
            description="Check and service the drive motors",
            interval_hours=motor_hours,
            warning_threshold=0.9
        )
        
        # Battery maintenance
        battery_cycles = self.config.get("maintenance.battery_maintenance.interval_cycles", 50.0)
        # Convert cycles to approximate hours (assuming 2 hours per cycle)
        battery_hours = battery_cycles * 2.0
        self.maintenance_items["battery_maintenance"] = MaintenanceItem(
            name="Battery Maintenance",
            description="Check battery health and connections",
            interval_hours=battery_hours,
            warning_threshold=0.8
        )
        
        # Software updates
        self.maintenance_items["software_update"] = MaintenanceItem(
            name="Software Update Check",
            description="Check for software updates",
            interval_hours=self.config.get("maintenance.software_update.interval_hours", 168.0),  # 1 week
            warning_threshold=1.0  # No warning, just schedule
        )
        
        # Sensor cleaning
        self.maintenance_items["sensor_cleaning"] = MaintenanceItem(
            name="Sensor Cleaning",
            description="Clean all sensors and cameras",
            interval_hours=self.config.get("maintenance.sensor_cleaning.interval_hours", 50.0),
            warning_threshold=0.9
        )
    
    def _load_maintenance_data(self) -> None:
        """Load maintenance data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                items_data = data.get("maintenance_items", {})
                
                # Update existing items with saved data
                for item_id, item_data in items_data.items():
                    if item_id in self.maintenance_items:
                        # Update existing item
                        saved_item = MaintenanceItem.from_dict(item_data)
                        self.maintenance_items[item_id] = saved_item
                    else:
                        # Add new item from saved data
                        self.maintenance_items[item_id] = MaintenanceItem.from_dict(item_data)
                
                self.logger.info(f"Loaded maintenance data for {len(items_data)} items")
                
                # Initialize runtime tracking
                for item_id in self.maintenance_items:
                    self.runtime_since_last_update[item_id] = 0.0
                
            except Exception as e:
                self.logger.error(f"Error loading maintenance data: {e}")
    
    def _save_maintenance_data(self) -> None:
        """Save maintenance data to file"""
        try:
            # Convert items to dictionaries
            items_data = {item_id: item.to_dict() for item_id, item in self.maintenance_items.items()}
            
            data = {
                "maintenance_items": items_data,
                "last_update": datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.debug("Saved maintenance data")
        except Exception as e:
            self.logger.error(f"Error saving maintenance data: {e}")
    
    def start(self) -> bool:
        """
        Start the maintenance tracker
        
        Returns:
            Success or failure
        """
        if not self.enabled:
            self.logger.info("Maintenance tracker is disabled in configuration")
            return False
        
        if self.running:
            self.logger.warning("Maintenance tracker already running")
            return True
        
        self.running = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        
        self.logger.info("Maintenance tracker started")
        return True
    
    def stop(self) -> None:
        """Stop the maintenance tracker"""
        self.running = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=3.0)
        
        # Update one last time before stopping
        self._update_runtime()
        self._save_maintenance_data()
        
        self.logger.info("Maintenance tracker stopped")
    
    def _tracking_loop(self) -> None:
        """Main tracking loop running in a separate thread"""
        while self.running:
            try:
                # Update runtime tracking
                self._update_runtime()
                
                # Check maintenance status periodically
                if datetime.now() - self.last_status_check >= self.status_check_interval:
                    self._check_maintenance_status()
                    self.last_status_check = datetime.now()
                
                # Sleep for a bit
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in maintenance tracking loop: {e}")
                time.sleep(5.0)  # Sleep longer on error
    
    def _update_runtime(self) -> None:
        """Update runtime for all maintenance items"""
        current_time = datetime.now()
        elapsed_hours = (current_time - self.last_update_time).total_seconds() / 3600.0
        
        # Don't update if no time has passed (or time went backward)
        if elapsed_hours <= 0.0:
            return
        
        # Update blade runtime based on blade controller
        if self.blade_controller and self.blade_controller.is_running():
            blade_speed = self.blade_controller.get_speed()
            # Scale runtime by blade speed (higher speed = faster wear)
            scaled_blade_hours = elapsed_hours * blade_speed * 1.5
            self.runtime_since_last_update["blade_replacement"] += scaled_blade_hours
        
        # Update motor runtime based on motor controller
        if self.motor_controller:
            # In a real implementation, this would use actual motor speed and load
            # For this example, we'll just use a simple approximation
            motor_status = self.motor_controller.get_status()
            if "running" in motor_status and motor_status["running"]:
                self.runtime_since_last_update["motor_maintenance"] += elapsed_hours
            
            # Also update general inspection and filter runtime for active motors
            if "running" in motor_status and motor_status["running"]:
                self.runtime_since_last_update["general_inspection"] += elapsed_hours
                self.runtime_since_last_update["filter_cleaning"] += elapsed_hours
        
        # Update battery runtime based on power manager
        if self.power_manager:
            # Only count runtime against battery when not charging
            if not self.power_manager.is_charging():
                self.runtime_since_last_update["battery_maintenance"] += elapsed_hours
        
        # Update sensor cleaning runtime (always accumulates)
        self.runtime_since_last_update["sensor_cleaning"] += elapsed_hours
        
        # Software update check (always accumulates)
        self.runtime_since_last_update["software_update"] += elapsed_hours
        
        # Apply accumulated runtime every 10 minutes
        if (current_time - self.last_update_time).total_seconds() >= 600:  # 10 minutes
            for item_id, runtime in self.runtime_since_last_update.items():
                if item_id in self.maintenance_items and runtime > 0:
                    self.maintenance_items[item_id].update_runtime(runtime)
                    self.runtime_since_last_update[item_id] = 0.0
            
            # Save after applying runtime
            self._save_maintenance_data()
            
            self.last_update_time = current_time
    
    def _check_maintenance_status(self) -> None:
        """Check maintenance status and log warnings for overdue items"""
        if not self.notify_overdue:
            return
        
        for item_id, item in self.maintenance_items.items():
            status = item.get_status()
            
            if status == MaintenanceStatus.OVERDUE:
                self.logger.warning(f"Maintenance overdue: {item.name} - {item.description}")
            elif status == MaintenanceStatus.DUE_SOON:
                percentage = item.get_percentage_until_maintenance()
                self.logger.info(f"Maintenance due soon: {item.name} ({percentage:.1f}% of interval)")
    
    def perform_maintenance(self, item_id: str) -> bool:
        """
        Record that maintenance has been performed on an item
        
        Args:
            item_id: ID of the maintenance item
            
        Returns:
            Success or failure
        """
        if item_id not in self.maintenance_items:
            self.logger.error(f"Unknown maintenance item: {item_id}")
            return False
        
        try:
            self.maintenance_items[item_id].perform_maintenance()
            self.logger.info(f"Maintenance performed: {self.maintenance_items[item_id].name}")
            
            # Save after recording maintenance
            self._save_maintenance_data()
            return True
        except Exception as e:
            self.logger.error(f"Error recording maintenance: {e}")
            return False
    
    def add_custom_maintenance_item(self, 
                                   item_id: str,
                                   name: str,
                                   description: str,
                                   interval_hours: float,
                                   warning_threshold: float = 0.9) -> bool:
        """
        Add a custom maintenance item
        
        Args:
            item_id: Unique identifier for the item
            name: Display name for the item
            description: Description of maintenance required
            interval_hours: Hours between maintenance
            warning_threshold: Percentage of interval to trigger warning
            
        Returns:
            Success or failure
        """
        if item_id in self.maintenance_items:
            self.logger.warning(f"Maintenance item already exists: {item_id}")
            return False
        
        try:
            self.maintenance_items[item_id] = MaintenanceItem(
                name=name,
                description=description,
                interval_hours=interval_hours,
                warning_threshold=warning_threshold
            )
            
            # Initialize runtime tracking
            self.runtime_since_last_update[item_id] = 0.0
            
            # Save after adding new item
            self._save_maintenance_data()
            
            self.logger.info(f"Added custom maintenance item: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding custom maintenance item: {e}")
            return False
    
    def remove_maintenance_item(self, item_id: str) -> bool:
        """
        Remove a maintenance item
        
        Args:
            item_id: ID of the maintenance item to remove
            
        Returns:
            Success or failure
        """
        if item_id not in self.maintenance_items:
            self.logger.error(f"Unknown maintenance item: {item_id}")
            return False
        
        try:
            # Remove the item
            del self.maintenance_items[item_id]
            
            if item_id in self.runtime_since_last_update:
                del self.runtime_since_last_update[item_id]
            
            # Save after removing item
            self._save_maintenance_data()
            
            self.logger.info(f"Removed maintenance item: {item_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing maintenance item: {e}")
            return False
    
    def get_maintenance_schedule(self) -> List[Dict[str, Any]]:
        """
        Get the current maintenance schedule
        
        Returns:
            List of maintenance items with status information
        """
        schedule = []
        
        for item_id, item in self.maintenance_items.items():
            status = item.get_status()
            
            # Calculate next due date based on runtime
            due_hours = item.get_time_until_maintenance()
            if due_hours is not None:
                # Estimate when maintenance will be due
                # This is a rough approximation and would be more accurate in a real system
                estimated_hours_per_day = 2.0  # Assume 2 hours of use per day
                days_until_due = due_hours / estimated_hours_per_day
                next_due_date = datetime.now() + timedelta(days=days_until_due)
            else:
                next_due_date = datetime.now()  # Already overdue
            
            # Calculate days overdue if applicable
            days_overdue = None
            if status == MaintenanceStatus.OVERDUE:
                hours_overdue = item.get_runtime_since_maintenance() - item.interval_hours
                days_overdue = hours_overdue / 24.0
            
            schedule.append({
                "id": item_id,
                "name": item.name,
                "description": item.description,
                "status": status.value,
                "last_maintenance": item.last_maintenance.isoformat() if item.last_maintenance else None,
                "next_due_date": next_due_date.isoformat(),
                "days_overdue": days_overdue,
                "percentage": item.get_percentage_until_maintenance(),
                "total_runtime_hours": item.total_runtime_hours,
                "interval_hours": item.interval_hours
            })
        
        return schedule
    
    def get_maintenance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of maintenance status
        
        Returns:
            Maintenance summary dictionary
        """
        all_items = self.get_maintenance_schedule()
        
        # Count items by status
        status_counts = {status.value: 0 for status in MaintenanceStatus}
        for item in all_items:
            status_counts[item["status"]] += 1
        
        # Get overdue and due soon items
        overdue_items = [item for item in all_items if item["status"] == MaintenanceStatus.OVERDUE.value]
        due_soon_items = [item for item in all_items if item["status"] == MaintenanceStatus.DUE_SOON.value]
        
        # Get next maintenance item
        next_item = None
        min_days = float('inf')
        for item in all_items:
            if item["status"] == MaintenanceStatus.OVERDUE.value:
                # Overdue items are highest priority
                next_item = item
                break
            elif item["status"] == MaintenanceStatus.DUE_SOON.value:
                # For due soon items, find the one that's due soonest
                due_date = datetime.fromisoformat(item["next_due_date"])
                days = (due_date - datetime.now()).total_seconds() / 86400.0
                if days < min_days:
                    min_days = days
                    next_item = item
        
        return {
            "total_items": len(self.maintenance_items),
            "status_counts": status_counts,
            "overdue_count": len(overdue_items),
            "due_soon_count": len(due_soon_items),
            "overdue_items": overdue_items,
            "due_soon_items": due_soon_items,
            "next_maintenance": next_item,
            "has_critical_maintenance": len(overdue_items) > 0
        }

import time  # Import added for the tracking loop
