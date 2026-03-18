"""
Run History Store
=================

Persists per-run metrics to a local JSON Lines file so longitudinal
trending can be computed across sessions.

Storage location: ~/.biosystems/history.jsonl
Each line is a JSON object with the fields written by ``append_run``.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any


def history_path() -> Path:
    """Return the path to the local run history file."""
    base = Path(os.environ.get("BIOSYSTEMS_HOME", Path.home() / ".biosystems"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "history.jsonl"


def load_history() -> list[dict[str, Any]]:
    """
    Load all run history entries, sorted by date ascending.

    Returns
    -------
    list[dict]
        Each dict has at minimum: 'date' (ISO string), 'hrTSS' (float).
        Optional keys: 'ef', 'ef_gap', 'decoupling_pct', 'distance_km',
        'avg_hr', 'avg_pace_min_per_km', 'activity_name'.
    """
    path = history_path()
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    # Sort by date, dedup by date (keep last written for each date)
    by_date: dict[str, dict[str, Any]] = {}
    for e in entries:
        key = e.get("date", "")
        if key:
            by_date[key] = e

    return sorted(by_date.values(), key=lambda x: x["date"])


def append_run(entry: dict[str, Any], strava_efforts: dict[str, int] | None = None) -> None:
    """
    Append a run entry to the history file.

    If an entry with the same date already exists, the new entry
    replaces it (full rewrite to preserve dedup invariant).

    Parameters
    ----------
    entry : dict
        Must include 'date' (ISO YYYY-MM-DD string) and 'hrTSS' (float).
        All other fields are optional but recommended for richer trending.
    strava_efforts : dict[str, int], optional
        Dict mapping effort name to elapsed_time_s (e.g. {"1K": 240, "1 mile": 380}).
        Stored in history for future block-best comparisons.
    """
    if "date" not in entry:
        return

    if strava_efforts is not None:
        entry = dict(entry)  # avoid mutating caller's dict
        entry["strava_efforts"] = strava_efforts

    existing = load_history()
    by_date: dict[str, dict[str, Any]] = {e["date"]: e for e in existing}
    by_date[entry["date"]] = entry

    path = history_path()
    lines = [json.dumps(e, separators=(",", ":")) for e in sorted(by_date.values(), key=lambda x: x["date"])]
    path.write_text("\n".join(lines) + "\n")


def detect_block_bests(
    current_efforts: list[dict[str, Any]],
    window_days: int | None = None,
) -> list[dict[str, Any]]:
    """
    Compare current run's best efforts against our own recorded history.

    By default (window_days=None) compares against the entire recorded history —
    from the very first run we stored. Pass window_days to restrict the window.

    Parameters
    ----------
    current_efforts : list[dict]
        BestEffort-schema dicts from the current run (name, elapsed_time_s, distance_m, …).
    window_days : int or None
        Look-back window in days. None (default) = all recorded history.

    Returns
    -------
    list[dict]
        BlockBest-schema dicts (one per distance in current_efforts).
    """
    history = load_history()
    if window_days is not None:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=window_days)).isoformat()
        window_history = [e for e in history if e.get("date", "") >= cutoff]
    else:
        window_history = history

    results: list[dict[str, Any]] = []
    for effort in current_efforts:
        name = effort.get("name", "")
        elapsed_s = effort.get("elapsed_time_s")
        distance_m = effort.get("distance_m", 0)

        if not name or not elapsed_s or elapsed_s <= 0:
            continue

        # Derive pace in min/km from elapsed time and distance
        pace_min_per_km: float | None = None
        if distance_m > 0:
            pace_min_per_km = round((elapsed_s / 60.0) / (distance_m / 1000.0), 2)

        # Find previous best in window (excluding current run — history not yet written)
        prev_bests: list[int] = []
        for hist_entry in window_history:
            efforts_in_entry = hist_entry.get("strava_efforts", {})
            if name in efforts_in_entry:
                t = efforts_in_entry[name]
                if isinstance(t, int) and t > 0:
                    prev_bests.append(t)

        prev_best_s: int | None = min(prev_bests) if prev_bests else None
        improvement_s: int | None = None
        is_new_best = False

        if prev_best_s is not None:
            improvement_s = prev_best_s - elapsed_s  # positive = faster
            is_new_best = improvement_s > 0
        else:
            # First ever recorded — it's a new best by definition
            is_new_best = True

        results.append({
            "name": name,
            "elapsed_time_s": elapsed_s,
            "pace_min_per_km": pace_min_per_km,
            "prev_best_s": prev_best_s,
            "improvement_s": improvement_s,
            "window_days": window_days,
            "is_new_best": is_new_best,
        })

    return results


def backfill_from_strava(
    n: int,
    zone_config: "ZoneConfig",  # type: ignore[name-defined]  # noqa: F821
    access_token: str | None = None,
) -> list[dict[str, Any]]:
    """
    Estimate hrTSS from Strava activity summaries (no stream data needed).

    Uses the Banister-approximation: hrTSS ≈ (duration_h × (avg_hr / threshold_hr)²) × 100.
    Less accurate than stream-derived hrTSS but sufficient for PMC trends.
    Only fills dates that don't already have a history entry.

    Parameters
    ----------
    n : int
        Number of recent run summaries to fetch.
    zone_config : ZoneConfig
        Used to get threshold_hr for TSS estimation.
    access_token : str, optional
        Pre-fetched Strava access token.

    Returns
    -------
    list[dict]
        New entries added (already appended to history).
    """
    from biosystems.ingestion.strava import fetch_recent_runs

    summaries = fetch_recent_runs(n=n, access_token=access_token)
    existing = {e["date"] for e in load_history()}
    threshold_hr = float(zone_config.threshold_hr)

    new_entries: list[dict[str, Any]] = []
    for s in summaries:
        run_date = s.get("start_date_local", "")[:10]
        if not run_date or run_date in existing:
            continue

        avg_hr = float(s.get("average_heartrate") or 0)
        moving_s = float(s.get("moving_time") or 0)
        distance_m = float(s.get("distance") or 0)

        if avg_hr <= 0 or moving_s <= 0:
            continue

        duration_h = moving_s / 3600.0
        hr_ratio = avg_hr / threshold_hr
        hr_tss = round(duration_h * (hr_ratio ** 2) * 100, 1)

        pace_min_km: float | None = None
        if distance_m > 0:
            pace_min_km = round(moving_s / 60.0 / (distance_m / 1000.0), 2)

        entry = {
            "date": run_date,
            "hrTSS": hr_tss,
            "distance_km": round(distance_m / 1000.0, 2),
            "avg_hr": round(avg_hr, 1),
            "avg_pace_min_per_km": pace_min_km,
            "activity_name": s.get("name"),
            "source": "strava_summary_estimate",
        }
        append_run(entry)
        new_entries.append(entry)

    return new_entries
