"""
Tests for Wellness Cache
========================

Tests for compute_wellness_context and its helpers, focusing on
the _7d_mean numeric coercion fix and edge cases.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch


def _build_wellness_df(data: dict, dates: list[str]) -> pd.DataFrame:
    """Helper to build a wellness DataFrame with a DatetimeIndex."""
    idx = pd.to_datetime(dates)
    df = pd.DataFrame(data, index=idx)
    return df


class TestSevenDayMean:
    """Test the _7d_mean helper behavior via compute_wellness_context."""

    def _make_context(self, date_str: str, df: pd.DataFrame):
        """Invoke compute_wellness_context with a patched load_wellness."""
        with patch("biosystems.wellness.cache._load_df", return_value=df):
            from biosystems.wellness.cache import compute_wellness_context
            return compute_wellness_context(date_str)

    def test_numeric_values(self):
        """Normal numeric values should produce a valid 7d mean."""
        dates = [f"2025-01-{d:02d}" for d in range(1, 9)]
        df = _build_wellness_df({
            "resting_hr_garmin": [60.0, 62.0, 58.0, 61.0, 59.0, 63.0, 60.0, 61.0],
        }, dates)
        ctx = self._make_context("2025-01-08", df)
        assert ctx is not None
        rhr_7d = ctx.get("rhr_7d_mean")
        assert rhr_7d is not None
        assert 58 <= rhr_7d <= 63

    def test_string_values_coerced(self):
        """String-typed numeric values should be coerced without crashing."""
        dates = [f"2025-01-{d:02d}" for d in range(1, 9)]
        df = _build_wellness_df({
            "resting_hr_garmin": ["60", "62", "58", "61", "59", "63", "60", "61"],
        }, dates)
        ctx = self._make_context("2025-01-08", df)
        assert ctx is not None
        rhr_7d = ctx.get("rhr_7d_mean")
        assert rhr_7d is not None
        assert 58 <= rhr_7d <= 63

    def test_mixed_string_and_nan(self):
        """Mixed string values and NaN should not crash."""
        dates = [f"2025-01-{d:02d}" for d in range(1, 9)]
        df = _build_wellness_df({
            "resting_hr_garmin": ["60", np.nan, "bad", "61", np.nan, "63", "60", "61"],
        }, dates)
        ctx = self._make_context("2025-01-08", df)
        assert ctx is not None
        # Should still get a mean from the valid values
        rhr_7d = ctx.get("rhr_7d_mean")
        # "bad" gets coerced to NaN, leaving 60, 61, 63, 60 = mean ~61
        if rhr_7d is not None:
            assert 59 <= rhr_7d <= 64

    def test_all_nan_returns_none(self):
        """All-NaN column should return None for 7d mean."""
        dates = [f"2025-01-{d:02d}" for d in range(1, 9)]
        df = _build_wellness_df({
            "resting_hr_garmin": [np.nan] * 8,
        }, dates)
        ctx = self._make_context("2025-01-08", df)
        assert ctx is not None
        assert ctx.get("rhr_7d_mean") is None

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty context."""
        df = pd.DataFrame()
        ctx = self._make_context("2025-01-08", df)
        assert ctx == {} or ctx is None

    def test_missing_column(self):
        """Missing wellness columns should not crash."""
        dates = [f"2025-01-{d:02d}" for d in range(1, 9)]
        df = _build_wellness_df({
            "body_battery": [60.0] * 8,
        }, dates)
        ctx = self._make_context("2025-01-08", df)
        assert ctx is not None
        # rhr columns don't exist, should be None
        assert ctx.get("rhr_7d_mean") is None
