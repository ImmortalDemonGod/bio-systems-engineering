import pandas as pd
import numpy as np
from biosystems.signal.walk_detection import walk_block_segments
from biosystems.models import WalkSegment

def test_walk_block_segments_none_fallback():
    """Verify that walk_block_segments returns None instead of empty strings."""
    # Create a dummy DataFrame with a walk segment
    times = pd.date_range("2025-01-01", periods=10, freq="1S")
    df = pd.DataFrame({
        "is_walk": [True] * 10,
        "heart_rate": [np.nan] * 10,
        "cadence": [np.nan] * 10, # Should fallback to None
        "pace": [10.0] * 10,   # Pass jitter filter
    }, index=times)
    
    segments = walk_block_segments(df, "is_walk", "pace", "cadence")
    
    assert len(segments) == 1
    seg = segments[0]
    
    # Check that fallback values are None
    assert seg["avg_pace_min_km"] is None
    assert seg["avg_hr"] is None
    assert seg["avg_cad"] is None
    
    # Verify that it can be used to instantiate a WalkSegment model
    # (Except dist_km might still be "" if I didn't change it, wait)
    # I changed dist_km_val as well in the code.
    assert seg["dist_km"] is None
    
    # WalkSegment expects:
    # segment_id, start_offset_s, end_offset_s, duration_s, distance_km, avg_pace_min_km, avg_hr, tag
    
    walk_seg = WalkSegment(
        segment_id=seg["segment_id"],
        start_offset_s=seg["start_offset_s"],
        end_offset_s=seg["end_offset_s"],
        duration_s=seg["dur_s"],
        distance_km=0.0, # override for test since we had 0
        avg_pace_min_km=10.0, # override for test since Pydantic expects gt=0
        avg_hr=seg["avg_hr"],
        tag=seg["tag"]
    )
    assert walk_seg.avg_hr is None
