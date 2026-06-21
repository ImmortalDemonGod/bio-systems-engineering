"""
Tests for Grade Adjusted Pace (GAP) Calculations
=================================================

Tests Minetti's equation and all GAP calculation functions.
"""

import numpy as np
import pandas as pd
import pytest

from biosystems.models import HeartRateZone, ZoneConfig
from biosystems.physics.gap import (
    calculate_average_gap,
    calculate_gap_from_dataframe,
    calculate_gap_segment,
    calculate_grade_percent,
    check_elevation_quality,
    minetti_energy_cost,
)
from biosystems.physics.metrics import run_metrics


class TestElevationQuality:
    """Test elevation data quality checks."""

    def test_reliable_elevation(self):
        """Test ok signal for reasonable grade variation."""
        df = pd.DataFrame({
            'ele': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            'dist': [10.0] * 11
        })
        is_ok, reason = check_elevation_quality(df)
        assert is_ok is True
        assert reason == "ok"

    def test_corrupted_jitter(self):
        """Test detection of extreme vertical jitter (>45% grade spikes)."""
        # Create a series with huge elevation jumps relative to distance
        df = pd.DataFrame({
            'ele': [100.0, 150.0, 100.0, 150.0, 100.0, 150.0, 100.0, 150.0, 100.0, 150.0, 100.0],
            'dist': [1.0] * 11  # 50m jump over 1m distance = 5000% grade
        })
        is_ok, reason = check_elevation_quality(df)
        assert is_ok is False
        assert "elevation data likely corrupted" in reason

    def test_insufficient_data(self):
        """Test failure on too few points."""
        df = pd.DataFrame({'ele': [100, 101], 'dist': [10, 10]})
        is_ok, reason = check_elevation_quality(df)
        assert is_ok is False
        assert "insufficient elevation data" in reason

    def test_missing_columns(self):
        """Test failure on missing columns."""
        df = pd.DataFrame({'foo': [1, 2, 3]})
        is_ok, reason = check_elevation_quality(df)
        assert is_ok is False
        assert "column missing" in reason


class TestCalculateGradePercent:
    """Test grade percentage calculation."""

    def test_flat_ground(self):
        """Test flat ground (0% grade)."""
        grade = calculate_grade_percent(0, 1000)
        assert grade == 0.0

    def test_uphill_5_percent(self):
        """Test 5% uphill grade."""
        grade = calculate_grade_percent(50, 1000)
        assert grade == 5.0

    def test_downhill_3_percent(self):
        """Test 3% downhill grade."""
        grade = calculate_grade_percent(-30, 1000)
        assert grade == -3.0

    def test_zero_distance(self):
        """Test zero distance returns 0%."""
        grade = calculate_grade_percent(10, 0)
        assert grade == 0.0

    def test_steep_uphill(self):
        """Test steep 15% grade."""
        grade = calculate_grade_percent(150, 1000)
        assert grade == 15.0


class TestMinettiEnergyCost:
    """Test Minetti's energy cost equation."""

    def test_flat_ground_baseline(self):
        """Test flat ground returns normalized cost of 1.0."""
        cost = minetti_energy_cost(0.0)
        assert cost == pytest.approx(1.0, rel=0.01)

    def test_uphill_5_percent(self):
        """Test 5% uphill costs more energy."""
        cost = minetti_energy_cost(5.0)
        assert cost > 1.0
        assert cost == pytest.approx(1.301, rel=0.01)

    def test_uphill_10_percent(self):
        """Test 10% uphill costs significantly more."""
        cost = minetti_energy_cost(10.0)
        assert cost > 1.5

    def test_downhill_5_percent(self):
        """Test 5% downhill costs less energy."""
        cost = minetti_energy_cost(-5.0)
        assert cost < 1.0

    def test_steep_uphill(self):
        """Test very steep uphill (20%)."""
        cost = minetti_energy_cost(20.0)
        assert cost > 2.0


class TestCalculateGAPSegment:
    """Test single segment GAP calculation."""

    def test_flat_ground_no_adjustment(self):
        """Test flat ground pace is unchanged."""
        pace = 300  # 5:00/km in seconds
        gap = calculate_gap_segment(pace, 0.0)
        assert gap == pytest.approx(pace, rel=0.01)

    def test_uphill_faster_gap(self):
        """Test uphill pace adjusts to faster GAP."""
        pace = 300  # 5:00/km actual
        gap = calculate_gap_segment(pace, 5.0)
        assert gap < pace  # GAP should be faster (lower number)
        assert gap == pytest.approx(230.5, rel=0.01)

    def test_downhill_slower_gap(self):
        """Test downhill pace adjusts to slower GAP."""
        pace = 240  # 4:00/km actual
        gap = calculate_gap_segment(pace, -5.0)
        assert gap > pace  # GAP should be slower (higher number)

    def test_very_slow_uphill(self):
        """Test slow uphill pace."""
        pace = 420  # 7:00/km actual
        gap = calculate_gap_segment(pace, 10.0)
        assert gap < pace


class TestCalculateGAPFromDataFrame:
    """Test DataFrame GAP calculation."""

    def test_simple_dataframe(self):
        """
        Validate GAP computation on a simple uniformly uphill DataFrame.

        Creates a 10-row DataFrame with constant pace, 5 m elevation gain per segment, and 100 m segment distance (≈5% grade), then verifies the first GAP equals the input pace (no prior grade) and that interior and final GAP values are faster than the input pace.
        """
        n = 10
        df = pd.DataFrame({
            'pace_sec_km': [300.0] * n,
            'ele': [100.0 + 5.0 * i for i in range(n)],  # 5m gain per segment
            'dist': [100.0] * n,  # 100m per segment → 5% grade
        })

        gap_series = calculate_gap_from_dataframe(df)

        # First point has no grade (prev diff is NaN)
        assert gap_series.iloc[0] == pytest.approx(300, rel=0.01)

        # Interior points should adjust for ~5% uphill → GAP faster than pace
        assert gap_series.iloc[5] < 300
        assert gap_series.iloc[-1] < 300

    def test_flat_dataframe(self):
        """Test GAP on flat terrain matches actual pace."""
        df = pd.DataFrame({
            'pace_sec_km': [300, 300, 300],
            'ele': [100, 100, 100],  # No elevation change
            'dist': [100, 100, 100]
        })

        gap_series = calculate_gap_from_dataframe(df)

        # All points should be same as original
        assert gap_series.tolist() == pytest.approx([300, 300, 300], rel=0.01)

    def test_missing_values(self):
        """Test handling of NaN values."""
        df = pd.DataFrame({
            'pace_sec_km': [300, np.nan, 300],
            'ele': [100, 105, 110],
            'dist': [100, 100, 100]
        })

        gap_series = calculate_gap_from_dataframe(df)

        # Should preserve NaN
        assert pd.isna(gap_series.iloc[1])
        assert not pd.isna(gap_series.iloc[0])


class TestCalculateAverageGAP:
    """Test time-weighted average GAP."""

    def test_simple_average(self):
        """Test average GAP calculation."""
        df = pd.DataFrame({
            'pace_sec_km': [300, 300, 300],
            'ele': [100, 105, 110],
            'dist': [100, 100, 100],
            'dt': [60, 60, 60]  # 1 minute each
        })

        avg_gap = calculate_average_gap(df)

        # Should be valid number
        assert not np.isnan(avg_gap)
        assert avg_gap > 0
        assert avg_gap < 400  # Reasonable pace

    def test_weighted_by_time(self):
        """Test that average is weighted by segment duration."""
        df = pd.DataFrame({
            'pace_sec_km': [240, 360],  # 4:00 and 6:00 pace
            'ele': [100, 100],  # Flat
            'dist': [100, 100],
            'dt': [30, 90]  # Different durations
        })

        avg_gap = calculate_average_gap(df)

        # Weighted average should be closer to 360 (longer duration)
        assert avg_gap > 300

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame({
            'pace_sec_km': [],
            'ele': [],
            'dist': [],
            'dt': []
        })

        avg_gap = calculate_average_gap(df)

        # Should return NaN for empty data
        assert np.isnan(avg_gap)


class TestPhysicalProperties:
    """Physical oracle properties P1-P4 (Minetti 2002, sea-level invariant).

    All DataFrames are synthetic (np.zeros / literals). No data/ paths referenced.
    """

    def test_p1_flat_grade_identity(self):
        """P1: all-ele=0 flat run — average GAP equals mean raw pace within 1%."""
        n = 20
        pace = 300.0
        df = pd.DataFrame({
            'pace_sec_km': [pace] * n,
            'ele': np.zeros(n),
            'dist': [100.0] * n,
            'dt': [60.0] * n,
        })
        avg_gap = calculate_average_gap(df)
        assert not np.isnan(avg_gap), "calculate_average_gap returned NaN for flat all-ele=0 df"
        assert abs(avg_gap - pace) / pace < 0.01, (
            f"P1 violated: avg_gap={avg_gap:.2f} deviates from raw pace {pace:.2f} by more than 1%"
        )

    def test_p2_ele_zero_validity(self):
        """P2: check_elevation_quality returns (True, 'ok') for all-ele=0 DataFrame."""
        n = 20
        df = pd.DataFrame({
            'ele': np.zeros(n),
            'dist': [100.0] * n,
        })
        is_ok, reason = check_elevation_quality(df)
        assert is_ok is True, f"P2 violated: check_elevation_quality rejected all-ele=0 df: {reason}"
        assert reason == "ok"

    def test_p3_minetti_positivity(self):
        """P3: minetti_energy_cost is strictly > 0 for every grade in [-40, +40]."""
        for grade in [-40, -20, -10, 0, 10, 20, 40]:
            cost = minetti_energy_cost(float(grade))
            assert cost > 0, f"P3 violated: minetti_energy_cost({grade}) = {cost} is not > 0"

    def test_p4_minetti_reference_value(self):
        """P4: Minetti 0%-grade cost * 3.6 matches published flat cost ~3.6 J/kg/m within 5%."""
        cost_at_zero = minetti_energy_cost(0.0)
        abs_cost = cost_at_zero * 3.6
        assert 3.42 <= abs_cost <= 3.78, (
            f"P4 violated: minetti_energy_cost(0.0) * 3.6 = {abs_cost:.3f}, "
            f"expected in [3.42, 3.78] (Minetti 2002 ±5%)"
        )


# ---------------------------------------------------------------------------
# P2 — ELE=0 VALIDITY (unit layer): BUG-1
# check_elevation_quality must treat 0 m as valid sea-level terrain, not missing
# ---------------------------------------------------------------------------

def _sea_level_df(n: int = 20) -> pd.DataFrame:
    """Synthetic all-zero-elevation DataFrame simulating a sea-level run.

    All values are caller-supplied constants; no real GPS data.
    """
    return pd.DataFrame({
        "ele": [0.0] * n,
        "dist": [50.0] * n,  # 50 m segments
        "pace_sec_km": [300.0] * n,  # 5:00/km
        "dt": [10.0] * n,  # 10 s per segment
    })


class TestElevationQualitySeaLevel:
    """P2 — BUG-1: quality gate must accept all-zero (sea-level) elevation.

    Bug catalog ref: BUG-1
    Oracle: check_elevation_quality(df_all_zero_ele) returns (True, ...)
    Layer: UNIT — caller supplies the DataFrame; no production ingestion.
    """

    def test_check_elevation_quality_returns_true_for_all_zero_elevation_sea_level_activity(self):
        """BUG-1: replace(0,NaN).dropna() silently empties a sea-level DataFrame,
        causing check_elevation_quality to return (False, 'insufficient elevation
        data points') instead of (True, 'ok') for valid 0 m terrain.
        """
        df = _sea_level_df(n=20)
        is_ok, reason = check_elevation_quality(df)
        # Sea-level (all-ele=0) is valid flat terrain — quality gate must agree
        # with the computation path (gap.py:165) that treats 0 as valid.
        assert is_ok is True, (
            f"check_elevation_quality wrongly rejected sea-level activity: {reason!r}. "
            "BUG-1: replace(0, np.nan).dropna() conflates missing GPS (0=sentinel) "
            "with genuine 0 m elevation."
        )

    def test_check_elevation_quality_preserves_ok_reason_for_sea_level(self):
        """BUG-1 (reason string): when is_ok is True for all-ele=0, reason must
        be 'ok', not a fallthrough from the insufficient-data branch.
        """
        df = _sea_level_df(n=20)
        is_ok, reason = check_elevation_quality(df)
        assert is_ok is True
        assert reason == "ok", (
            f"Expected reason='ok' for valid sea-level data, got {reason!r}"
        )

    def test_check_elevation_quality_distinguishes_sea_level_from_genuinely_missing_elevation(self):
        """BUG-1 (negative path): a DataFrame with all-NaN elevation (true GPS
        dropout) must still return (False, ...) — the fix must not over-correct
        and accept genuinely absent data.
        """
        df = pd.DataFrame({
            "ele": [np.nan] * 20,
            "dist": [50.0] * 20,
        })
        is_ok, _ = check_elevation_quality(df)
        assert is_ok is False, (
            "A DataFrame with all-NaN elevation (true GPS dropout) must still "
            "be rejected — the fix must only exempt genuine 0 m readings."
        )


# ---------------------------------------------------------------------------
# P1 — FLAT-GRADE IDENTITY (unit layer): BUG-3 / characterisation
# The computation path (calculate_average_gap) already treats 0m as flat terrain.
# This test pins that correct behavior so the fix cannot break it.
# ---------------------------------------------------------------------------

class TestFlatGradeIdentitySeaLevel:
    """P1 — FLAT-GRADE IDENTITY: for all-flat (all-ele=0) terrain, average GAP
    must equal mean raw pace within 1%.

    Bug catalog ref: BUG-3 (characterisation — computation path is already correct)
    Oracle: |calculate_average_gap(df) - mean_pace| / mean_pace < 0.01
    Layer: UNIT — calls calculate_average_gap directly, bypassing the quality gate.
    Status: GREEN (pins correct behavior; prevents regression during the fix)
    """

    def test_calculate_average_gap_all_zero_elevation_equals_raw_pace_flat_grade_identity(self):
        """P1: for an all-ele=0 sea-level run at constant pace 300 s/km,
        the time-weighted average GAP must equal 300 s/km within 1%.

        Minetti energy_multiplier == 1.0 at 0% grade, so GAP == raw pace.
        Passes today (computation path is correct); would fail if the fix
        accidentally introduced a 0→NaN replacement in calculate_gap_from_dataframe.
        """
        df = _sea_level_df(n=20)
        avg_gap = calculate_average_gap(df)
        mean_pace = 300.0
        assert not np.isnan(avg_gap), "calculate_average_gap returned NaN for sea-level df"
        assert abs(avg_gap - mean_pace) / mean_pace < 0.01, (
            f"P1 flat-grade identity violated: avg_gap={avg_gap:.2f} vs "
            f"mean_pace={mean_pace:.2f} (>1% deviation)"
        )


# ---------------------------------------------------------------------------
# P3 — MINETTI POSITIVITY: energy cost > 0 for all grades in [-40%, +40%]
# ---------------------------------------------------------------------------

class TestMinettiPositivity:
    """P3 — MINETTI POSITIVITY: minetti_energy_cost is strictly positive for
    every integer grade in the range [-40, +40] percent.

    Bug catalog ref: BUG-4
    Oracle: minetti_energy_cost(g) > 0 for g in range(-40, 41)
    Layer: UNIT
    Status: GREEN (current polynomial is correct; pins this invariant)
    """

    @pytest.mark.parametrize("grade", range(-40, 41))
    def test_minetti_energy_cost_positive_for_all_valid_grades_p3(self, grade: int):
        """P3: minetti_energy_cost must be > 0 for grade={grade}%.

        A zero or negative multiplier would produce infinite or negative GAP,
        silently corrupting all downstream pace adjustments.
        """
        cost = minetti_energy_cost(float(grade))
        assert cost > 0, (
            f"P3 Minetti positivity violated at grade={grade}%: cost={cost}"
        )


# ---------------------------------------------------------------------------
# P4 — REFERENCE VALUE: Minetti 2002 published constant at 0% grade ≈ 3.6 J/kg/m
# ---------------------------------------------------------------------------

class TestMinettiReferenceValue:
    """P4 — REFERENCE VALUE: the Minetti polynomial at 0% grade must yield
    ~3.6 J/kg/m (Minetti 2002), within 5%.

    Bug catalog ref: BUG-5
    Oracle: minetti_energy_cost(0.0) * 3.6 ≈ 3.6 within 5%
    Layer: UNIT
    Status: GREEN (current constant is correct; pins reference to published value)
    """

    def test_minetti_energy_cost_at_zero_grade_matches_published_3_6_joules_per_kg_per_m_p4(self):
        """P4: at 0% grade, the raw Minetti energy cost (before normalization by 3.6)
        must equal ~3.6 J/kg/m (Minetti 2002, Table 1) within 5%.

        minetti_energy_cost returns ec/3.6, so the raw ec = return_value * 3.6.
        Pins the normalization constant against the published reference.
        """
        published_flat_cost_j_per_kg_per_m = 3.6
        tolerance = 0.05  # 5%
        raw_ec = minetti_energy_cost(0.0) * 3.6
        assert abs(raw_ec - published_flat_cost_j_per_kg_per_m) / published_flat_cost_j_per_kg_per_m <= tolerance, (
            f"P4 reference-value mismatch: raw_ec={raw_ec:.4f} vs "
            f"Minetti 2002 {published_flat_cost_j_per_kg_per_m} J/kg/m "
            f"(deviation > {tolerance*100:.0f}%)"
        )


# ---------------------------------------------------------------------------
# P2 — ELE=0 VALIDITY (integration layer): BUG-2
# run_metrics must compute GAP (non-None gap_min_per_km) for all-zero elevation
# ---------------------------------------------------------------------------

@pytest.fixture(name="flat_zone_config")
def _flat_zone_config() -> ZoneConfig:
    """Minimal synthetic zone config for integration tests."""
    return ZoneConfig(
        resting_hr=50,
        threshold_hr=186,
        zones={
            "Z2 (Aerobic)": HeartRateZone(
                name="Z2 (Aerobic)",
                bpm=(160, 186),
                pace_min_per_km=(9.0, 9.4),
            ),
        },
    )


class TestRunMetricsGAPSeaLevel:
    """P2 — BUG-2: run_metrics integration gate must compute GAP for all-zero elevation.

    Bug catalog ref: BUG-2
    Oracle: run_metrics(df_all_zero_ele, zone_cfg).gap_min_per_km is not None
    Layer: INTEGRATION — run_metrics is the production caller that decides whether
    GAP is computed; unit test of check_elevation_quality is insufficient because
    metrics.py:317-318 adds a second gate before even calling check_elevation_quality.
    """

    def test_run_metrics_gap_computed_for_all_zero_elevation_sea_level_activity(
        self, flat_zone_config: ZoneConfig
    ):
        """BUG-2: metrics.py:317-318 applies replace(0, np.nan) on the elevation
        column and guards the entire GAP block with `if not ele_series.isna().all()`.
        For a sea-level run this guard fires (all values become NaN), so
        gap_min_per_km stays None even though the data is valid.

        This test must be RED (fail) until metrics.py:317-318 is fixed.
        """
        n = 600  # 10 minutes at 1 Hz — enough data for quality gate to pass
        df = pd.DataFrame({
            "dist": [10.0] * n,
            "dt": [1.0] * n,
            "hr": [165.0] * n,
            "pace_sec_km": [300.0] * n,
            "ele": [0.0] * n,  # valid sea-level terrain
        })
        metrics = run_metrics(df, flat_zone_config)
        assert metrics.gap_min_per_km is not None, (
            "BUG-2: run_metrics returned gap_min_per_km=None for a sea-level "
            "(all-ele=0) activity. metrics.py:317-318 incorrectly treats 0 m "
            "elevation as missing data and skips the GAP computation block entirely."
        )

    def test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run(
        self, flat_zone_config: ZoneConfig
    ):
        """BUG-2 + P1 (integration): when GAP is computed for an all-ele=0 run,
        gap_min_per_km must equal avg_pace_min_per_km within 1%
        (flat grade → Minetti multiplier = 1.0 → GAP ≈ raw pace).

        This test is also RED today because gap_min_per_km is None (BUG-2).
        Once BUG-2 is fixed, this additionally guards P1 at the integration layer.
        """
        n = 600
        pace_sec_km = 300.0  # 5:00/km
        df = pd.DataFrame({
            "dist": [10.0] * n,
            "dt": [1.0] * n,
            "hr": [165.0] * n,
            "pace_sec_km": [pace_sec_km] * n,
            "ele": [0.0] * n,
        })
        metrics = run_metrics(df, flat_zone_config)
        assert metrics.gap_min_per_km is not None, (
            "BUG-2: gap_min_per_km is None — run_metrics skipped GAP for all-ele=0"
        )
        expected_gap_min_per_km = pace_sec_km / 60  # 5.0 min/km
        assert abs(metrics.gap_min_per_km - expected_gap_min_per_km) / expected_gap_min_per_km < 0.01, (
            f"P1 flat-grade identity violated at integration layer: "
            f"gap={metrics.gap_min_per_km:.4f} vs expected={expected_gap_min_per_km:.4f} min/km"
        )
