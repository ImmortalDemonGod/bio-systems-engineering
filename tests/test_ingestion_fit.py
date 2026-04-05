"""
Tests for FIT file parser (src/biosystems/ingestion/fit.py).

Uses unittest.mock to avoid requiring a real .fit binary fixture.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import fitdecode  # type: ignore[import-untyped]
import pandas as pd
import pytest

from biosystems.ingestion.fit import parse_fit  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEMICIRCLE_SCALE = 180.0 / 2**31  # FIT semicircle → degrees conversion


def _make_record(
    ts: datetime,
    lat_deg: float = 35.5,
    lon_deg: float = -98.4,
    altitude: float = 350.0,
    heart_rate: int = 145,
    cadence: int = 82,
    speed: float = 3.5,
) -> MagicMock:
    """
    Create a MagicMock that simulates a FIT 'record' data message for use in tests.

    The mock is specified as a fitdecode.FitDataMessage, has its `name` set to "record",
    and provides FI T-like raw fields:
    - `timestamp` set from `ts`.
    - `position_lat` and `position_long` set as integer semicircle values derived from `lat_deg`/`lon_deg`.
    - `altitude`, `heart_rate`, `cadence`, and `speed` set from the corresponding arguments.

    Behavior:
    - `has_field(name)` returns True only for the keys listed above.
    - `get_value(name, fallback)` returns the stored value for `name` or `fallback` if absent.

    Parameters:
        ts (datetime): UTC timestamp to assign to the mock record.
        lat_deg (float): Latitude in degrees (converted to FIT semicircles).
        lon_deg (float): Longitude in degrees (converted to FIT semicircles).
        altitude (float): Altitude value to store.
        heart_rate (int): Heart rate value to store.
        cadence (int): Cadence value to store.
        speed (float): Speed value to store.

    Returns:
        MagicMock: A mock object masquerading as a fitdecode.FitDataMessage with the behavior described above.
    """
    frame = MagicMock(spec=fitdecode.FitDataMessage)
    frame.name = "record"

    # Store the raw semicircle values as FIT would
    fields = {
        "timestamp": ts,
        "position_lat": int(lat_deg / _SEMICIRCLE_SCALE),
        "position_long": int(lon_deg / _SEMICIRCLE_SCALE),
        "altitude": altitude,
        "heart_rate": heart_rate,
        "cadence": cadence,
        "speed": speed,
    }

    frame.has_field.side_effect = lambda name: name in fields
    frame.get_value.side_effect = lambda name, fallback=None: fields.get(name, fallback)
    return frame


def _parse_with_records(records: list) -> pd.DataFrame:
    """
    Run parse_fit using a patched FitReader that iterates over the provided mocked FIT records.

    Parameters:
        records (list): Iterable of mocked `fitdecode.FitDataMessage`-like objects to be yielded by the patched reader.

    Returns:
        pd.DataFrame: The DataFrame produced by `parse_fit` when consuming `records`.
    """
    mock_fit = MagicMock()
    mock_fit.__iter__ = MagicMock(return_value=iter(records))
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_fit)
    mock_cm.__exit__ = MagicMock(return_value=False)
    with patch("biosystems.ingestion.fit.fitdecode.FitReader", return_value=mock_cm):
        result: pd.DataFrame = parse_fit("fake.fit")
        return result


def _three_point_df() -> pd.DataFrame:
    """
    Create a DataFrame parsed from three mocked FIT record messages with consecutive UTC timestamps.

    Returns:
        pd.DataFrame: DataFrame with three rows (one per mocked record). The index is named "timestamp" and contains timezone-aware UTC datetimes; columns correspond to the values produced by parse_fit (for example, latitude/longitude, aliased lat/lon, ele, hr, cadence, speed).
    """
    records = [
        _make_record(ts=datetime(2025, 6, 1, 8, 0, i, tzinfo=timezone.utc))
        for i in range(3)
    ]
    return _parse_with_records(records)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseFitBasic:
    def test_returns_dataframe(self):
        """
        Verify that parsing a small set of mocked FIT records produces a pandas DataFrame.

        Asserts that calling the helper which parses three mocked FIT record messages returns an instance of `pandas.DataFrame`.
        """
        assert isinstance(_three_point_df(), pd.DataFrame)

    def test_row_count(self):
        records = [
            _make_record(ts=datetime(2025, 6, 1, 8, 0, i, tzinfo=timezone.utc))
            for i in range(5)
        ]
        assert len(_parse_with_records(records)) == 5

    def test_index_is_utc_datetime(self):
        df = _three_point_df()
        assert df.index.name == "timestamp"
        assert str(df.index.tz) == "UTC"

    def test_altitude_renamed_to_ele(self):
        df = _three_point_df()
        assert "ele" in df.columns
        assert "altitude" not in df.columns

    def test_heart_rate_renamed_to_hr(self):
        df = _three_point_df()
        assert "hr" in df.columns
        assert "heart_rate" not in df.columns

    def test_lat_alias_present(self):
        """parse_fit must expose lat column for GPX cross-compatibility."""
        df = _three_point_df()
        assert "lat" in df.columns, "lat alias column missing from FIT output"

    def test_lon_alias_present(self):
        """parse_fit must expose lon column for GPX cross-compatibility."""
        df = _three_point_df()
        assert "lon" in df.columns, "lon alias column missing from FIT output"

    def test_lat_lon_values_match_latitude_longitude(self):
        df = _three_point_df()
        pd.testing.assert_series_equal(
            df["lat"].reset_index(drop=True),
            df["latitude"].reset_index(drop=True),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            df["lon"].reset_index(drop=True),
            df["longitude"].reset_index(drop=True),
            check_names=False,
        )

    def test_semicircle_conversion(self):
        df = _three_point_df()
        assert abs(df["latitude"].iloc[0] - 35.5) < 0.01
        assert abs(df["longitude"].iloc[0] - (-98.4)) < 0.01

    def test_zero_hr_becomes_nan(self):
        rec = _make_record(ts=datetime(2025, 6, 1, 8, 0, 0, tzinfo=timezone.utc), heart_rate=0)
        df = _parse_with_records([rec])
        assert pd.isna(df["hr"].iloc[0])

    def test_zero_cadence_becomes_nan(self):
        rec = _make_record(ts=datetime(2025, 6, 1, 8, 0, 0, tzinfo=timezone.utc), cadence=0)
        df = _parse_with_records([rec])
        assert pd.isna(df["cadence"].iloc[0])

    def test_empty_file_raises_value_error(self):
        with pytest.raises(ValueError, match="No record messages"):
            _parse_with_records([])
