"""
Longitudinal Trending & Performance Management
===============================================

Computes Performance Management Chart (PMC) metrics and rolling fitness
trends from a sorted list of run history entries.

Concepts
--------
ATL (Acute Training Load)   — 7-day exponential moving average of hrTSS.
                              Represents fatigue. Responds quickly to load.
CTL (Chronic Training Load) — 42-day exponential moving average of hrTSS.
                              Represents fitness. Changes slowly.
TSB (Training Stress Balance) = CTL - ATL, computed *before* today's load.
                              Positive = fresh/rested. Negative = fatigued.

These are the Banister Impulse–Response model as popularised by TrainingPeaks.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any


def compute_pmc(
    entries: list[dict[str, Any]],
    decay_atl: int = 7,
    decay_ctl: int = 42,
) -> list[dict[str, Any]]:
    """
    Compute daily ATL, CTL, and TSB across the calendar range covered by the provided run entries.
    
    Aggregates multiple runs on the same ISO date by summing `hrTSS` and summing `distance_km`; when multiple distinct non-empty `activity_name` values occur on the same date they are concatenated with " + ". Days with no runs use `hrTSS = 0` for decay purposes. TSB is computed for each day before that day's load is applied. ATL, CTL, and TSB are rounded to one decimal place; `hrTSS` is rounded to one decimal when present and otherwise returned as `None`.
    
    Parameters:
        entries (list[dict]): Run history entries containing at minimum `'date'` (ISO YYYY-MM-DD) and `'hrTSS'`. Entries should be sorted ascending by date.
        decay_atl (int): Time constant for ATL in days (default 7).
        decay_ctl (int): Time constant for CTL in days (default 42).
    
    Returns:
        list[dict]: One dictionary per calendar day from the earliest to latest entry date. Each dictionary contains:
            - `date` (str): ISO date (YYYY-MM-DD)
            - `hrTSS` (float|None): Daily hrTSS if > 0 (rounded to 0.1), otherwise `None`
            - `atl` (float): ATL rounded to 0.1
            - `ctl` (float): CTL rounded to 0.1
            - `tsb` (float): CTB = CTL - ATL (rounded to 0.1) computed before that day's load
            - optional metadata copied/aggregated from input: `activity_name`, `distance_km`, `ef`, `ef_gap`, `decoupling_pct`, `avg_hr`, `avg_pace_min_per_km`
    """
    if not entries:
        return []

    # Build a TSS-by-date lookup, aggregating multiple same-day runs
    tss_by_date: dict[str, float] = {}
    meta_by_date: dict[str, dict[str, Any]] = {}
    for e in entries:
        d = e.get("date", "")
        if d:
            tss_by_date[d] = tss_by_date.get(d, 0.0) + float(e.get("hrTSS", 0))
            if d not in meta_by_date:
                meta_by_date[d] = dict(e)
            else:
                # Aggregate distance and mark as multi-run day
                prev = meta_by_date[d]
                prev_dist = prev.get("distance_km") or 0.0
                curr_dist = e.get("distance_km") or 0.0
                prev["distance_km"] = prev_dist + curr_dist
                prev_name = prev.get("activity_name", "")
                curr_name = e.get("activity_name", "")
                if curr_name and curr_name != prev_name:
                    prev["activity_name"] = f"{prev_name} + {curr_name}"

    dates_sorted = sorted(tss_by_date.keys())
    if not dates_sorted:
        return []

    start = date.fromisoformat(dates_sorted[0])
    end = date.fromisoformat(dates_sorted[-1])

    # Decay multipliers (standard Banister formulation)
    k_atl = math.exp(-1.0 / decay_atl)
    k_ctl = math.exp(-1.0 / decay_ctl)
    g_atl = 1.0 - k_atl  # gain factor
    g_ctl = 1.0 - k_ctl

    atl = 0.0
    ctl = 0.0
    result: list[dict[str, Any]] = []

    current = start
    while current <= end:
        ds = current.isoformat()
        tss = tss_by_date.get(ds, 0.0)
        meta = meta_by_date.get(ds, {})

        # TSB is computed BEFORE today's load
        tsb = round(ctl - atl, 1)

        # Update ATL and CTL with today's load
        atl = atl * k_atl + tss * g_atl
        ctl = ctl * k_ctl + tss * g_ctl

        result.append({
            "date": ds,
            "hrTSS": round(tss, 1) if tss > 0 else None,
            "atl": round(atl, 1),
            "ctl": round(ctl, 1),
            "tsb": tsb,
            "activity_name": meta.get("activity_name"),
            "distance_km": meta.get("distance_km"),
            "ef": meta.get("ef"),
            "ef_gap": meta.get("ef_gap"),
            "decoupling_pct": meta.get("decoupling_pct"),
            "avg_hr": meta.get("avg_hr"),
            "avg_pace_min_per_km": meta.get("avg_pace_min_per_km"),
        })
        current += timedelta(days=1)

    return result


def compute_rolling_stats(
    entries: list[dict[str, Any]],
    window: int = 10,
) -> list[dict[str, Any]]:
    """
    Compute rolling average of EF, EF (grade-adjusted), and decoupling_pct
    over the last ``window`` runs (run days only, not calendar days).

    Parameters
    ----------
    entries : list[dict]
        Run history entries sorted ascending by date.
    window : int
        Number of runs in rolling window.

    Returns
    -------
    list[dict]
        One entry per run (days with hrTSS > 0) with keys:
        'date', 'ef', 'ef_gap', 'decoupling_pct',
        'ef_roll', 'ef_gap_roll', 'decoupling_roll'.
        Rolling values are None until enough data accumulates.
    """
    run_entries = [e for e in entries if (e.get("hrTSS") or 0) > 0]

    result: list[dict[str, Any]] = []
    ef_window: list[float] = []
    ef_gap_window: list[float] = []
    dec_window: list[float] = []

    for e in run_entries:
        ef = e.get("ef")
        ef_gap = e.get("ef_gap")
        dec = e.get("decoupling_pct")

        if ef is not None:
            ef_window.append(float(ef))
        if ef_gap is not None:
            ef_gap_window.append(float(ef_gap))
        if dec is not None:
            dec_window.append(float(dec))

        def _roll(buf: list[float]) -> float | None:
            tail = buf[-window:]
            return round(sum(tail) / len(tail), 5) if len(tail) >= 3 else None

        result.append({
            "date": e["date"],
            "activity_name": e.get("activity_name"),
            "distance_km": e.get("distance_km"),
            "hrTSS": e.get("hrTSS"),
            "ef": ef,
            "ef_gap": ef_gap,
            "decoupling_pct": dec,
            "ef_roll": _roll(ef_window),
            "ef_gap_roll": _roll(ef_gap_window),
            "decoupling_roll": _roll(dec_window),
            "avg_hr": e.get("avg_hr"),
            "avg_pace_min_per_km": e.get("avg_pace_min_per_km"),
        })

    return result


def summarize_trend(
    pmc: list[dict[str, Any]],
    rolling: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a top-level summary of current fitness state.

    Returns a dict suitable for JSON output containing today's CTL/ATL/TSB
    and recent EF/decoupling trend direction.
    """
    if not pmc:
        return {}

    latest_pmc = pmc[-1]
    current_ctl = latest_pmc["ctl"]
    current_atl = latest_pmc["atl"]
    current_tsb = latest_pmc["tsb"]

    # Fitness trend: compare CTL now vs 14 days ago
    ctl_14d_ago: float | None = None
    if len(pmc) >= 14:
        ctl_14d_ago = pmc[-14]["ctl"]
    ctl_trend: str | None = None
    if ctl_14d_ago is not None:
        delta = current_ctl - ctl_14d_ago
        if delta > 1.5:
            ctl_trend = "building"
        elif delta < -1.5:
            ctl_trend = "detraining"
        else:
            ctl_trend = "maintaining"

    # EF trend: last 5 vs previous 5 runs
    ef_trend: str | None = None
    if len(rolling) >= 6:
        recent_ef = [r["ef"] for r in rolling[-5:] if r.get("ef") is not None]
        prior_ef = [r["ef"] for r in rolling[-10:-5] if r.get("ef") is not None]
        if len(recent_ef) >= 3 and len(prior_ef) >= 3:
            delta_ef = sum(recent_ef) / len(recent_ef) - sum(prior_ef) / len(prior_ef)
            if delta_ef > 0.0003:
                ef_trend = "improving"
            elif delta_ef < -0.0003:
                ef_trend = "declining"
            else:
                ef_trend = "stable"

    latest_run = rolling[-1] if rolling else {}

    return {
        "ctl": current_ctl,
        "atl": current_atl,
        "tsb": current_tsb,
        "ctl_trend": ctl_trend,
        "ef_trend": ef_trend,
        "latest_run": {
            "date": latest_run.get("date"),
            "ef": latest_run.get("ef"),
            "ef_gap": latest_run.get("ef_gap"),
            "ef_roll": latest_run.get("ef_roll"),
            "decoupling_pct": latest_run.get("decoupling_pct"),
            "decoupling_roll": latest_run.get("decoupling_roll"),
        } if latest_run else None,
        "history_runs": len(rolling),
    }
