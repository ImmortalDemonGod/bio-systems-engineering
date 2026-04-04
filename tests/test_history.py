"""
Tests for src/biosystems/analytics/history.py

Covers: append_run deduplication, load_history ordering, file-lock
concurrency safety, strava_activity_id keying, and detect_block_bests.
"""

from __future__ import annotations

import threading

import pytest

import biosystems.analytics.history as hist_mod

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    """Redirect history storage to a temp directory for each test."""
    monkeypatch.setenv("BIOSYSTEMS_HOME", str(tmp_path))
    yield tmp_path


# ---------------------------------------------------------------------------
# load_history
# ---------------------------------------------------------------------------


def test_load_history_empty():
    assert hist_mod.load_history() == []


def test_load_history_returns_sorted_by_date():
    hist_mod.append_run({"date": "2025-03-10", "hrTSS": 50.0})
    hist_mod.append_run({"date": "2025-01-01", "hrTSS": 30.0})
    hist_mod.append_run({"date": "2025-06-15", "hrTSS": 70.0})

    entries = hist_mod.load_history()
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# append_run — date-based deduplication (legacy)
# ---------------------------------------------------------------------------


def test_append_run_deduplicates_by_date():
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 40.0, "ef": 0.018})
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 55.0, "ef": 0.020})

    entries = hist_mod.load_history()
    assert len(entries) == 1
    assert entries[0]["hrTSS"] == 55.0  # last write wins


def test_append_run_multiple_dates_kept_separately():
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 40.0})
    hist_mod.append_run({"date": "2025-05-02", "hrTSS": 50.0})

    entries = hist_mod.load_history()
    assert len(entries) == 2


def test_append_run_stores_strava_efforts():
    efforts = {"1K": 240, "5K": 1250}
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 40.0}, strava_efforts=efforts)

    entries = hist_mod.load_history()
    assert entries[0]["strava_efforts"] == efforts


# ---------------------------------------------------------------------------
# append_run — activity_id-based deduplication
# ---------------------------------------------------------------------------


def test_append_run_deduplicates_by_activity_id():
    """Two writes with the same strava_activity_id should produce one entry."""
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 40.0, "strava_activity_id": 12345, "ef": 0.018})
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 55.0, "strava_activity_id": 12345, "ef": 0.020})

    entries = hist_mod.load_history()
    assert len(entries) == 1
    assert entries[0]["ef"] == 0.020


def test_append_run_different_activity_ids_same_date_kept_separately():
    """Two runs on the same date with different activity IDs must coexist."""
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 40.0, "strava_activity_id": 11111})
    hist_mod.append_run({"date": "2025-05-01", "hrTSS": 55.0, "strava_activity_id": 22222})

    entries = hist_mod.load_history()
    assert len(entries) == 2


# ---------------------------------------------------------------------------
# Concurrency safety
# ---------------------------------------------------------------------------


def test_append_run_concurrent_writes_no_data_loss():
    """Parallel threads must not lose entries due to race conditions."""
    n_threads = 20
    errors: list[Exception] = []

    def write_entry(i: int) -> None:
        try:
            hist_mod.append_run({
                "date": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "hrTSS": float(i),
                "strava_activity_id": 90000 + i,
            })
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write_entry, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Exceptions during concurrent writes: {errors}"
    entries = hist_mod.load_history()
    # Each thread wrote a unique activity_id so all must be present
    assert len(entries) == n_threads


# ---------------------------------------------------------------------------
# detect_block_bests
# ---------------------------------------------------------------------------


def test_detect_block_bests_first_ever():
    """First time an effort distance is seen should be marked is_new_best with no prev."""
    efforts = [{"name": "5K", "elapsed_time_s": 1200, "distance_m": 5000}]
    results = hist_mod.detect_block_bests(efforts)

    assert len(results) == 1
    r = results[0]
    assert r["name"] == "5K"
    assert r["is_new_best"] is True
    assert r["prev_best_s"] is None


def test_detect_block_bests_improvement_detected():
    hist_mod.append_run(
        {"date": "2025-01-01", "hrTSS": 50.0},
        strava_efforts={"5K": 1300},
    )
    efforts = [{"name": "5K", "elapsed_time_s": 1200, "distance_m": 5000}]
    results = hist_mod.detect_block_bests(efforts)

    r = results[0]
    assert r["is_new_best"] is True
    assert r["prev_best_s"] == 1300
    assert r["improvement_s"] == 100


def test_detect_block_bests_no_improvement():
    hist_mod.append_run(
        {"date": "2025-01-01", "hrTSS": 50.0},
        strava_efforts={"5K": 1100},
    )
    efforts = [{"name": "5K", "elapsed_time_s": 1200, "distance_m": 5000}]
    results = hist_mod.detect_block_bests(efforts)

    r = results[0]
    assert r["is_new_best"] is False
    assert r["prev_best_s"] == 1100


def test_detect_block_bests_window_days_restricts_history():
    """Efforts outside the window should not count as prior bests."""
    hist_mod.append_run(
        {"date": "2020-01-01", "hrTSS": 50.0},
        strava_efforts={"5K": 1100},
    )
    efforts = [{"name": "5K", "elapsed_time_s": 1200, "distance_m": 5000}]
    # 30-day window excludes the 2020 entry → current is treated as first-ever
    results = hist_mod.detect_block_bests(efforts, window_days=30)

    r = results[0]
    assert r["is_new_best"] is True
    assert r["prev_best_s"] is None
