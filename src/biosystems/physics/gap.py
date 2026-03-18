"""
Grade Adjusted Pace (GAP) Calculation
======================================

Implements Minetti et al.'s equation for normalizing running pace based on
grade (slope). This allows fair comparison of performance across different
terrains.

Reference:
Minetti, A. E., Moia, C., Roi, G. S., Susta, D., & Ferretti, G. (2002).
Energy cost of walking and running at extreme uphill and downhill slopes.
Journal of Applied Physiology, 93(3), 1039-1046.
"""

from typing import cast

import numpy as np
import pandas as pd


def calculate_grade_percent(elevation_gain_m: float, distance_m: float) -> float:
    """
    Calculate grade as a percentage.

    Parameters
    ----------
    elevation_gain_m : float
        Elevation gain in metres
    distance_m : float
        Horizontal distance in metres

    Returns
    -------
    float
        Grade as percentage (positive for uphill, negative for downhill)
    """
    if distance_m == 0:
        return 0.0
    return (elevation_gain_m / distance_m) * 100


def minetti_energy_cost(grade_percent: float) -> float:
    """
    Calculate relative energy cost based on grade using Minetti's equation.

    Minetti's equation models the energy cost of running on slopes.
    The cost is normalized to flat running (grade = 0).

    Parameters
    ----------
    grade_percent : float
        Grade as percentage (e.g., 5.0 for 5% uphill, -3.0 for 3% downhill)

    Returns
    -------
    float
        Relative energy cost multiplier (1.0 = flat running)

    Notes
    -----
    The equation is:
    EC(i) = 155.4 * i^5 - 30.4 * i^4 - 43.3 * i^3 + 46.3 * i^2 + 19.5 * i + 3.6

    Where i is grade as a decimal (grade_percent / 100)

    For flat running (i=0), EC = 3.6 (baseline)
    """
    # Clamp to Minetti's valid domain. The 5th-degree polynomial diverges rapidly
    # outside ±45% grade: at i=-1 (100% descent) ec = -112, yielding a negative
    # energy multiplier that would make GAP negative. GPS altimeter glitches
    # (tunnel dropout, barometric spike) can produce apparent grades far beyond
    # real terrain, so clamping is a mandatory guard, not just a nicety.
    clamped = max(min(grade_percent, 45.0), -45.0)
    i = clamped / 100.0

    # Minetti's polynomial equation for energy cost
    ec = 155.4 * i**5 - 30.4 * i**4 - 43.3 * i**3 + 46.3 * i**2 + 19.5 * i + 3.6

    # Normalize to flat running (EC at i=0 is 3.6)
    return ec / 3.6


def calculate_gap_segment(pace_sec_km: float, grade_percent: float) -> float:
    """
    Calculate Grade Adjusted Pace for a single segment.

    GAP adjusts your actual pace to what it would be on flat ground,
    accounting for the extra energy cost of hills.

    Parameters
    ----------
    pace_sec_km : float
        Actual pace in seconds per kilometer
    grade_percent : float
        Grade as percentage (positive for uphill, negative for downhill)

    Returns
    -------
    float
        Grade adjusted pace in seconds per kilometer

    Examples
    --------
    >>> # Running 5:00/km pace on 5% uphill
    >>> gap = calculate_gap_segment(300, 5.0)
    >>> # GAP will be faster (lower number) than actual pace
    >>> gap < 300
    True

    >>> # Running 5:00/km on flat
    >>> gap = calculate_gap_segment(300, 0.0)
    >>> gap == 300
    True
    """
    # Get energy cost multiplier
    energy_multiplier = minetti_energy_cost(grade_percent)

    # Adjust pace: higher energy cost = effectively faster pace
    # If uphill costs 1.5x energy, GAP should be 1.5x faster (lower pace number)
    gap_sec_km = pace_sec_km / energy_multiplier

    return gap_sec_km


def calculate_gap_from_dataframe(
    df: pd.DataFrame, pace_col: str = "pace_sec_km", ele_col: str = "ele", dist_col: str = "dist"
) -> pd.Series:
    """
    Calculate Grade Adjusted Pace for entire activity DataFrame.

    Calculates grade for each segment based on elevation change and distance,
    then applies Minetti's equation to adjust pace.

    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame with elevation and pace data
    pace_col : str
        Name of pace column (seconds per km)
    ele_col : str
        Name of elevation column (metres)
    dist_col : str
        Name of distance column (metres per segment)

    Returns
    -------
    pd.Series
        Grade adjusted pace for each point (seconds per km)

    Notes
    -----
    - First point has no grade (uses actual pace)
    - Grade is calculated from smoothed elevation to suppress GPS noise
    - Raw GPS elevation accuracy is ±5-10m; noise is amplified by the 5th-degree
      polynomial at steep apparent grades. A 5-point rolling average is applied
      before differencing, preserving real terrain features while eliminating jitter.
    - Handles NaN values gracefully
    """
    # Initialize with actual pace
    gap = df[pace_col].copy()

    # Smooth elevation before differencing to suppress GPS vertical noise.
    # Raw GPS elevation has ±5-10m accuracy; unsmoothed diffs produce spurious
    # grades that Minetti's polynomial amplifies into unrealistic adjustments.
    ele_smoothed = df[ele_col].rolling(window=5, min_periods=1, center=True).mean()

    # Calculate elevation change between smoothed points
    ele_diff = ele_smoothed.diff()

    # Calculate grade for each segment
    grades = []
    for i in range(len(df)):
        ele_val = cast(float, ele_diff.iloc[i])
        dist_val = cast(float, df[dist_col].iloc[i])
        if i == 0 or pd.isna(ele_val) or dist_val == 0:
            grades.append(0.0)
        else:
            grade_pct = calculate_grade_percent(ele_val, dist_val)
            grades.append(grade_pct)

    # Apply Minetti adjustment
    for i in range(len(df)):
        gap_val = cast(float, gap.iloc[i])
        if not pd.isna(gap_val) and grades[i] != 0:
            gap.iloc[i] = calculate_gap_segment(gap_val, grades[i])

    return gap


def calculate_average_gap(
    df: pd.DataFrame,
    pace_col: str = "pace_sec_km",
    ele_col: str = "ele",
    dist_col: str = "dist",
    dt_col: str = "dt",
) -> float:
    """
    Calculate time-weighted average Grade Adjusted Pace for entire activity.

    This provides a single GAP metric for the whole run, properly weighted
    by the time spent at each pace.

    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame
    pace_col : str
        Pace column name
    ele_col : str
        Elevation column name
    dist_col : str
        Distance column name
    dt_col : str
        Delta time column name (seconds)

    Returns
    -------
    float
        Average GAP in seconds per kilometer, or NaN if calculation fails

    Notes
    -----
    Uses time-weighted average to account for varying segment durations.
    """
    # Calculate GAP for each segment
    gap_series = calculate_gap_from_dataframe(df, pace_col, ele_col, dist_col)

    # Filter out NaN values
    valid_mask = ~gap_series.isna() & ~df[dt_col].isna()

    if not valid_mask.any():
        return np.nan

    # Time-weighted average
    weights = df.loc[valid_mask, dt_col]
    values = gap_series.loc[valid_mask]

    avg_gap = np.average(values, weights=weights)

    return float(avg_gap)


def convert_gap_to_pace_adjustment(actual_pace_sec_km: float, gap_sec_km: float) -> dict:
    """
    Compare actual pace to GAP and provide interpretation.

    Parameters
    ----------
    actual_pace_sec_km : float
        Actual measured pace
    gap_sec_km : float
        Grade adjusted pace

    Returns
    -------
    dict
        Dictionary with:
        - actual_pace_min_km: float
        - gap_min_km: float
        - difference_sec_km: float (positive if GAP is faster)
        - effort_multiplier: float (GAP energy cost relative to actual)
        - interpretation: str
    """
    diff_sec = actual_pace_sec_km - gap_sec_km
    effort_mult = actual_pace_sec_km / gap_sec_km if gap_sec_km > 0 else 1.0

    if diff_sec > 30:  # More than 30 sec/km slower
        interp = "Significant uphill - GAP much faster than actual pace"
    elif diff_sec > 10:
        interp = "Moderate uphill - GAP faster than actual pace"
    elif diff_sec > -10:
        interp = "Relatively flat - GAP similar to actual pace"
    elif diff_sec > -30:
        interp = "Moderate downhill - GAP slower than actual pace"
    else:
        interp = "Significant downhill - GAP much slower than actual pace"

    return {
        "actual_pace_min_km": round(actual_pace_sec_km / 60, 2),
        "gap_min_km": round(gap_sec_km / 60, 2),
        "difference_sec_km": round(diff_sec, 1),
        "effort_multiplier": round(effort_mult, 3),
        "interpretation": interp,
    }
