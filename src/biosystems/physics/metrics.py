"""
Physiological Metrics Calculations
===================================

Core algorithms for calculating running performance metrics including:
- Efficiency Factor (EF): Speed / Heart Rate
- Aerobic Decoupling: HR drift over time
- Training Stress Score (TSS): Quantified training load
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from biosystems.models import PhysiologicalMetrics, RunContext, ZoneConfig
from biosystems.physics.gap import calculate_average_gap


def _as_series(arr: Any) -> pd.Series:
    """Convert array to pandas Series if not already."""
    return pd.Series(arr) if not isinstance(arr, pd.Series) else arr


def lower_z2_bpm(zone_config: ZoneConfig) -> int:
    """
    Get the lower BPM boundary of Zone 2 (Aerobic).

    Parameters
    ----------
    zone_config : ZoneConfig
        Zone configuration

    Returns
    -------
    int
        Lower BPM bound of Z2
    """
    for name, zone in zone_config.zones.items():
        if "Z2" in name or "Aerobic" in name:
            return zone.bpm[0]
    raise ValueError("No Z2 (Aerobic) zone found in configuration")


def compute_training_zones(
    hr_array: pd.Series, pace_array: pd.Series, zone_config: ZoneConfig
) -> tuple[pd.Series, pd.Series, list[Any]]:
    """
    Classify each data point into training zones based on HR and pace.

    Parameters
    ----------
    hr_array : pd.Series
        Heart rate values (bpm)
    pace_array : pd.Series
        Pace values (sec/km or min/km)
    zone_config : ZoneConfig
        Zone configuration

    Returns
    -------
    zone_hr : pd.Series
        Zone classification by heart rate
    zone_pace : pd.Series
        Zone classification by pace
    zone_effective : list
        Effective zone (HR if match, otherwise "mixed")
    """
    hr_array = _as_series(hr_array)
    pace_array = _as_series(pace_array)

    def zone_hr(hr: float) -> str | None:
        if np.isnan(hr):
            return None
        for name, zone in zone_config.zones.items():
            lo, hi = zone.bpm
            if lo <= hr <= hi:
                return name
        return None

    # Convert pace to min/km if in sec/km
    # Use median-based check to avoid GPS spikes breaking logic
    if pace_array.median() > 20:  # ≈ sec/km
        pace_min = pace_array / 60
    else:
        pace_min = pace_array

    def zone_pace(pace: float) -> str | None:
        if np.isnan(pace):
            return None
        for name, zone in zone_config.zones.items():
            lo, hi = zone.pace_min_per_km
            if lo <= pace <= hi:
                return name
        return None

    zone_hr_col = hr_array.apply(zone_hr)
    zone_pace_col = pace_min.apply(zone_pace)

    def zone_effective(hr: str | None, pace: str | None) -> str | None:
        if hr and pace:
            return hr if hr == pace else "mixed"
        return hr or pace

    zone_effective_col = [zone_effective(h, p) for h, p in zip(zone_hr_col, zone_pace_col)]

    return zone_hr_col, zone_pace_col, zone_effective_col


def calculate_efficiency_factor(df: pd.DataFrame, zone_config: ZoneConfig) -> float:
    """
    Calculate Efficiency Factor: avg speed / avg heart rate.

    This is THE KEY METRIC for aerobic efficiency. Higher is better.

    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame with 'dist', 'dt', 'hr' columns
    zone_config : ZoneConfig
        Zone configuration (for Z2 filtering)

    Returns
    -------
    float
        Efficiency factor (m/s per bpm)
    """
    # Strip walk segments when the pipeline has classified them
    base_df = df[~df["is_walk"].astype(bool)] if "is_walk" in df.columns else df

    # Drop rows with missing HR before filtering — prevents silent exclusion of
    # distance covered during sensor dropouts
    hr_df = base_df.dropna(subset=["hr"])

    # Filter to "work" data (above Z2 lower bound) to exclude warm-up
    lz2 = lower_z2_bpm(zone_config)
    work_df = hr_df[hr_df["hr"] >= lz2]

    # If insufficient work data, use full HR-valid dataset
    if work_df.empty or len(work_df) < 120:  # < 2 min
        work_df = hr_df if not hr_df.empty else base_df

    total_dist_m = float(work_df["dist"].sum())
    secs = float(work_df["dt"].sum())
    avg_hr = float(work_df["hr"].mean())
    avg_speed = total_dist_m / secs  # m/s

    return float(avg_speed / avg_hr)


def calculate_decoupling(df: pd.DataFrame, zone_config: ZoneConfig) -> float:
    """
    Calculate aerobic decoupling (Pa:HR drift).

    This measures HR drift over the course of a run. Higher values indicate
    poor aerobic fitness or fatigue.

    Interpretation:
    - < 5%: Strong aerobic base
    - 5-10%: Borderline
    - > 10%: Significant drift (poor durability)

    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame with 'dist', 'dt', 'hr' columns
    zone_config : ZoneConfig
        Zone configuration (for Z2 filtering)

    Returns
    -------
    float
        Decoupling percentage
    """
    # Strip walk segments when the pipeline has classified them
    base_df = df[~df["is_walk"].astype(bool)] if "is_walk" in df.columns else df

    # Drop rows with missing HR before filtering
    hr_df = base_df.dropna(subset=["hr"])

    # Filter to "work" data (above Z2 lower bound)
    lz2 = lower_z2_bpm(zone_config)
    work_df = hr_df[hr_df["hr"] >= lz2]

    # If insufficient work data, use full HR-valid dataset
    if work_df.empty or len(work_df) < 120:  # < 2 min
        work_df = hr_df if not hr_df.empty else base_df

    # Split by cumulative elapsed time so the midpoint is always temporal,
    # regardless of whether the index is a DatetimeIndex (Strava) or an
    # integer RangeIndex (GPX/FIT). Index arithmetic on integers counts
    # samples, not seconds — wrong when sampling rate is non-uniform or the
    # watch auto-paused.
    elapsed = work_df["dt"].cumsum()
    midpoint_s = elapsed.iloc[-1] / 2.0
    first_half = work_df[elapsed <= midpoint_s]
    second_half = work_df[elapsed > midpoint_s]

    # Calculate EF for each half
    ef_1 = (
        float(first_half["dist"].sum())
        / float(first_half["dt"].sum())
        / float(first_half["hr"].mean())
    )
    ef_2 = (
        float(second_half["dist"].sum())
        / float(second_half["dt"].sum())
        / float(second_half["hr"].mean())
    )

    # Decoupling is the % change in EF
    decouple_pct = abs(ef_2 - ef_1) / ef_1 * 100

    return float(decouple_pct)


def calculate_hr_tss(df: pd.DataFrame, zone_config: ZoneConfig) -> float:
    """
    Calculate heart rate-based Training Stress Score.

    This is a proxy for TrainingPeaks TSS using HR instead of power.
    A score of 100 ≈ 1 hour at threshold.

    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame with 'dt', 'hr' columns
    zone_config : ZoneConfig
        Zone configuration with resting_hr and threshold_hr

    Returns
    -------
    float
        Training Stress Score
    """
    secs = float(df["dt"].sum())
    avg_hr = float(df["hr"].mean())

    intensity_factor = (avg_hr - zone_config.resting_hr) / (
        zone_config.threshold_hr - zone_config.resting_hr
    )
    hr_tss = secs * intensity_factor**2 / 36

    return float(hr_tss)


def run_metrics(
    df: pd.DataFrame, zone_config: ZoneConfig, context: RunContext | None = None
) -> PhysiologicalMetrics:
    """
    Compute all headline metrics for a single steady-state run.

    This is the primary analysis function that calculates:
    - Efficiency Factor (EF)
    - Aerobic Decoupling
    - Training Stress Score (TSS)
    - Zone distributions

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from parse_gpx() with columns: dist, dt, hr, pace_sec_km, etc.
    zone_config : ZoneConfig
        Heart rate zone configuration
    context : RunContext, optional
        Environmental and wellness context

    Returns
    -------
    PhysiologicalMetrics
        Complete metrics object with all calculated values

    Notes
    -----
    - Efficiency Factor (EF) = avg speed (m/s) ÷ avg HR (bpm)
    - Aerobic decoupling is |EF² – EF¹| / EF¹ expressed as %
    - hrTSS scales like TrainingPeaks TSS (100 ≈ 1 h at threshold)
    """
    # Basic statistics
    total_dist_m = float(df["dist"].sum())
    secs = float(df["dt"].sum())
    avg_hr = float(df["hr"].mean())
    avg_speed = total_dist_m / secs  # m/s
    avg_pace = 1000 / avg_speed / 60  # min/km

    # Calculate primary metrics
    ef = calculate_efficiency_factor(df, zone_config)
    decouple_pct = calculate_decoupling(df, zone_config)
    hr_tss = calculate_hr_tss(df, zone_config)

    # Optionally calculate zone distributions (adds columns to df)
    zone_hr, zone_pace, zone_effective = compute_training_zones(
        df["hr"], df["pace_sec_km"], zone_config
    )
    df["zone_hr"] = zone_hr
    df["zone_pace"] = zone_pace
    df["zone_effective"] = zone_effective

    # Calculate average cadence if available
    avg_cadence = None
    if "cadence" in df.columns:
        cadence_series = df["cadence"].replace(0, np.nan)
        if not cadence_series.isna().all():
            avg_cadence = int(cadence_series.mean())

    # Calculate Grade Adjusted Pace if elevation data available
    gap_min_per_km = None
    if "ele" in df.columns and "pace_sec_km" in df.columns and "dist" in df.columns:
        # Check if we have valid elevation data
        ele_series = df["ele"].replace(0, np.nan)
        if not ele_series.isna().all():
            try:
                gap_sec_km = calculate_average_gap(
                    df, pace_col="pace_sec_km", ele_col="ele", dist_col="dist", dt_col="dt"
                )
                if not np.isnan(gap_sec_km):
                    gap_min_per_km = round(gap_sec_km / 60, 2)
            except Exception:
                # If GAP calculation fails, leave as None
                pass

    return PhysiologicalMetrics(
        distance_km=round(total_dist_m / 1_000, 2),
        duration_min=round(secs / 60, 1),
        avg_pace_min_per_km=round(avg_pace, 2),
        avg_hr=round(avg_hr, 1),
        efficiency_factor=round(ef, 5),
        decoupling_pct=round(decouple_pct, 2),
        hr_tss=round(hr_tss, 1),
        avg_cadence=avg_cadence,
        gap_min_per_km=gap_min_per_km,
        context=context,
    )
