"""
Multi-Zone Management

This module provides functionality for managing multiple lawn zones with
different mowing patterns, schedules, and settings.
"""

import os
import json
import logging
import numpy as np
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, time
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import triangulate

from ..core.config import ConfigManager


class MowingPattern(Enum):
    """Enumeration of mowing patterns"""
    PARALLEL = "parallel"
    SPIRAL = "spiral"
    RANDOM = "random"
    ZIGZAG = "zigzag"
    PERIMETER_FIRST = "perimeter_first"
    CUSTOM = "custom"


class EdgeHandlingMode(Enum):
    """Enumeration of edge handling modes"""
    NORMAL = "normal"
    PRECISE = "precise"
    OVERLAP = "overlap"
    SKIP = "skip"


@dataclass
class MowingSchedule:
    """Class for zone mowing schedule"""
    days: List[int]  # 0-6 (Monday-Sunday)
    start_time: time
    duration_minutes: int
    priority: int = 1  # Higher number = higher priority
    enabled: bool = True


@dataclass
class ZoneSettings:
    """Class for zone-specific settings"""
    cutting_height: int  # mm
    mowing_speed: float  # 0.0 to 1.0
    pattern: MowingPattern
    edge_mode: EdgeHandlingMode
    overlap_percent: int = 10  # % overlap between paths
    schedule: Optional[MowingSchedule] = None
    blade_speed: float = 0.8  # 0.0 to 1.0
    completed_last: Optional[datetime] = None
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Zone:
    """Class representing a lawn zone"""
    id: int
    name: str
    boundary: List[Tuple[float, float]]  # List of (x, y) coordinates defining the boundary
    settings: ZoneSettings
    no_mow_areas: List[List[Tuple[float, float]]] = field(default_factory=list)
    obstacles: List[Dict[str, Any]] = field(default_factory=list)
    area: float = 0.0  # m²
    enabled: bool = True
    
    def __post_init__(self):
        """Calculate area after initialization"""
        if len(self.boundary) >= 3:
            polygon = Polygon(self.boundary)
            self.area = polygon.area
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within the zone"""
        if len(self.boundary) < 3:
            return False
        
        polygon = Polygon(self.boundary)
        return polygon.contains(Point(x, y))
    
    def is_in_no_mow_area(self, x: float, y: float) -> bool:
        """Check if a point is within a no-mow area"""
        point = Point(x, y)
        
        for no_mow_boundary in self.no_mow_areas:
            if len(no_mow_boundary) >= 3:
                no_mow_polygon = Polygon(no_mow_boundary)
                if no_mow_polygon.contains(point):
                    return True
        
        return False
    
    def is_near_boundary(self, x: float, y: float, distance: float) -> bool:
        """Check if a point is near the zone boundary"""
        if len(self.boundary) < 3:
            return False
        
        polygon = Polygon(self.boundary)
        point = Point(x, y)
        
        # Check distance to boundary
        return polygon.contains(point) and polygon.boundary.distance(point) <= distance
    
    def get_path_for_pattern(self) -> List[Tuple[float, float]]:
        """Generate a mowing path based on the zone's pattern setting"""
        if len(self.boundary) < 3:
            return []
        
        polygon = Polygon(self.boundary)
        
        # Remove no-mow areas from the polygon
        for no_mow_boundary in self.no_mow_areas:
            if len(no_mow_boundary) >= 3:
                no_mow_polygon = Polygon(no_mow_boundary)
                if polygon.contains(no_mow_polygon):
                    polygon = polygon.difference(no_mow_polygon)
        
        # Generate path based on pattern
        if self.settings.pattern == MowingPattern.PARALLEL:
            return self._generate_parallel_path(polygon)
        elif self.settings.pattern == MowingPattern.SPIRAL:
            return self._generate_spiral_path(polygon)
        elif self.settings.pattern == MowingPattern.ZIGZAG:
            return self._generate_zigzag_path(polygon)
        elif self.settings.pattern == MowingPattern.PERIMETER_FIRST:
            return self._generate_perimeter_first_path(polygon)
        else:  # Default to RANDOM
            return self._generate_random_path(polygon)
    
    def _generate_parallel_path(self, polygon: Polygon) -> List[Tuple[float, float]]:
        """Generate a parallel line pattern path"""
        # This is a simplified implementation
        # A real implementation would be more sophisticated
        
        # Get the bounding box
        minx, miny, maxx, maxy = polygon.bounds
        
        # Calculate the width between lines based on overlap
        mower_width = 0.3  # meters, typical mower width
        path_width = mower_width * (1 - self.settings.overlap_percent / 100)
        
        # Generate parallel lines
        lines = []
        y = miny
        direction = 1  # Alternating direction for back-and-forth pattern
        
        while y <= maxy:
            if direction > 0:
                lines.append([(minx, y), (maxx, y)])
            else:
                lines.append([(maxx, y), (minx, y)])
            
            y += path_width
            direction *= -1
        
        # Clip lines to the polygon and connect them
        path = []
        for line in lines:
            line_obj = LineString(line)
            if polygon.intersects(line_obj):
                intersection = polygon.intersection(line_obj)
                if isinstance(intersection, LineString):
                    coords = list(intersection.coords)
                    if coords:
                        path.extend(coords)
        
        return path
    
    def _generate_spiral_path(self, polygon: Polygon) -> List[Tuple[float, float]]:
        """Generate a spiral pattern path"""
        # This is a simplified implementation
        # A real implementation would compute an actual spiral
        
        # Get centroid and generate a rough spiral
        centroid = polygon.centroid
        cx, cy = centroid.x, centroid.y
        
        # Start from the center and spiral outward
        spiral = []
        a = 0.1  # Controls how tight the spiral is
        b = 0.5  # Controls how fast the spiral expands
        
        for t in range(0, 1000, 5):
            t_rad = t * 0.1
            r = a + b * t_rad
            x = cx + r * np.cos(t_rad)
            y = cy + r * np.sin(t_rad)
            
            # Check if point is in polygon
            point = Point(x, y)
            if polygon.contains(point):
                spiral.append((x, y))
        
        return spiral
    
    def _generate_zigzag_path(self, polygon: Polygon) -> List[Tuple[float, float]]:
        """Generate a zigzag pattern path"""
        # Similar to parallel but with zigzag connections
        # This is a simplified implementation
        
        # Get the bounding box
        minx, miny, maxx, maxy = polygon.bounds
        
        # Calculate the width between lines based on overlap
        mower_width = 0.3  # meters
        path_width = mower_width * (1 - self.settings.overlap_percent / 100)
        
        # Generate path
        path = []
        y = miny
        
        while y <= maxy:
            # Add a zigzag pattern
            path.append((minx, y))
            path.append((maxx, y))
            y += path_width
            
            if y <= maxy:
                path.append((maxx, y))
                path.append((minx, y))
                y += path_width
        
        # Clip path to polygon
        filtered_path = []
        for point in path:
            if polygon.contains(Point(point)):
                filtered_path.append(point)
        
        return filtered_path
    
    def _generate_perimeter_first_path(self, polygon: Polygon) -> List[Tuple[float, float]]:
        """Generate a perimeter-first pattern path"""
        path = []
        
        # Start with the perimeter
        boundary = list(polygon.exterior.coords)
        path.extend(boundary)
        
        # Then fill in with a spiral or parallel pattern for the interior
        interior_polygon = polygon.buffer(-0.5)  # 0.5m inset from perimeter
        if not interior_polygon.is_empty:
            # Fill the interior with a spiral
            path.extend(self._generate_spiral_path(interior_polygon))
        
        return path
    
    def _generate_random_path(self, polygon: Polygon) -> List[Tuple[float, float]]:
        """Generate a random pattern path"""
        # This is a simplified random walk implementation
        # A real implementation would be more sophisticated
        
        # Start at the centroid
        centroid = polygon.centroid
        current = (centroid.x, centroid.y)
        path = [current]
        
        # Random walk with 500 steps
        for _ in range(500):
            # Generate a random step
            angle = np.random.random() * 2 * np.pi
            distance = 0.2  # 0.2m per step
            
            next_x = current[0] + distance * np.cos(angle)
            next_y = current[1] + distance * np.sin(angle)
            next_point = (next_x, next_y)
            
            # Check if still in polygon
            if polygon.contains(Point(next_point)):
                path.append(next_point)
                current = next_point
        
        return path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the zone to a dictionary for storage"""
        return {
            "id": self.id,
            "name": self.name,
            "boundary": self.boundary,
            "settings": {
                "cutting_height": self.settings.cutting_height,
                "mowing_speed": self.settings.mowing_speed,
                "pattern": self.settings.pattern.value,
                "edge_mode": self.settings.edge_mode.value,
                "overlap_percent": self.settings.overlap_percent,
                "blade_speed": self.settings.blade_speed,
                "completed_last": self.settings.completed_last.isoformat() if self.settings.completed_last else None,
                "custom_parameters": self.settings.custom_parameters
            },
            "schedule": {
                "days": self.settings.schedule.days,
                "start_time": self.settings.schedule.start_time.isoformat() if self.settings.schedule else None,
                "duration_minutes": self.settings.schedule.duration_minutes if self.settings.schedule else 60,
                "priority": self.settings.schedule.priority if self.settings.schedule else 1,
                "enabled": self.settings.schedule.enabled if self.settings.schedule else True
            } if self.settings.schedule else None,
            "no_mow_areas": self.no_mow_areas,
            "obstacles": self.obstacles,
            "area": self.area,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Zone':
        """Create a zone from a dictionary"""
        # Parse schedule if it exists
        schedule = None
        if data.get("schedule"):
            schedule_data = data["schedule"]
            schedule = MowingSchedule(
                days=schedule_data.get("days", [0, 2, 4]),  # Default to Mon, Wed, Fri
                start_time=time.fromisoformat(schedule_data.get("start_time", "10:00:00")),
                duration_minutes=schedule_data.get("duration_minutes", 60),
                priority=schedule_data.get("priority", 1),
                enabled=schedule_data.get("enabled", True)
            )
        
        # Parse settings
        settings_data = data.get("settings", {})
        settings = ZoneSettings(
            cutting_height=settings_data.get("cutting_height", 35),
            mowing_speed=settings_data.get("mowing_speed", 0.5),
            pattern=MowingPattern(settings_data.get("pattern", "parallel")),
            edge_mode=EdgeHandlingMode(settings_data.get("edge_mode", "normal")),
            overlap_percent=settings_data.get("overlap_percent", 10),
            blade_speed=settings_data.get("blade_speed", 0.8),
            completed_last=datetime.fromisoformat(settings_data["completed_last"]) if settings_data.get("completed_last") else None,
            custom_parameters=settings_data.get("custom_parameters", {}),
            schedule=schedule
        )
        
        return cls(
            id=data.get("id", 0),
            name=data.get("name", "Default Zone"),
            boundary=data.get("boundary", []),
            settings=settings,
            no_mow_areas=data.get("no_mow_areas", []),
            obstacles=data.get("obstacles", []),
            area=data.get("area", 0.0),
            enabled=data.get("enabled", True)
        )


class ZoneManager:
    """
    Manager for lawn zones
    
    Handles creation, loading, saving and management of lawn zones.
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the zone manager
        
        Args:
            config: ConfigManager instance for configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Configuration
        data_dir = config.get("system.data_dir", "data")
        self.zones_file = os.path.join(data_dir, "zones.json")
        
        # State
        self.zones: Dict[int, Zone] = {}
        self.current_zone_id: Optional[int] = None
        self.next_zone_id = 1
        
        # Create data directory if needed
        os.makedirs(os.path.dirname(self.zones_file), exist_ok=True)
        
        # Load zones
        self.load_zones()
        
        self.logger.info(f"Zone manager initialized with {len(self.zones)} zones")
    
    def load_zones(self) -> bool:
        """
        Load zones from the zones file
        
        Returns:
            Success or failure
        """
        if not os.path.exists(self.zones_file):
            self.logger.info(f"Zones file not found at {self.zones_file}, creating empty zones list")
            return self.save_zones()
        
        try:
            with open(self.zones_file, 'r') as f:
                data = json.load(f)
            
            # Parse zones
            self.zones = {}
            for zone_data in data.get("zones", []):
                zone = Zone.from_dict(zone_data)
                self.zones[zone.id] = zone
                self.next_zone_id = max(self.next_zone_id, zone.id + 1)
            
            # Parse current zone ID
            self.current_zone_id = data.get("current_zone_id")
            
            self.logger.info(f"Loaded {len(self.zones)} zones from {self.zones_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error loading zones: {e}")
            return False
    
    def save_zones(self) -> bool:
        """
        Save zones to the zones file
        
        Returns:
            Success or failure
        """
        try:
            # Convert zones to dictionaries
            zones_data = [zone.to_dict() for zone in self.zones.values()]
            
            # Create data structure
            data = {
                "zones": zones_data,
                "current_zone_id": self.current_zone_id
            }
            
            # Save to file
            with open(self.zones_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.zones)} zones to {self.zones_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving zones: {e}")
            return False
    
    def add_zone(self, name: str, boundary: List[Tuple[float, float]], settings: ZoneSettings) -> int:
        """
        Add a new zone
        
        Args:
            name: Zone name
            boundary: List of (x, y) coordinates defining the boundary
            settings: Zone settings
            
        Returns:
            Zone ID
        """
        zone_id = self.next_zone_id
        self.next_zone_id += 1
        
        # Create the zone
        zone = Zone(
            id=zone_id,
            name=name,
            boundary=boundary,
            settings=settings
        )
        
        # Add to zones
        self.zones[zone_id] = zone
        
        # Save changes
        self.save_zones()
        
        self.logger.info(f"Added zone '{name}' with ID {zone_id}")
        return zone_id
    
    def update_zone(self, zone_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing zone
        
        Args:
            zone_id: Zone ID
            updates: Dictionary of updates to apply
            
        Returns:
            Success or failure
        """
        if zone_id not in self.zones:
            self.logger.error(f"Zone ID {zone_id} not found")
            return False
        
        zone = self.zones[zone_id]
        
        # Update fields
        if "name" in updates:
            zone.name = updates["name"]
        
        if "boundary" in updates:
            zone.boundary = updates["boundary"]
            # Recalculate area
            if len(zone.boundary) >= 3:
                polygon = Polygon(zone.boundary)
                zone.area = polygon.area
        
        if "settings" in updates:
            settings_updates = updates["settings"]
            
            if "cutting_height" in settings_updates:
                zone.settings.cutting_height = settings_updates["cutting_height"]
            
            if "mowing_speed" in settings_updates:
                zone.settings.mowing_speed = settings_updates["mowing_speed"]
            
            if "pattern" in settings_updates:
                zone.settings.pattern = MowingPattern(settings_updates["pattern"])
            
            if "edge_mode" in settings_updates:
                zone.settings.edge_mode = EdgeHandlingMode(settings_updates["edge_mode"])
            
            if "overlap_percent" in settings_updates:
                zone.settings.overlap_percent = settings_updates["overlap_percent"]
            
            if "blade_speed" in settings_updates:
                zone.settings.blade_speed = settings_updates["blade_speed"]
            
            if "custom_parameters" in settings_updates:
                zone.settings.custom_parameters.update(settings_updates["custom_parameters"])
        
        if "schedule" in updates:
            schedule_updates = updates["schedule"]
            
            if zone.settings.schedule is None:
                # Create a default schedule
                zone.settings.schedule = MowingSchedule(
                    days=[0, 2, 4],  # Mon, Wed, Fri
                    start_time=time(10, 0),  # 10:00 AM
                    duration_minutes=60,
                    priority=1,
                    enabled=True
                )
            
            if "days" in schedule_updates:
                zone.settings.schedule.days = schedule_updates["days"]
            
            if "start_time" in schedule_updates:
                if isinstance(schedule_updates["start_time"], str):
                    zone.settings.schedule.start_time = time.fromisoformat(schedule_updates["start_time"])
                else:
                    zone.settings.schedule.start_time = schedule_updates["start_time"]
            
            if "duration_minutes" in schedule_updates:
                zone.settings.schedule.duration_minutes = schedule_updates["duration_minutes"]
            
            if "priority" in schedule_updates:
                zone.settings.schedule.priority = schedule_updates["priority"]
            
            if "enabled" in schedule_updates:
                zone.settings.schedule.enabled = schedule_updates["enabled"]
        
        if "no_mow_areas" in updates:
            zone.no_mow_areas = updates["no_mow_areas"]
        
        if "obstacles" in updates:
            zone.obstacles = updates["obstacles"]
        
        if "enabled" in updates:
            zone.enabled = updates["enabled"]
        
        # Save changes
        self.save_zones()
        
        self.logger.info(f"Updated zone '{zone.name}' (ID {zone_id})")
        return True
    
    def delete_zone(self, zone_id: int) -> bool:
        """
        Delete a zone
        
        Args:
            zone_id: Zone ID
            
        Returns:
            Success or failure
        """
        if zone_id not in self.zones:
            self.logger.error(f"Zone ID {zone_id} not found")
            return False
        
        # Remove from zones
        zone_name = self.zones[zone_id].name
        del self.zones[zone_id]
        
        # Update current zone if needed
        if self.current_zone_id == zone_id:
            self.current_zone_id = None
        
        # Save changes
        self.save_zones()
        
        self.logger.info(f"Deleted zone '{zone_name}' (ID {zone_id})")
        return True
    
    def get_zone(self, zone_id: int) -> Optional[Zone]:
        """
        Get a zone by ID
        
        Args:
            zone_id: Zone ID
            
        Returns:
            Zone or None if not found
        """
        return self.zones.get(zone_id)
    
    def get_all_zones(self) -> List[Zone]:
        """
        Get all zones
        
        Returns:
            List of all zones
        """
        return list(self.zones.values())
    
    def find_zone_at_position(self, x: float, y: float) -> Optional[int]:
        """
        Find the zone that contains a position
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Zone ID or None if not found
        """
        for zone_id, zone in self.zones.items():
            if zone.contains_point(x, y):
                return zone_id
        
        return None
    
    def set_current_zone(self, zone_id: Optional[int]) -> bool:
        """
        Set the current active zone
        
        Args:
            zone_id: Zone ID or None to clear
            
        Returns:
            Success or failure
        """
        if zone_id is not None and zone_id not in self.zones:
            self.logger.error(f"Zone ID {zone_id} not found")
            return False
        
        self.current_zone_id = zone_id
        
        # Save changes
        self.save_zones()
        
        if zone_id is not None:
            self.logger.info(f"Set current zone to '{self.zones[zone_id].name}' (ID {zone_id})")
        else:
            self.logger.info("Cleared current zone")
        
        return True
    
    def get_current_zone(self) -> Optional[Zone]:
        """
        Get the current zone
        
        Returns:
            Current zone or None if not set
        """
        if self.current_zone_id is None:
            return None
        
        return self.zones.get(self.current_zone_id)
    
    def mark_zone_completed(self, zone_id: int) -> bool:
        """
        Mark a zone as completed
        
        Args:
            zone_id: Zone ID
            
        Returns:
            Success or failure
        """
        if zone_id not in self.zones:
            self.logger.error(f"Zone ID {zone_id} not found")
            return False
        
        # Update completion time
        self.zones[zone_id].settings.completed_last = datetime.now()
        
        # Save changes
        self.save_zones()
        
        self.logger.info(f"Marked zone '{self.zones[zone_id].name}' (ID {zone_id}) as completed")
        return True
    
    def get_next_scheduled_zone(self) -> Optional[int]:
        """
        Get the next zone due for mowing based on schedule
        
        Returns:
            Zone ID or None if no zones are scheduled
        """
        now = datetime.now()
        today_weekday = now.weekday()  # 0-6 (Monday-Sunday)
        current_time = now.time()
        
        # Filter zones with enabled schedules
        scheduled_zones = [
            (zone_id, zone) for zone_id, zone in self.zones.items()
            if zone.enabled and zone.settings.schedule and zone.settings.schedule.enabled
        ]
        
        if not scheduled_zones:
            return None
        
        # Find zones scheduled for today
        today_zones = []
        for zone_id, zone in scheduled_zones:
            if today_weekday in zone.settings.schedule.days:
                # Check if it's time to mow
                if zone.settings.schedule.start_time <= current_time:
                    today_zones.append((zone_id, zone))
        
        if today_zones:
            # Sort by priority and last completion time
            today_zones.sort(key=lambda x: (
                -x[1].settings.schedule.priority,  # Higher priority first
                x[1].settings.completed_last or datetime.min  # Oldest completion first
            ))
            return today_zones[0][0]  # Return highest priority zone ID
        
        # If no zones for today, find next scheduled zone
        all_scheduled = []
        for zone_id, zone in scheduled_zones:
            days_until_next = float('inf')
            for day in zone.settings.schedule.days:
                days_away = (day - today_weekday) % 7
                if days_away == 0:
                    # Today but already missed the time
                    days_away = 7
                days_until_next = min(days_until_next, days_away)
            
            all_scheduled.append((zone_id, zone, days_until_next))
        
        # Sort by days until next and priority
        all_scheduled.sort(key=lambda x: (
            x[2],  # Earliest next day first
            -x[1].settings.schedule.priority  # Higher priority first
        ))
        
        return all_scheduled[0][0] if all_scheduled else None
    
    def get_zones_due_for_mowing(self) -> List[int]:
        """
        Get all zones that are due for mowing based on schedule
        
        Returns:
            List of zone IDs
        """
        now = datetime.now()
        today_weekday = now.weekday()  # 0-6 (Monday-Sunday)
        
        due_zones = []
        
        for zone_id, zone in self.zones.items():
            if not zone.enabled:
                continue
            
            # Skip zones without schedules
            if not zone.settings.schedule or not zone.settings.schedule.enabled:
                continue
            
            # Check if scheduled for today
            if today_weekday in zone.settings.schedule.days:
                # Check if it's past the start time
                if zone.settings.schedule.start_time <= now.time():
                    # Check if it was already completed today
                    if zone.settings.completed_last is None:
                        due_zones.append(zone_id)
                    elif zone.settings.completed_last.date() < now.date():
                        due_zones.append(zone_id)
        
        return due_zones
    
    def get_edge_following_zones(self) -> List[int]:
        """
        Get all zones with edge-following mode enabled
        
        Returns:
            List of zone IDs
        """
        return [
            zone_id for zone_id, zone in self.zones.items()
            if zone.enabled and zone.settings.edge_mode in [EdgeHandlingMode.PRECISE, EdgeHandlingMode.OVERLAP]
        ]
    
    def calculate_total_lawn_area(self) -> float:
        """
        Calculate the total area of all enabled zones
        
        Returns:
            Total area in square meters
        """
        return sum(zone.area for zone in self.zones.values() if zone.enabled)
    
    def export_zones_to_file(self, filename: str) -> bool:
        """
        Export zones to a file
        
        Args:
            filename: Target filename
            
        Returns:
            Success or failure
        """
        try:
            # Convert zones to dictionaries
            zones_data = [zone.to_dict() for zone in self.zones.values()]
            
            # Create data structure
            data = {
                "zones": zones_data,
                "current_zone_id": self.current_zone_id,
                "exported_at": datetime.now().isoformat()
            }
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Exported {len(self.zones)} zones to {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting zones: {e}")
            return False
    
    def import_zones_from_file(self, filename: str) -> bool:
        """
        Import zones from a file
        
        Args:
            filename: Source filename
            
        Returns:
            Success or failure
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Parse zones
            zones = {}
            next_id = 1
            
            for zone_data in data.get("zones", []):
                zone = Zone.from_dict(zone_data)
                zones[zone.id] = zone
                next_id = max(next_id, zone.id + 1)
            
            # Update state
            self.zones = zones
            self.next_zone_id = next_id
            self.current_zone_id = data.get("current_zone_id")
            
            # Save changes
            self.save_zones()
            
            self.logger.info(f"Imported {len(self.zones)} zones from {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Error importing zones: {e}")
            return False
