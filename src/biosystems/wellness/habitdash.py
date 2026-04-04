"""
HabitDash API Client
====================

Fetches wellness telemetry (Whoop + Garmin) from the HabitDash aggregation API.

Requires HABITDASH_API_KEY environment variable.
Rate limit: ~4 req/min → 15s inter-request delay (matches old cultivation sync).
Retry logic: up to 3 attempts on 429 with exponential backoff.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.habitdash.com/v1"
_REQUEST_DELAY = 15.0  # seconds between requests (matches old cultivation sync)
_MAX_RETRIES   = 3
_RETRY_WAIT    = 60.0  # seconds to wait after a 429


# ── Field ID registry ────────────────────────────────────────────────────────
# These IDs are stable across accounts; they identify metric types, not users.

FIELD_IDS: dict[str, dict[str, int]] = {
    "whoop": {
        "hrv_rmssd":              86,   # Heart Rate Variability RMSSD (ms)
        "resting_hr":             87,   # Resting Heart Rate (bpm)
        "recovery_score":         88,   # Recovery Score (0–100)
        "sleep_score":           107,   # Sleep Performance Score (0–100)
        "sleep_duration_s":      101,   # Total Sleep Duration (seconds)
        "sleep_disturbances_ph":  93,   # Sleep Disturbances per Hour
        "sleep_consistency":     106,   # Sleep Consistency (%)
        "strain_score":          112,   # Day Strain Score
        "skin_temp_c":           340,   # Skin Temperature (°C)
        "respiratory_rate":      105,   # Sleep Respiratory Rate (rpm)
    },
    "garmin": {
        "resting_hr":            162,   # Resting Heart Rate (bpm)
        "body_battery":          188,   # Body Battery (0–100)
        "steps":                 170,   # Daily Steps
        "active_time_s":         173,   # Total Active Time (seconds)
        "avg_stress":            176,   # Average Stress Level
        "respiratory_rate":      191,   # Sleep Respiratory Rate (rpm)
        "vo2max":                187,   # VO2 Max (ml/kg/min)
    },
}

# Canonical column names written to the wellness cache parquet.
# Format: (source, field_key) → column_name
COLUMN_MAP: dict[tuple[str, str], str] = {
    ("whoop", "hrv_rmssd"):             "hrv_rmssd",
    ("whoop", "resting_hr"):            "resting_hr_whoop",
    ("whoop", "recovery_score"):        "recovery_score",
    ("whoop", "sleep_score"):           "sleep_score",
    ("whoop", "sleep_duration_s"):      "sleep_duration_s",
    ("whoop", "sleep_disturbances_ph"): "sleep_disturbances_ph",
    ("whoop", "sleep_consistency"):     "sleep_consistency",
    ("whoop", "strain_score"):          "strain_score",
    ("whoop", "skin_temp_c"):           "skin_temp_c",
    ("whoop", "respiratory_rate"):      "respiratory_rate_whoop",
    ("garmin", "resting_hr"):           "resting_hr_garmin",
    ("garmin", "body_battery"):         "body_battery",
    ("garmin", "steps"):                "steps",
    ("garmin", "active_time_s"):        "active_time_s",
    ("garmin", "avg_stress"):           "avg_stress",
    ("garmin", "respiratory_rate"):     "respiratory_rate_garmin",
    ("garmin", "vo2max"):               "vo2max",
}


class HabitDashClient:
    """Thin wrapper around the HabitDash REST API."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("HABITDASH_API_KEY", "")
        if not key:
            raise ValueError(
                "HABITDASH_API_KEY not set. "
                "Export it or pass api_key= explicitly."
            )
        self._session = requests.Session()
        self._session.headers.update({
            "accept":    "application/json",
            "x-api-key": key,
        })

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """GET request with header-aware rate limiting and 429 retry."""
        url = f"{BASE_URL}/{endpoint}/"
        for attempt in range(1, _MAX_RETRIES + 1):
            time.sleep(_REQUEST_DELAY)
            try:
                resp = self._session.get(url, params=params, timeout=15)

                # Honor rate-limit headers proactively
                remaining = resp.headers.get("x-ratelimit-remaining")
                reset_secs = resp.headers.get("x-ratelimit-reset")
                if remaining is not None and int(remaining) == 0 and reset_secs is not None:
                    wait = min(int(reset_secs) + 1, 3600)
                    log.warning("Rate limit exhausted — waiting %ds for reset", wait)
                    time.sleep(wait)

                if resp.status_code == 429:
                    wait = _RETRY_WAIT * attempt
                    log.warning("429 rate-limit on %s — waiting %.0fs (attempt %d/%d)",
                                endpoint, wait, attempt, _MAX_RETRIES)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                # HabitDash may wrap results in {"results": [...]} or return a plain list
                if isinstance(data, dict):
                    return data.get("results", data)
                return data
            except requests.exceptions.RequestException as exc:
                log.error("Request failed (%s): %s", url, exc)
                if attempt == _MAX_RETRIES:
                    return None
        return None

    def fetch_metric(
        self,
        source: str,
        field_key: str,
        date_start: str,
        date_end: str,
    ) -> list[dict[str, Any]]:
        """
        Fetch a single metric for a date range.

        Parameters
        ----------
        source : str
            "whoop" or "garmin"
        field_key : str
            Key from FIELD_IDS[source]
        date_start, date_end : str
            YYYY-MM-DD inclusive range

        Returns
        -------
        list[dict]
            [{"date": "YYYY-MM-DD", "value": float}, ...]
        """
        field_id = FIELD_IDS.get(source, {}).get(field_key)
        if not field_id:
            log.warning("No field ID for %s/%s — skipping", source, field_key)
            return []
        result = self._get("data", params={
            "field_id":   field_id,
            "date_start": date_start,
            "date_end":   date_end,
        })
        if not result:
            return []
        if isinstance(result, list):
            return result
        return []

    def fetch_all_metrics(
        self,
        date_start: str,
        date_end: str,
    ) -> list[dict[str, Any]]:
        """
        Fetch every metric in FIELD_IDS for the given date range.

        Returns flat list of {"date", "column", "value"} records.
        """
        records: list[dict[str, Any]] = []
        for source, fields in FIELD_IDS.items():
            for field_key in fields:
                col = COLUMN_MAP.get((source, field_key))
                if not col:
                    continue
                rows = self.fetch_metric(source, field_key, date_start, date_end)
                for row in rows:
                    date_val = row.get("date")
                    value    = row.get("value")
                    if date_val is not None and value is not None:
                        records.append({"date": date_val, "column": col, "value": value})
                        log.debug("  %s %s %s = %s", source, field_key, date_val, value)
        return records
