"""
Tests for Physiological Metrics Calculations
=============================================

Tests EF, decoupling, TSS, and zone classification.
"""

import pytest
import numpy as np
import pandas as pd

from biosystems.physics.metrics import (
    calculate_efficiency_factor,
    calculate_decoupling,
    calculate_hr_tss,
    compute_training_zones,
    lower_z2_bpm,
    run_metrics,
)
from biosystems.models import ZoneConfig, HeartRateZone, PhysiologicalMetrics


@pytest.fixture
def sample_zone_config():
    """Create sample zone configuration for testing."""
    return ZoneConfig(
        resting_hr=50,
        threshold_hr=186,
        zones={
            "Z2 (Aerobic)": HeartRateZone(
                name="Z2 (Aerobic)",
                bpm=(160, 186),
                pace_min_per_km=(9.0, 9.4)
            ),
            "Z3 (Tempo)": HeartRateZone(
                name="Z3 (Tempo)",
                bpm=(186, 195),
                pace_min_per_km=(8.5, 8.9)
            )
        }
    )


@pytest.fixture
def sample_activity_df():
    """Create sample activity DataFrame for testing."""
    # 10 minutes of data, 1 Hz sampling
    n_points = 600
    
    return pd.DataFrame({
        'dist': [10.0] * n_points,  # 10m per second = 36 km/h
        'dt': [1.0] * n_points,      # 1 second intervals
        'hr': [165.0] * n_points,    # Steady HR
        'pace_sec_km': [300.0] * n_points,  # 5:00/km pace
        'cadence': [170] * n_points,
    })


class TestCalculateEfficiencyFactor:
    """Test efficiency factor calculation."""
    
    def test_steady_state_run(self, sample_activity_df, sample_zone_config):
        """Test EF on steady-state run."""
        ef = calculate_efficiency_factor(sample_activity_df, sample_zone_config)
        
        # EF = speed / HR
        # speed = 10m/s, HR = 165 → EF ≈ 0.0606
        assert ef > 0
        assert ef == pytest.approx(0.0606, rel=0.01)
    
    def test_filters_warmup(self, sample_zone_config):
        """Test that warm-up below Z2 is filtered out."""
        df = pd.DataFrame({
            'dist': [10.0] * 600,
            'dt': [1.0] * 600,
            'hr': [150.0] * 300 + [165.0] * 300,  # First half below Z2
            'pace_sec_km': [360.0] * 300 + [300.0] * 300,
        })
        
        ef = calculate_efficiency_factor(df, sample_zone_config)
        
        # Should only use second half (HR >= 160)
        assert ef > 0
    
    def test_all_below_z2(self, sample_zone_config):
        """Test handling when all data is below Z2."""
        df = pd.DataFrame({
            'dist': [10.0] * 100,
            'dt': [1.0] * 100,
            'hr': [150.0] * 100,  # All below Z2 lower bound (160)
            'pace_sec_km': [360.0] * 100,
        })
        
        ef = calculate_efficiency_factor(df, sample_zone_config)
        
        # Should use full dataset as fallback
        assert ef > 0


class TestCalculateDecoupling:
    """Test aerobic decoupling calculation."""
    
    def test_no_drift(self, sample_activity_df, sample_zone_config):
        """Test decoupling with no HR drift."""
        decoupling = calculate_decoupling(sample_activity_df, sample_zone_config)
        
        # No drift → decoupling should be ~0%
        assert decoupling == pytest.approx(0.0, abs=0.1)
    
    def test_positive_drift(self, sample_zone_config):
        """Test decoupling with HR drift (fatigue)."""
        df = pd.DataFrame({
            'dist': [10.0] * 600,
            'dt': [1.0] * 600,
            # HR increases over time (fatigue)
            'hr': [160.0] * 300 + [170.0] * 300,
            'pace_sec_km': [300.0] * 600,  # Same pace
        })
        df.index = pd.date_range('2024-01-01', periods=600, freq='S')
        
        decoupling = calculate_decoupling(df, sample_zone_config)
        
        # Should show positive decoupling (HR went up)
        assert decoupling > 0
    
    def test_negative_drift(self, sample_zone_config):
        """Test decoupling with HR drop (super-compensation)."""
        df = pd.DataFrame({
            'dist': [10.0] * 600,
            'dt': [1.0] * 600,
            # HR decreases over time
            'hr': [170.0] * 300 + [160.0] * 300,
            'pace_sec_km': [300.0] * 600,
        })
        df.index = pd.date_range('2024-01-01', periods=600, freq='S')
        
        decoupling = calculate_decoupling(df, sample_zone_config)
        
        # Should show decoupling (absolute value)
        assert decoupling > 0


class TestCalculateHRTSS:
    """Test Training Stress Score calculation."""
    
    def test_threshold_pace(self, sample_activity_df, sample_zone_config):
        """Test TSS at threshold heart rate."""
        # Modify to threshold HR (186)
        sample_activity_df['hr'] = 186.0
        
        tss = calculate_hr_tss(sample_activity_df, sample_zone_config)
        
        # 1 hour at threshold = 100 TSS
        # 10 minutes at threshold ≈ 16.7 TSS
        assert tss > 0
        assert tss == pytest.approx(16.7, rel=0.1)
    
    def test_easy_pace(self, sample_activity_df, sample_zone_config):
        """Test TSS at easy pace (low HR)."""
        sample_activity_df['hr'] = 140.0  # Easy pace
        
        tss = calculate_hr_tss(sample_activity_df, sample_zone_config)
        
        # Low intensity → low TSS
        assert tss > 0
        assert tss < 10


class TestComputeTrainingZones:
    """Test zone classification."""
    
    def test_zone_classification(self, sample_zone_config):
        """Test HR and pace zone classification."""
        hr_array = pd.Series([165, 170, 190])
        pace_array = pd.Series([540, 510, 540])  # In seconds per km
        
        zone_hr, zone_pace, zone_effective = compute_training_zones(
            hr_array, pace_array, sample_zone_config
        )
        
        # Check types
        assert isinstance(zone_hr, pd.Series)
        assert isinstance(zone_pace, pd.Series)
        assert isinstance(zone_effective, list)
        
        # First point should be in Z2
        assert "Z2" in str(zone_hr.iloc[0])
    
    def test_handles_nan(self, sample_zone_config):
        """Test handling of NaN values."""
        hr_array = pd.Series([165, np.nan, 170])
        pace_array = pd.Series([540, 510, np.nan])
        
        zone_hr, zone_pace, zone_effective = compute_training_zones(
            hr_array, pace_array, sample_zone_config
        )
        
        # Should handle NaN gracefully
        assert zone_hr.iloc[1] is None
        assert zone_pace.iloc[2] is None


class TestLowerZ2BPM:
    """Test Z2 lower bound extraction."""
    
    def test_extracts_z2_lower(self, sample_zone_config):
        """Test extracting Z2 lower bound."""
        z2_lower = lower_z2_bpm(sample_zone_config)
        
        assert z2_lower == 160
    
    def test_missing_z2(self):
        """Test error when Z2 zone is missing."""
        config = ZoneConfig(
            resting_hr=50,
            threshold_hr=186,
            zones={
                "Z1": HeartRateZone(
                    name="Z1",
                    bpm=(120, 140),
                    pace_min_per_km=(10.0, 12.0)
                )
            }
        )
        
        with pytest.raises(ValueError, match="No Z2"):
            lower_z2_bpm(config)


class TestRunMetrics:
    """Test complete run metrics calculation."""
    
    def test_complete_analysis(self, sample_activity_df, sample_zone_config):
        """Test full run metrics calculation."""
        metrics = run_metrics(sample_activity_df, sample_zone_config)
        
        # Check return type
        assert isinstance(metrics, PhysiologicalMetrics)
        
        # Check all fields populated
        assert metrics.distance_km > 0
        assert metrics.duration_min > 0
        assert metrics.avg_hr > 0
        assert metrics.efficiency_factor > 0
        assert metrics.decoupling_pct >= 0
        assert metrics.hr_tss > 0
    
    def test_with_cadence(self, sample_activity_df, sample_zone_config):
        """Test metrics calculation includes cadence."""
        metrics = run_metrics(sample_activity_df, sample_zone_config)
        
        assert metrics.avg_cadence is not None
        assert metrics.avg_cadence == 170
    
    def test_without_elevation(self, sample_activity_df, sample_zone_config):
        """Test that GAP is None without elevation data."""
        # Remove elevation column if it exists
        if 'ele' in sample_activity_df.columns:
            sample_activity_df = sample_activity_df.drop(columns=['ele'])
        
        metrics = run_metrics(sample_activity_df, sample_zone_config)
        
        # GAP should be None without elevation
        assert metrics.gap_min_per_km is None
