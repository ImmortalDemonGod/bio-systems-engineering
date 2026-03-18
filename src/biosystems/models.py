"""
Data Contracts for Bio-Systems Engineering
===========================================

This module defines the core data structures using Pydantic for runtime validation
and clean API contracts between components.

All metrics, configurations, and contexts are defined here to ensure type safety
and documentation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
    bpm: tuple[int, int] = Field(..., description="(lower, upper) HR bounds in bpm")
    pace_min_per_km: tuple[float, float] = Field(..., description="(lower, upper) pace in min/km")

    @field_validator("bpm")
    @classmethod
    def validate_bpm_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Ensure HR bounds are valid (lower < upper, both positive)."""
        if v[0] >= v[1]:
            raise ValueError(f"Lower HR ({v[0]}) must be less than upper HR ({v[1]})")
        if v[0] < 0 or v[1] <= 0:
            raise ValueError("Heart rate values must be non-negative (lower) and positive (upper)")
        return v

    @field_validator("pace_min_per_km")
    @classmethod
    def validate_pace_range(cls, v: tuple[float, float]) -> tuple[float, float]:
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
    max_hr: int | None = Field(None, gt=0, description="Max HR in bpm")
    zones: dict[str, HeartRateZone] = Field(..., description="Zone definitions")

    @field_validator("threshold_hr")
    @classmethod
    def validate_threshold_above_resting(cls, v: int, info) -> int:
        """Ensure threshold HR is higher than resting HR."""
        if "resting_hr" in info.data and v <= info.data["resting_hr"]:
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

    temperature_c: float | None = Field(default=None, description="Temperature in °C")
    weather_code: int | None = Field(default=None, description="WMO weather code")
    weather_description: str | None = Field(default=None, description="Weather description")
    rest_hr: int | None = Field(default=None, gt=0, description="Resting HR in bpm")
    sleep_score: float | None = Field(default=None, ge=0, le=100, description="Sleep score 0-100")
    hrv_rmssd: float | None = Field(default=None, gt=0, description="HRV RMSSD in ms")


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
    avg_cadence: int | None = Field(None, gt=0)
    gap_min_per_km: float | None = Field(None, gt=0, description="Grade Adjusted Pace")
    gap_quality_note: str | None = Field(None, description="Set when GAP was suppressed due to bad elevation data")
    context: RunContext | None = None

    @field_validator("decoupling_pct")
    @classmethod
    def validate_decoupling_reasonable(cls, v: float) -> float:
        """Accept any decoupling value; callers inspect the field directly."""
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
    file_source: str | None = None


class KmSplit(BaseModel):
    """Per-kilometer split from Strava's splits_metric."""

    km: int  # 1-based km number
    distance_m: float
    elapsed_time_s: int
    moving_time_s: int
    pace_min_per_km: float  # derived from average_speed
    gap_pace_min_per_km: float | None  # derived from average_grade_adjusted_speed
    avg_hr: float | None
    elevation_diff_m: float | None
    pace_zone: int | None


class Lap(BaseModel):
    """A lap as recorded by the watch lap button."""

    lap_index: int
    distance_m: float
    elapsed_time_s: int
    moving_time_s: int
    pace_min_per_km: float
    avg_hr: float | None
    max_hr: float | None
    avg_cadence: float | None  # steps/min (doubled from Strava single-foot)
    elevation_gain_m: float | None
    pace_zone: int | None


class BestEffort(BaseModel):
    """
    A Strava-detected best effort for a standard distance within a run.

    Attributes
    ----------
    name : str
        Distance name (e.g. "400m", "1/2 mile", "1 mile", "5K", "10K")
    distance_m : float
        Actual segment distance in metres
    elapsed_time_s : int
        Wall-clock time for the effort in seconds
    moving_time_s : int
        Moving time (pauses excluded) in seconds
    pr_rank : int or None
        1 = all-time PR, 2 = 2nd best, None = not a top-10 effort
    start_offset_s : int or None
        Seconds from activity start
    """

    name: str
    distance_m: float
    elapsed_time_s: int
    moving_time_s: int
    pr_rank: int | None = None
    start_offset_s: int | None = None


class BlockBest(BaseModel):
    """A best-effort for a standard distance within our own tracking window."""

    name: str  # "1K", "1mi", "5K", etc.
    elapsed_time_s: int
    pace_min_per_km: float  # derived
    prev_best_s: int | None  # previous best in history, None if first ever recorded
    improvement_s: int | None  # positive = faster than prev best
    window_days: int | None  # None = all recorded history
    is_new_best: bool


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
    avg_hr: float | None = Field(None, gt=0)
    avg_cad: float | None = Field(None, gt=0)
    tag: str = Field(..., pattern="^(warm-up|mid-session|cool-down|pause)$")


class ZoneTimeEntry(BaseModel):
    """Time spent in a single training zone."""
    zone: str
    seconds: float
    percent: float


class WalkSummary(BaseModel):
    """Aggregate statistics for all walk segments in a session."""
    segment_count: int
    total_time_s: float
    total_time_pct: float
    total_distance_km: float
    avg_pace_min_km: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    avg_cadence: float | None = None
    avg_hr_recovery_bpm_per_s: float | None = None


class StrideSegment(BaseModel):
    """A detected fast stride burst within a run."""
    segment_id: int = Field(..., gt=0)
    start_ts: str
    duration_s: float
    avg_pace_min_km: float
    avg_hr: float | None = None


class RunDynamics(BaseModel):
    """Within-run dynamics: HR drift, pace strategy, HR/pace correlation."""
    first_half_hr: float
    second_half_hr: float
    hr_drift_pct: float
    first_half_pace_min_km: float
    second_half_pace_min_km: float
    pace_strategy: str  # "positive", "negative", or "even"
    hr_pace_correlation: float | None = None


class DistributionStats(BaseModel):
    """Percentile distribution summary for a metric."""
    mean: float
    std: float
    min: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    max: float


class FullRunReport(BaseModel):
    """
    Comprehensive run report combining session and run-only metrics,
    zone distributions, walk detail, dynamics, strides, and distributions.

    This is the primary output of the bio-systems Strava pipeline.
    """
    activity_name: str | None = None
    start_time: str | None = None

    # Dual-mode: full session vs walk-filtered run
    session: PhysiologicalMetrics
    run_only: PhysiologicalMetrics

    # Improvements over original system
    ef_grade_adjusted: float | None = Field(None, description="GAP-speed / avg_hr")
    gap_quality_note: str | None = Field(None, description="Set when EF_GAP was suppressed due to bad elevation data")
    ef_reliability_cv: float | None = Field(None, description="CV of instantaneous EF — lower = steadier effort")
    aev_pace_min_per_km: float | None = Field(None, description="Pace at reference HR (aerobic efficiency velocity)")
    aev_ref_hr: int | None = Field(None, description="Reference HR used for AeV calculation")

    # Zone time distributions (run-only)
    zone_hr: list[ZoneTimeEntry] = Field(default_factory=list)
    zone_pace: list[ZoneTimeEntry] = Field(default_factory=list)

    # Walk analysis
    walk_summary: WalkSummary | None = None
    walk_segments: list[dict] = Field(default_factory=list)

    # Within-run dynamics
    dynamics: RunDynamics | None = None

    # Stride detection
    strides: list[StrideSegment] = Field(default_factory=list)

    # Statistical distributions (run-only)
    hr_distribution: DistributionStats | None = None
    pace_distribution: DistributionStats | None = None
    cadence_distribution: DistributionStats | None = None

    # Physical
    elevation_gain_m: float | None = None

    # Per-km splits
    splits_km: list[KmSplit] = Field(default_factory=list)

    # Lap button splits (if used)
    laps: list[Lap] = Field(default_factory=list)

    # Activity-level metadata from Strava
    max_hr: float | None = None
    max_speed_mps: float | None = None
    calories: float | None = None
    perceived_exertion: float | None = None
    workout_type: str | None = None  # "race", "long_run", "workout", or None
    device_name: str | None = None
    description: str | None = None

    # Personal records / best efforts (from Strava)
    best_efforts: list[BestEffort] = Field(default_factory=list)

    # Own training-block bests (replaces/supplements Strava all-time best_efforts)
    block_bests: list[BlockBest] = Field(default_factory=list)

    # Context
    context: RunContext | None = None


# Type aliases for convenience
ZoneDict = dict[str, HeartRateZone]
# Final polish
