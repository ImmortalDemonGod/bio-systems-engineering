"""
Environment Module
==================

Tools for contextualizing activities with environmental data.

Features:
- Weather data integration (Open-Meteo API)
- Temperature and weather code lookup
- Caching for offline analysis
"""

from biosystems.environment.weather import (
    WeatherCache,
    fetch_weather_open_meteo,
    get_weather_description,
)

__all__ = [
    "fetch_weather_open_meteo",
    "get_weather_description",
    "WeatherCache",
]
