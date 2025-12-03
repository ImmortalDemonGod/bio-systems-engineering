"""
Tests for Grade Adjusted Pace (GAP) Calculations
=================================================

Tests Minetti's equation and all GAP calculation functions.
"""

import pytest
import numpy as np
import pandas as pd

from biosystems.physics.gap import (
    calculate_grade_percent,
    minetti_energy_cost,
    calculate_gap_segment,
    calculate_gap_from_dataframe,
    calculate_average_gap,
)


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
        """Test GAP calculation on simple DataFrame."""
        df = pd.DataFrame({
            'pace_sec_km': [300, 300, 300],
            'ele': [100, 105, 110],  # 5m elevation gain per segment
            'dist': [100, 100, 100]   # 100m per segment
        })
        
        gap_series = calculate_gap_from_dataframe(df)
        
        # First point should be same (no grade)
        assert gap_series.iloc[0] == pytest.approx(300, rel=0.01)
        
        # Subsequent points should adjust for ~5% grade
        assert gap_series.iloc[1] < 300  # Faster GAP
        assert gap_series.iloc[2] < 300
    
    def test_flat_dataframe(self):
        """Test GAP on flat terrain matches actual pace."""
        df = pd.DataFrame({
            'pace_sec_km': [300, 300, 300],
            'ele': [100, 100, 100],  # No elevation change
            'dist': [100, 100, 100]
        })
        
        gap_series = calculate_gap_from_dataframe(df)
        
        # All points should be same as original
        assert all(gap_series == pytest.approx(300, rel=0.01))
    
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
