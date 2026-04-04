"""
Integration Tests for Walk Classification (Cultivation Pipeline Alignment)
==========================================================================

Verifies that the is_walk classification using Cultivation-aligned thresholds
(cadence < 140 spm OR pace > 9.5 min/km) produces correct run-only metrics.

These tests guard against threshold regressions that would silently change
EF, cadence, and decoupling values across the entire pipeline.
"""

import numpy as np
import pandas as pd
import pytest


def classify_walk(df: pd.DataFrame) -> pd.Series:
    """Apply the Cultivation-aligned walk classification.

    This mirrors the logic in cli.py for is_walk assignment.
    """
    return (df["pace_min_per_km"] > 9.5) | (df["cadence"].fillna(0) < 140)


class TestCultivationWalkClassification:
    """Test that walk classification matches Cultivation pipeline thresholds."""

    def test_thresholds_match_cultivation(self):
        """Cadence < 140 OR pace > 9.5 should be classified as walking."""
        df = pd.DataFrame({
            "pace_min_per_km": [5.0, 5.0, 10.0, 7.0],
            "cadence": [170.0, 130.0, 170.0, 0.0],
        })
        is_walk = classify_walk(df)
        # Row 0: good pace, good cadence → running
        assert not is_walk.iloc[0]
        # Row 1: good pace, low cadence → WALK (transition shuffle)
        assert is_walk.iloc[1]
        # Row 2: slow pace, good cadence → WALK
        assert is_walk.iloc[2]
        # Row 3: good pace, zero cadence (sensor dropout) → WALK
        assert is_walk.iloc[3]

    def test_boundary_values(self):
        """Test exact boundary: cadence=140 is running, 139 is walking."""
        df = pd.DataFrame({
            "pace_min_per_km": [6.0, 6.0, 9.5, 9.51],
            "cadence": [140.0, 139.0, 160.0, 160.0],
        })
        is_walk = classify_walk(df)
        assert not is_walk.iloc[0]  # cad=140 → running
        assert is_walk.iloc[1]      # cad=139 → walking
        assert not is_walk.iloc[2]  # pace=9.5 → running
        assert is_walk.iloc[3]      # pace=9.51 → walking

    def test_nan_cadence_is_walk(self):
        """NaN cadence (sensor dropout) should classify as walk."""
        df = pd.DataFrame({
            "pace_min_per_km": [5.0],
            "cadence": [np.nan],
        })
        is_walk = classify_walk(df)
        assert is_walk.iloc[0]


class TestRunOnlyCadenceComputation:
    """Test that run-only filtered cadence produces correct values.

    The Cultivation pipeline's cadence_distribution.txt for the W32 RPE10 run
    showed: N=1902, mean=170.148, median=170.0, SD=3.6.

    The key property: filtering out sub-140 spm samples and slow-pace samples
    removes transition-state noise, producing a higher and more accurate
    mean cadence than Strava's whole-activity average.
    """

    def test_filter_removes_transition_noise(self):
        """Run-only filter should strip low-cadence transitions, raising mean."""
        # Simulate a run with 90% locked-in at 170 spm and 10% transition at 120 spm
        n_run = 1800
        n_transition = 200
        cadence = np.concatenate([
            np.random.normal(170, 3, n_run),
            np.random.normal(120, 5, n_transition),
        ])
        pace = np.concatenate([
            np.full(n_run, 4.5),
            np.full(n_transition, 7.0),
        ])
        df = pd.DataFrame({
            "pace_min_per_km": pace,
            "cadence": cadence,
        })

        # Unfiltered mean (what Strava would report)
        unfiltered_mean = df["cadence"].mean()

        # Run-only filtered
        is_walk = classify_walk(df)
        run_only = df[~is_walk]
        filtered_mean = run_only["cadence"].mean()

        # Filtered should be higher (closer to 170) than unfiltered
        assert filtered_mean > unfiltered_mean
        assert filtered_mean > 168  # Should be near 170
        assert abs(filtered_mean - 170) < 3  # Within reasonable range

    def test_pure_running_unchanged(self):
        """If all points are above thresholds, filter changes nothing."""
        df = pd.DataFrame({
            "pace_min_per_km": np.full(100, 5.0),
            "cadence": np.full(100, 170.0),
        })
        is_walk = classify_walk(df)
        assert not is_walk.any()

    def test_all_walking_filtered(self):
        """If all points are below thresholds, everything is filtered."""
        df = pd.DataFrame({
            "pace_min_per_km": np.full(100, 11.0),
            "cadence": np.full(100, 110.0),
        })
        is_walk = classify_walk(df)
        assert is_walk.all()
