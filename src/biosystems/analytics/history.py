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
from pathlib import Path
from typing import Any

from filelock import FileLock


def history_path() -> Path:
    """
    Return the filesystem path to the local run history file.
    
    Ensures the base directory exists (uses $BIOSYSTEMS_HOME if set, otherwise ~/.biosystems).
    
    Returns:
        Path: Path to the `history.jsonl` file inside the base directory.
    """
    base = Path(os.environ.get("BIOSYSTEMS_HOME", Path.home() / ".biosystems"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "history.jsonl"


def _lock_path() -> Path:
    """Return the advisory lock file path alongside the history file."""
    return history_path().with_suffix(".lock")


def load_history() -> list[dict[str, Any]]:
    """
    Load the persistent run history from the history JSON Lines file and return deduplicated entries sorted by ascending date.
    
    Reads each non-empty line as a JSON object (invalid JSON lines are ignored). If the history file does not exist, returns an empty list. Deduplication keys entries by `strava_activity_id` when present (keyed as `id:{strava_activity_id}`) and otherwise by the entry's `date` (last-write-wins for date-only entries).
    
    Returns:
        list[dict[str, Any]]: A list of run-entry objects sorted by `date` (ISO yyyy-mm-dd strings). Each entry contains at minimum:
            - `date` (str): ISO date string.
            - `hrTSS` (float).
        Optional keys that may appear in entries include: `ef`, `ef_gap`, `decoupling_pct`, `distance_km`, `avg_hr`, `avg_pace_min_per_km`, `avg_cadence`, `activity_name`, and `strava_activity_id`.
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

    # Dedup: activity_id-keyed entries coexist; date-only entries dedup by date
    by_key: dict[str, dict[str, Any]] = {}
    for e in entries:
        activity_id = e.get("strava_activity_id")
        if activity_id:
            key = f"id:{activity_id}"
        else:
            key = e.get("date", "")
        if key:
            by_key[key] = e

    return sorted(by_key.values(), key=lambda x: x["date"])


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

    try:
        lock = FileLock(str(_lock_path()), timeout=15)
    except Exception as exc:
        raise RuntimeError(f"Cannot acquire history lock: {exc}") from exc

    with lock:
        existing = load_history()

        # Dedup by activity_id when present, else by date
        activity_id = entry.get("strava_activity_id")
        if activity_id:
            by_key: dict[str, dict[str, Any]] = {}
            for e in existing:
                eid = e.get("strava_activity_id")
                k = f"id:{eid}" if eid else e.get("date", "")
                if k:
                    by_key[k] = e
            by_key[f"id:{activity_id}"] = entry
        else:
            by_key = {e.get("strava_activity_id") and f"id:{e['strava_activity_id']}" or e["date"]: e
                      for e in existing if e.get("date")}
            by_key[entry["date"]] = entry

        path = history_path()
        lines = [json.dumps(e, separators=(",", ":")) for e in sorted(by_key.values(), key=lambda x: x["date"])]
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
    zone_config: ZoneConfig,  # type: ignore[name-defined]  # noqa: F821
    access_token: str | None = None,
) -> list[dict[str, Any]]:
    """
    Estimate hrTSS for recent Strava run summaries and append entries for dates not already present in history.
    
    Uses the Banister approximation: hrTSS ≈ (duration_h × (avg_hr / threshold_hr)²) × 100. Fetches up to `n` recent run summaries, skips activities missing required fields, and appends a compact estimated entry (including date, hrTSS, distance_km, avg_hr, optional avg_pace_min_per_km, activity_name, and source) for each new date.
    
    Parameters:
        n (int): Number of recent run summaries to fetch from Strava.
        zone_config (ZoneConfig): Provides `threshold_hr` for the TSS estimation.
        access_token (str | None): Optional Strava access token to use for the fetch.
    
    Returns:
        list[dict[str, Any]]: Entries that were added to history (each entry as written to the history file).
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
