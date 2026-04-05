"""
Strava API Ingestion
====================

Pulls running activity data from the Strava V3 API and converts it into
a DataFrame matching the pipeline schema (same columns as parse_fit).

Authentication
--------------
Uses OAuth 2.0 refresh token flow. Requires three environment variables:

    STRAVA_CLIENT_ID      - App client ID from https://www.strava.com/settings/api
    STRAVA_CLIENT_SECRET  - App client secret
    STRAVA_REFRESH_TOKEN  - Long-lived refresh token (from initial OAuth dance)

The refresh token is exchanged for a short-lived access token on every call.
No tokens are written to disk by this module.

Output Schema
-------------
Returns a DataFrame with a UTC DatetimeIndex and columns:

    hr                     : float  (bpm, NaN if absent)
    cadence                : float  (spm, NaN if absent)
    ele                    : float  (metres, NaN if absent)
    latitude               : float  (degrees, NaN if no GPS)
    longitude              : float  (degrees, NaN if no GPS)
    speed_mps              : float  (m/s from Strava smooth velocity)
    dist                   : float  (segment distance in metres)
    dt                     : float  (elapsed seconds for this segment)
    pace_sec_km            : float  (seconds per km)
    distance_cumulative_km : float  (cumulative distance in km)
    moving                 : bool   (Strava moving state, if available)

This matches the schema produced by parse_fit() + add_derived_metrics().
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests

_TOKEN_URL = "https://www.strava.com/oauth/token"
_BASE_URL = "https://www.strava.com/api/v3"

# Streams to request — order doesn't matter, Strava aligns them by index
_STREAM_KEYS = "time,distance,latlng,altitude,heartrate,cadence,velocity_smooth,moving"

# ---------------------------------------------------------------------------
# Rate-limit-aware HTTP helper
# ---------------------------------------------------------------------------

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _get_with_backoff(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = 15,
    max_retries: int = 3,
) -> requests.Response:
    """
    GET with automatic retry on transient / rate-limit responses.

    Respects the ``Retry-After`` header when Strava returns 429.
    Falls back to exponential backoff (1 s, 2 s, 4 s) for 5xx errors.

    Raises
    ------
    requests.HTTPError
        On non-retryable errors (4xx except 429) or exhausted retries.
    """
    for attempt in range(max_retries + 1):
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)

        if resp.status_code not in _RETRYABLE_STATUSES:
            resp.raise_for_status()
            return resp

        if attempt == max_retries:
            resp.raise_for_status()  # Exhausted — let caller handle

        # Respect Retry-After for 429; exponential backoff for 5xx
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            time.sleep(retry_after)
        else:
            time.sleep(2 ** attempt)

    # Unreachable, but satisfies type checkers
    raise requests.HTTPError("Retry loop exited unexpectedly")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def _get_credentials() -> tuple[str, str, str]:
    """
    Load Strava OAuth credentials from environment variables.
    
    Returns:
        tuple[str, str, str]: (client_id, client_secret, refresh_token) read from
            STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN.
    
    Raises:
        OSError: If any of the required environment variables are missing.
    """
    missing = [
        v
        for v in ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")
        if not os.environ.get(v)
    ]
    if missing:
        raise OSError(
            f"Missing Strava credentials in environment: {', '.join(missing)}\n"
            "Set STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN."
        )
    return (
        os.environ["STRAVA_CLIENT_ID"],
        os.environ["STRAVA_CLIENT_SECRET"],
        os.environ["STRAVA_REFRESH_TOKEN"],
    )


def _refresh_access_token() -> str:
    """
    Exchange the refresh token for a short-lived access token.

    Returns
    -------
    str
        Bearer access token (valid for ~6 hours).

    Raises
    ------
    EnvironmentError
        If credentials are missing.
    requests.HTTPError
        If Strava rejects the token request.
    """
    client_id, client_secret, refresh_token = _get_credentials()

    resp = requests.post(
        _TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


# ---------------------------------------------------------------------------
# Activity listing
# ---------------------------------------------------------------------------


def fetch_activity_efforts(
    activity_id: int,
    access_token: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Fetch best efforts for a single activity without pulling full streams.

    Much faster than fetch_activity_streams — only one API call.

    Returns
    -------
    (run_date, best_efforts)
        run_date : ISO date string (YYYY-MM-DD, local time)
        best_efforts : parsed list matching BestEffort schema
    """
    token = access_token or _refresh_access_token()
    resp = _get_with_backoff(
        f"{_BASE_URL}/activities/{activity_id}",
        headers=_auth_headers(token),
        params={"include_all_efforts": True},
    )
    activity = resp.json()
    run_date = activity.get("start_date_local", "")[:10]
    efforts = _parse_best_efforts(activity.get("best_efforts") or [])
    return run_date, efforts


def fetch_runs_since(
    after_date: str,
    access_token: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return all running activities since a given date, paginating as needed.

    Parameters
    ----------
    after_date : str
        ISO date string (YYYY-MM-DD). Activities with start_date_local >= this
        date are returned.
    access_token : str, optional
        Pre-fetched access token. If None, obtained via refresh flow.

    Returns
    -------
    list[dict]
        All SummaryActivity dicts with sport_type in {Run, TrailRun, VirtualRun},
        ordered newest-first (Strava default).
    """
    import calendar

    token = access_token or _refresh_access_token()

    # Convert date to Unix timestamp for Strava's `after` parameter
    dt = datetime.strptime(after_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    after_epoch = int(calendar.timegm(dt.timetuple()))

    run_types = {"Run", "TrailRun", "VirtualRun"}
    all_runs: list[dict[str, Any]] = []
    page = 1

    while True:
        resp = _get_with_backoff(
            f"{_BASE_URL}/athlete/activities",
            headers=_auth_headers(token),
            params={"per_page": 200, "page": page, "after": after_epoch},
        )
        batch = resp.json()
        if not batch:
            break
        runs = [a for a in batch if a.get("sport_type") in run_types]
        all_runs.extend(runs)
        if len(batch) < 200:
            break
        page += 1

    return all_runs


def fetch_recent_runs(n: int = 10, access_token: str | None = None) -> list[dict[str, Any]]:
    """
    Return the most recent running activities for the authenticated athlete.

    Parameters
    ----------
    n : int
        Number of activities to return (max 200 per Strava pagination).
    access_token : str, optional
        Pre-fetched access token. If None, a new token is obtained via
        the refresh flow (one extra HTTP request).

    Returns
    -------
    list[dict]
        List of SummaryActivity dicts from the Strava API, filtered to
        sport_type in {Run, TrailRun, VirtualRun}.

    Raises
    ------
    requests.HTTPError
        On any non-2xx response from Strava.
    """
    token = access_token or _refresh_access_token()
    per_page = min(n * 2, 200)  # over-fetch to account for non-Run activities

    resp = _get_with_backoff(
        f"{_BASE_URL}/athlete/activities",
        headers=_auth_headers(token),
        params={"per_page": per_page, "page": 1},
    )

    run_types = {"Run", "TrailRun", "VirtualRun"}
    activities = [a for a in resp.json() if a.get("sport_type") in run_types]
    return activities[:n]


# ---------------------------------------------------------------------------
# Stream fetching and conversion
# ---------------------------------------------------------------------------


def _streams_to_dict(raw_streams: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Unpack Strava stream list into {type: data} dict."""
    return {s["type"]: s["data"] for s in raw_streams}


def parse_strava_streams(
    streams: dict[str, list[Any]],
    start_date: str | datetime,
    activity_id: int | None = None,
) -> pd.DataFrame:
    """
    Convert Strava stream data into a pipeline-compatible DataFrame.

    Parameters
    ----------
    streams : dict
        Stream dict keyed by type (e.g. 'heartrate', 'distance'). Typically
        the output of ``_streams_to_dict()``.
    start_date : str or datetime
        Activity start time (UTC). Used to build absolute timestamps from
        the relative 'time' stream.
    activity_id : int, optional
        For error messages only.

    Returns
    -------
    pd.DataFrame
        DataFrame with UTC DatetimeIndex and pipeline schema columns.

    Raises
    ------
    ValueError
        If the 'time' stream is missing (required for index construction).
    """
    if "time" not in streams:
        raise ValueError(
            f"Activity {activity_id}: 'time' stream is required but was not returned by Strava."
        )

    # --- Build absolute UTC timestamp index ---
    if isinstance(start_date, str):
        start_dt = pd.Timestamp(start_date, tz="UTC")
    elif isinstance(start_date, datetime):
        start_dt = pd.Timestamp(start_date).tz_localize("UTC") if start_date.tzinfo is None else pd.Timestamp(start_date).tz_convert("UTC")
    else:
        start_dt = pd.Timestamp(start_date, tz="UTC")

    time_offsets = pd.to_timedelta(streams["time"], unit="s")
    timestamps = start_dt + time_offsets

    len(streams["time"])
    df = pd.DataFrame(index=timestamps)
    df.index.name = "timestamp"

    # --- Heart rate ---
    if "heartrate" in streams:
        hr = pd.array(streams["heartrate"], dtype="float64")
        df["hr"] = hr
        df["hr"] = df["hr"].replace(0, np.nan)
    else:
        df["hr"] = np.nan

    # --- Cadence ---
    if "cadence" in streams:
        # Strava reports running cadence as single-foot RPM.
        # Multiply by 2 to get total steps per minute, matching FIT file convention.
        df["cadence"] = pd.array(streams["cadence"], dtype="float64") * 2
        df["cadence"] = df["cadence"].replace(0, np.nan)
    else:
        df["cadence"] = np.nan

    # --- Elevation ---
    if "altitude" in streams:
        df["ele"] = pd.array(streams["altitude"], dtype="float64")
    else:
        df["ele"] = np.nan

    # --- GPS coordinates ---
    if "latlng" in streams:
        latlng = streams["latlng"]
        df["latitude"] = [pt[0] if pt else np.nan for pt in latlng]
        df["longitude"] = [pt[1] if pt else np.nan for pt in latlng]
    else:
        df["latitude"] = np.nan
        df["longitude"] = np.nan

    # --- Moving flag ---
    if "moving" in streams:
        df["moving"] = streams["moving"]
    else:
        df["moving"] = True

    # --- Velocity and pace ---
    if "velocity_smooth" in streams:
        df["speed_mps"] = pd.array(streams["velocity_smooth"], dtype="float64")
        df["speed_mps"] = df["speed_mps"].replace(0, np.nan)
    else:
        df["speed_mps"] = np.nan

    df["pace_sec_km"] = (1000.0 / df["speed_mps"]).replace([np.inf, -np.inf], np.nan)

    # --- Segment distance and time delta ---
    # Strava's 'distance' is cumulative. Diff gives per-point segment metres.
    if "distance" in streams:
        dist_cumulative = pd.array(streams["distance"], dtype="float64")
        dist_diff = np.diff(dist_cumulative, prepend=0.0)
        df["dist"] = dist_diff
        df["distance_cumulative_km"] = dist_cumulative / 1000.0
    else:
        df["dist"] = np.nan
        df["distance_cumulative_km"] = np.nan

    # Time delta in seconds per point
    time_secs = np.array(streams["time"], dtype="float64")
    df["dt"] = np.diff(time_secs, prepend=0.0)

    # Fill first-point speed from second point (no delta at t=0)
    df["speed_mps"] = df["speed_mps"].bfill()
    df["pace_sec_km"] = df["pace_sec_km"].bfill()

    return df


def _parse_best_efforts(raw_efforts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extract best effort fields relevant to biosystems from raw Strava effort dicts.

    Returns a list of dicts matching the BestEffort model schema.
    """
    results = []
    for e in raw_efforts:
        name = e.get("name", "")
        distance_m = float(e.get("distance", 0))
        elapsed = int(e.get("elapsed_time", 0))
        moving = int(e.get("moving_time", elapsed))
        pr_rank = e.get("pr_rank")  # 1 = PR, 2 = 2nd best, None = not ranked
        start_offset = e.get("start_index")  # sample index, close enough for offset

        if distance_m > 0 and elapsed > 0:
            results.append({
                "name": name,
                "distance_m": distance_m,
                "elapsed_time_s": elapsed,
                "moving_time_s": moving,
                "pr_rank": pr_rank,
                "start_offset_s": start_offset,
            })
    return results


def fetch_activity_streams(
    activity_id: int,
    access_token: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Fetch streams for a single activity and return a pipeline-ready DataFrame
    together with full activity metadata.

    Parameters
    ----------
    activity_id : int
        Strava activity ID.
    access_token : str, optional
        Pre-fetched access token. If None, obtained via refresh flow.

    Returns
    -------
    df : pd.DataFrame
        Pipeline-compatible DataFrame (same schema as parse_fit + add_derived_metrics).
    activity_meta : dict
        Full activity metadata including best_efforts, splits_metric, max_heartrate,
        max_speed, calories, total_elevation_gain, perceived_exertion, workout_type,
        device_name, description, laps, and pr_count.

    Raises
    ------
    requests.HTTPError
        On non-2xx Strava response.
    ValueError
        If required streams are missing.
    """
    token = access_token or _refresh_access_token()

    # Fetch full activity detail (include_all_efforts=True gets best_efforts list)
    activity_resp = _get_with_backoff(
        f"{_BASE_URL}/activities/{activity_id}",
        headers=_auth_headers(token),
        params={"include_all_efforts": True},
    )
    activity = activity_resp.json()
    start_date = activity["start_date"]  # ISO 8601 UTC

    # Extract all activity metadata
    best_efforts = _parse_best_efforts(activity.get("best_efforts") or [])
    activity_meta: dict[str, Any] = {
        "best_efforts": best_efforts,
        "splits_metric": activity.get("splits_metric") or [],
        "max_heartrate": activity.get("max_heartrate"),
        "max_speed": activity.get("max_speed"),
        "calories": activity.get("calories"),
        "total_elevation_gain": activity.get("total_elevation_gain"),
        "perceived_exertion": activity.get("perceived_exertion"),
        "workout_type": activity.get("workout_type"),
        "device_name": activity.get("device_name"),
        "description": activity.get("description"),
        "laps": activity.get("laps") or [],
        "pr_count": int(activity.get("pr_count") or 0),
    }

    # Fetch streams
    streams_resp = _get_with_backoff(
        f"{_BASE_URL}/activities/{activity_id}/streams",
        headers=_auth_headers(token),
        params={"keys": _STREAM_KEYS, "key_by_type": True},
    )

    # Strava returns a dict keyed by stream type when key_by_type=true
    raw = streams_resp.json()
    # Unpack: each value is a stream object with a 'data' key
    streams = {k: v["data"] for k, v in raw.items() if isinstance(v, dict) and "data" in v}

    df = parse_strava_streams(streams, start_date=start_date, activity_id=activity_id)
    return df, activity_meta


# ---------------------------------------------------------------------------
# Convenience: fetch latest run
# ---------------------------------------------------------------------------


def fetch_latest_run(
    access_token: str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    """
    Fetch the most recent running activity and return (summary, DataFrame, activity_meta).

    Parameters
    ----------
    access_token : str, optional
        Pre-fetched access token. Obtained via refresh if not provided.

    Returns
    -------
    summary : dict
        Strava SummaryActivity dict (distance, moving_time, start_date, name, …).
    df : pd.DataFrame
        Pipeline-ready DataFrame of streams.
    activity_meta : dict
        Full activity metadata including best_efforts, splits_metric, and other fields.

    Raises
    ------
    RuntimeError
        If no recent runs are found.
    """
    token = access_token or _refresh_access_token()

    runs = fetch_recent_runs(n=1, access_token=token)
    if not runs:
        raise RuntimeError("No recent running activities found on this Strava account.")

    summary = runs[0]
    df, activity_meta = fetch_activity_streams(summary["id"], access_token=token)
    return summary, df, activity_meta
