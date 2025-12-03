"""
Tests for GPX File Parsing
===========================

Tests GPX XML parsing, distance calculation, and metric derivation.
"""

import pytest
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from biosystems.ingestion.gpx import parse_gpx, _haversine


class TestHaversine:
    """Test haversine distance calculation."""
    
    def test_same_point(self):
        """Test distance between same point is zero."""
        dist = _haversine(40.7128, -74.0060, 40.7128, -74.0060)
        assert dist == pytest.approx(0.0, abs=1.0)
    
    def test_known_distance(self):
        """Test known distance (NYC to LA is ~3936 km)."""
        # NYC coordinates
        lat1, lon1 = 40.7128, -74.0060
        # LA coordinates  
        lat2, lon2 = 34.0522, -118.2437
        
        dist_m = _haversine(lat1, lon1, lat2, lon2)
        dist_km = dist_m / 1000
        
        # Should be approximately 3936 km
        assert dist_km == pytest.approx(3936, rel=0.05)
    
    def test_short_distance(self):
        """Test short distance (100m)."""
        # Two points ~100m apart
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7138, -74.0060  # ~0.001 degree ≈ 111m
        
        dist = _haversine(lat1, lon1, lat2, lon2)
        
        # Should be roughly 100m
        assert dist == pytest.approx(111, rel=0.2)


class TestParseGPX:
    """Test GPX file parsing."""
    
    @pytest.fixture
    def sample_gpx_file(self):
        """Create a minimal valid GPX file for testing."""
        gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">
  <trk>
    <trkseg>
      <trkpt lat="40.7128" lon="-74.0060">
        <ele>10.0</ele>
        <time>2024-01-01T10:00:00Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>150</gpxtpx:hr>
            <gpxtpx:cad>170</gpxtpx:cad>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
      <trkpt lat="40.7138" lon="-74.0060">
        <ele>11.0</ele>
        <time>2024-01-01T10:00:10Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>155</gpxtpx:hr>
            <gpxtpx:cad>172</gpxtpx:cad>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
      <trkpt lat="40.7148" lon="-74.0060">
        <ele>12.0</ele>
        <time>2024-01-01T10:00:20Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>160</gpxtpx:hr>
            <gpxtpx:cad>174</gpxtpx:cad>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
    </trkseg>
  </trk>
</gpx>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
            f.write(gpx_content)
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        temp_path.unlink()
    
    def test_parse_valid_gpx(self, sample_gpx_file):
        """Test parsing a valid GPX file."""
        df = parse_gpx(sample_gpx_file)
        
        # Check structure
        assert len(df) == 3
        assert 'lat' in df.columns
        assert 'lon' in df.columns
        assert 'ele' in df.columns
        assert 'hr' in df.columns
        assert 'cadence' in df.columns
    
    def test_extracts_coordinates(self, sample_gpx_file):
        """Test that coordinates are correctly extracted."""
        df = parse_gpx(sample_gpx_file)
        
        assert df['lat'].iloc[0] == pytest.approx(40.7128, rel=0.0001)
        assert df['lon'].iloc[0] == pytest.approx(-74.0060, rel=0.0001)
    
    def test_extracts_heart_rate(self, sample_gpx_file):
        """Test that heart rate is correctly extracted."""
        df = parse_gpx(sample_gpx_file)
        
        assert df['hr'].iloc[0] == 150
        assert df['hr'].iloc[1] == 155
        assert df['hr'].iloc[2] == 160
    
    def test_calculates_distance(self, sample_gpx_file):
        """Test that distance is calculated."""
        df = parse_gpx(sample_gpx_file)
        
        # First point should have dist=0
        assert df['dist'].iloc[0] == 0.0
        
        # Subsequent points should have positive distance
        assert df['dist'].iloc[1] > 0
        assert df['dist'].iloc[2] > 0
    
    def test_calculates_speed(self, sample_gpx_file):
        """Test that speed is calculated."""
        df = parse_gpx(sample_gpx_file)
        
        # Speed should be positive
        assert df['speed_mps'].notna().sum() > 0
        assert (df['speed_mps'] > 0).sum() >= 2
    
    def test_calculates_pace(self, sample_gpx_file):
        """Test that pace is calculated."""
        df = parse_gpx(sample_gpx_file)
        
        # Pace should be positive
        assert df['pace_sec_km'].notna().sum() > 0
    
    def test_time_sorting(self, sample_gpx_file):
        """Test that data is sorted by time."""
        df = parse_gpx(sample_gpx_file)
        
        # Time should be monotonically increasing
        assert df.index.is_monotonic_increasing
    
    def test_handles_missing_hr(self):
        """Test handling of missing heart rate data."""
        gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="40.7128" lon="-74.0060">
        <ele>10.0</ele>
        <time>2024-01-01T10:00:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
            f.write(gpx_content)
            temp_path = Path(f.name)
        
        try:
            df = parse_gpx(temp_path)
            
            # Should have NaN for HR
            assert df['hr'].isna().all()
        finally:
            temp_path.unlink()
    
    def test_invalid_file(self):
        """Test handling of invalid GPX file."""
        with pytest.raises((ValueError, FileNotFoundError, ET.ParseError)):
            parse_gpx("nonexistent_file.gpx")
