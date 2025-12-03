"""
FIT File Parser
===============

Parses Garmin .fit (Flexible and Interoperable Data Transfer) binary files
into structured DataFrames.

FIT files contain GPS, heart rate, cadence, power, and temperature data in
a compact binary format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional

import numpy as np
import pandas as pd
import fitdecode


def parse_fit(path: Union[str, Path]) -> pd.DataFrame:
    """
    Parse a FIT file into a tidy, chronologically sorted DataFrame.
    
    This parser extracts record messages from Garmin FIT files containing:
    - GPS coordinates (position_lat, position_long)
    - Heart rate (bpm)
    - Cadence (steps per minute)
    - Power (watts)
    - Speed, distance, altitude
    - Temperature
    
    Parameters
    ----------
    path : str or Path
        Path to the FIT file
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - timestamp : pandas.Timestamp (index)
        - latitude : float (degrees, converted from semicircles)
        - longitude : float (degrees, converted from semicircles)
        - altitude : float (metres)
        - heart_rate : int (bpm, NaN if absent)
        - cadence : int (spm, NaN if absent)
        - speed : float (m/s, if present in FIT)
        - distance : float (metres, if present in FIT)
        - temperature : float (°C, if present)
        - power : int (watts, NaN if absent)
        
    Raises
    ------
    fitdecode.FitDecodeError
        If FIT file is corrupted or invalid format
    FileNotFoundError
        If file does not exist
    ValueError
        If no record messages are found in file
        
    Notes
    -----
    - Garmin stores GPS coordinates as semicircles (180/2^31 degrees)
    - Conversion: degrees = semicircles * (180.0 / 2^31)
    - FIT files may contain gaps or missing sensor data
    """
    data_records = []
    
    try:
        with fitdecode.FitReader(str(path)) as fit:
            for frame in fit:
                # Look for data messages (not definition messages)
                if isinstance(frame, fitdecode.FitDataMessage):
                    # We only care about 'record' messages (telemetry points)
                    if frame.name == 'record':
                        record_data = {'timestamp': None}
                        
                        # Extract timestamp (required)
                        if frame.has_field('timestamp'):
                            record_data['timestamp'] = frame.get_value('timestamp')
                        
                        # Extract all available fields
                        field_names = [
                            'position_lat',     # GPS latitude (semicircles)
                            'position_long',    # GPS longitude (semicircles)
                            'altitude',         # Elevation (metres)
                            'heart_rate',       # Heart rate (bpm)
                            'cadence',          # Cadence (spm, but stored as rpm for run)
                            'speed',            # Speed (m/s)
                            'distance',         # Cumulative distance (metres)
                            'temperature',      # Temperature (°C)
                            'power'             # Power (watts)
                        ]
                        
                        for field_name in field_names:
                            if frame.has_field(field_name):
                                record_data[field_name] = frame.get_value(field_name)
                        
                        # Convert GPS coordinates from semicircles to degrees
                        # Formula: degrees = semicircles * (180.0 / 2^31)
                        if 'position_lat' in record_data and record_data['position_lat'] is not None:
                            record_data['latitude'] = record_data.pop('position_lat') * (180.0 / 2**31)
                        
                        if 'position_long' in record_data and record_data['position_long'] is not None:
                            record_data['longitude'] = record_data.pop('position_long') * (180.0 / 2**31)
                        
                        # Only add records with valid timestamps
                        if record_data['timestamp']:
                            data_records.append(record_data)
    
    except fitdecode.FitDecodeError as e:
        raise fitdecode.FitDecodeError(f"Error decoding FIT file '{path}': {e}")
    
    except FileNotFoundError:
        raise FileNotFoundError(f"FIT file not found at '{path}'")
    
    # Validate we got data
    if not data_records:
        raise ValueError(f"No record messages found in FIT file '{path}'")
    
    # Create DataFrame
    df = pd.DataFrame(data_records)
    
    # Convert timestamp to datetime and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').set_index('timestamp')
    
    # Standardize column names for consistency with GPX parser
    # Rename altitude -> ele (elevation) to match GPX
    if 'altitude' in df.columns:
        df = df.rename(columns={'altitude': 'ele'})
    
    # Rename heart_rate -> hr for consistency
    if 'heart_rate' in df.columns:
        df = df.rename(columns={'heart_rate': 'hr'})
    
    # Handle potential NaN values
    # Convert cadence to int where valid, NaN otherwise
    if 'cadence' in df.columns:
        df['cadence'] = df['cadence'].replace(0, np.nan)
    
    if 'hr' in df.columns:
        df['hr'] = df['hr'].replace(0, np.nan)
    
    if 'power' in df.columns:
        df['power'] = df['power'].replace(0, np.nan)
    
    return df


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived distance, speed, and pace metrics to FIT DataFrame.
    
    Calculates:
    - Segment distance (haversine from GPS)
    - Time delta between points
    - Speed (m/s)
    - Pace (sec/km)
    - Cumulative distance
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from parse_fit() with latitude/longitude columns
        
    Returns
    -------
    pd.DataFrame
        DataFrame with additional columns:
        - dist : float (segment distance in metres)
        - dt : float (time delta in seconds)
        - speed_mps : float (speed in m/s)
        - pace_sec_km : float (pace in seconds per km)
        - distance_cumulative_km : float (cumulative distance in km)
        
    Notes
    -----
    - Uses haversine formula for GPS distance calculation
    - Requires latitude and longitude columns
    - First point has dist=0, dt=0
    """
    from biosystems.ingestion.gpx import _haversine
    
    df = df.copy()
    
    # Check required columns
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        raise ValueError("DataFrame must have 'latitude' and 'longitude' columns")
    
    # Calculate elapsed time between points
    df['time_prev'] = df.index.to_series().shift(1)
    df['dt'] = (df.index - df['time_prev']).dt.total_seconds().fillna(0)
    
    # Calculate segment distances using haversine
    seg_dist = [0.0] + [
        _haversine(
            df['latitude'].iloc[i - 1],
            df['longitude'].iloc[i - 1],
            df['latitude'].iloc[i],
            df['longitude'].iloc[i],
        )
        for i in range(1, len(df))
    ]
    df['dist'] = seg_dist
    
    # Calculate speed (m/s)
    df['speed_mps'] = df['dist'] / df['dt'].replace(0, np.nan)
    df['speed_mps'] = df['speed_mps'].bfill()  # Backfill first point
    
    # Calculate pace (sec/km)
    df['pace_sec_km'] = 1000 / df['speed_mps'].replace(0, np.nan)
    
    # Calculate cumulative distance (km)
    df['distance_cumulative_km'] = df['dist'].cumsum() / 1000.0
    
    # Clean up temporary columns
    df = df.drop(columns=['time_prev'])
    
    return df
