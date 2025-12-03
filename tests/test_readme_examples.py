"""
Test that README examples actually work.

This prevents documentation from drifting out of sync with the actual API.
All code examples in README.md should be validated here.
"""

import pytest
import pandas as pd
from pathlib import Path

from biosystems.physics.metrics import run_metrics
from biosystems.models import ZoneConfig, HeartRateZone


class TestReadmeExamples:
    """Validate all code examples from README.md"""
    
    @pytest.fixture
    def sample_data_path(self) -> Path:
        """Path to sample data file."""
        return Path(__file__).parent.parent / "data" / "sample" / "sample_run.csv"
    
    @pytest.fixture
    def sample_zones(self) -> ZoneConfig:
        """Zone configuration from README example."""
        return ZoneConfig(
            resting_hr=50,
            threshold_hr=186,
            zones={
                "Z2": HeartRateZone(
                    name="Z2 (Aerobic)",
                    bpm=(145, 165),
                    pace_min_per_km=(4.5, 6.0)
                )
            }
        )
    
    def test_quick_start_example(self, sample_data_path, sample_zones):
        """
        Test the Quick Start example from README.
        
        This is the EXACT code users will copy-paste, so it MUST work.
        """
        # This is copied directly from README
        df = pd.read_csv(sample_data_path, parse_dates=['time'])
        zones = sample_zones
        
        metrics = run_metrics(df, zones)
        
        # Verify we get reasonable values
        assert metrics.efficiency_factor > 0, "EF should be positive"
        assert 0 <= metrics.decoupling_pct <= 100, "Decoupling should be a percentage"
        assert metrics.hr_tss > 0, "TSS should be positive"
        
        # Verify output matches README claims (with tolerance)
        assert abs(metrics.efficiency_factor - 0.02162) < 0.0001, \
            f"EF should match README: expected 0.02162, got {metrics.efficiency_factor:.5f}"
        assert abs(metrics.decoupling_pct - 3.33) < 0.5, \
            f"Decoupling should match README: expected 3.33%, got {metrics.decoupling_pct:.2f}%"
        assert abs(metrics.hr_tss - 42.8) < 1.0, \
            f"TSS should match README: expected 42.8, got {metrics.hr_tss:.1f}"
    
    def test_sample_data_has_required_columns(self, sample_data_path):
        """
        Sample data must have all columns expected by run_metrics.
        
        This prevents KeyError failures when users run the example.
        """
        df = pd.read_csv(sample_data_path)
        
        required_columns = ['time', 'hr', 'dist', 'dt', 'pace_sec_km']
        for col in required_columns:
            assert col in df.columns, \
                f"Sample data missing required column '{col}'. Has: {list(df.columns)}"
    
    def test_zone_config_api(self):
        """
        Verify ZoneConfig API matches what's documented in README.
        
        If this fails, the README import statements are wrong.
        """
        # README says: from biosystems.models import ZoneConfig, HeartRateZone
        from biosystems.models import ZoneConfig, HeartRateZone
        
        # README shows this pattern
        zone = HeartRateZone(
            name="Z2 (Aerobic)",
            bpm=(145, 165),
            pace_min_per_km=(4.5, 6.0)
        )
        
        config = ZoneConfig(
            resting_hr=50,
            threshold_hr=186,
            zones={"Z2": zone}
        )
        
        assert config.resting_hr == 50
        assert config.threshold_hr == 186
        assert "Z2" in config.zones
        assert config.zones["Z2"].name == "Z2 (Aerobic)"
    
    def test_sample_data_is_realistic(self, sample_data_path):
        """
        Sample data should represent a realistic run.
        
        Prevents using synthetic data that doesn't match real-world patterns.
        """
        df = pd.read_csv(sample_data_path)
        
        # Check data size is reasonable (not too small)
        assert len(df) >= 1000, "Sample run should be at least 1000 data points"
        
        # Check HR values are realistic
        assert df['hr'].min() > 100, "Minimum HR should be above resting"
        assert df['hr'].max() < 200, "Maximum HR should be below 200"
        assert df['hr'].mean() > 120, "Average HR should be in working range"
        
        # Check speed is realistic (not standing still or supersonic)
        assert df['speed_mps'].min() > 0, "Speed should be positive"
        assert df['speed_mps'].max() < 10, "Speed should be < 10 m/s (sub-2min/km pace)"
