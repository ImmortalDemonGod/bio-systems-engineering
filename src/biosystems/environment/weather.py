"""
Weather Data Integration
========================

Fetch and cache weather data from Open-Meteo API to provide environmental
context for activities.
"""

import requests
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Union, Tuple

import numpy as np
import pandas as pd


# WMO Weather interpretation codes (WW) mapping
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}


def get_weather_description(code: Optional[Union[int, float, str]]) -> str:
    """
    Convert WMO weather code to human-readable description.
    
    Parameters
    ----------
    code : int, float, str, or None
        WMO weather code
        
    Returns
    -------
    str
        Human-readable weather description
    """
    if code is None:
        return "Unknown"
    
    try:
        code_int = int(float(code))
        return WMO_WEATHER_CODES.get(code_int, f"Unknown weather code: {code_int}")
    except (ValueError, TypeError):
        return f"Invalid weather code: {code}"


def make_json_serializable(obj):
    """
    Recursively convert numpy arrays in dicts/lists to lists for JSON serialization.
    
    Parameters
    ----------
    obj : any
        Object to convert
        
    Returns
    -------
    any
        JSON-serializable version of object
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


class WeatherCache:
    """
    Simple weather data cache using Parquet file storage.
    
    Attributes
    ----------
    cache_path : Path
        Path to cache Parquet file
    cache : pd.DataFrame
        In-memory cache
    """
    
    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize weather cache.
        
        Parameters
        ----------
        cache_path : Path, optional
            Path to cache file. If None, caching is disabled.
        """
        self.cache_path = cache_path
        
        # Load existing cache if available
        if cache_path and cache_path.exists():
            self.cache = pd.read_parquet(cache_path)
            # Ensure weather column is always a string (JSON)
            if 'weather' in self.cache.columns:
                def safe_serialize(x):
                    if isinstance(x, dict):
                        try:
                            return json.dumps(make_json_serializable(x))
                        except Exception:
                            return None
                    return x if pd.notnull(x) else None
                self.cache['weather'] = self.cache['weather'].apply(safe_serialize)
        else:
            self.cache = pd.DataFrame(columns=['lat', 'lon', 'date', 'weather'])
    
    def get(self, lat: float, lon: float, date_str: str) -> Optional[dict]:
        """
        Get cached weather data.
        
        Parameters
        ----------
        lat : float
            Latitude
        lon : float
            Longitude
        date_str : str
            Date in YYYY-MM-DD format
            
        Returns
        -------
        dict or None
            Weather data if cached, None otherwise
        """
        if self.cache.empty:
            return None
        
        cached = self.cache[
            (self.cache['lat'] == lat) &
            (self.cache['lon'] == lon) &
            (self.cache['date'] == date_str)
        ]
        
        if not cached.empty:
            weather = cached.iloc[0]['weather']
            if isinstance(weather, str):
                try:
                    return json.loads(weather)
                except Exception:
                    pass
            return weather
        
        return None
    
    def set(self, lat: float, lon: float, date_str: str, weather: dict):
        """
        Save weather data to cache.
        
        Parameters
        ----------
        lat : float
            Latitude
        lon : float
            Longitude
        date_str : str
            Date in YYYY-MM-DD format
        weather : dict
            Weather data to cache
        """
        if not self.cache_path:
            return  # Caching disabled
        
        # Add to in-memory cache
        self.cache = pd.concat([
            self.cache,
            pd.DataFrame([{
                'lat': lat,
                'lon': lon,
                'date': date_str,
                'weather': json.dumps(weather)
            }])
        ], ignore_index=True)
        
        # Save to disk
        self.cache.to_parquet(self.cache_path, index=False)


def fetch_weather_open_meteo(
    lat: float,
    lon: float,
    dt: datetime,
    cache: Optional[WeatherCache] = None,
    max_retries: int = 6,
    max_backoff: float = 2.0
) -> Tuple[Optional[dict], Optional[float]]:
    """
    Robustly fetch weather for a given latitude, longitude, and datetime (UTC).
    
    Implements exponential backoff on network/API errors.
    Tries variations in time (±0 to ±5 hours) on the same day and location
    (rounded, nudged lat/lon) until data is found.
    
    Parameters
    ----------
    lat : float
        Latitude (degrees)
    lon : float
        Longitude (degrees)
    dt : datetime
        Target datetime (UTC)
    cache : WeatherCache, optional
        Cache instance for storing/retrieving data
    max_retries : int
        Maximum number of retry attempts
    max_backoff : float
        Maximum backoff time in seconds
        
    Returns
    -------
    weather : dict or None
        Weather data if successful
    offset_hours : float or None
        Time offset in hours if successful
    """
    # Check cache first
    date_str = pd.to_datetime(dt).strftime('%Y-%m-%d')
    
    if cache:
        cached = cache.get(lat, lon, date_str)
        if cached:
            return cached, 0
    
    # Try variations in time and location
    time_offsets = [timedelta(hours=h) for h in range(-5, 6)]
    lat_variations = [lat, round(lat, 3), round(lat, 2), lat+0.01, lat-0.01, lat+0.05, lat-0.05, lat+0.1, lat-0.1]
    lon_variations = [lon, round(lon, 3), round(lon, 2), lon+0.01, lon-0.01, lon+0.05, lon-0.05, lon+0.1, lon-0.1]
    
    attempt = 0
    while attempt < max_retries:
        all_failed = True
        
        for lat_try in lat_variations:
            for lon_try in lon_variations:
                for offset in time_offsets:
                    hour_iso = (dt + offset).replace(minute=0, second=0, microsecond=0).isoformat()
                    
                    try:
                        url = (
                            f"https://api.open-meteo.com/v1/forecast?"
                            f"latitude={lat_try}&longitude={lon_try}&"
                            f"hourly=temperature_2m,precipitation,weathercode,windspeed_10m,windgusts_10m,winddirection_10m&"
                            f"start={hour_iso}&end={hour_iso}&timezone=UTC"
                        )
                        resp = requests.get(url, timeout=6)
                        
                        if resp.status_code == 200:
                            weather = resp.json()
                            if 'hourly' in weather and weather['hourly']['temperature_2m']:
                                result = weather
                                # Save to cache
                                if cache:
                                    cache.set(lat, lon, date_str, result)
                                return result, offset.total_seconds() / 3600
                    except Exception as e:
                        print(f"[Weather] Error: {e} (lat={lat_try}, lon={lon_try}, time={hour_iso})")
        
        # If we reach here, all variations failed for this attempt
        if all_failed:
            backoff = min(max_backoff, 0.2 * (2 ** attempt))
            print(f"[Weather][Backoff] Attempt {attempt+1} failed, retrying in {backoff:.2f}s...")
            time.sleep(backoff)
        attempt += 1
    
    print(f"[Weather] Failed to fetch weather after {max_retries} retries for lat={lat}, lon={lon}, time={dt}")
    return None, None
