"""
Tests for Pydantic Data Models
===============================

Tests all validation logic, field constraints, and model serialization.
"""

import pytest
from pydantic import ValidationError

from biosystems.models import (
    ActivitySummary,
    HeartRateZone,
    PhysiologicalMetrics,
    RunContext,
    WalkSegment,
    ZoneConfig,
)


class TestHeartRateZone:
    """Test HeartRateZone model validation."""

    def test_valid_zone(self):
        """Test creating valid heart rate zone."""
        zone = HeartRateZone(
            name="Z2 (Aerobic)",
            bpm=(160, 186),
            pace_min_per_km=(9.0, 9.4)
        )
        assert zone.name == "Z2 (Aerobic)"
        assert zone.bpm == (160, 186)
        assert zone.pace_min_per_km == (9.0, 9.4)


    def test_bpm_validation_zero_lower_allowed(self):
        """Test that zero is allowed as lower BPM bound (Z1 / 'any HR' sentinel)."""
        zone = HeartRateZone(
            name="Z1 (Recovery)",
            bpm=(0, 145),
            pace_min_per_km=(6.75, 999.0)
        )
        assert zone.bpm == (0, 145)

    def test_bpm_validation_negative(self):
        """Test that negative lower BPM values are rejected."""
        with pytest.raises(ValidationError):
            HeartRateZone(
                name="Invalid",
                bpm=(-1, 100),
                pace_min_per_km=(5.0, 6.0)
            )

    def test_reversed_bpm_range(self):
        """Test that reversed BPM range is rejected."""
        with pytest.raises(ValidationError):
            HeartRateZone(
                name="Test",
                bpm=(180, 160),  # Reversed
                pace_min_per_km=(5.0, 6.0)
            )


class TestZoneConfig:
    """Test ZoneConfig model validation."""

    def test_valid_config(self):
        """Test creating valid zone configuration."""
        config = ZoneConfig(
            resting_hr=50,
            threshold_hr=186,
            zones={
                "Z2": HeartRateZone(
                    name="Z2",
                    bpm=(160, 186),
                    pace_min_per_km=(9.0, 9.4)
                )
            }
        )
        assert config.resting_hr == 50
        assert config.threshold_hr == 186
        assert "Z2" in config.zones

    def test_invalid_resting_hr(self):
        """Test that invalid resting HR is rejected."""
        with pytest.raises(ValidationError):
            ZoneConfig(
                resting_hr=0,
                threshold_hr=186,
                zones={}
            )

    def test_invalid_threshold_hr(self):
        """Test that invalid threshold HR is rejected."""
        with pytest.raises(ValidationError):
            ZoneConfig(
                resting_hr=50,
                threshold_hr=0,
                zones={}
            )


class TestRunContext:
    """Test RunContext model."""

    def test_valid_context(self):
        """Test creating valid run context."""
        context = RunContext(
            temperature_c=25.0,
            rest_hr=50,
            sleep_score=85.0
        )
        assert context.temperature_c == 25.0
        assert context.rest_hr == 50
        assert context.sleep_score == 85.0

    def test_optional_fields(self):
        """Test that optional fields work."""
        context = RunContext(
            temperature_c=25.0,
            rest_hr=50
        )
        assert context.sleep_score is None

    def test_invalid_rest_hr(self):
        """Test that invalid rest HR is rejected."""
        with pytest.raises(ValidationError):
            RunContext(
                temperature_c=25.0,
                rest_hr=-5
            )


class TestPhysiologicalMetrics:
    """Test PhysiologicalMetrics model."""

    def test_valid_metrics(self):
        """Test creating valid metrics."""
        metrics = PhysiologicalMetrics(
            distance_km=10.5,
            duration_min=65.3,
            avg_pace_min_per_km=6.2,
            avg_hr=162.0,
            efficiency_factor=0.00617,
            decoupling_pct=4.5,
            hr_tss=75.2
        )
        assert metrics.distance_km == 10.5
        assert metrics.avg_hr == 162.0
        assert metrics.efficiency_factor == 0.00617

    def test_optional_fields(self):
        """Test optional fields in metrics."""
        metrics = PhysiologicalMetrics(
            distance_km=10.0,
            duration_min=60.0,
            avg_pace_min_per_km=6.0,
            avg_hr=160.0,
            efficiency_factor=0.006,
            decoupling_pct=5.0,
            hr_tss=70.0,
            avg_cadence=170,
            gap_min_per_km=5.8
        )
        assert metrics.avg_cadence == 170
        assert metrics.gap_min_per_km == 5.8

    def test_validation_negative_distance(self):
        """Test that negative distance is rejected."""
        with pytest.raises(ValidationError):
            PhysiologicalMetrics(
                distance_km=-1.0,
                duration_min=60.0,
                avg_pace_min_per_km=6.0,
                avg_hr=160.0,
                efficiency_factor=0.006,
                decoupling_pct=5.0,
                hr_tss=70.0
            )

    def test_validation_zero_duration(self):
        """Test that zero duration is rejected."""
        with pytest.raises(ValidationError):
            PhysiologicalMetrics(
                distance_km=10.0,
                duration_min=0.0,
                avg_pace_min_per_km=6.0,
                avg_hr=160.0,
                efficiency_factor=0.006,
                decoupling_pct=5.0,
                hr_tss=70.0
            )


class TestActivitySummary:
    """Test ActivitySummary model."""

    def test_valid_summary(self):
        """Test creating valid activity summary."""
        summary = ActivitySummary(
            activity_id="20240806_100000",
            timestamp="2024-08-06T10:00:00Z",
            activity_type="run",
            metrics=PhysiologicalMetrics(
                distance_km=10.0,
                duration_min=60.0,
                avg_pace_min_per_km=6.0,
                avg_hr=160.0,
                efficiency_factor=0.006,
                decoupling_pct=5.0,
                hr_tss=70.0
            )
        )
        assert summary.activity_id == "20240806_100000"
        assert summary.activity_type == "run"
        assert summary.metrics.distance_km == 10.0


class TestWalkSegment:
    """Test WalkSegment model."""

    def test_valid_segment(self):
        """Test creating valid walk segment."""
        segment = WalkSegment(
            segment_id=1,
            start_offset_s=0,
            end_offset_s=150,
            duration_s=150,
            distance_km=0.3,
            avg_pace_min_km=8.33,
            tag="warm-up"
        )
        assert segment.segment_id == 1
        assert segment.duration_s == 150
        assert segment.tag == "warm-up"

    def test_optional_fields(self):
        """Test optional fields in walk segment."""
        segment = WalkSegment(
            segment_id=1,
            start_offset_s=0,
            end_offset_s=150,
            duration_s=150,
            distance_km=0.0,
            avg_pace_min_km=10.0,
            tag="mid-session"
        )
        assert segment.avg_hr is None
        assert segment.avg_cad is None
