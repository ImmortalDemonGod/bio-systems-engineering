"""
Wellness Analytics
==================

Pure-computation analytics over the wellness parquet DataFrame.
No biosystems imports — accepts only a pd.DataFrame, returns plain Python dicts.

Functions:
  compute_coverage(df)       → coverage table per metric
  compute_baselines(df)      → mean/std/percentiles per metric
  compute_correlations(df)   → cross-metric correlation matrix
  compute_era_stats(df)      → Whoop-era vs Garmin-era breakdown
  calibrate_thresholds(df)   → personal G/A/R thresholds from data distribution

Era boundary: Whoop data ends 2025-12-25; Garmin-only era begins 2026-01-01.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

# ── Era boundary ──────────────────────────────────────────────────────────────
_WHOOP_ERA_END = pd.Timestamp("2025-12-26")   # first date with NO Whoop data

# ── Fallback clinical thresholds (used when insufficient personal data) ───────
_FALLBACK = {
    "hrv_pct_drop_red":   20.0,
    "hrv_pct_drop_amber": 10.0,
    "rhr_spike_red":       8.0,
    "rhr_spike_amber":     5.0,
    "body_battery": {"red": 30.0, "amber": 45.0},
    "avg_stress":   {"red": 55.0, "amber": 40.0},
    "calibrated": False,
}

# Metrics to include in baselines/correlations
_WHOOP_METRICS = [
    "hrv_rmssd", "resting_hr_whoop", "recovery_score", "sleep_score",
    "strain_score", "sleep_duration_s", "sleep_disturbances_ph",
    "sleep_consistency", "respiratory_rate_whoop", "skin_temp_c",
]
_GARMIN_METRICS = [
    "resting_hr_garmin", "body_battery", "avg_stress", "steps",
    "active_time_s", "vo2max", "sleep_duration_s_garmin",
    "respiratory_rate_garmin",
]


# ── Coverage ──────────────────────────────────────────────────────────────────

def compute_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with one row per metric showing coverage stats.

    Columns: metric, n_rows, date_start, date_end, span_days, pct_coverage
    """
    if df.empty:
        return pd.DataFrame(columns=["metric", "n_rows", "date_start", "date_end",
                                     "span_days", "pct_coverage"])
    total_days = (df.index.max() - df.index.min()).days + 1
    rows = []
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            continue
        n = len(s)
        start = s.index.min()
        end   = s.index.max()
        span  = (end - start).days + 1
        rows.append({
            "metric":       col,
            "n_rows":       n,
            "date_start":   start.date(),
            "date_end":     end.date(),
            "span_days":    span,
            "pct_coverage": round(n / span * 100, 1),
        })
    return pd.DataFrame(rows).set_index("metric")


# ── Baselines ─────────────────────────────────────────────────────────────────

def compute_baselines(
    df: pd.DataFrame,
    cols: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """
    Return mean/std/percentiles for each numeric column.

    Returns dict keyed by column name:
      {"mean", "std", "p10", "p25", "p50", "p75", "p90", "n"}
    """
    if df.empty:
        return {}
    if cols is None:
        cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    result: dict[str, dict[str, float]] = {}
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if len(s) < 5:
            continue
        result[col] = {
            "mean": round(float(s.mean()), 2),
            "std":  round(float(s.std()),  2),
            "p10":  round(float(s.quantile(0.10)), 2),
            "p25":  round(float(s.quantile(0.25)), 2),
            "p50":  round(float(s.quantile(0.50)), 2),
            "p75":  round(float(s.quantile(0.75)), 2),
            "p90":  round(float(s.quantile(0.90)), 2),
            "n":    int(len(s)),
        }
    return result


# ── Correlations ──────────────────────────────────────────────────────────────

def compute_correlations(
    df: pd.DataFrame,
    cols: list[str] | None = None,
) -> pd.DataFrame:
    """
    Return Pearson correlation matrix for the specified columns.
    Only rows with all columns non-null are used (pairwise by default).
    """
    if df.empty:
        return pd.DataFrame()
    if cols is None:
        cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    valid = [c for c in cols if c in df.columns]
    if len(valid) < 2:
        return pd.DataFrame()
    return df[valid].corr(method="pearson")


# ── Era stats ─────────────────────────────────────────────────────────────────

def compute_era_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    Split data into Whoop era and Garmin-only era and compute baselines for each.

    Returns:
      {
        "boundary": "2025-12-26",
        "whoop_era":  {"start", "end", "days", "baselines": {...}},
        "garmin_era": {"start", "end", "days", "baselines": {...}},
      }
    """
    if df.empty:
        return {}

    whoop_df  = df[df.index < _WHOOP_ERA_END]
    garmin_df = df[df.index >= _WHOOP_ERA_END]

    def _era(era_df: pd.DataFrame, metric_cols: list[str]) -> dict[str, Any]:
        if era_df.empty:
            return {"start": None, "end": None, "days": 0, "baselines": {}}
        available = [c for c in metric_cols if c in era_df.columns]
        return {
            "start":     era_df.index.min().date().isoformat(),
            "end":       era_df.index.max().date().isoformat(),
            "days":      len(era_df),
            "baselines": compute_baselines(era_df, cols=available),
        }

    return {
        "boundary":   _WHOOP_ERA_END.date().isoformat(),
        "whoop_era":  _era(whoop_df,  _WHOOP_METRICS),
        "garmin_era": _era(garmin_df, _GARMIN_METRICS),
    }


# ── Threshold calibration ─────────────────────────────────────────────────────

def calibrate_thresholds(
    df: pd.DataFrame,
    min_garmin_days: int = 30,
) -> dict[str, Any]:
    """
    Derive personal G/A/R thresholds from the athlete's own data distribution.

    Uses Garmin-era data (index >= _WHOOP_ERA_END) for current-era signals.
    Falls back to clinical constants (_FALLBACK) when insufficient data.

    Returns a complete threshold dict (never raises):
      {
        "hrv_pct_drop_red":   float,  # % drop from 7d mean to trigger RED
        "hrv_pct_drop_amber": float,
        "rhr_spike_red":      float,  # bpm above 7d mean to trigger RED
        "rhr_spike_amber":    float,
        "body_battery":       {"red": float, "amber": float, "n": int},
        "avg_stress":         {"red": float, "amber": float, "n": int},
        "calibrated":         bool,   # True if personal data used
        "garmin_days":        int,
        "norms": {                    # personal mean/std for display
            "rhr_garmin_mean": float | None,
            "hrv_mean":        float | None,
            "bb_mean":         float | None,
            "stress_mean":     float | None,
            "vo2max_mean":     float | None,
            "sleep_h_mean":    float | None,
        },
      }
    """
    result: dict[str, Any] = dict(_FALLBACK)  # start with fallbacks

    if df.empty:
        result["garmin_days"] = 0
        result["norms"] = _empty_norms()
        return result

    garmin_df = df[df.index >= _WHOOP_ERA_END]
    n_garmin  = len(garmin_df)
    result["garmin_days"] = n_garmin

    # ── Personal norms (always computed if data exists) ───────────────────────
    result["norms"] = _compute_norms(df, garmin_df)

    if n_garmin < min_garmin_days:
        return result  # not enough data → keep clinical fallbacks

    # ── Body Battery: use p25 = RED, p50 = AMBER ─────────────────────────────
    bb = garmin_df["body_battery"].dropna() if "body_battery" in garmin_df.columns else pd.Series([], dtype=float)
    if len(bb) >= min_garmin_days:
        result["body_battery"] = {
            "red":   round(float(bb.quantile(0.20)), 1),  # bottom 20th %ile
            "amber": round(float(bb.quantile(0.40)), 1),  # bottom 40th %ile
            "n":     int(len(bb)),
        }

    # ── Avg Stress: use p75 = AMBER, p90 = RED ───────────────────────────────
    stress = garmin_df["avg_stress"].dropna() if "avg_stress" in garmin_df.columns else pd.Series([], dtype=float)
    if len(stress) >= min_garmin_days:
        result["avg_stress"] = {
            "red":   round(float(stress.quantile(0.90)), 1),
            "amber": round(float(stress.quantile(0.75)), 1),
            "n":     int(len(stress)),
        }

    # ── HRV: derive RED/AMBER % drop thresholds from variance ────────────────
    # Use full-history HRV (Whoop era) for stable baseline
    hrv = df["hrv_rmssd"].dropna() if "hrv_rmssd" in df.columns else pd.Series([], dtype=float)
    if len(hrv) >= 90:
        hrv_std  = float(hrv.std())
        hrv_mean = float(hrv.mean())
        if hrv_mean > 0:
            # RED = drop of 2× std; AMBER = drop of 1× std (as % of mean)
            result["hrv_pct_drop_red"]   = round(hrv_std * 2 / hrv_mean * 100, 1)
            result["hrv_pct_drop_amber"] = round(hrv_std * 1 / hrv_mean * 100, 1)

    # ── RHR: derive spike thresholds from Garmin-era RHR std ─────────────────
    rhr = garmin_df["resting_hr_garmin"].dropna() if "resting_hr_garmin" in garmin_df.columns else pd.Series([], dtype=float)
    if len(rhr) >= min_garmin_days:
        rhr_std = float(rhr.std())
        result["rhr_spike_red"]   = round(rhr_std * 2.5, 1)   # ~2.5 sigma spike
        result["rhr_spike_amber"] = round(rhr_std * 1.5, 1)   # ~1.5 sigma spike

    result["calibrated"] = True
    return result


def _empty_norms() -> dict[str, Any]:
    return {k: None for k in [
        "rhr_garmin_mean", "hrv_mean", "bb_mean",
        "stress_mean", "vo2max_mean", "sleep_h_mean",
    ]}


def _compute_norms(df: pd.DataFrame, garmin_df: pd.DataFrame) -> dict[str, Any]:
    def _mean(src: pd.DataFrame, col: str) -> float | None:
        if col not in src.columns:
            return None
        s = src[col].dropna()
        return round(float(s.mean()), 1) if len(s) >= 5 else None

    sleep_s = _mean(df, "sleep_duration_s") or _mean(garmin_df, "sleep_duration_s_garmin")
    sleep_h = round(sleep_s / 3600, 1) if sleep_s else None

    return {
        "rhr_garmin_mean": _mean(garmin_df, "resting_hr_garmin"),
        "hrv_mean":        _mean(df,        "hrv_rmssd"),
        "bb_mean":         _mean(garmin_df, "body_battery"),
        "stress_mean":     _mean(garmin_df, "avg_stress"),
        "vo2max_mean":     _mean(garmin_df, "vo2max"),
        "sleep_h_mean":    sleep_h,
    }
