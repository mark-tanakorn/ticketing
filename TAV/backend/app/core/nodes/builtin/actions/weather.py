"""
Weather Node - Free Weather Data using Open-Meteo API

Fetches current weather information for any location worldwide.
Uses Open-Meteo API which requires no API key.
"""

import logging
import httpx
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="weather",
    category=NodeCategory.ACTIONS,
    name="Weather",
    description="Get current weather information for any location using Open-Meteo API (no API key required)",
    icon="fa-solid fa-cloud-sun",
    version="1.0.0"
)
class WeatherNode(Node):
    """
    Weather Node - Free weather data from Open-Meteo
    
    Features:
    - No API key required
    - Global coverage
    - Current conditions + forecast
    - Multiple units (Celsius/Fahrenheit)
    - Wind speed in various units
    
    Data includes:
    - Temperature & feels like
    - Humidity
    - Weather conditions
    - Wind speed & direction
    - Precipitation
    - Cloud cover
    - Pressure
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "input",
                "type": PortType.UNIVERSAL,
                "display_name": "Input",
                "description": "Optional input (can extract location from text)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "output",
                "type": PortType.UNIVERSAL,
                "display_name": "Weather Data",
                "description": "Weather information and forecast"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "location": {
                "type": "string",
                "label": "Location",
                "description": "Location for weather lookup (city name, coordinates, etc.)",
                "required": False,
                "placeholder": "e.g., London, New York, Paris",
                "widget": "text",
                "help": "Leave empty to extract from input text"
            },
            "units": {
                "type": "select",
                "widget": "select",
                "label": "Temperature Units",
                "description": "Temperature unit system",
                "required": False,
                "options": [
                    {"label": "Celsius (°C)", "value": "celsius"},
                    {"label": "Fahrenheit (°F)", "value": "fahrenheit"}
                ],
                "default": "celsius"
            },
            "wind_speed_unit": {
                "type": "select",
                "widget": "select",
                "label": "Wind Speed Unit",
                "description": "Wind speed measurement unit",
                "required": False,
                "options": [
                    {"label": "km/h", "value": "kmh"},
                    {"label": "m/s", "value": "ms"},
                    {"label": "mph", "value": "mph"},
                    {"label": "knots", "value": "kn"}
                ],
                "default": "kmh"
            },
            "include_forecast": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Include Forecast",
                "description": "Include 7-day weather forecast",
                "required": False,
                "default": False
            },
            "include_hourly": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Include Hourly Data",
                "description": "Include hourly forecast for next 24 hours",
                "required": False,
                "default": False
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute weather node"""
        try:
            # Get location from config or input
            location = self.resolve_config(input_data, "location", "")
            
            # If no location in config, try to extract from input
            if not location:
                port_input = input_data.ports.get("input")
                from app.core.nodes.multimodal import extract_content
                location = extract_content(port_input) if port_input else ""
                if isinstance(port_input, dict) and not location:
                    location = port_input.get("location", "")
                if location and not isinstance(port_input, dict):
                    location = self._extract_location_from_text(location)
            
            if not location:
                return {
                    "output": {
                        "error": "No location provided. Please specify a location in config or input.",
                        "success": False
                    }
                }
            
            logger.info(f"🌤️ Getting weather for: {location}")
            
            # Geocode location
            geo_data = await self._geocode_location(location)
            if not geo_data:
                return {
                    "output": {
                        "error": f"Could not find location: {location}",
                        "success": False
                    }
                }
            
            # Get weather data
            units = self.resolve_config(input_data, "units", "celsius")
            wind_speed_unit = self.resolve_config(input_data, "wind_speed_unit", "kmh")
            include_forecast = self.resolve_config(input_data, "include_forecast", False)
            include_hourly = self.resolve_config(input_data, "include_hourly", False)
            
            weather_data = await self._get_weather_data(
                geo_data["latitude"],
                geo_data["longitude"],
                units,
                wind_speed_unit,
                include_forecast,
                include_hourly
            )
            
            if not weather_data:
                return {
                    "output": {
                        "error": "Failed to fetch weather data",
                        "success": False
                    }
                }
            
            # Parse current weather
            current = weather_data.get("current", {})
            weather_code = current.get("weather_code", 0)
            weather_desc = self._get_weather_description(weather_code)
            
            result = {
                "location": {
                    "name": geo_data["name"],
                    "country": geo_data["country"],
                    "latitude": geo_data["latitude"],
                    "longitude": geo_data["longitude"],
                    "timezone": geo_data.get("timezone", "UTC")
                },
                "current": {
                    "temperature": current.get("temperature_2m"),
                    "feels_like": current.get("apparent_temperature"),
                    "humidity": current.get("relative_humidity_2m"),
                    "weather": weather_desc,
                    "weather_code": weather_code,
                    "is_day": bool(current.get("is_day")),
                    "precipitation": current.get("precipitation"),
                    "rain": current.get("rain"),
                    "snowfall": current.get("snowfall"),
                    "cloud_cover": current.get("cloud_cover"),
                    "pressure": current.get("pressure_msl"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "wind_direction": current.get("wind_direction_10m"),
                    "wind_gusts": current.get("wind_gusts_10m"),
                },
                "units": {
                    "temperature": "°F" if units == "fahrenheit" else "°C",
                    "wind_speed": wind_speed_unit,
                    "precipitation": "mm",
                    "pressure": "hPa"
                },
                "success": True
            }
            
            # Add forecast if requested
            if include_forecast and "daily" in weather_data:
                result["forecast"] = self._parse_forecast(weather_data["daily"], units)
            
            # Add hourly if requested
            if include_hourly and "hourly" in weather_data:
                result["hourly"] = self._parse_hourly(weather_data["hourly"], units)
            
            logger.info(
                f"✅ Weather fetched: {geo_data['name']}, {current.get('temperature_2m')}°, "
                f"{weather_desc}"
            )
            
            return {"output": result}
            
        except Exception as e:
            logger.error(f"❌ Weather node error: {e}", exc_info=True)
            return {
                "output": {
                    "error": str(e),
                    "success": False
                }
            }
    
    async def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        """Geocode location using Open-Meteo Geocoding API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={
                        "name": location,
                        "count": 1,
                        "language": "en",
                        "format": "json"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if results:
                    loc = results[0]
                    return {
                        "name": loc.get("name"),
                        "country": loc.get("country"),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "timezone": loc.get("timezone"),
                        "admin1": loc.get("admin1")
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    async def _get_weather_data(
        self,
        latitude: float,
        longitude: float,
        units: str,
        wind_speed_unit: str,
        include_forecast: bool,
        include_hourly: bool
    ) -> Optional[Dict[str, Any]]:
        """Get weather data from Open-Meteo API"""
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join([
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "is_day",
                    "precipitation",
                    "rain",
                    "showers",
                    "snowfall",
                    "weather_code",
                    "cloud_cover",
                    "pressure_msl",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m"
                ]),
                "temperature_unit": "fahrenheit" if units == "fahrenheit" else "celsius",
                "wind_speed_unit": wind_speed_unit,
                "timezone": "auto"
            }
            
            if include_forecast:
                params["daily"] = ",".join([
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "wind_speed_10m_max"
                ])
                params["forecast_days"] = 7
            
            if include_hourly:
                params["hourly"] = ",".join([
                    "temperature_2m",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m"
                ])
                params["forecast_hours"] = 24
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return None
    
    def _get_weather_description(self, weather_code: int) -> str:
        """Convert WMO weather code to description"""
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(weather_code, "Unknown")
    
    def _parse_forecast(self, daily: Dict[str, Any], units: str) -> List[Dict[str, Any]]:
        """Parse daily forecast data"""
        forecast = []
        times = daily.get("time", [])
        
        for i, date in enumerate(times):
            forecast.append({
                "date": date,
                "temp_max": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                "temp_min": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                "weather": self._get_weather_description(daily.get("weather_code", [])[i]) if i < len(daily.get("weather_code", [])) else "Unknown",
                "precipitation": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                "wind_speed_max": daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None
            })
        
        return forecast
    
    def _parse_hourly(self, hourly: Dict[str, Any], units: str) -> List[Dict[str, Any]]:
        """Parse hourly forecast data"""
        hourly_data = []
        times = hourly.get("time", [])
        
        for i, time in enumerate(times):
            hourly_data.append({
                "time": time,
                "temperature": hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else None,
                "weather": self._get_weather_description(hourly.get("weather_code", [])[i]) if i < len(hourly.get("weather_code", [])) else "Unknown",
                "precipitation": hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else None,
                "wind_speed": hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else None
            })
        
        return hourly_data
    
    def _extract_location_from_text(self, text: str) -> str:
        """Simple location extraction from text"""
        import re
        
        # Look for common patterns
        patterns = [
            r"weather (?:in|for|at) ([A-Z][a-zA-Z\s]{2,30})",
            r"(?:in|at) ([A-Z][a-zA-Z\s]{2,30})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return ""


if __name__ == "__main__":
    print("Weather Node - Open-Meteo Integration")

