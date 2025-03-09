"""
Grass Growth Prediction Module

This module provides functionality for predicting grass growth rates based on
historical data, weather forecasts, and lawn conditions.
"""

import os
import json
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests

from ..core.config import ConfigManager
from .lawn_health import LawnHealthAnalyzer, GrassHealthStatus


@dataclass
class WeatherForecast:
    """Weather forecast data structure"""
    date: datetime
    temperature_high: float
    temperature_low: float
    precipitation_mm: float
    humidity: float
    cloud_cover: float
    uv_index: float
    

@dataclass
class GrowthPrediction:
    """Grass growth prediction data structure"""
    date: datetime
    growth_rate: float  # mm/day
    confidence: float  # 0-1 scale
    factors: Dict[str, float]  # Contribution of each factor
    irrigation_needed: bool
    optimal_mowing_date: datetime
    

class GrassGrowthPredictor:
    """
    Class for predicting grass growth based on weather and conditions
    
    Uses historical growth data, weather forecasts, and lawn health analysis
    to predict future grass growth rates.
    """
    
    def __init__(self, config: ConfigManager, health_analyzer: Optional[LawnHealthAnalyzer] = None):
        """
        Initialize the grass growth predictor
        
        Args:
            config: Configuration manager
            health_analyzer: Lawn health analyzer for current lawn conditions (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.health_analyzer = health_analyzer
        
        # Configuration
        self.weather_api_key = config.get("weather.api_key", "")
        self.weather_api_url = config.get("weather.api_url", "https://api.example.com/weather")
        self.data_dir = config.get("system.data_dir", "data")
        self.growth_history_file = os.path.join(self.data_dir, "growth_history.json")
        self.location = {
            "latitude": config.get("location.latitude", 0.0),
            "longitude": config.get("location.longitude", 0.0),
            "city": config.get("location.city", "Unknown"),
            "country": config.get("location.country", "Unknown"),
        }
        
        # Parameters from config
        self.grass_type = config.get("lawn.grass_type", "unknown")
        self.soil_type = config.get("lawn.soil_type", "unknown")
        self.irrigation_system = config.get("lawn.irrigation_system", False)
        self.optimal_cutting_height = config.get("mowing.cutting_height", 35)  # mm
        self.mowing_threshold = config.get("growth_prediction.mowing_threshold", 15)  # mm above optimal
        
        # State
        self.weather_forecast: List[WeatherForecast] = []
        self.growth_history: List[Dict[str, Any]] = []
        self.last_prediction: Optional[List[GrowthPrediction]] = None
        self.last_prediction_time = datetime.min
        
        # Growth factors for different grass types (mm/day in ideal conditions)
        self.base_growth_rates = {
            "bermuda": 2.5,
            "fescue": 2.0,
            "kentucky_bluegrass": 1.8,
            "ryegrass": 2.2,
            "zoysia": 1.5,
            "st_augustine": 2.0,
            "bentgrass": 1.2,
            "buffalo": 1.7,
            "unknown": 2.0,  # Default
        }
        
        # Season adjustment factors
        self.season_factors = {
            # Northern hemisphere seasons (month numbers)
            "spring": [3, 4, 5],  # March-May
            "summer": [6, 7, 8],  # June-August
            "fall": [9, 10, 11],  # September-November
            "winter": [12, 1, 2],  # December-February
        }
        
        # Load growth history if available
        self._load_growth_history()
        
        self.logger.info("Grass growth predictor initialized")
    
    def _load_growth_history(self) -> None:
        """Load grass growth history from file"""
        if not os.path.exists(self.growth_history_file):
            self.logger.info("No growth history file found, starting with empty history")
            return
        
        try:
            with open(self.growth_history_file, 'r') as f:
                data = json.load(f)
                
            self.growth_history = data.get("history", [])
            self.logger.info(f"Loaded {len(self.growth_history)} growth history entries")
        except Exception as e:
            self.logger.error(f"Error loading growth history: {e}")
    
    def _save_growth_history(self) -> bool:
        """Save grass growth history to file"""
        try:
            os.makedirs(os.path.dirname(self.growth_history_file), exist_ok=True)
            
            data = {
                "history": self.growth_history,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self.growth_history_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.debug(f"Saved {len(self.growth_history)} growth history entries")
            return True
        except Exception as e:
            self.logger.error(f"Error saving growth history: {e}")
            return False
    
    def update_weather_forecast(self) -> bool:
        """
        Update the weather forecast data
        
        Returns:
            Success or failure
        """
        if not self.weather_api_key:
            self.logger.warning("No weather API key configured, using mock forecast data")
            self._generate_mock_forecast()
            return True
            
        try:
            # In a real implementation, this would call a weather API
            # For this example, we'll generate mock data
            self._generate_mock_forecast()
            return True
        except Exception as e:
            self.logger.error(f"Error updating weather forecast: {e}")
            return False
    
    def _generate_mock_forecast(self) -> None:
        """Generate mock weather forecast data for demonstration"""
        now = datetime.now()
        forecast = []
        
        # Generate forecast for the next 7 days
        for day in range(7):
            date = now + timedelta(days=day)
            month = date.month
            
            # Seasonal variation
            is_summer = month in [6, 7, 8]
            is_winter = month in [12, 1, 2]
            
            # Generate reasonable temperature and precipitation values based on season
            if is_summer:
                temp_high = np.random.normal(28, 3)  # Summer temps around 28°C
                temp_low = np.random.normal(18, 2)
                precip = np.random.exponential(2) if np.random.random() < 0.3 else 0
                humidity = np.random.normal(0.65, 0.1)
                cloud_cover = np.random.beta(2, 5)  # Generally clearer in summer
                uv_index = np.random.normal(8, 1.5)
            elif is_winter:
                temp_high = np.random.normal(5, 3)  # Winter temps around 5°C
                temp_low = np.random.normal(-2, 3)
                precip = np.random.exponential(3) if np.random.random() < 0.4 else 0
                humidity = np.random.normal(0.75, 0.1)
                cloud_cover = np.random.beta(5, 2)  # Generally cloudier in winter
                uv_index = np.random.normal(2, 1)
            else:
                temp_high = np.random.normal(18, 5)  # Spring/Fall temps around 18°C
                temp_low = np.random.normal(8, 4)
                precip = np.random.exponential(2.5) if np.random.random() < 0.35 else 0
                humidity = np.random.normal(0.7, 0.1)
                cloud_cover = np.random.beta(3, 3)  # Mix of cloudy and clear days
                uv_index = np.random.normal(5, 2)
            
            # Create forecast entry
            forecast_entry = WeatherForecast(
                date=date,
                temperature_high=round(float(temp_high), 1),
                temperature_low=round(float(temp_low), 1),
                precipitation_mm=round(float(precip), 1),
                humidity=min(1.0, max(0.0, float(humidity))),
                cloud_cover=min(1.0, max(0.0, float(cloud_cover))),
                uv_index=max(0.0, float(uv_index))
            )
            
            forecast.append(forecast_entry)
        
        self.weather_forecast = forecast
        self.logger.info(f"Generated mock weather forecast for {len(forecast)} days")
    
    def add_growth_measurement(self, height_mm: float, date: Optional[datetime] = None) -> bool:
        """
        Add a new grass height measurement
        
        Args:
            height_mm: Measured grass height in mm
            date: Date of measurement (default: now)
            
        Returns:
            Success or failure
        """
        measurement_date = date or datetime.now()
        
        # Get weather data for this date
        weather_data = self._get_weather_data_for_date(measurement_date)
        
        # Get latest lawn health if available
        health_status = None
        if self.health_analyzer.last_report:
            health_status = self.health_analyzer.last_report.health_status.value
        
        # Create measurement entry
        entry = {
            "date": measurement_date.isoformat(),
            "height_mm": height_mm,
            "weather": weather_data,
            "health_status": health_status
        }
        
        # Add to history
        self.growth_history.append(entry)
        
        # Limit history length (keep the most recent 100 entries)
        if len(self.growth_history) > 100:
            self.growth_history = self.growth_history[-100:]
        
        # Save updated history
        return self._save_growth_history()
    
    def _get_weather_data_for_date(self, date: datetime) -> Dict[str, Any]:
        """
        Get weather data for a specific date
        
        If the date is in the past, try to use historical data.
        If the date is in the future, use forecast if available.
        Otherwise, use reasonable defaults.
        
        Args:
            date: The date to get weather data for
            
        Returns:
            Weather data dictionary
        """
        now = datetime.now()
        
        # For dates in the future, check forecast
        if date > now:
            for forecast in self.weather_forecast:
                if forecast.date.date() == date.date():
                    return {
                        "temperature_high": forecast.temperature_high,
                        "temperature_low": forecast.temperature_low,
                        "precipitation_mm": forecast.precipitation_mm,
                        "humidity": forecast.humidity,
                        "cloud_cover": forecast.cloud_cover,
                        "uv_index": forecast.uv_index
                    }
        
        # For past dates, check history
        for entry in reversed(self.growth_history):
            entry_date = datetime.fromisoformat(entry["date"])
            if entry_date.date() == date.date() and "weather" in entry:
                return entry["weather"]
        
        # If no data found, use reasonable defaults
        month = date.month
        is_summer = month in [6, 7, 8]
        is_winter = month in [12, 1, 2]
        
        if is_summer:
            return {
                "temperature_high": 28.0,
                "temperature_low": 18.0,
                "precipitation_mm": 0.0,
                "humidity": 0.65,
                "cloud_cover": 0.3,
                "uv_index": 8.0
            }
        elif is_winter:
            return {
                "temperature_high": 5.0,
                "temperature_low": -2.0,
                "precipitation_mm": 0.0,
                "humidity": 0.75,
                "cloud_cover": 0.7,
                "uv_index": 2.0
            }
        else:
            return {
                "temperature_high": 18.0,
                "temperature_low": 8.0,
                "precipitation_mm": 0.0,
                "humidity": 0.7,
                "cloud_cover": 0.5,
                "uv_index": 5.0
            }
    
    def calculate_growth_rate(self, date: datetime) -> float:
        """
        Calculate grass growth rate for a specific date
        
        Args:
            date: The date to calculate for
            
        Returns:
            Growth rate in mm/day
        """
        # Get base growth rate for this grass type
        base_rate = self.base_growth_rates.get(self.grass_type, self.base_growth_rates["unknown"])
        
        # Get weather data for this date
        weather = self._get_weather_data_for_date(date)
        
        # Get season adjustment
        month = date.month
        season_factor = 1.0
        if month in self.season_factors["spring"]:
            season_factor = 1.3  # Faster growth in spring
        elif month in self.season_factors["summer"]:
            season_factor = 1.0
        elif month in self.season_factors["fall"]:
            season_factor = 0.7  # Slower in fall
        elif month in self.season_factors["winter"]:
            season_factor = 0.3  # Minimal in winter
        
        # Calculate weather factor
        # Temperature factor: optimal growth between 15-25°C
        temp_avg = (weather["temperature_high"] + weather["temperature_low"]) / 2
        if temp_avg < 5:
            temp_factor = 0.1  # Minimal growth below 5°C
        elif temp_avg < 15:
            temp_factor = 0.5 + 0.5 * (temp_avg - 5) / 10  # Ramp up from 5-15°C
        elif temp_avg <= 25:
            temp_factor = 1.0  # Optimal from 15-25°C
        elif temp_avg <= 35:
            temp_factor = 1.0 - 0.5 * (temp_avg - 25) / 10  # Ramp down from 25-35°C
        else:
            temp_factor = 0.5  # Stressed above 35°C
        
        # Water factor: combination of precipitation and humidity
        precip = weather["precipitation_mm"]
        humidity = weather["humidity"]
        
        if precip > 10:
            water_factor = 1.0  # Plenty of water
        elif precip > 0:
            water_factor = 0.7 + 0.3 * (precip / 10)  # Some water
        else:
            # No rain, rely on humidity and irrigation
            water_factor = 0.4 + 0.3 * humidity
            
            # Adjust for irrigation if available
            if self.irrigation_system:
                water_factor = max(water_factor, 0.8)
        
        # Sunlight factor: function of UV index and cloud cover
        sunlight_factor = 0.5 + 0.5 * (1 - weather["cloud_cover"]) * min(1.0, weather["uv_index"] / 8)
        
        # Health adjustment from most recent health analysis
        health_factor = 1.0
        if self.health_analyzer.last_report:
            health_status = self.health_analyzer.last_report.health_status
            if health_status == GrassHealthStatus.HEALTHY:
                health_factor = 1.0
            elif health_status == GrassHealthStatus.NEEDS_WATER:
                health_factor = 0.7
            elif health_status == GrassHealthStatus.OVERGROWN:
                health_factor = 0.9
            elif health_status == GrassHealthStatus.DAMAGED:
                health_factor = 0.5
            elif health_status == GrassHealthStatus.DISEASED:
                health_factor = 0.3
            elif health_status == GrassHealthStatus.WEED_INFESTED:
                health_factor = 0.8  # Weeds grow quickly!
        
        # Combine all factors
        growth_rate = base_rate * season_factor * temp_factor * water_factor * sunlight_factor * health_factor
        
        return growth_rate
    
    def predict_growth(self, days: int = 7) -> List[GrowthPrediction]:
        """
        Predict grass growth for the next n days
        
        Args:
            days: Number of days to predict (default: 7)
            
        Returns:
            List of GrowthPrediction objects
        """
        # Update weather forecast first
        self.update_weather_forecast()
        
        # Starting point: current date
        start_date = datetime.now()
        
        # Starting height
        current_height = self.optimal_cutting_height
        if self.growth_history:
            # Get most recent height measurement
            latest = sorted(self.growth_history, key=lambda x: x["date"], reverse=True)[0]
            current_height = latest["height_mm"]
        
        predictions = []
        accumulated_height = current_height
        
        for day in range(days):
            date = start_date + timedelta(days=day)
            
            # Calculate growth rate for this day
            daily_rate = self.calculate_growth_rate(date)
            
            # Get weather for this day
            weather = self._get_weather_data_for_date(date)
            
            # Factors that influenced the prediction
            factors = {
                "temperature": (weather["temperature_high"] + weather["temperature_low"]) / 2,
                "precipitation": weather["precipitation_mm"],
                "humidity": weather["humidity"],
                "sunlight": (1 - weather["cloud_cover"]) * weather["uv_index"],
                "season": self._get_season_factor(date.month),
                "grass_type": 1.0 if self.grass_type != "unknown" else 0.8,
                "soil_type": 1.0 if self.soil_type != "unknown" else 0.8,
            }
            
            # Add to accumulated height
            accumulated_height += daily_rate
            
            # Calculate confidence based on forecast distance
            # Confidence decreases the further we predict
            confidence = max(0.4, 1.0 - 0.1 * day)
            
            # Determine if irrigation is needed
            irrigation_needed = (
                weather["precipitation_mm"] < 3 and  # Less than 3mm rain
                daily_rate < self.base_growth_rates.get(self.grass_type, 2.0) * 0.7  # Growing slower than 70% of optimal
            )
            
            # Determine optimal mowing date
            days_until_mowing = self._calculate_days_until_mowing(accumulated_height)
            optimal_mowing_date = start_date + timedelta(days=days_until_mowing)
            
            # Create prediction
            prediction = GrowthPrediction(
                date=date,
                growth_rate=daily_rate,
                confidence=confidence,
                factors=factors,
                irrigation_needed=irrigation_needed,
                optimal_mowing_date=optimal_mowing_date
            )
            
            predictions.append(prediction)
        
        # Update state
        self.last_prediction = predictions
        self.last_prediction_time = datetime.now()
        
        return predictions
    
    def _get_season_factor(self, month: int) -> float:
        """Get season factor for a given month"""
        if month in self.season_factors["spring"]:
            return 1.3
        elif month in self.season_factors["summer"]:
            return 1.0
        elif month in self.season_factors["fall"]:
            return 0.7
        else:  # winter
            return 0.3
    
    def _calculate_days_until_mowing(self, current_height: float) -> int:
        """
        Calculate days until mowing is needed
        
        Args:
            current_height: Current grass height in mm
            
        Returns:
            Days until mowing needed
        """
        height_threshold = self.optimal_cutting_height + self.mowing_threshold
        
        if current_height >= height_threshold:
            return 0  # Mowing needed now
        
        height_remaining = height_threshold - current_height
        
        # Calculate average growth rate over the next few days
        start_date = datetime.now()
        avg_growth_rate = 0.0
        
        for day in range(5):  # Look ahead 5 days max
            date = start_date + timedelta(days=day)
            avg_growth_rate += self.calculate_growth_rate(date)
        
        avg_growth_rate /= 5
        
        if avg_growth_rate <= 0.1:
            return 14  # Minimal growth, check back in 2 weeks
        
        days_until_mowing = int(height_remaining / avg_growth_rate)
        return min(14, max(0, days_until_mowing))  # Cap at 14 days
    
    def get_next_mowing_date(self) -> datetime:
        """
        Get the next recommended mowing date
        
        Returns:
            Next mowing date
        """
        if not self.last_prediction:
            # No prediction available, generate one
            self.predict_growth()
        
        if not self.last_prediction:
            # Still no prediction, use default
            return datetime.now() + timedelta(days=7)
        
        # Find the earliest optimal mowing date from predictions
        mowing_dates = [p.optimal_mowing_date for p in self.last_prediction]
        return min(mowing_dates)
    
    def get_irrigation_recommendation(self) -> Dict[str, Any]:
        """
        Get irrigation recommendation
        
        Returns:
            Dictionary with irrigation recommendations
        """
        if not self.last_prediction:
            # No prediction available, generate one
            self.predict_growth()
        
        if not self.last_prediction:
            # Still no prediction, use default
            return {
                "irrigation_needed": False,
                "message": "No prediction data available to make irrigation recommendation"
            }
        
        # Check predictions for the next few days
        irrigation_days = []
        
        for prediction in self.last_prediction[:5]:  # Look at next 5 days
            if prediction.irrigation_needed:
                irrigation_days.append(prediction.date.date().isoformat())
        
        irrigation_needed = len(irrigation_days) > 0
        
        # Create recommendation
        recommendation = {
            "irrigation_needed": irrigation_needed,
            "irrigation_days": irrigation_days,
            "message": (
                f"Irrigation recommended on {', '.join(irrigation_days)}" 
                if irrigation_needed else "No irrigation needed in the next 5 days"
            ),
            "factors": {
                "precipitation_forecast": [p._get_weather_data_for_date(p.date)["precipitation_mm"] for p in self.last_prediction[:5]],
                "temperature_forecast": [(p._get_weather_data_for_date(p.date)["temperature_high"] + p._get_weather_data_for_date(p.date)["temperature_low"]) / 2 for p in self.last_prediction[:5]],
            }
        }
        
        return recommendation
    
    def get_growth_summary(self) -> Dict[str, Any]:
        """
        Get a summary of growth predictions
        
        Returns:
            Summary dictionary
        """
        if not self.last_prediction:
            # No prediction available, generate one
            self.predict_growth()
        
        if not self.last_prediction:
            # Still no prediction, use default
            return {
                "available": False,
                "message": "No prediction data available"
            }
        
        # Calculate summary statistics
        avg_growth_rate = sum(p.growth_rate for p in self.last_prediction) / len(self.last_prediction)
        max_growth_rate = max(p.growth_rate for p in self.last_prediction)
        irrigation_days_count = sum(1 for p in self.last_prediction if p.irrigation_needed)
        
        # Get next mowing date
        next_mowing_date = self.get_next_mowing_date()
        days_until_mowing = (next_mowing_date.date() - datetime.now().date()).days
        
        # Create summary
        summary = {
            "available": True,
            "prediction_time": self.last_prediction_time.isoformat(),
            "average_growth_rate": avg_growth_rate,
            "max_growth_rate": max_growth_rate,
            "total_growth_7days": sum(p.growth_rate for p in self.last_prediction[:7]),
            "irrigation_needed_days": irrigation_days_count,
            "next_mowing_date": next_mowing_date.isoformat(),
            "days_until_mowing": days_until_mowing,
            "message": f"Next mowing recommended in {days_until_mowing} days"
        }
        
        return summary
