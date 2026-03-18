"""
Wellness Cache
==============

Manages the local wellness parquet store at ~/.biosystems/wellness.parquet.

Responsibilities:
  - sync_wellness()          pull HabitDash → merge into parquet
  - get_wellness_for_date()  single-day raw values
  - compute_wellness_context()  raw values + 1d/7d deltas + G/A/R signal
  - load_wellness_df()       public accessor for the full DataFrame

G/A/R logic (delta-first, raw-fallback; thresholds calibrated from personal data):
  RED    HRV 7d drop > threshold OR RHR 7d spike > threshold
         OR recovery_score < 34 OR sleep_score < 60 OR body_battery < personal p20
  AMBER  HRV 7d drop moderate OR RHR 7d spike moderate
         OR recovery/sleep borderline OR body_battery < personal p40
  GREEN  all signals stable
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

# ── Fallback thresholds (used before calibration data is available) ────────────
_RHR_SPIKE_RED   = 8.0   # bpm above 7d mean → RED
_RHR_SPIKE_AMBER = 5.0   # bpm above 7d mean → AMBER
_HRV_DROP_RED    = 20.0  # % drop from 7d mean → RED
_HRV_DROP_AMBER  = 10.0  # % drop from 7d mean → AMBER
_RECOVERY_RED    = 34    # Whoop recovery score
_RECOVERY_AMBER  = 67
_SLEEP_RED       = 60    # sleep score
_SLEEP_AMBER     = 80
_BB_RED          = 30    # Body Battery absolute → RED
_BB_AMBER        = 45    # Body Battery absolute → AMBER


def wellness_path() -> Path:
    """~/.biosystems/wellness.parquet (respects BIOSYSTEMS_HOME env var)."""
    base = Path(os.environ.get("BIOSYSTEMS_HOME", Path.home() / ".biosystems"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "wellness.parquet"


# ── Parquet I/O ───────────────────────────────────────────────────────────────

def _load_df() -> pd.DataFrame:
    """Load existing wellness cache; return empty DataFrame if absent."""
    p = wellness_path()
    if not p.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(p)
        df.index = pd.to_datetime(df.index).normalize()
        return df
    except Exception as exc:
        log.warning("Could not read wellness cache (%s): %s", p, exc)
        return pd.DataFrame()


def load_wellness_df() -> pd.DataFrame:
    """Public accessor for the full wellness DataFrame."""
    return _load_df()


def _save_df(df: pd.DataFrame) -> None:
    """Write DataFrame to parquet, sorted by date."""
    df = df.sort_index()
    df.to_parquet(wellness_path())


# ── Sync ─────────────────────────────────────────────────────────────────────

def sync_wellness(
    days: int = 7,
    date_start: str | None = None,
    date_end: str | None = None,
    api_key: str | None = None,
) -> int:
    """
    Fetch wellness metrics from HabitDash and merge into the local cache.

    Parameters
    ----------
    days : int
        Number of days to look back from today (used when date_start/end not set).
    date_start, date_end : str | None
        Explicit YYYY-MM-DD range; overrides *days* when both provided.
    api_key : str | None
        HabitDash API key; falls back to HABITDASH_API_KEY env var.

    Returns
    -------
    int
        Number of date rows updated/inserted.
    """
    from biosystems.wellness.habitdash import HabitDashClient

    if date_end is None:
        date_end = date.today().isoformat()
    if date_start is None:
        date_start = (date.today() - timedelta(days=days)).isoformat()

    log.info("Syncing HabitDash wellness %s → %s", date_start, date_end)

    try:
        client = HabitDashClient(api_key=api_key)
    except ValueError as exc:
        log.error("%s", exc)
        raise

    records = client.fetch_all_metrics(date_start, date_end)
    if not records:
        log.warning("No wellness data returned for %s–%s", date_start, date_end)
        return 0

    # Pivot flat records → date-indexed DataFrame
    new_df = pd.DataFrame(records)
    new_df["date"] = pd.to_datetime(new_df["date"]).dt.normalize()
    pivoted = new_df.pivot_table(
        index="date", columns="column", values="value", aggfunc="first"
    )
    pivoted.columns.name = None  # remove column axis name

    # Merge with existing cache (new data wins on conflict)
    existing = _load_df()
    if existing.empty:
        combined = pivoted
    else:
        combined = pivoted.combine_first(existing)
        for col in pivoted.columns:
            if col in combined.columns:
                combined[col] = combined[col].where(
                    pivoted[col].isna(), pivoted[col]
                )

    combined = combined.sort_index()
    _save_df(combined)

    updated = len(pivoted)
    log.info("Wellness cache updated: %d date rows written to %s", updated, wellness_path())
    return updated


# ── Lookup ────────────────────────────────────────────────────────────────────

def get_wellness_for_date(date_str: str) -> dict[str, Any]:
    """
    Return all wellness columns for a specific date.
    Returns {} if the date is not in the cache.
    """
    df = _load_df()
    if df.empty:
        return {}
    target = pd.Timestamp(date_str).normalize()
    if target not in df.index:
        return {}
    row = df.loc[target]
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


def get_wellness_window(
    date_str: str,
    days: int = 30,
) -> pd.DataFrame:
    """
    Return a DataFrame of the *days* days ending on date_str (inclusive).
    Used for delta computation.
    """
    df = _load_df()
    if df.empty:
        return pd.DataFrame()
    end   = pd.Timestamp(date_str).normalize()
    start = end - timedelta(days=days - 1)
    mask  = (df.index >= start) & (df.index <= end)
    return df[mask].copy()


# ── Delta computation ─────────────────────────────────────────────────────────

def _pct_change(today: float | None, reference: float | None) -> float | None:
    """Return (today - reference) / reference * 100 or None."""
    if today is None or reference is None or reference == 0:
        return None
    return (today - reference) / abs(reference) * 100


def compute_wellness_context(date_str: str) -> dict[str, Any]:
    """
    Build a full wellness context dict for a given date:
      - raw values for the day
      - 1-day absolute deltas
      - 7-day rolling mean deltas
      - G/A/R readiness signal (calibrated thresholds when sufficient data)
      - body_battery, sleep_hours, avg_stress, vo2max
      - personal norms for display context

    Returns empty dict if no wellness data exists at all.
    """
    # Single parquet load — used for both window slice and threshold calibration
    full_df = _load_df()
    if full_df.empty:
        return {}

    today_ts = pd.Timestamp(date_str).normalize()
    end      = today_ts
    start    = end - timedelta(days=29)  # 30-day window
    mask     = (full_df.index >= start) & (full_df.index <= end)
    window   = full_df[mask].copy()

    if window.empty:
        return {}

    today_row = window[window.index == today_ts]
    prev_row  = window[window.index < today_ts].tail(1)

    # Staleness check
    latest_date    = window.index.max()
    staleness_days = (today_ts - latest_date).days
    stale          = staleness_days > 1

    def _val(df_subset: pd.DataFrame, col: str) -> float | None:
        if df_subset.empty or col not in df_subset.columns:
            return None
        v = df_subset[col].iloc[0]
        return None if pd.isna(v) else float(v)

    def _7d_mean(col: str) -> float | None:
        prior = window[window.index < today_ts].tail(7)
        if prior.empty or col not in prior.columns:
            return None
        vals = prior[col].dropna()
        return float(vals.mean()) if not vals.empty else None

    # ── Raw values ────────────────────────────────────────────────────────────
    hrv_today      = _val(today_row, "hrv_rmssd")
    rhr_today      = (_val(today_row, "resting_hr_whoop")
                      or _val(today_row, "resting_hr_garmin"))
    recovery_today = _val(today_row, "recovery_score")
    sleep_today    = _val(today_row, "sleep_score")
    sleep_dur_s    = (_val(today_row, "sleep_duration_s")
                      or _val(today_row, "sleep_duration_s_garmin"))
    body_battery   = _val(today_row, "body_battery")
    strain_today   = _val(today_row, "strain_score")
    avg_stress     = _val(today_row, "avg_stress")
    vo2max         = _val(today_row, "vo2max")

    sleep_hours = round(sleep_dur_s / 3600, 1) if sleep_dur_s else None

    # ── 1-day deltas ──────────────────────────────────────────────────────────
    hrv_1d_delta = None
    rhr_1d_delta = None
    if not prev_row.empty:
        hrv_prev = _val(prev_row, "hrv_rmssd")
        rhr_prev = (_val(prev_row, "resting_hr_whoop")
                    or _val(prev_row, "resting_hr_garmin"))
        hrv_1d_delta = (hrv_today - hrv_prev) if (hrv_today and hrv_prev) else None
        rhr_1d_delta = (rhr_today - rhr_prev) if (rhr_today and rhr_prev) else None

    # ── 7-day rolling mean deltas ─────────────────────────────────────────────
    hrv_7d_mean   = _7d_mean("hrv_rmssd")
    rhr_7d_mean   = _7d_mean("resting_hr_whoop") or _7d_mean("resting_hr_garmin")
    bb_7d_mean    = _7d_mean("body_battery")
    hrv_7d_pct    = _pct_change(hrv_today, hrv_7d_mean)
    rhr_7d_delta  = ((rhr_today - rhr_7d_mean)
                     if (rhr_today and rhr_7d_mean) else None)
    bb_7d_delta   = ((body_battery - bb_7d_mean)
                     if (body_battery is not None and bb_7d_mean) else None)

    # ── Calibrated thresholds ─────────────────────────────────────────────────
    try:
        from biosystems.wellness.analytics import calibrate_thresholds
        thresholds = calibrate_thresholds(full_df)
    except Exception:
        thresholds = {}

    hrv_drop_red   = thresholds.get("hrv_pct_drop_red",   _HRV_DROP_RED)
    hrv_drop_amber = thresholds.get("hrv_pct_drop_amber", _HRV_DROP_AMBER)
    rhr_spike_red  = thresholds.get("rhr_spike_red",      _RHR_SPIKE_RED)
    rhr_spike_amb  = thresholds.get("rhr_spike_amber",    _RHR_SPIKE_AMBER)
    bb_red         = thresholds.get("body_battery", {}).get("red",   _BB_RED)
    bb_amber       = thresholds.get("body_battery", {}).get("amber", _BB_AMBER)
    str_red        = thresholds.get("avg_stress",   {}).get("red",   55.0)
    str_amber      = thresholds.get("avg_stress",   {}).get("amber", 40.0)
    norms          = thresholds.get("norms", {})

    # ── G/A/R classification ──────────────────────────────────────────────────
    red_signals:   list[str] = []
    amber_signals: list[str] = []

    if hrv_7d_pct is not None:
        if hrv_7d_pct < -hrv_drop_red:
            red_signals.append(f"HRV {hrv_7d_pct:+.0f}% vs 7d mean")
        elif hrv_7d_pct < -hrv_drop_amber:
            amber_signals.append(f"HRV {hrv_7d_pct:+.0f}% vs 7d mean")

    if rhr_7d_delta is not None:
        if rhr_7d_delta > rhr_spike_red:
            red_signals.append(f"RHR +{rhr_7d_delta:.0f} bpm vs 7d mean")
        elif rhr_7d_delta > rhr_spike_amb:
            amber_signals.append(f"RHR +{rhr_7d_delta:.0f} bpm vs 7d mean")

    if recovery_today is not None:
        if recovery_today < _RECOVERY_RED:
            red_signals.append(f"Recovery {recovery_today:.0f}%")
        elif recovery_today < _RECOVERY_AMBER:
            amber_signals.append(f"Recovery {recovery_today:.0f}%")

    if sleep_today is not None:
        if sleep_today < _SLEEP_RED:
            red_signals.append(f"Sleep {sleep_today:.0f}%")
        elif sleep_today < _SLEEP_AMBER:
            amber_signals.append(f"Sleep {sleep_today:.0f}%")

    if body_battery is not None:
        if body_battery < bb_red:
            red_signals.append(f"Body Battery {body_battery:.0f}% (low)")
        elif body_battery < bb_amber:
            amber_signals.append(f"Body Battery {body_battery:.0f}% (below norm)")

    if avg_stress is not None:
        if avg_stress > str_red:
            red_signals.append(f"Stress {avg_stress:.0f}")
        elif avg_stress > str_amber:
            amber_signals.append(f"Stress {avg_stress:.0f}")

    if red_signals:
        gar        = "🔴 RED"
        gar_detail = "; ".join(red_signals)
    elif amber_signals:
        gar        = "🟡 AMBER"
        gar_detail = "; ".join(amber_signals)
    else:
        gar        = "🟢 GREEN"
        gar_detail = "all signals stable"

    ctx: dict[str, Any] = {
        # Raw values
        "hrv_rmssd":        hrv_today,
        "resting_hr":       rhr_today,
        "recovery_score":   recovery_today,
        "sleep_score":      sleep_today,
        "sleep_duration_s": sleep_dur_s,
        "sleep_hours":      sleep_hours,
        "body_battery":     body_battery,
        "strain_score":     strain_today,
        "avg_stress":       avg_stress,
        "vo2max":           vo2max,
        # Deltas
        "hrv_1d_delta":     round(hrv_1d_delta, 1)  if hrv_1d_delta  is not None else None,
        "hrv_7d_pct":       round(hrv_7d_pct, 1)    if hrv_7d_pct    is not None else None,
        "hrv_7d_mean":      round(hrv_7d_mean, 1)   if hrv_7d_mean   is not None else None,
        "rhr_1d_delta":     round(rhr_1d_delta, 1)  if rhr_1d_delta  is not None else None,
        "rhr_7d_delta":     round(rhr_7d_delta, 1)  if rhr_7d_delta  is not None else None,
        "rhr_7d_mean":      round(rhr_7d_mean, 1)   if rhr_7d_mean   is not None else None,
        "bb_7d_mean":       round(bb_7d_mean, 1)    if bb_7d_mean    is not None else None,
        "bb_7d_delta":      round(bb_7d_delta, 1)   if bb_7d_delta   is not None else None,
        # G/A/R
        "gar":              gar,
        "gar_detail":       gar_detail,
        # Personal norms (from calibrated thresholds)
        "norms":            norms,
        "thresholds_calibrated": thresholds.get("calibrated", False),
        # Metadata
        "stale":            stale,
        "staleness_days":   staleness_days if stale else 0,
    }
    return ctx


# ── RunContext helper ─────────────────────────────────────────────────────────

def enrich_run_context(
    date_str: str,
    existing_context: Any | None,
) -> Any | None:
    """
    Populate RunContext.rest_hr / sleep_score / hrv_rmssd from wellness cache.
    Returns the original context object if no wellness data is available.
    Imports RunContext lazily to avoid circular dependency.
    """
    wellness = get_wellness_for_date(date_str)
    if not wellness:
        return existing_context

    from biosystems.models import RunContext

    if existing_context is not None:
        kw: dict[str, Any] = existing_context.model_dump()
    else:
        kw = {}

    hrv = wellness.get("hrv_rmssd")
    rhr = wellness.get("resting_hr_whoop") or wellness.get("resting_hr_garmin")
    slp = wellness.get("sleep_score")

    if hrv is not None:
        kw["hrv_rmssd"] = float(hrv)
    if rhr is not None:
        kw["rest_hr"] = int(round(float(rhr)))
    if slp is not None:
        kw["sleep_score"] = float(slp)

    try:
        return RunContext(**kw)
    except Exception:
        return existing_context
