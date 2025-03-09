"""
Theft Protection Module

This module provides anti-theft functionality for the robot mower, including
GPS tracking, motion detection, alarm systems, and remote disabling capabilities.
"""

import os
import time
import json
import logging
import threading
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from ..core.config import ConfigManager
from ..hardware.interfaces import GPSPosition, GPSSensor, IMUSensor, StatusIndicator, PowerManagement


class TheftStatus(Enum):
    """Enumeration of theft detection statuses"""
    NORMAL = "normal"  # No theft detected
    SUSPICIOUS = "suspicious"  # Suspicious activity detected
    ALERT = "alert"  # Theft alert active
    VERIFIED = "verified"  # Theft confirmed
    RECOVERY = "recovery"  # Recovery mode active


class DisableMode(Enum):
    """Enumeration of remote disable modes"""
    NONE = "none"  # No disabling
    SOFT = "soft"  # Soft disable (safe stop)
    HARD = "hard"  # Hard disable (immediate shutdown)
    RECOVERY = "recovery"  # Recovery mode (reduced functionality)


class TheftProtection:
    """
    Class providing anti-theft functionality for the robot mower
    
    Features include:
    - GPS tracking of the mower's position
    - Geofencing with alerts when the mower leaves designated areas
    - Motion detection when the mower should be stationary
    - Alarm systems (sound, lights)
    - Remote disabling capabilities
    - Theft alert notifications
    - Location history tracking
    """
    
    def __init__(self, 
                 config: ConfigManager, 
                 gps_sensor: GPSSensor,
                 imu_sensor: IMUSensor,
                 indicator: StatusIndicator,
                 power_manager: PowerManagement):
        """
        Initialize the theft protection system
        
        Args:
            config: Configuration manager
            gps_sensor: GPS sensor for position tracking
            imu_sensor: IMU sensor for motion detection
            indicator: Status indicator for alarms
            power_manager: Power management for remote disable
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.gps_sensor = gps_sensor
        self.imu_sensor = imu_sensor
        self.indicator = indicator
        self.power_manager = power_manager
        
        # Load configuration
        self.enabled = config.get("security.theft_protection.enabled", True)
        self.geofence_enabled = config.get("security.theft_protection.geofence_enabled", True)
        self.geofence_radius = config.get("security.theft_protection.geofence_radius", 100.0)  # meters
        self.geofence_center = config.get("security.theft_protection.geofence_center", None)  # (lat, lon)
        self.alarm_enabled = config.get("security.theft_protection.alarm_enabled", True)
        self.alarm_delay = config.get("security.theft_protection.alarm_delay", 30)  # seconds
        self.position_update_interval = config.get("security.theft_protection.position_update_interval", 60)  # seconds
        self.suspicious_movement_threshold = config.get("security.theft_protection.suspicious_movement_threshold", 5.0)  # m/s²
        
        # Email notification settings
        self.email_notifications = config.get("security.theft_protection.email_notifications", False)
        self.email_recipient = config.get("security.theft_protection.email_recipient", "")
        self.email_sender = config.get("security.theft_protection.email_sender", "")
        self.email_smtp_server = config.get("security.theft_protection.email_smtp_server", "")
        self.email_smtp_port = config.get("security.theft_protection.email_smtp_port", 587)
        self.email_smtp_username = config.get("security.theft_protection.email_smtp_username", "")
        self.email_smtp_password = config.get("security.theft_protection.email_smtp_password", "")
        
        # SMS notification settings
        self.sms_notifications = config.get("security.theft_protection.sms_notifications", False)
        self.sms_provider_url = config.get("security.theft_protection.sms_provider_url", "")
        self.sms_provider_api_key = config.get("security.theft_protection.sms_provider_api_key", "")
        self.sms_recipient = config.get("security.theft_protection.sms_recipient", "")
        
        # State
        self.current_status = TheftStatus.NORMAL
        self.current_position: Optional[GPSPosition] = None
        self.home_position: Optional[GPSPosition] = None
        self.last_update_time = 0
        self.alarm_active = False
        self.disable_mode = DisableMode.NONE
        self.position_history: List[Dict[str, Any]] = []
        self.last_notification_time = 0
        self.notification_cooldown = 300  # seconds (5 minutes)
        self.running = False
        self.monitoring_thread = None
        
        # Set home position if not already set
        if self.geofence_center is None:
            self._update_home_position()
        else:
            lat, lon = self.geofence_center
            self.home_position = GPSPosition(
                latitude=lat,
                longitude=lon,
                altitude=0.0,
                accuracy=0.0,
                timestamp=time.time()
            )
        
        # Create data directory if needed
        data_dir = config.get("system.data_dir", "data")
        self.history_file = os.path.join(data_dir, "theft_protection_history.json")
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        # Load position history
        self._load_position_history()
        
        self.logger.info("Theft protection system initialized")
    
    def _update_home_position(self) -> None:
        """Update the home position based on current GPS position"""
        position = self.gps_sensor.get_position()
        if position:
            self.home_position = position
            self.geofence_center = (position.latitude, position.longitude)
            self.logger.info(f"Home position set to {position}")
    
    def _load_position_history(self) -> None:
        """Load position history from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                self.position_history = data.get("positions", [])
                self.logger.info(f"Loaded {len(self.position_history)} position history entries")
            except Exception as e:
                self.logger.error(f"Error loading position history: {e}")
                self.position_history = []
    
    def _save_position_history(self) -> None:
        """Save position history to file"""
        try:
            data = {
                "positions": self.position_history,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Saved {len(self.position_history)} position history entries")
        except Exception as e:
            self.logger.error(f"Error saving position history: {e}")
    
    def start(self) -> bool:
        """
        Start the theft protection system
        
        Returns:
            Success or failure
        """
        if not self.enabled:
            self.logger.info("Theft protection is disabled in configuration")
            return False
        
        if self.running:
            self.logger.warning("Theft protection system already running")
            return True
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Theft protection system started")
        return True
    
    def stop(self) -> None:
        """Stop the theft protection system"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=3.0)
        
        if self.alarm_active:
            self._deactivate_alarm()
        
        self.logger.info("Theft protection system stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in a separate thread"""
        while self.running:
            try:
                current_time = time.time()
                
                # Update position at regular intervals
                if current_time - self.last_update_time >= self.position_update_interval:
                    self._update_position()
                    self.last_update_time = current_time
                
                # Check for suspicious movement
                if self._check_suspicious_movement():
                    if self.current_status == TheftStatus.NORMAL:
                        self.logger.warning("Suspicious movement detected")
                        self.current_status = TheftStatus.SUSPICIOUS
                        self._record_event("suspicious_movement")
                
                # Check geofence if enabled
                if self.geofence_enabled and self.geofence_center and self.current_position:
                    if not self._is_within_geofence():
                        if self.current_status == TheftStatus.NORMAL or self.current_status == TheftStatus.SUSPICIOUS:
                            self.logger.warning("Geofence violation detected")
                            self.current_status = TheftStatus.ALERT
                            self._record_event("geofence_violation")
                            self._activate_alarm()
                            self._send_theft_alert()
                
                # Implement a state machine for different theft statuses
                if self.current_status == TheftStatus.SUSPICIOUS:
                    # If suspicious for too long, escalate to alert
                    if self._check_continued_suspicious_activity():
                        self.current_status = TheftStatus.ALERT
                        self.logger.warning("Suspicious activity persisted, escalating to alert")
                        self._record_event("escalated_to_alert")
                        self._activate_alarm()
                        self._send_theft_alert()
                
                elif self.current_status == TheftStatus.ALERT:
                    # In alert status, keep alarm active and continue to track
                    # May be downgraded to NORMAL if activity ceases
                    if not self._check_suspicious_movement() and self._is_within_geofence():
                        # Potential false alarm, but stay vigilant
                        self.logger.info("Alert conditions no longer met, but maintaining alert status")
                
                elif self.current_status == TheftStatus.VERIFIED:
                    # Theft has been verified by user or external system
                    # Continue to provide location updates and keep alarm active
                    self._update_position()  # Update more frequently in verified theft mode
                    
                # Sleep to avoid hammering CPU
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error in theft protection monitoring loop: {e}")
                time.sleep(5.0)  # Sleep longer on error
    
    def _update_position(self) -> None:
        """Update and record the current position"""
        position = self.gps_sensor.get_position()
        if position:
            self.current_position = position
            
            # Add to history
            entry = {
                "latitude": position.latitude,
                "longitude": position.longitude,
                "altitude": position.altitude,
                "accuracy": position.accuracy,
                "timestamp": datetime.fromtimestamp(position.timestamp).isoformat(),
                "status": self.current_status.value
            }
            self.position_history.append(entry)
            
            # Limit history size (keep last 1000 entries)
            if len(self.position_history) > 1000:
                self.position_history = self.position_history[-1000:]
            
            # Save history periodically (every 10 updates)
            if len(self.position_history) % 10 == 0:
                self._save_position_history()
    
    def _check_suspicious_movement(self) -> bool:
        """
        Check for suspicious movement using the IMU
        
        Returns:
            True if suspicious movement is detected
        """
        # Get acceleration data from IMU
        accel = self.imu_sensor.get_acceleration()
        accel_magnitude = (accel[0]**2 + accel[1]**2 + accel[2]**2)**0.5
        
        # Check if acceleration is above threshold
        return accel_magnitude > self.suspicious_movement_threshold
    
    def _check_continued_suspicious_activity(self) -> bool:
        """
        Check if suspicious activity has continued for a significant period
        
        Returns:
            True if activity has continued
        """
        # This is a simplified implementation
        # A real implementation would analyze the pattern of suspicious activity over time
        suspicious_events = [entry for entry in self.position_history[-10:] 
                             if entry.get("status") == TheftStatus.SUSPICIOUS.value]
        return len(suspicious_events) >= 5  # At least 5 out of the last 10 entries are suspicious
    
    def _is_within_geofence(self) -> bool:
        """
        Check if the current position is within the geofence
        
        Returns:
            True if within geofence, False otherwise
        """
        if not self.current_position or not self.home_position:
            return True  # Assume within geofence if position data is unavailable
        
        # Calculate distance from home position
        distance = self._calculate_distance(
            self.current_position.latitude, self.current_position.longitude,
            self.home_position.latitude, self.home_position.longitude
        )
        
        return distance <= self.geofence_radius
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in meters using the Haversine formula
        
        Args:
            lat1: Latitude of point 1 (degrees)
            lon1: Longitude of point 1 (degrees)
            lat2: Latitude of point 2 (degrees)
            lon2: Longitude of point 2 (degrees)
            
        Returns:
            Distance in meters
        """
        import math
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Earth radius in meters
        earth_radius = 6371000.0
        
        # Haversine formula
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = earth_radius * c
        
        return distance
    
    def _activate_alarm(self) -> None:
        """Activate the alarm system"""
        if not self.alarm_enabled or self.alarm_active:
            return
        
        self.logger.info("Activating anti-theft alarm")
        self.alarm_active = True
        
        # Activate visual indicator
        try:
            self.indicator.set_status("alarm", "red")
        except Exception as e:
            self.logger.error(f"Error activating visual alarm: {e}")
        
        # In a real implementation, this would activate a sound alarm as well
        # self.sound_alarm.activate()
        
        self._record_event("alarm_activated")
    
    def _deactivate_alarm(self) -> None:
        """Deactivate the alarm system"""
        if not self.alarm_active:
            return
        
        self.logger.info("Deactivating anti-theft alarm")
        self.alarm_active = False
        
        # Deactivate visual indicator
        try:
            self.indicator.clear()
        except Exception as e:
            self.logger.error(f"Error deactivating visual alarm: {e}")
        
        # In a real implementation, this would deactivate the sound alarm as well
        # self.sound_alarm.deactivate()
        
        self._record_event("alarm_deactivated")
    
    def _send_theft_alert(self) -> None:
        """Send a theft alert notification"""
        current_time = time.time()
        
        # Check if we're in the notification cooldown period
        if current_time - self.last_notification_time < self.notification_cooldown:
            self.logger.debug("Skipping notification due to cooldown period")
            return
        
        self.last_notification_time = current_time
        
        # Prepare notification message
        message = f"ALERT: Potential theft detected for your Robot Mower\n\n"
        message += f"Status: {self.current_status.value}\n"
        
        if self.current_position:
            message += f"Last known position: {self.current_position}\n"
            message += f"Time: {datetime.fromtimestamp(self.current_position.timestamp).isoformat()}\n"
            
            # Add map link
            map_link = f"https://www.google.com/maps?q={self.current_position.latitude},{self.current_position.longitude}"
            message += f"Map: {map_link}\n"
        
        # Send email notification if configured
        if self.email_notifications and self.email_recipient:
            self._send_email_alert(message)
        
        # Send SMS notification if configured
        if self.sms_notifications and self.sms_recipient:
            self._send_sms_alert(message)
        
        self._record_event("theft_alert_sent")
    
    def _send_email_alert(self, message: str) -> bool:
        """
        Send an email alert
        
        Args:
            message: Alert message text
            
        Returns:
            Success or failure
        """
        if not self.email_smtp_server or not self.email_sender or not self.email_recipient:
            self.logger.warning("Email alert settings incomplete, cannot send email")
            return False
        
        try:
            # Set up email message
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = self.email_recipient
            msg['Subject'] = f"Robot Mower Theft Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server and send
            server = smtplib.SMTP(self.email_smtp_server, self.email_smtp_port)
            server.starttls()
            
            # Login if credentials provided
            if self.email_smtp_username and self.email_smtp_password:
                server.login(self.email_smtp_username, self.email_smtp_password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Theft alert email sent to {self.email_recipient}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending theft alert email: {e}")
            return False
    
    def _send_sms_alert(self, message: str) -> bool:
        """
        Send an SMS alert
        
        Args:
            message: Alert message text
            
        Returns:
            Success or failure
        """
        if not self.sms_provider_url or not self.sms_recipient:
            self.logger.warning("SMS alert settings incomplete, cannot send SMS")
            return False
        
        try:
            # This is a simplified implementation
            # Real implementation would use a specific SMS provider's API
            
            # Prepare request data
            data = {
                "to": self.sms_recipient,
                "message": message[:160],  # Limit to 160 characters
                "api_key": self.sms_provider_api_key
            }
            
            # Send request to SMS provider
            response = requests.post(self.sms_provider_url, json=data)
            
            if response.status_code == 200:
                self.logger.info(f"Theft alert SMS sent to {self.sms_recipient}")
                return True
            else:
                self.logger.error(f"SMS provider returned error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending theft alert SMS: {e}")
            return False
    
    def _record_event(self, event_type: str) -> None:
        """
        Record a theft protection event
        
        Args:
            event_type: Type of event
        """
        if not self.current_position:
            position = self.gps_sensor.get_position()
        else:
            position = self.current_position
        
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "status": self.current_status.value,
            "position": {
                "latitude": position.latitude if position else None,
                "longitude": position.longitude if position else None,
                "accuracy": position.accuracy if position else None
            } if position else None
        }
        
        # In a real implementation, events would be stored in a database
        # For this example, we'll just log them
        self.logger.info(f"Theft protection event recorded: {event_type}")
    
    def verify_theft(self) -> None:
        """Manually verify theft (typically called by user or monitoring center)"""
        self.logger.warning("Theft manually verified")
        self.current_status = TheftStatus.VERIFIED
        self._record_event("theft_verified")
        
        if not self.alarm_active:
            self._activate_alarm()
        
        self._send_theft_alert()
    
    def cancel_alert(self) -> None:
        """Cancel an active alert (typically called by authenticated user)"""
        if self.current_status in [TheftStatus.ALERT, TheftStatus.VERIFIED]:
            self.logger.info("Theft alert canceled by user")
            self.current_status = TheftStatus.NORMAL
            self._record_event("alert_canceled")
            
            if self.alarm_active:
                self._deactivate_alarm()
    
    def set_disable_mode(self, mode: DisableMode) -> bool:
        """
        Set the remote disable mode
        
        Args:
            mode: DisableMode to set
            
        Returns:
            Success or failure
        """
        if mode == self.disable_mode:
            return True
        
        self.logger.info(f"Setting disable mode to {mode.value}")
        
        # Apply the requested disable mode
        try:
            if mode == DisableMode.SOFT:
                # Soft disable: safe stop
                # In a real implementation, this would signal the main control system to stop
                self._record_event("soft_disable_activated")
            
            elif mode == DisableMode.HARD:
                # Hard disable: immediate shutdown
                # In a real implementation, this would directly shut down the system
                self._record_event("hard_disable_activated")
                self.power_manager.shutdown()
            
            elif mode == DisableMode.RECOVERY:
                # Recovery mode: reduced functionality
                # In a real implementation, this would limit functionality
                # but allow navigation and location tracking
                self._record_event("recovery_mode_activated")
            
            elif mode == DisableMode.NONE:
                # Remove any disabling
                self._record_event("disable_mode_cleared")
            
            self.disable_mode = mode
            return True
        except Exception as e:
            self.logger.error(f"Error setting disable mode: {e}")
            return False
    
    def get_position_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the position history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of position history entries
        """
        # Return the most recent entries, up to the limit
        return self.position_history[-limit:] if limit > 0 else []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the theft protection system
        
        Returns:
            Status dictionary
        """
        position = self.current_position
        
        return {
            "enabled": self.enabled,
            "status": self.current_status.value,
            "alarm_active": self.alarm_active,
            "disable_mode": self.disable_mode.value,
            "position": {
                "latitude": position.latitude,
                "longitude": position.longitude,
                "accuracy": position.accuracy,
                "timestamp": datetime.fromtimestamp(position.timestamp).isoformat()
            } if position else None,
            "geofence": {
                "enabled": self.geofence_enabled,
                "radius": self.geofence_radius,
                "center": self.geofence_center
            } if self.geofence_enabled else None,
            "within_geofence": self._is_within_geofence() if self.geofence_enabled else None
        }
