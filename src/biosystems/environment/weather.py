"""
Weather Data Integration
========================

Fetch and cache weather data from Open-Meteo API to provide environmental
context for activities.
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import requests

# WMO Weather interpretation codes (WW) mapping
WMO_WEATHER_CODES: dict[int, str] = {
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
    99: "Thunderstorm with heavy hail",
}


def get_weather_description(code: int | float | str | None) -> str:
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


def make_json_serializable(obj: Any) -> Any:
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

    def __init__(self, cache_path: Path | None = None):
        """
        Initialize weather cache.

        Parameters
        ----------
        cache_path : Path, optional
            Path to cache file. If None, caching is memory-only.
        """
        self.cache_path = cache_path

        # Load existing cache if available
        if cache_path and cache_path.exists():
            try:
                self.cache = pd.read_parquet(cache_path)
                # Ensure weather column is always a string (JSON)
                if "weather" in self.cache.columns:

                    def safe_serialize(x):
                        if isinstance(x, dict):
                            try:
                                return json.dumps(make_json_serializable(x))
                            except Exception:
                                return None
                        return x if pd.notnull(x) else None

                    self.cache["weather"] = self.cache["weather"].apply(safe_serialize)
            except Exception:
                # If reading fails (e.g. empty file), start fresh
                self.cache = pd.DataFrame(columns=["lat", "lon", "date", "weather"])
        else:
            self.cache = pd.DataFrame(columns=["lat", "lon", "date", "weather"])

    def get(self, lat: float, lon: float, date_str: str) -> dict[Any, Any] | None:
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
            (self.cache["lat"] == lat)
            & (self.cache["lon"] == lon)
            & (self.cache["date"] == date_str)
        ]

        if not cached.empty:
            weather = cached.iloc[0]["weather"]
            if isinstance(weather, str):
                try:
                    return cast(dict[Any, Any], json.loads(weather))
                except Exception:
                    pass
            return cast(dict[Any, Any], weather)

        return None

    def set(self, lat: float, lon: float, date_str: str, weather: dict[Any, Any]):
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
        # Add to in-memory cache
        new_row = pd.DataFrame(
            [
                {
                    "lat": lat,
                    "lon": lon,
                    "date": date_str,
                    "weather": json.dumps(make_json_serializable(weather)),
                }
            ]
        )

        if self.cache.empty:
            self.cache = new_row
        else:
            self.cache = pd.concat([self.cache, new_row], ignore_index=True)

        # Save to disk if path provided
        if self.cache_path:
            self.cache.to_parquet(self.cache_path, index=False)


def _weather_base_url(dt: datetime) -> str:
    """
    Return the appropriate Open-Meteo base URL for the given datetime.

    Open-Meteo exposes two distinct endpoints:
    - ``/v1/forecast``  — real-time + up to 16 days ahead (also serves the
      most recent ~3 days of historical data, but not further back).
    - ``/v1/archive``   — historical archive from 1940 to ~5 days ago.

    Using the forecast endpoint for activities from months ago silently
    returns an empty or mismatched hourly series, which is the root cause
    of the previous ~891-request search loop.
    """
    now = datetime.utcnow()
    age_days = (now.date() - dt.date()).days if dt.tzinfo is None else (
        now.replace(tzinfo=timezone.utc) - dt.replace(tzinfo=timezone.utc)
    ).days
    if age_days > 3:
        return "https://archive-api.open-meteo.com/v1/archive"
    return "https://api.open-meteo.com/v1/forecast"


def fetch_weather_open_meteo(
    lat: float,
    lon: float,
    dt: datetime,
    cache: WeatherCache | None = None,
    max_retries: int = 3,
    max_backoff: float = 2.0,
) -> tuple[dict[Any, Any] | None, float | None]:
    """
    Fetch weather for a given latitude, longitude, and datetime (UTC).

    Uses the Open-Meteo archive endpoint for historical dates (>3 days ago)
    and the forecast endpoint for recent/future dates. Open-Meteo maps any
    lat/lon to the nearest grid cell automatically, so lat/lon nudging is
    unnecessary and has been removed.

    Tries the target hour and ±1 hour offsets (3 requests per attempt at
    most) with exponential backoff on transient errors.

    Parameters
    ----------
    lat : float
        Latitude (degrees)
    lon : float
        Longitude (degrees)
    dt : datetime
        Target datetime (UTC). May be tz-naive or tz-aware.
    cache : WeatherCache, optional
        Cache instance for storing/retrieving data.
    max_retries : int
        Maximum number of retry attempts on network error.
    max_backoff : float
        Maximum backoff duration in seconds.

    Returns
    -------
    weather : dict or None
        Parsed Open-Meteo hourly response dict, or None on failure.
    offset_hours : float or None
        Hour offset used (0.0 on cache hit or exact match).
    """
    from datetime import timezone as _tz

    date_str = pd.to_datetime(dt).strftime("%Y-%m-%d")

    if cache:
        cached = cache.get(lat, lon, date_str)
        if cached:
            return cached, 0.0

    base_url = _weather_base_url(dt)
    lat_r = round(lat, 4)
    lon_r = round(lon, 4)
    hourly_vars = "temperature_2m,precipitation,weathercode,windspeed_10m,windgusts_10m,winddirection_10m"

    # Try exact hour first, then ±1 hour — 3 requests max per attempt
    time_offsets = [timedelta(hours=h) for h in (0, 1, -1)]

    attempt = 0
    while attempt < max_retries:
        for offset in time_offsets:
            target = dt + offset
            if target.tzinfo is None:
                target = target.replace(tzinfo=_tz.utc)
            hour_str = target.strftime("%Y-%m-%dT%H:00")

            try:
                resp = requests.get(
                    base_url,
                    params={
                        "latitude": lat_r,
                        "longitude": lon_r,
                        "hourly": hourly_vars,
                        "start_hour": hour_str,
                        "end_hour": hour_str,
                        "timezone": "UTC",
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    weather = resp.json()
                    temps = (weather.get("hourly") or {}).get("temperature_2m")
                    if temps:
                        if cache:
                            cache.set(lat, lon, date_str, weather)
                        return weather, offset.total_seconds() / 3600
            except Exception as e:
                print(f"[Weather] Error on attempt {attempt + 1}: {e}", file=sys.stderr)

        backoff = min(max_backoff, 0.2 * (2 ** attempt))
        print(f"[Weather][Backoff] Attempt {attempt + 1} failed, retrying in {backoff:.2f}s...", file=sys.stderr)
        time.sleep(backoff)
        attempt += 1

    print(f"[Weather] Failed after {max_retries} retries for lat={lat_r}, lon={lon_r}, time={dt}", file=sys.stderr)
    return None, None
