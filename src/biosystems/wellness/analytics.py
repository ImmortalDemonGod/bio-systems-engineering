"""
Wellness Analytics
==================

Pure-computation analytics over the wellness parquet DataFrame.
No biosystems imports — accepts only a pd.DataFrame, returns plain Python dicts.

Functions:
  compute_coverage(df)              → coverage table per metric
  compute_baselines(df)             → mean/std/percentiles per metric
  compute_correlations(df)          → cross-metric correlation matrix
  compute_era_stats(df)             → Whoop-era vs Garmin-era breakdown
  calibrate_thresholds(df)          → personal G/A/R thresholds (incl. resp rate)
  compute_longitudinal_fitness(df)  → RHR and VO2max trend over time
  compute_sleep_debt(df)            → 7-day rolling cumulative sleep debt (hours)
  compute_recovery_model(run_df, wellness_df)  → TSS→next-day BB lookup table

Era boundary: Whoop data ends 2025-12-25; Garmin-only era begins 2026-01-01.
"""

from __future__ import annotations

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
    Compute per-metric coverage statistics from a date-indexed DataFrame.

    Parameters:
        df (pd.DataFrame): Input DataFrame whose index is date-like and whose columns are metric series.

    Returns:
        pd.DataFrame: A DataFrame indexed by metric with columns:
            - n_rows (int): count of non-missing observations for the metric.
            - date_start (date): first date with a non-missing value.
            - date_end (date): last date with a non-missing value.
            - span_days (int): inclusive number of days between date_start and date_end.
            - pct_coverage (float): percent coverage = n_rows / span_days * 100, rounded to 1 decimal.
    """
    if df.empty:
        return pd.DataFrame(columns=["metric", "n_rows", "date_start", "date_end",
                                     "span_days", "pct_coverage"])
    (df.index.max() - df.index.min()).days + 1
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

    # ── Respiratory Rate: sigma-based illness/overtraining warning ────────────
    # Prefer Garmin-era; fall back to whoop-era column if absent
    rr_col = next(
        (c for c in ["respiratory_rate_garmin", "respiratory_rate_whoop"]
         if c in garmin_df.columns),
        None,
    )
    if rr_col is None:
        rr_col = next(
            (c for c in ["respiratory_rate_garmin", "respiratory_rate_whoop"]
             if c in df.columns),
            None,
        )
        rr_src = df
    else:
        rr_src = garmin_df

    if rr_col is not None:
        rr = rr_src[rr_col].dropna()
        if len(rr) >= min_garmin_days:
            rr_mean = float(rr.mean())
            rr_std  = float(rr.std())
            result["respiratory_rate"] = {
                "mean":  round(rr_mean, 2),
                "std":   round(rr_std,  2),
                "amber": round(rr_mean + 1.5 * rr_std, 2),  # 1.5σ = early warning
                "red":   round(rr_mean + 2.5 * rr_std, 2),  # 2.5σ = illness/OTS flag
                "n":     int(len(rr)),
            }

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


# ── Longitudinal Fitness ───────────────────────────────────────────────────────

def compute_longitudinal_fitness(df: pd.DataFrame) -> dict[str, Any]:
    """
    Track long-term fitness arc: RHR and VO2max monthly trends.

    Returns:
      {
        "rhr": {
          "monthly_means": [{"month": "2023-11", "mean": 60.1, "n": int}, ...],
          "total_delta":   float,   # latest_month - first_month (negative = improvement)
          "trend_label":   str,     # e.g. "-14 bpm over 28 months"
          "n_months":      int,
        },
        "vo2max": {
          "monthly_means": [...],
          "total_delta":   float,
          "trend_label":   str,
          "n_months":      int,
        },
        "era_summary": str,  # one-line narrative
      }
    """
    if df.empty:
        return {}

    result: dict[str, Any] = {}

    def _monthly_trend(col: str, label: str, unit: str, higher_is_better: bool) -> dict[str, Any] | None:
        # Prefer Garmin resting_hr_garmin for RHR; fall back to whoop
        cols_to_try = [col]
        if col == "resting_hr_garmin":
            cols_to_try = ["resting_hr_garmin", "resting_hr_whoop"]

        series = pd.Series(dtype=float)
        for c in cols_to_try:
            if c in df.columns:
                s = df[c].dropna()
                if not s.empty:
                    series = s
                    break

        if len(series) < 10:
            return None

        # Group by calendar month
        monthly = series.groupby(series.index.to_period("M")).agg(["mean", "count"])
        monthly = monthly[monthly["count"] >= 5]  # need ≥5 readings/month
        if len(monthly) < 2:
            return None

        monthly_means = [
            {"month": str(p), "mean": round(float(row["mean"]), 1), "n": int(row["count"])}
            for p, row in monthly.iterrows()
        ]

        first_mean = monthly_means[0]["mean"]
        last_mean  = monthly_means[-1]["mean"]
        delta      = round(last_mean - first_mean, 1)
        n_months   = len(monthly_means)

        sign = "+" if delta > 0 else ""
        # improvement: delta<0 for lower-is-better metrics, delta>0 for higher-is-better
        direction = "improvement" if (delta < 0) != higher_is_better else "decline"
        trend_label = (
            f"{sign}{delta} {unit} over {n_months} months ({direction})"
        )

        return {
            "monthly_means": monthly_means,
            "total_delta":   delta,
            "trend_label":   trend_label,
            "n_months":      n_months,
        }

    rhr_trend    = _monthly_trend("resting_hr_garmin", "RHR",    "bpm", higher_is_better=False)
    vo2max_trend = _monthly_trend("vo2max",            "VO2max", "ml/kg/min", higher_is_better=True)

    if rhr_trend:
        result["rhr"] = rhr_trend
    if vo2max_trend:
        result["vo2max"] = vo2max_trend

    # Build narrative summary
    parts = []
    if rhr_trend:
        parts.append(f"RHR {rhr_trend['trend_label']}")
    if vo2max_trend:
        parts.append(f"VO2max {vo2max_trend['trend_label']}")
    result["era_summary"] = " · ".join(parts) if parts else "Insufficient data for trend"

    return result


# ── Sleep Debt ─────────────────────────────────────────────────────────────────

def compute_sleep_debt(
    df: pd.DataFrame,
    personal_mean_h: float | None = None,
) -> pd.Series:
    """
    Compute 7-day rolling cumulative sleep debt in hours.

    Positive = debt (slept less than baseline); negative = surplus.
    Uses personal_mean_h if provided; otherwise derives from full-history mean.

    Returns:
      pd.Series indexed by date, values = cumulative 7-day debt in hours.
      Empty Series if insufficient data.
    """
    if df.empty:
        return pd.Series(dtype=float)

    # Merge Whoop and Garmin sleep columns into a single best-available series.
    # Garmin wins when both exist for a date; Whoop fills earlier history.
    sleep_s: pd.Series | None = None
    if "sleep_duration_s" in df.columns and "sleep_duration_s_garmin" in df.columns:
        combined = df["sleep_duration_s"].combine_first(df["sleep_duration_s_garmin"])
        s = combined.dropna()
        if not s.empty:
            sleep_s = s
    else:
        for col in ["sleep_duration_s", "sleep_duration_s_garmin"]:
            if col in df.columns:
                s = df[col].dropna()
                if not s.empty:
                    sleep_s = s
                    break

    if sleep_s is None or len(sleep_s) < 7:
        return pd.Series(dtype=float)

    sleep_h = sleep_s / 3600.0

    if personal_mean_h is None:
        personal_mean_h = float(sleep_h.mean())

    # Daily deficit (positive = slept less than mean)
    daily_deficit = personal_mean_h - sleep_h

    # 7-day rolling cumulative sum (sum of deficits over last 7 days)
    rolling_debt = daily_deficit.rolling(window=7, min_periods=3).sum()
    return rolling_debt.round(2)


# ── Recovery Model ─────────────────────────────────────────────────────────────

def compute_recovery_model(
    run_df: pd.DataFrame,
    wellness_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Model how training load (hrTSS) affects next-day Body Battery.

    run_df:      DataFrame with DatetimeIndex and 'hr_tss' column (or 'hrTSS').
    wellness_df: The full wellness parquet DataFrame.

    Returns lookup table by TSS bucket:
      {
        "bins": {
          "easy (0-40)":        {"mean_bb_delta": float, "std": float, "n": int},
          "moderate (40-70)":   {...},
          "hard (70-100)":      {...},
          "very_hard (100+)":   {...},
        },
        "overall_correlation": float | None,  # r between hrTSS and next-day BB delta
        "n_pairs":             int,
        "note":                str,
      }
    """
    if run_df.empty or wellness_df.empty:
        return {"bins": {}, "overall_correlation": None, "n_pairs": 0,
                "note": "Insufficient data"}

    if "body_battery" not in wellness_df.columns:
        return {"bins": {}, "overall_correlation": None, "n_pairs": 0,
                "note": "No Body Battery data"}

    # Normalise TSS column name
    tss_col = next((c for c in ["hr_tss", "hrTSS", "tss"] if c in run_df.columns), None)
    if tss_col is None:
        return {"bins": {}, "overall_correlation": None, "n_pairs": 0,
                "note": "No TSS column found in run_df"}

    # Build (date, hrTSS, next_day_bb_delta) triplets
    bb = wellness_df["body_battery"].dropna()
    pairs: list[dict[str, float]] = []

    for run_date, run_row in run_df.iterrows():
        tss = run_row[tss_col]
        if pd.isna(tss):
            continue
        run_ts      = pd.Timestamp(run_date).normalize()
        next_ts     = run_ts + pd.Timedelta(days=1)
        if run_ts not in bb.index or next_ts not in bb.index:
            continue
        bb_delta = float(bb[next_ts]) - float(bb[run_ts])
        pairs.append({"tss": float(tss), "bb_delta": bb_delta})

    if not pairs:
        return {"bins": {}, "overall_correlation": None, "n_pairs": 0,
                "note": "No matching run/wellness date pairs"}

    pairs_df = pd.DataFrame(pairs)
    n_pairs  = len(pairs_df)

    # Overall correlation
    if n_pairs >= 5:
        overall_r = round(float(pairs_df["tss"].corr(pairs_df["bb_delta"])), 3)
    else:
        overall_r = None

    # Bin by TSS
    bins_def = [
        ("easy (0-40)",       0,   40),
        ("moderate (40-70)",  40,  70),
        ("hard (70-100)",     70,  100),
        ("very_hard (100+)",  100, float("inf")),
    ]
    bins: dict[str, Any] = {}
    for name, lo, hi in bins_def:
        subset = pairs_df[(pairs_df["tss"] >= lo) & (pairs_df["tss"] < hi)]
        if len(subset) >= 3:
            bins[name] = {
                "mean_bb_delta": round(float(subset["bb_delta"].mean()), 1),
                "std":           round(float(subset["bb_delta"].std()),  1),
                "n":             int(len(subset)),
            }

    # Interpretation note
    if overall_r is not None:
        note = (
            f"r={overall_r:.3f} — training load explains "
            f"{overall_r**2*100:.0f}% of next-day BB variance. "
            "Use bins as expected ranges; actual BB also reflects sleep and stress."
        )
    else:
        note = "Too few pairs for correlation; bin estimates available."

    return {
        "bins":                bins,
        "overall_correlation": overall_r,
        "n_pairs":             n_pairs,
        "note":                note,
    }
