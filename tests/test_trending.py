"""
Tests for Trending & PMC Computation
=====================================

Tests for compute_pmc, compute_rolling_stats, and summarize_trend.
"""

from biosystems.analytics.trending import compute_pmc, compute_rolling_stats, summarize_trend


class TestComputePMC:
    """Test Performance Management Chart computation."""

    def test_empty_input(self):
        assert compute_pmc([]) == []

    def test_single_entry(self):
        entries = [{"date": "2025-01-01", "hrTSS": 50.0}]
        result = compute_pmc(entries)
        assert len(result) == 1
        assert result[0]["date"] == "2025-01-01"
        assert result[0]["hrTSS"] == 50.0
        assert result[0]["atl"] > 0
        assert result[0]["ctl"] > 0

    def test_rest_days_filled(self):
        """Days between runs should have hrTSS=None and decaying ATL/CTL."""
        entries = [
            {"date": "2025-01-01", "hrTSS": 100.0},
            {"date": "2025-01-04", "hrTSS": 50.0},
        ]
        result = compute_pmc(entries)
        assert len(result) == 4  # Jan 1, 2, 3, 4
        assert result[1]["hrTSS"] is None  # rest day
        assert result[2]["hrTSS"] is None  # rest day
        # ATL should decay on rest days
        assert result[1]["atl"] < result[0]["atl"]
        assert result[2]["atl"] < result[1]["atl"]

    def test_tsb_computed_before_load(self):
        """TSB should reflect state BEFORE today's training load."""
        entries = [
            {"date": "2025-01-01", "hrTSS": 100.0},
            {"date": "2025-01-02", "hrTSS": 0.0},
        ]
        result = compute_pmc(entries)
        # Day 1 TSB: CTL(0) - ATL(0) = 0 (before any load)
        assert result[0]["tsb"] == 0.0

    def test_same_day_multi_run_aggregation(self):
        """Multiple runs on the same day should have their TSS summed."""
        entries = [
            {"date": "2025-01-01", "hrTSS": 40.0, "distance_km": 5.0,
             "activity_name": "Morning Run"},
            {"date": "2025-01-01", "hrTSS": 60.0, "distance_km": 8.0,
             "activity_name": "Evening Run"},
        ]
        result = compute_pmc(entries)
        assert len(result) == 1
        # TSS should be summed
        assert result[0]["hrTSS"] == 100.0
        # Distance should be summed
        assert result[0]["distance_km"] == 13.0
        # Activity names combined
        assert "Morning Run" in result[0]["activity_name"]
        assert "Evening Run" in result[0]["activity_name"]

    def test_same_day_single_run_unchanged(self):
        """Single run per day should pass through unchanged."""
        entries = [
            {"date": "2025-01-01", "hrTSS": 50.0, "distance_km": 8.0,
             "activity_name": "Morning Run"},
        ]
        result = compute_pmc(entries)
        assert result[0]["hrTSS"] == 50.0
        assert result[0]["distance_km"] == 8.0
        assert result[0]["activity_name"] == "Morning Run"

    def test_ctl_atl_direction(self):
        """CTL should respond slower than ATL to load changes."""
        # 7 days of high load then 7 days rest
        entries = [{"date": f"2025-01-{d:02d}", "hrTSS": 100.0} for d in range(1, 8)]
        entries += [{"date": f"2025-01-{d:02d}", "hrTSS": 0.0} for d in range(8, 15)]
        result = compute_pmc(entries)

        # After 7 days of rest, ATL should have dropped more than CTL
        day7 = result[6]  # last training day
        day14 = result[13]  # after 7 rest days
        atl_drop = day7["atl"] - day14["atl"]
        ctl_drop = day7["ctl"] - day14["ctl"]
        assert atl_drop > ctl_drop  # ATL decays faster


class TestComputeRollingStats:
    """Test rolling EF/decoupling statistics."""

    def test_empty_input(self):
        assert compute_rolling_stats([]) == []

    def test_rolling_requires_minimum_data(self):
        """Rolling values should be None until enough data accumulates."""
        entries = [
            {"date": f"2025-01-{d:02d}", "hrTSS": 50.0, "ef": 0.019 + d * 0.0001}
            for d in range(1, 3)
        ]
        result = compute_rolling_stats(entries, window=10)
        # Only 2 entries, need at least 3 for rolling
        assert result[0]["ef_roll"] is None
        assert result[1]["ef_roll"] is None

    def test_rolling_computes_after_threshold(self):
        entries = [
            {"date": f"2025-01-{d:02d}", "hrTSS": 50.0, "ef": 0.019}
            for d in range(1, 6)
        ]
        result = compute_rolling_stats(entries, window=3)
        # After 3 entries, rolling should be populated
        assert result[2]["ef_roll"] is not None
        assert abs(result[2]["ef_roll"] - 0.019) < 0.001


class TestSummarizeTrend:
    """Test trend summary generation."""

    def test_empty_pmc(self):
        assert summarize_trend([], []) == {}

    def test_returns_latest_values(self):
        pmc = [
            {"date": "2025-01-01", "ctl": 30.0, "atl": 40.0, "tsb": -10.0},
            {"date": "2025-01-15", "ctl": 35.0, "atl": 30.0, "tsb": 5.0},
        ]
        rolling = [
            {"date": "2025-01-15", "ef": 0.019, "ef_gap": 0.018,
             "ef_roll": 0.0185, "decoupling_pct": 3.0, "decoupling_roll": 3.5},
        ]
        result = summarize_trend(pmc, rolling)
        assert result["ctl"] == 35.0
        assert result["atl"] == 30.0
        assert result["tsb"] == 5.0
        assert result["latest_run"]["ef"] == 0.019
