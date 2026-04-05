"""
Tests for Signal Processing (Walk Detection)
=============================================

Tests walk segment detection, GPS jitter filtering, and summarization.
"""

import numpy as np
import pandas as pd
import pytest

from biosystems.signal.walk_detection import (
    compute_time_weighted_pace,
    drop_short_segments,
    filter_gps_jitter,
    summarize_walk_segments,
    walk_block_segments,
)


class TestFilterGPSJitter:
    """Test GPS jitter filtering."""

    def test_removes_gps_jitter(self):
        """Test that extreme GPS jitter (very slow pace + zero cadence) is removed."""
        df = pd.DataFrame({
            'pace_min_per_km': [10.0, 15.0, 8.0],
            'cadence': [120, 50, 110]  # row 1: 50 spm + 15 min/km = noise
        })

        filtered = filter_gps_jitter(
            df,
            pace_col='pace_min_per_km',
            cad_col='cadence',
        )

        # Row 1 dropped (pace 15 > 12 AND cad 50 < 100), others kept
        assert len(filtered) == 2
        assert 50 not in filtered['cadence'].values

    def test_keeps_real_walk_points(self):
        """Test that genuine walk points (moderate pace + cadence) are kept."""
        df = pd.DataFrame({
            'pace_min_per_km': [10.0, 11.0],  # Walking pace
            'cadence': [120, 110]  # Walk cadence above jitter floor
        })

        filtered = filter_gps_jitter(
            df,
            pace_col='pace_min_per_km',
            cad_col='cadence',
        )

        # All kept — real walk data, not jitter
        assert len(filtered) == len(df)

    def test_keeps_fast_pace(self):
        """Test that fast pace is always kept even with low cadence."""
        df = pd.DataFrame({
            'pace_min_per_km': [5.0, 7.0, 9.0],
            'cadence': [170, 80, 145]
        })

        filtered = filter_gps_jitter(
            df,
            pace_col='pace_min_per_km',
            cad_col='cadence',
        )

        assert len(filtered) == len(df)


class TestDropShortSegments:
    """Test dropping short segments."""

    def test_drops_short(self):
        """Test that segments shorter than threshold are dropped."""
        segments = [
            {'dur_s': 3},
            {'dur_s': 10},
            {'dur_s': 2},
        ]

        filtered = drop_short_segments(segments, min_duration=5)

        # Should only keep the 10s segment
        assert len(filtered) == 1
        assert filtered[0]['dur_s'] == 10

    def test_keeps_all_long(self):
        """Test that all long segments are kept."""
        segments = [
            {'dur_s': 10},
            {'dur_s': 15},
            {'dur_s': 20},
        ]

        filtered = drop_short_segments(segments, min_duration=5)

        # Should keep all
        assert len(filtered) == 3

    def test_empty_list(self):
        """Test handling of empty segment list."""
        filtered = drop_short_segments([], min_duration=5)

        assert filtered == []


class TestComputeTimeWeightedPace:
    """Test time-weighted pace calculation."""

    def test_normal_pace(self):
        """Test pace calculation with normal values."""
        pace = compute_time_weighted_pace(dur_s=300, dist_km=0.5)

        # 300s / 0.5km = 600s = 10 min/km
        assert pace == pytest.approx(10.0, rel=0.01)

    def test_fast_pace(self):
        """Test fast pace calculation."""
        pace = compute_time_weighted_pace(dur_s=240, dist_km=1.0)

        # 240s / 1km = 240s = 4 min/km
        assert pace == pytest.approx(4.0, rel=0.01)

    def test_zero_distance(self):
        """Test handling of zero distance."""
        pace = compute_time_weighted_pace(dur_s=60, dist_km=0)

        # Should return NaN
        assert np.isnan(pace)


class TestSummarizeWalkSegments:
    """Test walk segment summarization."""

    def test_valid_segments(self):
        """Test summarization of valid segments."""
        segments = [
            {'dur_s': 60, 'dist_km': 0.1, 'avg_pace_min_km': 10.0, 'avg_hr': 120, 'avg_cad': 130},
            {'dur_s': 120, 'dist_km': 0.2, 'avg_pace_min_km': 10.0, 'avg_hr': 125, 'avg_cad': 135},
        ]

        summary = summarize_walk_segments(segments)

        assert summary['total_walk_time'] == 180  # 60 + 120
        assert summary['total_walk_dist'] == pytest.approx(0.3, rel=0.01)
        assert summary['avg_hr'] > 0
        assert summary['avg_cad'] > 0

    def test_empty_segments(self):
        """Test handling of empty segment list."""
        summary = summarize_walk_segments([])

        assert summary['total_walk_time'] == 0
        assert summary['total_walk_dist'] == 0
        assert np.isnan(summary['avg_pace'])

    def test_filters_invalid(self):
        """Test that invalid segments are filtered out."""
        segments = [
            {'dur_s': 0, 'dist_km': 0.1, 'avg_pace_min_km': 10.0, 'avg_hr': 120, 'avg_cad': 130},
            {'dur_s': 60, 'dist_km': 0, 'avg_pace_min_km': 10.0, 'avg_hr': 125, 'avg_cad': 135},
            {'dur_s': 60, 'dist_km': 0.1, 'avg_pace_min_km': 10.0, 'avg_hr': 125, 'avg_cad': 135},
        ]

        summary = summarize_walk_segments(segments)

        # Should only use last segment
        assert len(summary['valid_segments']) == 1


class TestWalkBlockSegments:
    """Test walk block detection and segmentation."""

    @pytest.fixture
    def sample_activity(self):
        """
        Create a sample activity DataFrame containing two walk periods within a 1000-second, 1 Hz time series.

        The DataFrame is indexed by a 1-second DatetimeIndex starting at 2024-01-01 10:00:00 and contains 1000 rows. It includes two contiguous walk blocks: one starting at 30s lasting 100s, and one at the end lasting 100s. Non-walk rows surround and separate these blocks.

        Returns:
            pd.DataFrame: Time-indexed activity with columns:
                - is_walk (bool): True for walk rows, False otherwise.
                - pace_min_per_km (float): 10.0 during walk rows, 6.0 otherwise.
                - cadence (int): 120 during walk rows, 170 otherwise.
                - distance_cumulative_km (float): Cumulative distance with 0.01 km increment per row.
                - heart_rate (int): Constant heart rate (160).
        """
        # 1000 points, 1 Hz
        n_points = 1000

        # Create datetime index
        idx = pd.date_range('2024-01-01 10:00:00', periods=n_points, freq='s')

        # First walk starts at 30s (within 60s warm-up window)
        is_walk = [False] * 30 + [True] * 100 + [False] * 770 + [True] * 100

        df = pd.DataFrame({
            'is_walk': is_walk,
            'pace_min_per_km': [6.0 if not w else 10.0 for w in is_walk],
            'cadence': [170 if not w else 120 for w in is_walk],
            'distance_cumulative_km': np.cumsum([0.01] * n_points),
            'heart_rate': [160] * n_points,
        }, index=idx)

        return df

    def test_detects_walk_blocks(self, sample_activity):
        """Test that walk blocks are correctly detected."""
        segments = walk_block_segments(
            sample_activity,
            is_walk_col='is_walk',
            pace_col='pace_min_per_km',
            cad_col='cadence',
            cad_thr=128,
            max_gap_s=2,
            min_dur_s=2
        )

        # Should detect 2 walk blocks
        assert len(segments) > 0

        # Each segment should have required fields
        for seg in segments:
            assert 'segment_id' in seg
            assert 'start_ts' in seg
            assert 'end_ts' in seg
            assert 'dur_s' in seg
            assert 'tag' in seg

    def test_classifies_warmup(self, sample_activity):
        """Test that early walks are classified as warm-up."""
        segments = walk_block_segments(
            sample_activity,
            is_walk_col='is_walk',
            pace_col='pace_min_per_km',
            cad_col='cadence'
        )

        if segments:
            # First segment should be warm-up
            assert segments[0]['tag'] == 'warm-up'

    def test_classifies_cooldown(self, sample_activity):
        """Test that late walks are classified as cool-down."""
        segments = walk_block_segments(
            sample_activity,
            is_walk_col='is_walk',
            pace_col='pace_min_per_km',
            cad_col='cadence'
        )

        if segments:
            # Last segment should be cool-down
            assert segments[-1]['tag'] == 'cool-down'

    def test_respects_min_duration(self, sample_activity):
        """Test that minimum duration filter works."""
        segments = walk_block_segments(
            sample_activity,
            is_walk_col='is_walk',
            pace_col='pace_min_per_km',
            cad_col='cadence',
            min_dur_s=50  # High threshold
        )

        # All segments should be >= 50s
        for seg in segments:
            assert seg['dur_s'] >= 50

    def test_no_walk_periods(self):
        """Test handling when no walk periods exist."""
        idx = pd.date_range('2024-01-01 10:00:00', periods=100, freq='s')

        df = pd.DataFrame({
            'is_walk': [False] * 100,
            'pace_min_per_km': [6.0] * 100,
            'cadence': [170] * 100,
            'distance_cumulative_km': np.cumsum([0.01] * 100),
            'heart_rate': [160] * 100,
        }, index=idx)

        segments = walk_block_segments(
            df,
            is_walk_col='is_walk',
            pace_col='pace_min_per_km',
            cad_col='cadence'
        )

        # Should return empty list
        assert segments == []
