"""
Data Contracts for Bio-Systems Engineering
===========================================

This module defines the core data structures using Pydantic for runtime validation
and clean API contracts between components.

All metrics, configurations, and contexts are defined here to ensure type safety
and documentation.
"""

from typing import Optional, Dict, Tuple
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class HeartRateZone(BaseModel):
    """
    Definition of a single heart rate training zone.
    
    Attributes
    ----------
    name : str
        Zone name (e.g., "Z2 (Aerobic)")
    bpm : Tuple[int, int]
        (lower, upper) heart rate bounds in beats per minute
    pace_min_per_km : Tuple[float, float]
        (lower, upper) pace bounds in minutes per kilometer
    """
    name: str
    bpm: Tuple[int, int] = Field(..., description="(lower, upper) HR bounds in bpm")
    pace_min_per_km: Tuple[float, float] = Field(..., description="(lower, upper) pace in min/km")
    
    @field_validator('bpm')
    @classmethod
    def validate_bpm_range(cls, v: Tuple[int, int]) -> Tuple[int, int]:
        """Ensure HR bounds are valid (lower < upper, both positive)."""
        if v[0] >= v[1]:
            raise ValueError(f"Lower HR ({v[0]}) must be less than upper HR ({v[1]})")
        if v[0] < 0 or v[1] < 0:
            raise ValueError("Heart rate values must be positive")
        return v
    
    @field_validator('pace_min_per_km')
    @classmethod
    def validate_pace_range(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        """Ensure pace bounds are valid (lower < upper, both positive)."""
        if v[0] >= v[1]:
            raise ValueError(f"Lower pace ({v[0]}) must be less than upper pace ({v[1]})")
        if v[0] < 0 or v[1] < 0:
            raise ValueError("Pace values must be positive")
        return v


class ZoneConfig(BaseModel):
    """
    Complete heart rate zone configuration for an athlete.
    
    Attributes
    ----------
    resting_hr : int
        Morning resting heart rate in bpm
    threshold_hr : int
        Lactate threshold heart rate in bpm
    max_hr : int, optional
        Maximum heart rate in bpm
    zones : Dict[str, HeartRateZone]
        Dictionary of zone definitions (e.g., {"Z2": HeartRateZone(...)})
    """
    resting_hr: int = Field(..., gt=0, description="Resting HR in bpm")
    threshold_hr: int = Field(..., gt=0, description="Lactate threshold HR in bpm")
    max_hr: Optional[int] = Field(None, gt=0, description="Max HR in bpm")
    zones: Dict[str, HeartRateZone] = Field(..., description="Zone definitions")
    
    @field_validator('threshold_hr')
    @classmethod
    def validate_threshold_above_resting(cls, v: int, info) -> int:
        """Ensure threshold HR is higher than resting HR."""
        if 'resting_hr' in info.data and v <= info.data['resting_hr']:
            raise ValueError("Threshold HR must be greater than resting HR")
        return v


class RunContext(BaseModel):
    """
    Environmental and physiological context for a run.
    
    This optional metadata enriches analysis by providing context like weather
    conditions and wellness state.
    
    Attributes
    ----------
    temperature_c : float, optional
        Ambient temperature in Celsius
    weather_code : int, optional
        WMO weather code (0=clear, 61=rain, etc.)
    weather_description : str, optional
        Human-readable weather description
    rest_hr : int, optional
        Morning resting heart rate (bpm) on run day
    sleep_score : float, optional
        Sleep quality score (0-100)
    hrv_rmssd : float, optional
        Heart Rate Variability RMSSD in ms
    """
    temperature_c: Optional[float] = Field(None, description="Temperature in °C")
    weather_code: Optional[int] = Field(None, description="WMO weather code")
    weather_description: Optional[str] = Field(None, description="Weather description")
    rest_hr: Optional[int] = Field(None, gt=0, description="Resting HR in bpm")
    sleep_score: Optional[float] = Field(None, ge=0, le=100, description="Sleep score 0-100")
    hrv_rmssd: Optional[float] = Field(None, gt=0, description="HRV RMSSD in ms")


class PhysiologicalMetrics(BaseModel):
    """
    Core physiological metrics for a single run.
    
    These are the primary outputs of the bio-systems pipeline.
    
    Attributes
    ----------
    distance_km : float
        Total distance covered in kilometers
    duration_min : float
        Total duration in minutes
    avg_pace_min_per_km : float
        Average pace in minutes per kilometer
    avg_hr : float
        Average heart rate in bpm
    efficiency_factor : float
        Speed / Heart Rate (m/s / bpm)
    decoupling_pct : float
        Aerobic decoupling percentage (HR drift)
    hr_tss : float
        Heart rate-based Training Stress Score
    avg_cadence : int, optional
        Average cadence in steps per minute
    gap_min_per_km : float, optional
        Grade Adjusted Pace in min/km
    context : RunContext, optional
        Environmental and wellness context
    """
    distance_km: float = Field(..., gt=0)
    duration_min: float = Field(..., gt=0)
    avg_pace_min_per_km: float = Field(..., gt=0)
    avg_hr: float = Field(..., gt=0)
    efficiency_factor: float = Field(..., gt=0)
    decoupling_pct: float = Field(...)
    hr_tss: float = Field(..., ge=0)
    avg_cadence: Optional[int] = Field(None, gt=0)
    gap_min_per_km: Optional[float] = Field(None, gt=0, description="Grade Adjusted Pace")
    context: Optional[RunContext] = None
    
    @field_validator('decoupling_pct')
    @classmethod
    def validate_decoupling_reasonable(cls, v: float) -> float:
        """Warn if decoupling is suspiciously high (>50%)."""
        if v > 50:
            import warnings
            warnings.warn(f"Decoupling {v:.1f}% is unusually high. Check data quality.")
        return v


class ActivitySummary(BaseModel):
    """
    Complete summary of a processed activity.
    
    Combines metrics with metadata for storage and reporting.
    
    Attributes
    ----------
    activity_id : str
        Unique identifier (e.g., "20250806_191120")
    timestamp : datetime
        Activity start time (UTC)
    activity_type : str
        Type of activity ("run", "walk", "mixed")
    metrics : PhysiologicalMetrics
        Calculated physiological metrics
    file_source : str, optional
        Original file path
    """
    activity_id: str
    timestamp: datetime
    activity_type: str = Field(..., pattern="^(run|walk|mixed)$")
    metrics: PhysiologicalMetrics
    file_source: Optional[str] = None


class WalkSegment(BaseModel):
    """
    A detected walking segment within an activity.
    
    Attributes
    ----------
    segment_id : int
        Segment number (1-indexed)
    start_offset_s : int
        Seconds from activity start
    end_offset_s : int
        Seconds from activity start
    duration_s : int
        Segment duration in seconds
    distance_km : float
        Distance covered in segment
    avg_pace_min_km : float
        Average pace in segment
    avg_hr : float, optional
        Average heart rate in segment
    tag : str
        Classification ("warm-up", "mid-session", "cool-down")
    """
    segment_id: int = Field(..., gt=0)
    start_offset_s: int = Field(..., ge=0)
    end_offset_s: int = Field(..., ge=0)
    duration_s: int = Field(..., gt=0)
    distance_km: float = Field(..., ge=0)
    avg_pace_min_km: float = Field(..., gt=0)
    avg_hr: Optional[float] = Field(None, gt=0)
    avg_cad: Optional[float] = Field(None, gt=0)
    tag: str = Field(..., pattern="^(warm-up|mid-session|cool-down|pause)$")


# Type aliases for convenience
ZoneDict = Dict[str, HeartRateZone]
