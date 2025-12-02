"""
GPX File Parser
===============

Parses GPX (GPS Exchange Format) XML files into structured DataFrames.

This module handles the complexity of GPX namespace variations and robustly
extracts heart rate, cadence, power, and elevation data from various sources.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

# Earth radius for haversine distance calculations
EARTH_RADIUS_M = 6_371_000  # mean Earth radius in metres

VERBOSE = False  # Set to True for debug output


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance in metres between two WGS-84 points.
    
    Uses the haversine formula for accurate distance calculation on a sphere.
    
    Parameters
    ----------
    lat1, lon1 : float
        Latitude and longitude of first point (degrees)
    lat2, lon2 : float
        Latitude and longitude of second point (degrees)
        
    Returns
    -------
    float
        Distance in metres
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_gpx(path: Union[str, Path]) -> pd.DataFrame:
    """
    Parse a GPX file into a tidy, chronologically sorted DataFrame.
    
    This parser robustly handles:
    - Garmin GPX namespace variations
    - Missing heart rate, cadence, or power data
    - Non-namespaced GPX files (fallback)
    - Multiple power data locations in extensions
    
    Parameters
    ----------
    path : str or Path
        Path to the GPX file
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - time : pandas.Timestamp (UTC)
        - lat : float (degrees)
        - lon : float (degrees)
        - ele : float (metres, NaN if absent)
        - hr : int (bpm, NaN if absent)
        - cadence : int (spm, NaN if absent)
        - power : int (watts, NaN if absent)
        - dt : float (seconds since previous point)
        - dist : float (segment distance in metres)
        - speed_mps : raw speed (m/s)
        - speed_mps_smooth : 5-point rolling average (m/s)
        - pace_sec_km : smoothed pace (seconds per km)
        
    Raises
    ------
    ValueError
        If no trackpoints are found in the GPX file
    """
    # GPX namespaces (Garmin extensions)
    ns = {
        "g": "http://www.topografix.com/GPX/1/1",
        "gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
    }
    
    rows = []
    root = ET.parse(str(path)).getroot()
    debug_hr = []  # For debug output
    
    # Parse namespaced GPX
    for i, pt in enumerate(root.findall(".//g:trkpt", ns)):
        lat, lon = float(pt.attrib["lat"]), float(pt.attrib["lon"])
        
        # Elevation
        ele_node = pt.find("g:ele", ns)
        ele = float(ele_node.text) if ele_node is not None else np.nan
        
        # Timestamp (required)
        ts = pd.to_datetime(pt.find("g:time", ns).text, utc=True)
        
        # Heart rate (from Garmin extensions)
        hr_node = pt.find(".//gpxtpx:hr", ns)
        if hr_node is not None:
            hr_val = int(hr_node.text)
            hr = hr_val if hr_val > 0 else np.nan
        else:
            hr = np.nan
            
        # Debug first 5 points
        if i < 5:
            debug_hr.append((i, hr, hr_node.text if hr_node is not None else None))
            if VERBOSE:
                debug_ele = float(ele_node.text) if ele_node is not None else None
                print(f"[DEBUG] trkpt {i}: ele={debug_ele}")
        
        # Cadence
        cad_node = pt.find(".//gpxtpx:cad", ns)
        cad = int(cad_node.text) if cad_node is not None else np.nan
        
        # Power (try multiple locations - different devices put it in different places)
        power = np.nan
        # 1. Direct child of trkpt (no namespace)
        power_node = pt.find("power")
        if power_node is not None and power_node.text is not None:
            power = int(power_node.text)
        # 2. Direct child with namespace
        if np.isnan(power):
            power_node = pt.find(".//power", ns)
            if power_node is not None and power_node.text is not None:
                power = int(power_node.text)
        # 3. Garmin extension namespace
        if np.isnan(power):
            power_node = pt.find(".//gpxtpx:power", ns)
            if power_node is not None and power_node.text is not None:
                power = int(power_node.text)
        # 4. Inside extensions (various formats)
        if np.isnan(power):
            ext = pt.find("extensions")
            if ext is not None:
                for child in ext:
                    if child.tag.endswith('power') and child.text is not None:
                        try:
                            power = int(child.text)
                            if i < 3 and VERBOSE:
                                print(f"[DEBUG][POWER FOUND] trkpt {i}: {child.tag} -> {power}")
                            break
                        except Exception as e:
                            if i < 3 and VERBOSE:
                                print(f"[DEBUG][POWER ERROR] trkpt {i}: {child.tag}, error: {e}")
        
        rows.append((ts, lat, lon, ele, hr, cad, power))
    
    if debug_hr and VERBOSE:
        print("[DEBUG] First 5 HR values parsed:", debug_hr)
    
    # Fallback: handle un-namespaced GPX files
    if not rows:
        for i, pt in enumerate(root.findall(".//trkpt")):
            lat = float(pt.attrib.get("lat", 0))
            lon = float(pt.attrib.get("lon", 0))
            ele_node = pt.find("ele")
            ele = float(ele_node.text) if ele_node is not None else np.nan
            time_node = pt.find("time")
            ts = pd.to_datetime(time_node.text, utc=True) if time_node is not None else pd.NaT
            # HR and cadence unlikely in non-namespaced files
            hr = np.nan
            cad = np.nan
            rows.append((ts, lat, lon, ele, hr, cad, np.nan))
    
    if not rows:
        raise ValueError(f"No <trkpt> found in {path}")
    
    # Create DataFrame
    df = (
        pd.DataFrame(rows, columns=["time", "lat", "lon", "ele", "hr", "cadence", "power"])
        .sort_values("time")
        .reset_index(drop=True)
    )
    
    if VERBOSE:
        print("[DEBUG] HR column (raw, before fill/interp):")
        print(df["hr"].describe())
        print(df["hr"].head(10))
    
    # Calculate elapsed time between points
    df["dt"] = df["time"].diff().dt.total_seconds().fillna(0)
    
    # Calculate great-circle distance for each segment
    seg_dist = [0.0] + [
        _haversine(
            df.at[i - 1, "lat"],
            df.at[i - 1, "lon"],
            df.at[i, "lat"],
            df.at[i, "lon"],
        )
        for i in range(1, len(df))
    ]
    df["dist"] = seg_dist
    
    # Calculate instantaneous and smoothed speed
    df["speed_mps"] = df["dist"] / df["dt"].replace(0, np.nan)
    df["speed_mps"] = df["speed_mps"].bfill()  # Backfill first point
    df["speed_mps_smooth"] = (
        df["speed_mps"].rolling(window=5, center=True, min_periods=1).mean()
    )
    
    # Calculate pace (sec/km) from smoothed speed
    df["pace_sec_km"] = 1000 / df["speed_mps_smooth"].replace(0, np.nan)
    
    if VERBOSE:
        print("[DEBUG] Power column (raw, after parsing):")
        print(df["power"].describe())
        print(df["power"].head(10))
    
    return df
