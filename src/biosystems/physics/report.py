"""
Run Report Builder
==================

Assembles a FullRunReport from a pipeline DataFrame and zone configuration.
This is the comprehensive output layer that replaces the minimal
PhysiologicalMetrics output for the Strava CLI command.

Improvements over the original cultivation system:
- Grade-adjusted EF (uses GAP speed instead of raw speed)
- EF reliability score (coefficient of variation of instantaneous EF)
- Aerobic Efficiency Velocity (pace at reference HR via linear regression)
- Time-based decoupling split (not sample-count based)
- Strava moving flag for walk detection (cleaner than pace threshold)
- HR recovery rate within walk segments
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from biosystems.models import (
    BestEffort,
    BlockBest,
    DistributionStats,
    FullRunReport,
    KmSplit,
    Lap,
    RunContext,
    RunDynamics,
    StrideSegment,
    WalkSummary,
    ZoneConfig,
    ZoneTimeEntry,
)
from biosystems.physics.metrics import compute_training_zones, lower_z2_bpm, run_metrics

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _percentile_stats(series: pd.Series) -> DistributionStats | None:
    """Compute percentile distribution stats for a numeric series."""
    clean = series.dropna()
    if len(clean) < 10:
        return None
    return DistributionStats(
        mean=round(float(clean.mean()), 2),
        std=round(float(clean.std()), 2),
        min=round(float(clean.min()), 2),
        p10=round(float(clean.quantile(0.10)), 2),
        p25=round(float(clean.quantile(0.25)), 2),
        p50=round(float(clean.quantile(0.50)), 2),
        p75=round(float(clean.quantile(0.75)), 2),
        p90=round(float(clean.quantile(0.90)), 2),
        max=round(float(clean.max()), 2),
    )


def _zone_time_distribution(
    zone_col: pd.Series, dt_col: pd.Series
) -> list[ZoneTimeEntry]:
    """Compute seconds and percent of run time spent in each zone."""
    total_s = float(dt_col.sum())
    if total_s == 0:
        return []
    entries = []
    for zone in sorted(zone_col.dropna().unique()):
        mask = zone_col == zone
        secs = float(dt_col[mask].sum())
        entries.append(
            ZoneTimeEntry(
                zone=zone,
                seconds=round(secs, 1),
                percent=round(secs / total_s * 100, 2),
            )
        )
    return entries


def _detect_strides(
    df: pd.DataFrame,
    pace_threshold_min_km: float = 4.5,
    min_dur_s: float = 6.0,
) -> list[StrideSegment]:
    """
    Detect brief fast stride bursts: pace < threshold sustained for >= min_dur_s.

    Parameters
    ----------
    df : pd.DataFrame
        Run-only DataFrame with pace_min_per_km, dt, hr columns.
    pace_threshold_min_km : float
        Pace faster than this (min/km) qualifies as a stride.
    min_dur_s : float
        Minimum duration (seconds) to count as a stride.
    """
    if "pace_min_per_km" not in df.columns:
        return []

    strides: list[StrideSegment] = []
    seg_id = 1
    in_stride = False
    start_idx: pd.Timestamp | None = None

    for idx, row in df.iterrows():
        pace = row.get("pace_min_per_km")
        is_fast = isinstance(pace, float) and not np.isnan(pace) and pace < pace_threshold_min_km

        if is_fast and not in_stride:
            in_stride = True
            start_idx = idx  # type: ignore[assignment]
        elif not is_fast and in_stride and start_idx is not None:
            seg_df = df.loc[start_idx:idx]
            dur_s = float(seg_df["dt"].sum())
            if dur_s >= min_dur_s:
                avg_pace = float(seg_df["pace_min_per_km"].mean())
                hr_series = seg_df["hr"].dropna() if "hr" in seg_df.columns else pd.Series(dtype=float)
                avg_hr = round(float(hr_series.mean()), 1) if not hr_series.empty else None
                strides.append(
                    StrideSegment(
                        segment_id=seg_id,
                        start_ts=str(start_idx),
                        duration_s=round(dur_s, 1),
                        avg_pace_min_km=round(avg_pace, 2),
                        avg_hr=avg_hr,
                    )
                )
                seg_id += 1
            in_stride = False
            start_idx = None

    return strides


def _compute_dynamics(run_df: pd.DataFrame) -> RunDynamics | None:
    """Compute HR drift, pace strategy, and HR/pace correlation."""
    valid = run_df.dropna(subset=["hr", "pace_min_per_km"])
    if len(valid) < 20:
        return None

    # Time-based midpoint split
    midpoint = valid.index[0] + (valid.index[-1] - valid.index[0]) / 2
    first_half = valid[valid.index <= midpoint]
    second_half = valid[valid.index > midpoint]

    if first_half.empty or second_half.empty:
        return None

    fh_hr = float(first_half["hr"].mean())
    sh_hr = float(second_half["hr"].mean())
    hr_drift_pct = (sh_hr - fh_hr) / fh_hr * 100

    fh_pace = float(first_half["pace_min_per_km"].mean())
    sh_pace = float(second_half["pace_min_per_km"].mean())
    pace_diff_pct = (sh_pace - fh_pace) / fh_pace * 100

    if pace_diff_pct > 2:
        strategy = "positive"   # slowed in second half
    elif pace_diff_pct < -2:
        strategy = "negative"   # sped up in second half
    else:
        strategy = "even"

    corr: float | None = None
    if len(valid) > 10:
        corr = round(float(valid["hr"].corr(valid["pace_min_per_km"])), 3)

    return RunDynamics(
        first_half_hr=round(fh_hr, 1),
        second_half_hr=round(sh_hr, 1),
        hr_drift_pct=round(hr_drift_pct, 2),
        first_half_pace_min_km=round(fh_pace, 2),
        second_half_pace_min_km=round(sh_pace, 2),
        pace_strategy=strategy,
        hr_pace_correlation=corr,
    )


def _compute_aev(
    run_df: pd.DataFrame, ref_hr: int = 140
) -> tuple[float | None, int | None]:
    """
    Aerobic Efficiency Velocity: pace at reference HR via linear regression.

    Uses sub-threshold steady-state points to fit pace ~ HR, then
    extrapolates/interpolates to ref_hr.

    Returns
    -------
    (pace_at_ref_hr, ref_hr) or (None, None) if insufficient data.
    """
    valid = run_df[["hr", "pace_min_per_km"]].dropna()
    if len(valid) < 20:
        return None, None

    hr_vals = valid["hr"].values
    pace_vals = valid["pace_min_per_km"].values

    # Use aerobic-range data for stable regression
    mask = (hr_vals >= 130) & (hr_vals <= 175)
    if mask.sum() < 10:
        mask = (hr_vals >= 120) & (hr_vals <= 185)
    if mask.sum() < 5:
        return None, None

    hr_sub = hr_vals[mask]
    pace_sub = pace_vals[mask]

    # Guard against zero-variance HR (e.g. stuck sensor) which makes polyfit
    # numerically degenerate and raises RankWarning with unreliable coefficients.
    if np.std(hr_sub) == 0:
        return None, None

    coeffs = np.polyfit(hr_sub, pace_sub, 1)
    predicted_pace = float(coeffs[0] * ref_hr + coeffs[1])

    if predicted_pace <= 0 or predicted_pace > 20:
        return None, None

    return round(predicted_pace, 2), ref_hr


def _compute_ef_reliability(work_df: pd.DataFrame) -> float | None:
    """
    Coefficient of variation of instantaneous EF = speed_mps / hr.

    Lower CV means steadier effort and more reliable EF measurement.
    """
    if len(work_df) < 30:
        return None
    valid = work_df.dropna(subset=["hr", "speed_mps"])
    valid = valid[valid["hr"] > 0]
    if len(valid) < 30:
        return None
    inst_ef = valid["speed_mps"] / valid["hr"]
    mean_ef = float(inst_ef.mean())
    if mean_ef == 0:
        return None
    return round(float(inst_ef.std()) / mean_ef, 4)


def _compute_walk_summary(
    df: pd.DataFrame,
    session_duration_s: float,
) -> tuple[WalkSummary | None, list[dict]]:
    """Run walk_block_segments and summarize results."""
    from biosystems.signal.walk_detection import summarize_walk_segments, walk_block_segments

    if "is_walk" not in df.columns or not df["is_walk"].any():
        return None, []

    # walk_block_segments expects a 'heart_rate' column (not 'hr')
    df_w = df.copy()
    if "hr" in df_w.columns and "heart_rate" not in df_w.columns:
        df_w["heart_rate"] = df_w["hr"]

    try:
        segments = walk_block_segments(
            df_w,
            is_walk_col="is_walk",
            pace_col="pace_min_per_km",
            cad_col="cadence",
        )
    except Exception:
        return None, []

    if not segments:
        return None, []

    summary_dict = summarize_walk_segments(segments)
    total_walk_s = float(summary_dict["total_walk_time"])
    pct = (total_walk_s / session_duration_s * 100) if session_duration_s > 0 else 0.0

    # HR recovery rate: how fast HR drops during walk segments (bpm/s)
    hr_recovery_rates: list[float] = []
    for seg in summary_dict["valid_segments"]:
        try:
            start_ts = pd.Timestamp(seg["start_ts"])
            end_ts = pd.Timestamp(seg["end_ts"])
            seg_df = df.loc[start_ts:end_ts]
            if len(seg_df) > 5 and "hr" in seg_df.columns:
                peak_hr = float(seg_df["hr"].max())
                final_hr = float(seg_df["hr"].iloc[-1])
                dur = float(seg.get("dur_s", 1))
                if dur > 0 and final_hr < peak_hr:
                    hr_recovery_rates.append((peak_hr - final_hr) / dur)
        except Exception:
            pass

    avg_recovery = round(float(np.mean(hr_recovery_rates)), 3) if hr_recovery_rates else None

    def _safe(val: object) -> float | None:
        if val is None:
            return None
        try:
            f = float(val)  # type: ignore[arg-type]
            return None if np.isnan(f) else f
        except (TypeError, ValueError):
            return None

    raw_pace = _safe(summary_dict.get("avg_pace"))
    raw_hr = _safe(summary_dict.get("avg_hr"))
    raw_max_hr = _safe(summary_dict.get("max_hr"))
    raw_cad = _safe(summary_dict.get("avg_cad"))

    walk_summary = WalkSummary(
        segment_count=len(summary_dict["valid_segments"]),
        total_time_s=round(total_walk_s, 1),
        total_time_pct=round(pct, 1),
        total_distance_km=round(float(summary_dict["total_walk_dist"]), 3),
        avg_pace_min_km=round(raw_pace, 1) if raw_pace else None,
        avg_hr=round(raw_hr, 1) if raw_hr else None,
        max_hr=round(raw_max_hr, 1) if raw_max_hr else None,
        avg_cadence=round(raw_cad, 1) if raw_cad else None,
        avg_hr_recovery_bpm_per_s=avg_recovery,
    )

    return walk_summary, segments


def _compute_elevation_gain(df: pd.DataFrame) -> float | None:
    """Sum positive elevation differences (gain only)."""
    if "ele" not in df.columns:
        return None
    ele = df["ele"].dropna()
    if len(ele) < 2:
        return None
    diffs = ele.diff().dropna()
    gain = float(diffs[diffs > 0].sum())
    return round(gain, 1) if gain > 0 else None


def _parse_km_splits(splits_metric: list[dict]) -> list[KmSplit]:
    """
    Convert Strava splits_metric list into KmSplit model instances.

    Pace is derived from average_speed (m/s): pace_min_per_km = (1000/60) / speed.
    GAP pace is derived from average_grade_adjusted_speed if present.
    """
    result: list[KmSplit] = []
    for s in splits_metric:
        km = int(s.get("split", 0))
        distance_m = float(s.get("distance", 0))
        elapsed_time_s = int(s.get("elapsed_time", 0))
        moving_time_s = int(s.get("moving_time", elapsed_time_s))

        avg_speed = s.get("average_speed")
        if avg_speed and float(avg_speed) > 0:
            pace_min_per_km = round((1000.0 / 60.0) / float(avg_speed), 2)
        else:
            pace_min_per_km = 0.0

        gap_speed = s.get("average_grade_adjusted_speed")
        gap_pace: float | None = None
        if gap_speed and float(gap_speed) > 0:
            gap_pace = round((1000.0 / 60.0) / float(gap_speed), 2)

        avg_hr_raw = s.get("average_heartrate")
        avg_hr: float | None = round(float(avg_hr_raw), 1) if avg_hr_raw is not None else None

        ele_diff_raw = s.get("elevation_difference")
        ele_diff: float | None = round(float(ele_diff_raw), 1) if ele_diff_raw is not None else None

        pace_zone_raw = s.get("pace_zone")
        pace_zone: int | None = int(pace_zone_raw) if pace_zone_raw is not None else None

        result.append(KmSplit(
            km=km,
            distance_m=distance_m,
            elapsed_time_s=elapsed_time_s,
            moving_time_s=moving_time_s,
            pace_min_per_km=pace_min_per_km,
            gap_pace_min_per_km=gap_pace,
            avg_hr=avg_hr,
            elevation_diff_m=ele_diff,
            pace_zone=pace_zone,
        ))
    return result


_WT: dict[int, str] = {1: "race", 2: "long_run", 3: "workout"}


def _workout_type_str(wt: int | None) -> str | None:
    """Convert Strava workout_type integer to human-readable string."""
    return _WT.get(wt) if wt else None


def _parse_laps(raw_laps: list[dict]) -> list[Lap]:
    """Convert Strava laps list into Lap model instances."""
    result: list[Lap] = []
    for lap in raw_laps:
        avg_speed = lap.get("average_speed")
        if avg_speed and float(avg_speed) > 0:
            pace = round((1000.0 / 60.0) / float(avg_speed), 2)
        else:
            continue  # skip laps with no speed data

        avg_cad_raw = lap.get("average_cadence")
        avg_cad: float | None = round(float(avg_cad_raw) * 2, 1) if avg_cad_raw is not None else None

        result.append(Lap(
            lap_index=int(lap.get("lap_index", lap.get("split", 0))),
            distance_m=float(lap.get("distance", 0)),
            elapsed_time_s=int(lap.get("elapsed_time", 0)),
            moving_time_s=int(lap.get("moving_time", lap.get("elapsed_time", 0))),
            pace_min_per_km=pace,
            avg_hr=round(float(lap["average_heartrate"]), 1) if lap.get("average_heartrate") else None,
            max_hr=float(lap["max_heartrate"]) if lap.get("max_heartrate") else None,
            avg_cadence=avg_cad,
            elevation_gain_m=float(lap["total_elevation_gain"]) if lap.get("total_elevation_gain") else None,
            pace_zone=int(lap["pace_zone"]) if lap.get("pace_zone") else None,
        ))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_run_report(
    df: pd.DataFrame,
    zone_config: ZoneConfig,
    context: RunContext | None = None,
    activity_name: str | None = None,
    ref_hr_for_aev: int = 140,
    best_efforts: list[dict] | None = None,
    activity_meta: dict | None = None,
) -> FullRunReport:
    """
    Assemble a FullRunReport from a pipeline DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame with is_walk, pace_min_per_km, hr, speed_mps,
        dist, dt, cadence, ele columns. Timestamp index (UTC).
    zone_config : ZoneConfig
        Heart rate zone configuration.
    context : RunContext, optional
        Environmental and wellness context.
    activity_name : str, optional
        Human-readable activity name.
    ref_hr_for_aev : int
        Reference heart rate for Aerobic Efficiency Velocity calculation.
    best_efforts : list[dict], optional
        Strava best efforts (BestEffort-schema dicts). If None and activity_meta
        is provided, best_efforts from activity_meta are used.
    activity_meta : dict, optional
        Full activity metadata dict from fetch_activity_streams. When provided,
        km splits, activity-level fields, and block bests are populated.

    Returns
    -------
    FullRunReport
    """
    session_duration_s = float(df["dt"].sum())
    start_time = str(df.index[0]) if len(df) > 0 else None

    # --- Session metrics (full, walk included) ---
    df_session = df.drop(columns=["is_walk"], errors="ignore")
    session_metrics = run_metrics(df_session.copy(), zone_config, context=context)

    # --- Run-only metrics (walk filtered) ---
    run_only_metrics = run_metrics(df.copy(), zone_config, context=context)

    # --- Work DataFrame (run-only, above Z2) ---
    run_df = df[~df["is_walk"].astype(bool)].copy() if "is_walk" in df.columns else df.copy()
    run_df = run_df.dropna(subset=["hr"])
    lz2 = lower_z2_bpm(zone_config)
    work_df = run_df[run_df["hr"] >= lz2]
    if work_df.empty or len(work_df) < 120:
        work_df = run_df

    # --- Grade-adjusted EF ---
    ef_gap: float | None = None
    if run_only_metrics.gap_min_per_km and run_only_metrics.avg_hr:
        gap_speed_mps = (1000.0 / 60.0) / run_only_metrics.gap_min_per_km
        ef_gap = round(gap_speed_mps / run_only_metrics.avg_hr, 5)

    # --- EF reliability (CV of instantaneous EF) ---
    ef_cv = _compute_ef_reliability(work_df)

    # --- AeV: pace at reference HR ---
    aev_pace, aev_ref = _compute_aev(run_df, ref_hr=ref_hr_for_aev)

    # --- Zone time distributions (run-only) ---
    zone_hr_dist: list[ZoneTimeEntry] = []
    zone_pace_dist: list[ZoneTimeEntry] = []
    if not run_df.empty and "pace_sec_km" in run_df.columns:
        zone_hr_col, zone_pace_col, _ = compute_training_zones(
            run_df["hr"], run_df["pace_sec_km"], zone_config
        )
        zone_hr_dist = _zone_time_distribution(zone_hr_col, run_df["dt"])
        zone_pace_dist = _zone_time_distribution(zone_pace_col, run_df["dt"])

    # --- Walk summary and segments ---
    walk_summary, walk_segments = _compute_walk_summary(df, session_duration_s)

    # --- Within-run dynamics ---
    dynamics = _compute_dynamics(run_df)

    # --- Stride detection ---
    strides = _detect_strides(run_df)

    # --- Statistical distributions ---
    hr_dist = _percentile_stats(run_df["hr"]) if "hr" in run_df.columns else None
    pace_dist = (
        _percentile_stats(run_df["pace_min_per_km"])
        if "pace_min_per_km" in run_df.columns
        else None
    )
    cad_dist = (
        _percentile_stats(run_df["cadence"].replace(0, np.nan))
        if "cadence" in run_df.columns
        else None
    )

    # --- Elevation gain ---
    elevation_gain = _compute_elevation_gain(df)

    # --- Activity metadata from activity_meta ---
    splits_km: list[KmSplit] = []
    laps: list[Lap] = []
    max_hr: float | None = None
    max_speed_mps: float | None = None
    calories: float | None = None
    perceived_exertion: float | None = None
    workout_type_str: str | None = None
    device_name: str | None = None
    description: str | None = None
    block_bests: list[BlockBest] = []

    if activity_meta is not None:
        # Resolve best_efforts from activity_meta if not explicitly passed
        if best_efforts is None:
            best_efforts = activity_meta.get("best_efforts", [])

        # Build km splits and laps
        splits_raw = activity_meta.get("splits_metric", [])
        splits_km = _parse_km_splits(splits_raw)
        laps_raw = activity_meta.get("laps", [])
        if laps_raw:
            laps = _parse_laps(laps_raw)

        # Extract activity-level fields
        raw_max_hr = activity_meta.get("max_heartrate")
        if raw_max_hr is not None:
            max_hr = float(raw_max_hr)

        raw_max_speed = activity_meta.get("max_speed")
        if raw_max_speed is not None:
            max_speed_mps = float(raw_max_speed)

        raw_calories = activity_meta.get("calories")
        if raw_calories is not None:
            calories = float(raw_calories)

        raw_pe = activity_meta.get("perceived_exertion")
        if raw_pe is not None:
            perceived_exertion = float(raw_pe)

        workout_type_str = _workout_type_str(activity_meta.get("workout_type"))
        device_name = activity_meta.get("device_name")
        desc = activity_meta.get("description")
        description = desc if desc else None

        # Use barometric elevation gain if available (more accurate than GPS diff)
        baro_gain = activity_meta.get("total_elevation_gain")
        if baro_gain is not None:
            elevation_gain = round(float(baro_gain), 1)

        # Compute block bests
        from biosystems.analytics.history import detect_block_bests
        raw_bests = activity_meta.get("best_efforts", [])
        if raw_bests:
            block_best_dicts = detect_block_bests(raw_bests)
            for bb in block_best_dicts:
                try:
                    block_bests.append(BlockBest(**bb))
                except Exception:
                    pass

    # --- Best efforts ---
    parsed_efforts: list[BestEffort] = []
    for e in (best_efforts or []):
        try:
            parsed_efforts.append(BestEffort(**e))
        except Exception:
            pass

    return FullRunReport(
        activity_name=activity_name,
        start_time=start_time,
        session=session_metrics,
        run_only=run_only_metrics,
        ef_grade_adjusted=ef_gap,
        gap_quality_note=run_only_metrics.gap_quality_note,
        ef_reliability_cv=ef_cv,
        aev_pace_min_per_km=aev_pace,
        aev_ref_hr=aev_ref,
        zone_hr=zone_hr_dist,
        zone_pace=zone_pace_dist,
        walk_summary=walk_summary,
        walk_segments=walk_segments,
        dynamics=dynamics,
        strides=strides,
        hr_distribution=hr_dist,
        pace_distribution=pace_dist,
        cadence_distribution=cad_dist,
        elevation_gain_m=elevation_gain,
        splits_km=splits_km,
        laps=laps,
        max_hr=max_hr,
        max_speed_mps=max_speed_mps,
        calories=calories,
        perceived_exertion=perceived_exertion,
        workout_type=workout_type_str,
        device_name=device_name,
        description=description,
        best_efforts=parsed_efforts,
        block_bests=block_bests,
        context=context,
    )
