"""
Tests for src/biosystems/ingestion/strava.py

Covers: credential validation, parse_strava_streams, fetch_activity_streams
(mocked HTTP), fetch_recent_runs filtering, fetch_runs_since pagination,
and edge cases (missing streams, rate-limit HTML response, no heartrate data).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import requests

import biosystems.ingestion.strava as strava_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data=None, status_code=200, text=None):
    """Build a minimal mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(
            response=resp, request=MagicMock()
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _minimal_streams(n=5):
    """Return a minimal valid streams dict with n data points."""
    time = list(range(n))
    distance = [float(i * 10) for i in range(n)]
    hr = [150 + i for i in range(n)]
    velocity = [3.0 + i * 0.1 for i in range(n)]
    return {
        "time": time,
        "distance": distance,
        "heartrate": hr,
        "velocity_smooth": velocity,
    }


# ---------------------------------------------------------------------------
# _get_credentials
# ---------------------------------------------------------------------------


def test_get_credentials_raises_when_missing(monkeypatch):
    for var in ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(EnvironmentError, match="Missing Strava credentials"):
        strava_mod._get_credentials()


def test_get_credentials_raises_partial_missing(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "abc")
    monkeypatch.delenv("STRAVA_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("STRAVA_REFRESH_TOKEN", raising=False)
    with pytest.raises(EnvironmentError, match="STRAVA_CLIENT_SECRET"):
        strava_mod._get_credentials()


def test_get_credentials_returns_tuple(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "cid")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "csec")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "rtok")
    result = strava_mod._get_credentials()
    assert result == ("cid", "csec", "rtok")


# ---------------------------------------------------------------------------
# parse_strava_streams
# ---------------------------------------------------------------------------


def test_parse_strava_streams_raises_without_time():
    with pytest.raises(ValueError, match="'time' stream is required"):
        strava_mod.parse_strava_streams(
            {"heartrate": [150, 155]},
            start_date="2025-05-01T10:00:00Z",
        )


def test_parse_strava_streams_basic_shape():
    streams = _minimal_streams(n=5)
    df = strava_mod.parse_strava_streams(streams, start_date="2025-05-01T10:00:00Z")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert df.index.tz is not None  # UTC-aware index
    assert "hr" in df.columns
    assert "speed_mps" in df.columns
    assert "dist" in df.columns
    assert "dt" in df.columns
    assert "distance_cumulative_km" in df.columns


def test_parse_strava_streams_hr_zero_replaced_with_nan():
    streams = _minimal_streams(n=3)
    streams["heartrate"] = [0, 150, 0]
    df = strava_mod.parse_strava_streams(streams, start_date="2025-05-01T10:00:00Z")
    assert np.isnan(df["hr"].iloc[0])
    assert df["hr"].iloc[1] == 150.0
    assert np.isnan(df["hr"].iloc[2])


def test_parse_strava_streams_cadence_doubled():
    """Strava single-foot cadence should be doubled to match FIT convention."""
    streams = _minimal_streams(n=3)
    streams["cadence"] = [90, 91, 92]
    df = strava_mod.parse_strava_streams(streams, start_date="2025-05-01T10:00:00Z")
    assert df["cadence"].iloc[1] == 182.0


def test_parse_strava_streams_no_heartrate_column_is_nan():
    streams = _minimal_streams(n=3)
    del streams["heartrate"]
    df = strava_mod.parse_strava_streams(streams, start_date="2025-05-01T10:00:00Z")
    assert df["hr"].isna().all()


def test_parse_strava_streams_latlng_unpacked():
    streams = _minimal_streams(n=3)
    streams["latlng"] = [[37.1, -122.0], [37.2, -122.1], [37.3, -122.2]]
    df = strava_mod.parse_strava_streams(streams, start_date="2025-05-01T10:00:00Z")
    assert df["latitude"].iloc[0] == pytest.approx(37.1)
    assert df["longitude"].iloc[2] == pytest.approx(-122.2)


def test_parse_strava_streams_distance_cumulative():
    streams = _minimal_streams(n=4)
    streams["distance"] = [0.0, 100.0, 250.0, 400.0]
    df = strava_mod.parse_strava_streams(streams, start_date="2025-05-01T10:00:00Z")
    assert df["distance_cumulative_km"].iloc[-1] == pytest.approx(0.4)
    # dist column should be diffs (prepend=0): [0, 100, 150, 150]
    assert df["dist"].iloc[1] == pytest.approx(100.0)
    assert df["dist"].iloc[2] == pytest.approx(150.0)


def test_parse_strava_streams_datetime_object_start():
    streams = _minimal_streams(n=2)
    start = datetime(2025, 6, 1, 8, 30, 0, tzinfo=timezone.utc)
    df = strava_mod.parse_strava_streams(streams, start_date=start)
    assert df.index[0] == pd.Timestamp("2025-06-01 08:30:00+00:00")


# ---------------------------------------------------------------------------
# _parse_best_efforts
# ---------------------------------------------------------------------------


def test_parse_best_efforts_filters_zero_distance():
    raw = [
        {"name": "1K", "distance": 1000, "elapsed_time": 240, "moving_time": 238},
        {"name": "bad", "distance": 0, "elapsed_time": 100, "moving_time": 100},
    ]
    result = strava_mod._parse_best_efforts(raw)
    assert len(result) == 1
    assert result[0]["name"] == "1K"


def test_parse_best_efforts_pr_rank_preserved():
    raw = [{"name": "5K", "distance": 5000, "elapsed_time": 1200, "moving_time": 1195, "pr_rank": 1}]
    result = strava_mod._parse_best_efforts(raw)
    assert result[0]["pr_rank"] == 1


# ---------------------------------------------------------------------------
# fetch_recent_runs — mocked HTTP
# ---------------------------------------------------------------------------


def test_fetch_recent_runs_filters_non_run_sport_types(monkeypatch):
    activities = [
        {"id": 1, "sport_type": "Run", "name": "Morning run"},
        {"id": 2, "sport_type": "Ride", "name": "Cycling"},
        {"id": 3, "sport_type": "TrailRun", "name": "Trail"},
        {"id": 4, "sport_type": "Swim", "name": "Swimming"},
        {"id": 5, "sport_type": "VirtualRun", "name": "Treadmill"},
    ]
    with patch("requests.get", return_value=_mock_response(activities)):
        result = strava_mod.fetch_recent_runs(n=10, access_token="tok")
    sport_types = {a["sport_type"] for a in result}
    assert sport_types <= {"Run", "TrailRun", "VirtualRun"}
    assert len(result) == 3


def test_fetch_recent_runs_respects_n_limit(monkeypatch):
    activities = [{"id": i, "sport_type": "Run"} for i in range(20)]
    with patch("requests.get", return_value=_mock_response(activities)):
        result = strava_mod.fetch_recent_runs(n=5, access_token="tok")
    assert len(result) == 5


def test_fetch_recent_runs_raises_on_http_error():
    with patch("requests.get", return_value=_mock_response(status_code=401)):
        with pytest.raises(requests.HTTPError):
            strava_mod.fetch_recent_runs(n=5, access_token="bad_token")


def test_fetch_recent_runs_raises_on_rate_limit_html():
    """Simulate Strava returning 429 on every attempt — should raise after retries."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 429
    resp.headers = {"Retry-After": "0"}  # avoid real sleep in tests
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    with patch("requests.get", return_value=resp):
        with patch("biosystems.ingestion.strava.time.sleep"):  # skip waits
            with pytest.raises(requests.HTTPError):
                strava_mod.fetch_recent_runs(n=5, access_token="tok")


# ---------------------------------------------------------------------------
# fetch_runs_since — pagination
# ---------------------------------------------------------------------------


def test_fetch_runs_since_returns_only_run_types():
    batch = [
        {"id": 10, "sport_type": "Run"},
        {"id": 11, "sport_type": "Ride"},
        {"id": 12, "sport_type": "TrailRun"},
    ]
    with patch("requests.get", return_value=_mock_response(batch)):
        result = strava_mod.fetch_runs_since("2025-01-01", access_token="tok")
    assert all(a["sport_type"] in {"Run", "TrailRun", "VirtualRun"} for a in result)
    assert len(result) == 2


def test_fetch_runs_since_paginates_until_empty():
    """Should stop when a page returns an empty list."""
    page_1 = [{"id": i, "sport_type": "Run"} for i in range(200)]
    page_2 = [{"id": i + 200, "sport_type": "Run"} for i in range(50)]
    page_3 = []

    responses = [_mock_response(page_1), _mock_response(page_2), _mock_response(page_3)]
    with patch("requests.get", side_effect=responses):
        result = strava_mod.fetch_runs_since("2025-01-01", access_token="tok")
    # page_1=200 runs + page_2=50 runs, page_3 empty terminates
    assert len(result) == 250


def test_fetch_runs_since_stops_on_partial_page():
    """If a page returns < 200 items, no further requests should be made."""
    batch = [{"id": i, "sport_type": "Run"} for i in range(5)]
    with patch("requests.get", return_value=_mock_response(batch)) as mock_get:
        strava_mod.fetch_runs_since("2025-01-01", access_token="tok")
    assert mock_get.call_count == 1


def test_fetch_runs_since_passes_after_epoch():
    """Verify the `after` parameter is set to a non-zero epoch timestamp."""
    batch = []
    with patch("requests.get", return_value=_mock_response(batch)) as mock_get:
        strava_mod.fetch_runs_since("2025-06-01", access_token="tok")
    call_kwargs = mock_get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    # 2025-06-01 UTC epoch > 1_700_000_000
    assert params["after"] > 1_700_000_000


# ---------------------------------------------------------------------------
# fetch_activity_streams — mocked HTTP (2-call flow)
# ---------------------------------------------------------------------------


def _activity_meta_response():
    return {
        "id": 99999,
        "start_date": "2025-05-15T08:00:00Z",
        "best_efforts": [
            {"name": "1K", "distance": 1000, "elapsed_time": 240, "moving_time": 238}
        ],
        "splits_metric": [],
        "max_heartrate": 175,
        "max_speed": 4.5,
        "calories": 500,
        "total_elevation_gain": 20.0,
        "perceived_exertion": None,
        "workout_type": 0,
        "device_name": "Garmin Forerunner 965",
        "description": None,
        "laps": [],
        "pr_count": 1,
    }


def _streams_api_response():
    """Simulate Strava key_by_type=true streams response."""
    n = 4
    return {
        "time": {"data": list(range(n)), "series_type": "time", "original_size": n, "resolution": "high"},
        "distance": {"data": [0.0, 10.0, 20.0, 30.0], "series_type": "time", "original_size": n, "resolution": "high"},
        "heartrate": {"data": [150, 155, 158, 160], "series_type": "time", "original_size": n, "resolution": "high"},
        "velocity_smooth": {"data": [3.0, 3.1, 3.2, 3.3], "series_type": "time", "original_size": n, "resolution": "high"},
    }


def test_fetch_activity_streams_returns_df_and_meta():
    resp1 = _mock_response(_activity_meta_response())
    resp2 = _mock_response(_streams_api_response())
    with patch("requests.get", side_effect=[resp1, resp2]):
        df, meta = strava_mod.fetch_activity_streams(99999, access_token="tok")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert meta["max_heartrate"] == 175
    assert len(meta["best_efforts"]) == 1
    assert meta["best_efforts"][0]["name"] == "1K"


def test_fetch_activity_streams_raises_on_missing_time_stream():
    resp1 = _mock_response(_activity_meta_response())
    streams_no_time = {k: v for k, v in _streams_api_response().items() if k != "time"}
    resp2 = _mock_response(streams_no_time)
    with patch("requests.get", side_effect=[resp1, resp2]):
        with pytest.raises(ValueError, match="'time' stream is required"):
            strava_mod.fetch_activity_streams(99999, access_token="tok")


def test_fetch_activity_streams_raises_on_activity_404():
    resp1 = _mock_response(status_code=404)
    with patch("requests.get", return_value=resp1):
        with pytest.raises(requests.HTTPError):
            strava_mod.fetch_activity_streams(99999, access_token="tok")


def test_fetch_activity_streams_raises_on_streams_404():
    resp1 = _mock_response(_activity_meta_response())
    resp2 = _mock_response(status_code=404)
    with patch("requests.get", side_effect=[resp1, resp2]):
        with pytest.raises(requests.HTTPError):
            strava_mod.fetch_activity_streams(99999, access_token="tok")


def test_fetch_activity_streams_handles_empty_best_efforts():
    activity = _activity_meta_response()
    activity["best_efforts"] = None
    resp1 = _mock_response(activity)
    resp2 = _mock_response(_streams_api_response())
    with patch("requests.get", side_effect=[resp1, resp2]):
        df, meta = strava_mod.fetch_activity_streams(99999, access_token="tok")
    assert meta["best_efforts"] == []
