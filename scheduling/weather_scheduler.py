"""
Weather-Based Scheduling Module

This module provides functionality for automatically rescheduling mowing operations
based on weather forecasts, avoiding mowing during rain, extreme heat, or other
adverse weather conditions.
"""

import os
import json
import logging
import threading
import time
import random
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import requests
import math

from ..core.config import ConfigManager


class WeatherCondition(Enum):
    """Enumeration of weather conditions"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    STORM = "storm"
    FOG = "fog"
    WINDY = "windy"
    EXTREME_HEAT = "extreme_heat"
    FROST = "frost"
    UNKNOWN = "unknown"


class WeatherImpact(Enum):
    """Enumeration of weather impact on mowing"""
    NONE = "none"  # Safe to mow
    LOW = "low"  # Suboptimal but acceptable
    MEDIUM = "medium"  # Not recommended
    HIGH = "high"  # Unsafe, do not mow
    UNKNOWN = "unknown"


class WeatherForecast:
    """Class representing a weather forecast for a specific time"""
    
    def __init__(self, 
                 timestamp: datetime,
                 temperature: float,
                 feels_like: float,
                 humidity: float,
                 precipitation: float,
                 precipitation_probability: float,
                 wind_speed: float,
                 wind_direction: float,
                 pressure: float,
                 cloud_cover: float,
                 visibility: float,
                 condition: WeatherCondition,
                 description: str = ""):
        """
        Initialize a weather forecast
        
        Args:
            timestamp: Forecast time
            temperature: Temperature in degrees Celsius
            feels_like: Feels-like temperature in degrees Celsius
            humidity: Relative humidity (0-100%)
            precipitation: Precipitation amount in mm
            precipitation_probability: Probability of precipitation (0-100%)
            wind_speed: Wind speed in m/s
            wind_direction: Wind direction in degrees
            pressure: Atmospheric pressure in hPa
            cloud_cover: Cloud cover percentage (0-100%)
            visibility: Visibility in meters
            condition: Weather condition enum
            description: Text description of the weather
        """
        self.timestamp = timestamp
        self.temperature = temperature
        self.feels_like = feels_like
        self.humidity = humidity
        self.precipitation = precipitation
        self.precipitation_probability = precipitation_probability
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
        self.pressure = pressure
        self.cloud_cover = cloud_cover
        self.visibility = visibility
        self.condition = condition
        self.description = description
    
    def get_impact(self, config: Dict[str, Any]) -> WeatherImpact:
        """
        Determine the impact of this weather on mowing operations
        
        Args:
            config: Weather impact configuration
            
        Returns:
            WeatherImpact enum value
        """
        # Check for precipitation (rain/snow)
        if self.precipitation >= config.get("high_precipitation_threshold", 5.0):
            return WeatherImpact.HIGH
        elif self.precipitation >= config.get("medium_precipitation_threshold", 1.0):
            return WeatherImpact.MEDIUM
        elif self.precipitation >= config.get("low_precipitation_threshold", 0.2):
            return WeatherImpact.LOW
        
        # Check for high precipitation probability
        if self.precipitation_probability >= config.get("high_precipitation_probability", 80.0):
            return WeatherImpact.HIGH
        elif self.precipitation_probability >= config.get("medium_precipitation_probability", 50.0):
            return WeatherImpact.MEDIUM
        elif self.precipitation_probability >= config.get("low_precipitation_probability", 30.0):
            return WeatherImpact.LOW
        
        # Check for extreme temperatures
        if self.temperature >= config.get("high_temperature_threshold", 35.0):
            return WeatherImpact.HIGH
        elif self.temperature <= config.get("low_temperature_threshold", 0.0):
            return WeatherImpact.HIGH
        
        # Check for high winds
        if self.wind_speed >= config.get("high_wind_threshold", 10.0):
            return WeatherImpact.HIGH
        elif self.wind_speed >= config.get("medium_wind_threshold", 7.0):
            return WeatherImpact.MEDIUM
        
        # Check specific weather conditions
        if self.condition in [WeatherCondition.RAIN, WeatherCondition.HEAVY_RAIN, 
                             WeatherCondition.SNOW, WeatherCondition.STORM]:
            return WeatherImpact.HIGH
        elif self.condition in [WeatherCondition.FOG] and self.visibility < config.get("low_visibility_threshold", 1000.0):
            return WeatherImpact.MEDIUM
        
        # Default: no impact
        return WeatherImpact.NONE
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage
        
        Returns:
            Dictionary representation
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "temperature": self.temperature,
            "feels_like": self.feels_like,
            "humidity": self.humidity,
            "precipitation": self.precipitation,
            "precipitation_probability": self.precipitation_probability,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "pressure": self.pressure,
            "cloud_cover": self.cloud_cover,
            "visibility": self.visibility,
            "condition": self.condition.value,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeatherForecast':
        """
        Create from dictionary
        
        Args:
            data: Dictionary representation
            
        Returns:
            WeatherForecast instance
        """
        condition_str = data.get("condition", WeatherCondition.UNKNOWN.value)
        try:
            condition = WeatherCondition(condition_str)
        except ValueError:
            condition = WeatherCondition.UNKNOWN
        
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            temperature=data["temperature"],
            feels_like=data["feels_like"],
            humidity=data["humidity"],
            precipitation=data["precipitation"],
            precipitation_probability=data["precipitation_probability"],
            wind_speed=data["wind_speed"],
            wind_direction=data["wind_direction"],
            pressure=data["pressure"],
            cloud_cover=data["cloud_cover"],
            visibility=data["visibility"],
            condition=condition,
            description=data.get("description", "")
        )


class ScheduleAdjustment:
    """Class representing a schedule adjustment due to weather"""
    
    def __init__(self, 
                 original_time: datetime,
                 adjusted_time: Optional[datetime],
                 reason: str,
                 impact: WeatherImpact,
                 forecast: WeatherForecast,
                 id: Optional[str] = None):
        """
        Initialize a schedule adjustment
        
        Args:
            original_time: Original scheduled time
            adjusted_time: New scheduled time (None if canceled)
            reason: Reason for adjustment
            impact: Weather impact level
            forecast: Weather forecast that caused adjustment
            id: Unique identifier (generated if None)
        """
        self.id = id or f"{original_time.strftime('%Y%m%d_%H%M')}_{int(time.time())}"
        self.original_time = original_time
        self.adjusted_time = adjusted_time
        self.reason = reason
        self.impact = impact
        self.forecast = forecast
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "original_time": self.original_time.isoformat(),
            "adjusted_time": self.adjusted_time.isoformat() if self.adjusted_time else None,
            "reason": self.reason,
            "impact": self.impact.value,
            "forecast": self.forecast.to_dict(),
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleAdjustment':
        """
        Create from dictionary
        
        Args:
            data: Dictionary representation
            
        Returns:
            ScheduleAdjustment instance
        """
        return cls(
            id=data["id"],
            original_time=datetime.fromisoformat(data["original_time"]),
            adjusted_time=datetime.fromisoformat(data["adjusted_time"]) if data.get("adjusted_time") else None,
            reason=data["reason"],
            impact=WeatherImpact(data["impact"]),
            forecast=WeatherForecast.from_dict(data["forecast"])
        )


class WeatherBasedScheduler:
    """
    Class for rescheduling mowing operations based on weather forecasts
    
    This class fetches weather forecasts and adjusts mowing schedules to avoid
    adverse weather conditions.
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the weather-based scheduler
        
        Args:
            config: Configuration manager
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Weather API configuration
        self.weather_api_enabled = config.get("weather.api.enabled", False)
        self.weather_api_key = config.get("weather.api.key", "")
        self.weather_api_url = config.get("weather.api.url", "")
        self.weather_api_provider = config.get("weather.api.provider", "openweathermap")
        
        # Location settings
        self.latitude = config.get("location.latitude", 0.0)
        self.longitude = config.get("location.longitude", 0.0)
        
        # Scheduling settings
        self.enabled = config.get("scheduling.weather_based.enabled", True)
        self.forecast_days = config.get("scheduling.weather_based.forecast_days", 5)
        self.update_interval = config.get("scheduling.weather_based.update_interval", 3600)  # 1 hour
        self.min_reschedule_notice = config.get("scheduling.weather_based.min_reschedule_notice", 3)  # hours
        self.max_reschedule_delay = config.get("scheduling.weather_based.max_reschedule_delay", 48)  # hours
        self.rain_delay = config.get("scheduling.weather_based.rain_delay", 3)  # hours after rain
        
        # Impact thresholds (these will be passed to WeatherForecast.get_impact)
        self.impact_thresholds = {
            "high_precipitation_threshold": config.get("weather.thresholds.high_precipitation", 5.0),
            "medium_precipitation_threshold": config.get("weather.thresholds.medium_precipitation", 1.0),
            "low_precipitation_threshold": config.get("weather.thresholds.low_precipitation", 0.2),
            "high_precipitation_probability": config.get("weather.thresholds.high_precipitation_probability", 80.0),
            "medium_precipitation_probability": config.get("weather.thresholds.medium_precipitation_probability", 50.0),
            "low_precipitation_probability": config.get("weather.thresholds.low_precipitation_probability", 30.0),
            "high_temperature_threshold": config.get("weather.thresholds.high_temperature", 35.0),
            "low_temperature_threshold": config.get("weather.thresholds.low_temperature", 0.0),
            "high_wind_threshold": config.get("weather.thresholds.high_wind", 10.0),
            "medium_wind_threshold": config.get("weather.thresholds.medium_wind", 7.0),
            "low_visibility_threshold": config.get("weather.thresholds.low_visibility", 1000.0)
        }
        
        # State
        self.forecasts: List[WeatherForecast] = []
        self.schedule_adjustments: List[ScheduleAdjustment] = []
        self.running = False
        self.update_thread = None
        self.last_update_time = 0
        
        # Setup data paths
        data_dir = config.get("system.data_dir", "data")
        self.forecast_file = os.path.join(data_dir, "weather_forecast.json")
        self.adjustments_file = os.path.join(data_dir, "schedule_adjustments.json")
        os.makedirs(os.path.dirname(self.forecast_file), exist_ok=True)
        
        # Load saved data
        self._load_forecasts()
        self._load_adjustments()
        
        self.logger.info("Weather-based scheduler initialized")
    
    def _load_forecasts(self) -> None:
        """Load forecasts from file"""
        if os.path.exists(self.forecast_file):
            try:
                with open(self.forecast_file, 'r') as f:
                    data = json.load(f)
                
                # Parse forecasts
                self.forecasts = [WeatherForecast.from_dict(item) for item in data.get("forecasts", [])]
                self.last_update_time = data.get("last_update", 0)
                
                self.logger.info(f"Loaded {len(self.forecasts)} weather forecasts")
            except Exception as e:
                self.logger.error(f"Error loading forecasts: {e}")
                self.forecasts = []
    
    def _save_forecasts(self) -> None:
        """Save forecasts to file"""
        try:
            data = {
                "forecasts": [forecast.to_dict() for forecast in self.forecasts],
                "last_update": self.last_update_time
            }
            
            with open(self.forecast_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Saved {len(self.forecasts)} weather forecasts")
        except Exception as e:
            self.logger.error(f"Error saving forecasts: {e}")
    
    def _load_adjustments(self) -> None:
        """Load schedule adjustments from file"""
        if os.path.exists(self.adjustments_file):
            try:
                with open(self.adjustments_file, 'r') as f:
                    data = json.load(f)
                
                # Parse adjustments
                self.schedule_adjustments = [ScheduleAdjustment.from_dict(item) for item in data.get("adjustments", [])]
                
                self.logger.info(f"Loaded {len(self.schedule_adjustments)} schedule adjustments")
            except Exception as e:
                self.logger.error(f"Error loading schedule adjustments: {e}")
                self.schedule_adjustments = []
    
    def _save_adjustments(self) -> None:
        """Save schedule adjustments to file"""
        try:
            data = {
                "adjustments": [adjustment.to_dict() for adjustment in self.schedule_adjustments],
                "last_update": datetime.now().isoformat()
            }
            
            with open(self.adjustments_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Saved {len(self.schedule_adjustments)} schedule adjustments")
        except Exception as e:
            self.logger.error(f"Error saving schedule adjustments: {e}")
    
    def start(self) -> bool:
        """
        Start the weather-based scheduler
        
        Returns:
            Success or failure
        """
        if not self.enabled:
            self.logger.info("Weather-based scheduler is disabled in configuration")
            return False
        
        if self.running:
            self.logger.warning("Weather-based scheduler already running")
            return True
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        self.logger.info("Weather-based scheduler started")
        return True
    
    def stop(self) -> None:
        """Stop the weather-based scheduler"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=3.0)
        
        self.logger.info("Weather-based scheduler stopped")
    
    def _update_loop(self) -> None:
        """Main update loop running in a separate thread"""
        while self.running:
            try:
                current_time = time.time()
                
                # Update forecasts at regular intervals
                if current_time - self.last_update_time >= self.update_interval:
                    self.update_forecast()
                
                # Sleep for a bit
                time.sleep(60.0)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in weather scheduler update loop: {e}")
                time.sleep(300.0)  # Sleep longer on error
    
    def update_forecast(self) -> bool:
        """
        Update the weather forecast
        
        Returns:
            Success or failure
        """
        if not self.weather_api_enabled or not self.weather_api_key:
            # Generate mock forecast data if API not available
            self._generate_mock_forecast()
            self.last_update_time = time.time()
            self._save_forecasts()
            return True
        
        try:
            if self.weather_api_provider == "openweathermap":
                success = self._fetch_openweathermap_forecast()
            else:
                self.logger.warning(f"Unsupported weather API provider: {self.weather_api_provider}")
                success = False
            
            if success:
                self.last_update_time = time.time()
                self._save_forecasts()
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating weather forecast: {e}")
            return False
    
    def _fetch_openweathermap_forecast(self) -> bool:
        """
        Fetch forecast from OpenWeatherMap API
        
        Returns:
            Success or failure
        """
        try:
            # OpenWeatherMap 5-day forecast endpoint
            url = f"https://api.openweathermap.org/data/2.5/forecast"
            
            params = {
                "lat": self.latitude,
                "lon": self.longitude,
                "appid": self.weather_api_key,
                "units": "metric",  # Use metric units
                "cnt": min(40, self.forecast_days * 8)  # 8 forecasts per day (3-hour intervals)
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                self.logger.error(f"Error fetching weather forecast: {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            
            # Parse forecast data
            new_forecasts = []
            
            for item in data.get("list", []):
                timestamp_str = item.get("dt_txt", "")
                if not timestamp_str:
                    continue
                
                try:
                    # Parse weather data
                    timestamp = datetime.fromisoformat(timestamp_str.replace(" ", "T"))
                    
                    main_data = item.get("main", {})
                    wind_data = item.get("wind", {})
                    clouds_data = item.get("clouds", {})
                    weather_data = item.get("weather", [{}])[0]
                    rain_data = item.get("rain", {})
                    
                    # Map OpenWeatherMap condition codes to our conditions
                    condition_code = weather_data.get("id", 800)
                    condition = self._map_openweathermap_condition(condition_code)
                    
                    # Extract 3-hour precipitation amount (convert to mm)
                    precipitation = rain_data.get("3h", 0.0)
                    
                    # Create forecast object
                    forecast = WeatherForecast(
                        timestamp=timestamp,
                        temperature=main_data.get("temp", 0.0),
                        feels_like=main_data.get("feels_like", 0.0),
                        humidity=main_data.get("humidity", 0.0),
                        precipitation=precipitation,
                        precipitation_probability=item.get("pop", 0.0) * 100.0,  # Convert 0-1 to 0-100%
                        wind_speed=wind_data.get("speed", 0.0),
                        wind_direction=wind_data.get("deg", 0.0),
                        pressure=main_data.get("pressure", 0.0),
                        cloud_cover=clouds_data.get("all", 0.0),
                        visibility=item.get("visibility", 10000.0),
                        condition=condition,
                        description=weather_data.get("description", "")
                    )
                    
                    new_forecasts.append(forecast)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing forecast item: {e}")
            
            # Replace existing forecasts
            if new_forecasts:
                self.forecasts = new_forecasts
                self.logger.info(f"Updated weather forecast with {len(new_forecasts)} time points")
                return True
            else:
                self.logger.warning("No forecast data received")
                return False
                
        except Exception as e:
            self.logger.error(f"Error fetching OpenWeatherMap forecast: {e}")
            return False
    
    def _map_openweathermap_condition(self, condition_code: int) -> WeatherCondition:
        """
        Map OpenWeatherMap condition code to WeatherCondition enum
        
        Args:
            condition_code: OpenWeatherMap condition code
            
        Returns:
            WeatherCondition enum value
        """
        # Thunderstorm
        if 200 <= condition_code < 300:
            return WeatherCondition.STORM
        
        # Drizzle
        elif 300 <= condition_code < 400:
            return WeatherCondition.RAIN
        
        # Rain
        elif 500 <= condition_code < 600:
            if condition_code in [502, 503, 504, 522]:
                return WeatherCondition.HEAVY_RAIN
            else:
                return WeatherCondition.RAIN
        
        # Snow
        elif 600 <= condition_code < 700:
            return WeatherCondition.SNOW
        
        # Atmosphere (fog, mist, etc.)
        elif 700 <= condition_code < 800:
            return WeatherCondition.FOG
        
        # Clear
        elif condition_code == 800:
            return WeatherCondition.CLEAR
        
        # Clouds
        elif 801 <= condition_code < 900:
            return WeatherCondition.CLOUDY
        
        # Extreme conditions
        elif condition_code in [781, 900, 901, 902, 905, 906, 961, 962]:
            return WeatherCondition.STORM
        
        # Windy
        elif condition_code in [771, 957, 958, 959, 960]:
            return WeatherCondition.WINDY
        
        # Unknown
        else:
            return WeatherCondition.UNKNOWN
    
    def _generate_mock_forecast(self) -> None:
        """Generate mock forecast data for testing"""
        self.logger.info("Generating mock weather forecast")
        
        # Start with current time (rounded down to hour)
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        new_forecasts = []
        
        # Generate forecasts at 3-hour intervals
        for i in range(self.forecast_days * 8):  # 8 forecasts per day (3-hour intervals)
            forecast_time = now + timedelta(hours=i * 3)
            
            # Generate realistic conditions based on time of day
            hour = forecast_time.hour
            day_of_year = forecast_time.timetuple().tm_yday
            
            # Temperature varies by time of day and seasonally
            base_temp = 20.0  # Base temperature (°C)
            seasonal_variation = 10.0 * math.sin(2 * math.pi * (day_of_year - 172) / 365.0)  # +/-10°C annual variation
            diurnal_variation = 5.0 * math.sin(2 * math.pi * (hour - 14) / 24.0)  # +/-5°C daily variation
            
            temperature = base_temp + seasonal_variation + diurnal_variation
            
            # Add some random variation
            temperature += (random.random() * 4.0 - 2.0)  # +/-2°C random noise
            
            # Humidity inversely varies with temperature
            humidity = max(30.0, min(95.0, 80.0 - (temperature - 20.0) * 2.0 + (random.random() * 10.0 - 5.0)))
            
            # Precipitation - occasionally generate rain
            is_raining = random.random() < 0.2  # 20% chance of rain
            precipitation = 0.0
            precipitation_probability = 0.0
            
            if is_raining:
                precipitation = random.random() * 8.0  # 0-8 mm
                precipitation_probability = 70.0 + random.random() * 30.0  # 70-100%
            else:
                # Small chance of rain
                precipitation_probability = random.random() * 25.0  # 0-25%
            
            # Wind varies randomly
            wind_speed = random.random() * 8.0  # 0-8 m/s
            wind_direction = random.random() * 360.0  # 0-360 degrees
            
            # Condition is based on precipitation and other factors
            condition = WeatherCondition.CLEAR
            description = "Clear sky"
            
            if precipitation > 5.0:
                condition = WeatherCondition.HEAVY_RAIN
                description = "Heavy rain"
            elif precipitation > 0.0:
                condition = WeatherCondition.RAIN
                description = "Light rain"
            elif precipitation_probability > 50.0:
                condition = WeatherCondition.CLOUDY
                description = "Cloudy with chance of rain"
            elif random.random() < 0.3:
                condition = WeatherCondition.CLOUDY
                description = "Partly cloudy"
            
            # Create forecast object
            forecast = WeatherForecast(
                timestamp=forecast_time,
                temperature=temperature,
                feels_like=temperature - 2.0 if temperature < 10.0 else temperature + 2.0 if temperature > 28.0 else temperature,
                humidity=humidity,
                precipitation=precipitation,
                precipitation_probability=precipitation_probability,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                pressure=1013.0 + (random.random() * 20.0 - 10.0),  # 1003-1023 hPa
                cloud_cover=80.0 if condition == WeatherCondition.CLOUDY else 30.0 if condition == WeatherCondition.CLEAR else 100.0,
                visibility=10000.0 if condition == WeatherCondition.CLEAR else 5000.0,  # meters
                condition=condition,
                description=description
            )
            
            new_forecasts.append(forecast)
        
        # Replace existing forecasts
        self.forecasts = new_forecasts
        self.logger.info(f"Generated mock forecast with {len(new_forecasts)} time points")
    
    def check_schedule(self, scheduled_time: datetime) -> Tuple[bool, Optional[datetime], str]:
        """
        Check if a scheduled mowing operation should be adjusted
        
        Args:
            scheduled_time: Original scheduled time
            
        Returns:
            Tuple of (should_reschedule, new_time, reason)
        """
        # Don't reschedule past times
        if scheduled_time < datetime.now():
            return False, None, "Scheduled time is in the past"
        
        # Find forecast for this time
        forecast = self._get_forecast_for_time(scheduled_time)
        
        if not forecast:
            self.logger.warning(f"No forecast available for {scheduled_time}")
            return False, None, "No forecast available"
        
        # Check impact
        impact = forecast.get_impact(self.impact_thresholds)
        
        if impact == WeatherImpact.HIGH:
            # High impact - reschedule
            reschedule_reason = f"Adverse weather: {forecast.condition.value} - {forecast.description}"
            new_time = self._find_next_suitable_time(scheduled_time)
            
            # Record adjustment
            if new_time:
                adjustment = ScheduleAdjustment(
                    original_time=scheduled_time,
                    adjusted_time=new_time,
                    reason=reschedule_reason,
                    impact=impact,
                    forecast=forecast
                )
                self.schedule_adjustments.append(adjustment)
                self._save_adjustments()
                
                self.logger.info(f"Rescheduled {scheduled_time} to {new_time} due to {reschedule_reason}")
                return True, new_time, reschedule_reason
            else:
                # Can't find suitable time
                adjustment = ScheduleAdjustment(
                    original_time=scheduled_time,
                    adjusted_time=None,
                    reason=f"Canceled: {reschedule_reason} - No suitable alternative time found",
                    impact=impact,
                    forecast=forecast
                )
                self.schedule_adjustments.append(adjustment)
                self._save_adjustments()
                
                self.logger.warning(f"Canceled {scheduled_time} due to {reschedule_reason} - No suitable time found")
                return True, None, f"Canceled: {reschedule_reason} - No suitable alternative time found"
        
        elif impact == WeatherImpact.MEDIUM:
            # Medium impact - reschedule depending on settings
            if self.config.get("scheduling.weather_based.reschedule_medium_impact", True):
                reschedule_reason = f"Suboptimal weather: {forecast.condition.value} - {forecast.description}"
                new_time = self._find_next_suitable_time(scheduled_time)
                
                # Record adjustment
                if new_time:
                    adjustment = ScheduleAdjustment(
                        original_time=scheduled_time,
                        adjusted_time=new_time,
                        reason=reschedule_reason,
                        impact=impact,
                        forecast=forecast
                    )
                    self.schedule_adjustments.append(adjustment)
                    self._save_adjustments()
                    
                    self.logger.info(f"Rescheduled {scheduled_time} to {new_time} due to {reschedule_reason}")
                    return True, new_time, reschedule_reason
                else:
                    # Can't find suitable time
                    self.logger.info(f"Could not find suitable alternative time for {scheduled_time}")
                    return False, None, f"Unsuitable weather: {reschedule_reason} - No suitable alternative time found"
            else:
                # Medium impact but not configured to reschedule
                self.logger.info(f"Medium impact weather at {scheduled_time} but not configured to reschedule")
                return False, None, "Medium impact weather detected but not configured to reschedule"
        
        elif impact == WeatherImpact.LOW:
            # Low impact - typically don't reschedule
            if self.config.get("scheduling.weather_based.reschedule_low_impact", False):
                reschedule_reason = f"Minor weather concerns: {forecast.condition.value} - {forecast.description}"
                new_time = self._find_next_suitable_time(scheduled_time)
                
                # Record adjustment
                if new_time:
                    adjustment = ScheduleAdjustment(
                        original_time=scheduled_time,
                        adjusted_time=new_time,
                        reason=reschedule_reason,
                        impact=impact,
                        forecast=forecast
                    )
                    self.schedule_adjustments.append(adjustment)
                    self._save_adjustments()
                    
                    self.logger.info(f"Rescheduled {scheduled_time} to {new_time} due to {reschedule_reason}")
                    return True, new_time, reschedule_reason
                else:
                    # Can't find suitable time, but it's only low impact so proceed anyway
                    self.logger.info(f"Low impact weather at {scheduled_time} but no better time found")
                    return False, None, "Low impact weather detected but proceeding as scheduled"
            else:
                # Low impact and not configured to reschedule
                return False, None, "Low impact weather detected but proceeding as scheduled"
        
        # No impact, proceed as scheduled
        return False, None, "Weather looks good, proceeding as scheduled"
    
    def _get_forecast_for_time(self, target_time: datetime) -> Optional[WeatherForecast]:
        """
        Get the forecast closest to the target time
        
        Args:
            target_time: Target time to find forecast for
            
        Returns:
            WeatherForecast or None if no forecast available
        """
        if not self.forecasts:
            return None
        
        # Find closest forecast
        closest_forecast = None
        min_diff = timedelta.max
        
        for forecast in self.forecasts:
            diff = abs(forecast.timestamp - target_time)
            if diff < min_diff:
                min_diff = diff
                closest_forecast = forecast
        
        # Only use forecasts within 3 hours of target time
        if min_diff <= timedelta(hours=3):
            return closest_forecast
        else:
            return None
    
    def _find_next_suitable_time(self, original_time: datetime) -> Optional[datetime]:
        """
        Find the next suitable time for mowing
        
        Args:
            original_time: Original scheduled time
            
        Returns:
            New time or None if no suitable time found
        """
        # Define search window
        start_time = original_time + timedelta(hours=self.min_reschedule_notice)
        end_time = original_time + timedelta(hours=self.max_reschedule_delay)
        
        # Get list of forecasts within search window
        forecasts_in_window = [f for f in self.forecasts 
                              if start_time <= f.timestamp <= end_time]
        
        if not forecasts_in_window:
            self.logger.warning(f"No forecast available within search window for rescheduling {original_time}")
            return None
        
        # Find forecasts with no/low impact
        good_forecasts = []
        for forecast in forecasts_in_window:
            impact = forecast.get_impact(self.impact_thresholds)
            if impact in [WeatherImpact.NONE, WeatherImpact.LOW]:
                good_forecasts.append(forecast)
        
        # Find longest streak of good forecasts
        if not good_forecasts:
            # If no good forecasts, accept MEDIUM impact as a fallback
            for forecast in forecasts_in_window:
                impact = forecast.get_impact(self.impact_thresholds)
                if impact == WeatherImpact.MEDIUM:
                    good_forecasts.append(forecast)
        
        if not good_forecasts:
            self.logger.warning(f"No suitable weather found for rescheduling {original_time}")
            return None
        
        # Sort by timestamp
        good_forecasts.sort(key=lambda f: f.timestamp)
        
        # After rain, wait for rain_delay hours
        was_raining = False
        for forecast in forecasts_in_window:
            if forecast.timestamp < good_forecasts[0].timestamp:
                if forecast.precipitation > 0.5:  # Significant rain
                    was_raining = True
        
        if was_raining:
            # Find a good forecast after rain delay
            for forecast in good_forecasts:
                rain_ends_at = forecast.timestamp - timedelta(hours=self.rain_delay)
                # Check if all forecasts in rain_delay window have no significant rain
                all_dry = True
                for f in forecasts_in_window:
                    if rain_ends_at <= f.timestamp < forecast.timestamp:
                        if f.precipitation > 0.5:  # Significant rain
                            all_dry = False
                            break
                
                if all_dry:
                    # This is a good time after rain delay
                    return forecast.timestamp
        
        # If no rain delay needed, return the first good forecast
        return good_forecasts[0].timestamp
    
    def get_schedule_adjustments(self, start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None) -> List[ScheduleAdjustment]:
        """
        Get schedule adjustments within a time range
        
        Args:
            start_time: Start of time range (default: beginning of today)
            end_time: End of time range (default: 7 days from now)
            
        Returns:
            List of schedule adjustments
        """
        # Default time range is today to 7 days from now
        if start_time is None:
            start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_time is None:
            end_time = start_time + timedelta(days=7)
        
        # Filter adjustments by time range
        return [
            adj for adj in self.schedule_adjustments
            if start_time <= adj.original_time <= end_time or
               (adj.adjusted_time and start_time <= adj.adjusted_time <= end_time)
        ]
    
    def get_forecast_for_period(self, start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get forecasts for a time period in a simplified format
        
        Args:
            start_time: Start time (default: now)
            end_time: End time (default: 3 days from now)
            
        Returns:
            List of simplified forecast dictionaries
        """
        # Default time range is now to 3 days from now
        if start_time is None:
            start_time = datetime.now()
        
        if end_time is None:
            end_time = start_time + timedelta(days=3)
        
        # Filter forecasts by time range
        filtered_forecasts = [
            f for f in self.forecasts
            if start_time <= f.timestamp <= end_time
        ]
        
        # Sort by timestamp
        filtered_forecasts.sort(key=lambda f: f.timestamp)
        
        # Convert to simplified format
        result = []
        for forecast in filtered_forecasts:
            impact = forecast.get_impact(self.impact_thresholds)
            result.append({
                "time": forecast.timestamp.isoformat(),
                "condition": forecast.condition.value,
                "description": forecast.description,
                "temperature": forecast.temperature,
                "precipitation_mm": forecast.precipitation,
                "precipitation_probability": forecast.precipitation_probability,
                "wind_speed": forecast.wind_speed,
                "impact": impact.value
            })
        
        return result
    
    def get_weather_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current weather conditions and upcoming forecast
        
        Returns:
            Dictionary with weather summary
        """
        # Get current and near-future forecasts
        now = datetime.now()
        forecasts_24h = [f for f in self.forecasts if f.timestamp <= now + timedelta(hours=24)]
        forecasts_3d = [f for f in self.forecasts if f.timestamp <= now + timedelta(days=3)]
        
        if not forecasts_24h:
            return {
                "available": False,
                "message": "No weather forecast available"
            }
        
        # Sort by timestamp
        forecasts_24h.sort(key=lambda f: f.timestamp)
        forecasts_3d.sort(key=lambda f: f.timestamp)
        
        # Get current forecast (closest to now)
        current_forecast = min(self.forecasts, key=lambda f: abs(f.timestamp - now)) if self.forecasts else None
        
        # Calculate rain probability in next 24h
        rain_next_24h = any(f.precipitation > 0.5 for f in forecasts_24h)
        rain_probability_24h = max([f.precipitation_probability for f in forecasts_24h], default=0)
        
        # Calculate max high impact hours in next 3 days
        high_impact_forecasts = [f for f in forecasts_3d if f.get_impact(self.impact_thresholds) == WeatherImpact.HIGH]
        high_impact_hours = len(high_impact_forecasts) * 3  # Each forecast represents 3 hours
        
        # Find best mowing windows
        best_windows = self._find_mowing_windows(now, now + timedelta(days=3))
        
        return {
            "available": True,
            "current_condition": current_forecast.condition.value if current_forecast else None,
            "current_temperature": current_forecast.temperature if current_forecast else None,
            "current_description": current_forecast.description if current_forecast else None,
            "rain_expected_24h": rain_next_24h,
            "rain_probability_24h": rain_probability_24h,
            "high_impact_hours_3d": high_impact_hours,
            "forecast_updated": datetime.fromtimestamp(self.last_update_time).isoformat() if self.last_update_time else None,
            "best_mowing_windows": best_windows
        }
    
    def _find_mowing_windows(self, start_time: datetime, end_time: datetime,
                            min_window_hours: int = 3) -> List[Dict[str, Any]]:
        """
        Find optimal windows for mowing
        
        Args:
            start_time: Start of search period
            end_time: End of search period
            min_window_hours: Minimum window duration in hours
            
        Returns:
            List of mowing windows, each with start_time, end_time, and quality
        """
        # Get forecasts in range
        forecasts_in_range = [f for f in self.forecasts 
                           if start_time <= f.timestamp <= end_time]
        
        if not forecasts_in_range:
            return []
        
        # Sort by timestamp
        forecasts_in_range.sort(key=lambda f: f.timestamp)
        
        # Score each forecast point
        # 0-10 scale (10 = perfect, 0 = unsuitable)
        forecast_scores = []
        for forecast in forecasts_in_range:
            impact = forecast.get_impact(self.impact_thresholds)
            
            if impact == WeatherImpact.HIGH:
                score = 0  # Unsuitable
            elif impact == WeatherImpact.MEDIUM:
                score = 3  # Poor
            elif impact == WeatherImpact.LOW:
                score = 7  # Good
            else:  # NONE
                score = 10  # Perfect
            
            # Adjust for rain in preceding period (wet grass)
            # Look at previous 6 hours
            precip_factor = 1.0
            for prev_f in forecasts_in_range:
                if prev_f.timestamp < forecast.timestamp and \
                   forecast.timestamp - prev_f.timestamp <= timedelta(hours=6):
                    if prev_f.precipitation > 1.0:
                        # Heavy rain in last 6 hours
                        precip_factor = 0.5
                        break
                    elif prev_f.precipitation > 0.2:
                        # Light rain in last 6 hours
                        precip_factor = 0.7
                        break
            
            forecast_scores.append({
                "timestamp": forecast.timestamp,
                "score": score * precip_factor,
                "condition": forecast.condition.value,
                "precipitation": forecast.precipitation,
                "temperature": forecast.temperature
            })
        
        # Find windows of good conditions
        windows = []
        current_window = None
        
        for fs in forecast_scores:
            if fs["score"] >= 7:  # Good or better
                if current_window is None:
                    # Start new window
                    current_window = {
                        "start_time": fs["timestamp"],
                        "scores": [fs["score"]],
                        "forecasts": [fs]
                    }
                else:
                    # Extend window
                    current_window["scores"].append(fs["score"])
                    current_window["forecasts"].append(fs)
            else:
                # Close window if one is open
                if current_window is not None:
                    # Calculate window duration
                    start = current_window["start_time"]
                    end = current_window["forecasts"][-1]["timestamp"]
                    duration_hours = (end - start).total_seconds() / 3600
                    
                    # Only keep windows of sufficient duration
                    if duration_hours >= min_window_hours:
                        avg_score = sum(current_window["scores"]) / len(current_window["scores"])
                        windows.append({
                            "start_time": start.isoformat(),
                            "end_time": end.isoformat(),
                            "duration_hours": duration_hours,
                            "quality": avg_score / 10.0,  # 0-1 scale
                            "conditions": [f["condition"] for f in current_window["forecasts"]]
                        })
                    
                    current_window = None
        
        # Close final window if needed
        if current_window is not None:
            start = current_window["start_time"]
            end = current_window["forecasts"][-1]["timestamp"]
            duration_hours = (end - start).total_seconds() / 3600
            
            if duration_hours >= min_window_hours:
                avg_score = sum(current_window["scores"]) / len(current_window["scores"])
                windows.append({
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "duration_hours": duration_hours,
                    "quality": avg_score / 10.0,  # 0-1 scale
                    "conditions": [f["condition"] for f in current_window["forecasts"]]
                })
        
        # Sort by quality (best first)
        windows.sort(key=lambda w: w["quality"], reverse=True)
        
        return windows

import random  # Import needed for mock weather generation
