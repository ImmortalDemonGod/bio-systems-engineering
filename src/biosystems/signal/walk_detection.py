"""
Walk Detection and Segmentation
================================

Signal processing algorithms for detecting and classifying walking segments
within running activities. Uses pace and cadence thresholds to identify
recovery intervals.
"""

import numpy as np
import pandas as pd

from biosystems.models import WalkSegment
from typing import List


def filter_gps_jitter(df: pd.DataFrame, pace_col: str, cad_col: str, cad_thr: int) -> pd.DataFrame:
    """
    Remove GPS jitter points from walk segments.
    
    Drops rows where BOTH pace < 8.7 min/km AND cadence < threshold.
    Keeps points where EITHER pace >= 8.7 OR cadence >= threshold.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with pace and cadence columns
    pace_col : str
        Name of pace column (min/km)
    cad_col : str
        Name of cadence column (spm)
    cad_thr : int
        Cadence threshold (spm)
        
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with jitter removed
    """
    pace_flag = df[pace_col] >= 8.7
    cad_flag = df[cad_col] >= cad_thr
    return df[pace_flag | cad_flag]


def drop_short_segments(segments: List[dict], min_duration: int = 5) -> List[dict]:
    """
    Drop segments shorter than minimum duration.
    
    Parameters
    ----------
    segments : List[dict]
        List of segment dictionaries with 'dur_s' key
    min_duration : int
        Minimum duration in seconds
        
    Returns
    -------
    List[dict]
        Filtered list of segments
    """
    return [s for s in segments if s['dur_s'] >= min_duration]


def compute_time_weighted_pace(dur_s: float, dist_km: float) -> float:
    """
    Compute pace as time_minutes / distance_km.
    
    Parameters
    ----------
    dur_s : float
        Duration in seconds
    dist_km : float
        Distance in kilometers
        
    Returns
    -------
    float
        Pace in min/km, or NaN if distance is zero
    """
    return (dur_s / 60) / dist_km if dist_km > 0 else float('nan')


def summarize_walk_segments(segments: List[dict]) -> dict:
    """
    Calculate summary statistics for walk segments.
    
    Only uses segments with valid, positive duration and distance.
    
    Parameters
    ----------
    segments : List[dict]
        List of segment dictionaries
        
    Returns
    -------
    dict
        Summary with keys:
        - total_walk_time : total duration (seconds)
        - total_walk_dist : total distance (km)
        - avg_pace : average pace (min/km)
        - avg_hr : average heart rate (bpm)
        - max_hr : maximum heart rate (bpm)
        - avg_cad : average cadence (spm)
        - valid_segments : list of valid segments
    """
    # Filter for valid segments
    valid_segments = [
        s for s in segments
        if s.get('dur_s', 0) > 0
        and isinstance(s.get('dist_km'), (int, float))
        and not pd.isnull(s.get('dist_km'))
        and s.get('dist_km', 0) > 0
    ]
    
    # Return defaults if no valid segments
    if not valid_segments:
        return {
            'total_walk_time': 0,
            'total_walk_dist': 0,
            'avg_pace': np.nan,
            'avg_hr': np.nan,
            'max_hr': np.nan,
            'avg_cad': np.nan,
            'valid_segments': []
        }
    
    total_walk_time = sum(s['dur_s'] for s in valid_segments)
    total_walk_dist = sum(s['dist_km'] for s in valid_segments)
    
    # Extract valid metrics for aggregation
    paces = [s['avg_pace_min_km'] for s in valid_segments 
             if s.get('avg_pace_min_km') and not pd.isnull(s.get('avg_pace_min_km'))]
    hrs = [s['avg_hr'] for s in valid_segments 
           if s.get('avg_hr') and not pd.isnull(s.get('avg_hr'))]
    cads = [s['avg_cad'] for s in valid_segments 
            if s.get('avg_cad') and not pd.isnull(s.get('avg_cad'))]
    
    # Safely compute aggregates
    avg_pace = np.mean(paces) if paces else np.nan
    avg_hr = np.mean(hrs) if hrs else np.nan
    max_hr = max(hrs) if hrs else np.nan
    avg_cad = np.mean(cads) if cads else np.nan
    
    return {
        'total_walk_time': total_walk_time,
        'total_walk_dist': total_walk_dist,
        'avg_pace': avg_pace,
        'avg_hr': avg_hr,
        'max_hr': max_hr,
        'avg_cad': avg_cad,
        'valid_segments': valid_segments
    }


def walk_block_segments(
    gpx_df: pd.DataFrame,
    is_walk_col: str,
    pace_col: str,
    cad_col: str,
    cad_thr: int = 128,
    max_gap_s: float = 2,
    min_dur_s: int = 2
) -> List[dict]:
    """
    Group contiguous walk blocks, allowing small gaps between intervals.
    
    This function:
    1. Filters walk points to remove GPS jitter
    2. Identifies blocks of walking allowing up to max_gap_s of non-walk
    3. Classifies segments as warm-up, mid-session, or cool-down
    
    Parameters
    ----------
    gpx_df : pd.DataFrame
        Full activity DataFrame with datetime index
    is_walk_col : str
        Column indicating walk classification (boolean)
    pace_col : str
        Pace column name (min/km)
    cad_col : str
        Cadence column name (spm)
    cad_thr : int
        Cadence threshold for walk detection (default: 128 spm)
    max_gap_s : float
        Maximum gap in seconds to bridge between walk intervals (default: 2)
    min_dur_s : int
        Minimum segment duration in seconds (default: 2)
        
    Returns
    -------
    List[dict]
        List of segment dictionaries with keys:
        - segment_id : int (1-indexed)
        - start_ts : str (ISO timestamp)
        - end_ts : str (ISO timestamp)
        - dur_s : int (duration in seconds)
        - dist_km : float (distance covered)
        - avg_pace_min_km : float (average pace)
        - avg_hr : float (average heart rate)
        - avg_cad : float (average cadence)
        - tag : str ('warm-up', 'mid-session', 'cool-down', 'pause')
        - start_offset_s : int (seconds from activity start)
        - end_offset_s : int (seconds from activity end)
        - note : str (additional information)
    """
    # Filter walk points to remove GPS jitter
    walk_df = filter_gps_jitter(
        gpx_df[gpx_df[is_walk_col]].copy(), pace_col, cad_col, cad_thr
    )
    
    # Identify start/end of blocks allowing for gaps
    blocks = []
    block_start = None
    last_walk_idx = None
    
    for _, (idx, row) in enumerate(gpx_df.iterrows()):
        # Check if this is a valid walk point (in original data AND passed jitter filter)
        if row[is_walk_col] and idx in walk_df.index:
            if block_start is None:
                block_start = idx
            last_walk_idx = idx
        else:
            # Non-walk row
            if block_start is not None:
                # Check if gap exceeds max_gap_s
                time_gap = (idx - last_walk_idx).total_seconds() if last_walk_idx is not None else None
                if time_gap is not None and time_gap > max_gap_s:
                    blocks.append((block_start, last_walk_idx))
                    block_start = None
                    last_walk_idx = None
    
    # Close last block
    if block_start is not None and last_walk_idx is not None:
        blocks.append((block_start, last_walk_idx))
    
    # Build segments for each block
    session_start = gpx_df.index[0]
    session_end = gpx_df.index[-1]
    session_duration = (session_end - session_start).total_seconds()
    
    segments = []
    seg_id = 1
    
    for start_ts, end_ts in blocks:
        grp_df = gpx_df.loc[start_ts:end_ts]
        dur_s = (end_ts - start_ts).total_seconds()
        
        if dur_s < min_dur_s:
            continue
        
        # Calculate distance if cumulative column exists
        dist_km = (
            float(grp_df['distance_cumulative_km'].iloc[-1] - grp_df['distance_cumulative_km'].iloc[0])
            if 'distance_cumulative_km' in grp_df.columns
            else np.nan
        )
        
        # Sanity check: skip bad segments (long duration, zero distance)
        if dur_s >= 60 and (pd.isnull(dist_km) or dist_km <= 0):
            print(f"[SANITY DEBUG] SKIPPING BAD SEGMENT seg_id={seg_id}, dur_s={dur_s}, dist_km={dist_km}")
            continue
        
        # Calculate metrics
        avg_pace = compute_time_weighted_pace(dur_s, dist_km)
        avg_hr = grp_df['heart_rate'].mean() if 'heart_rate' in grp_df.columns else np.nan
        avg_cad = grp_df['cadence'].replace(0, np.nan).mean() if 'cadence' in grp_df.columns else np.nan
        
        # Classify segment by position in session
        start_offset = (start_ts - session_start).total_seconds()
        end_offset = (end_ts - session_start).total_seconds()
        
        if start_offset < 60:
            tag = 'warm-up'
        elif session_duration - end_offset < 120:
            tag = 'cool-down'
        else:
            tag = 'mid-session'
        
        # Add note for suspicious segments
        note = ''
        if tag == 'mid-session' and dur_s < 30 and dist_km < 0.05:
            note = 'pause?'
        
        # Format values for output
        avg_pace_val = round(avg_pace, 1) if not pd.isnull(avg_pace) else ''
        dist_km_val = round(dist_km, 3) if not pd.isnull(dist_km) else ''
        avg_hr_val = round(avg_hr, 1) if not pd.isnull(avg_hr) else ''
        avg_cad_val = round(avg_cad, 1) if not pd.isnull(avg_cad) else ''
        
        segments.append({
            'segment_id': seg_id,
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'dur_s': int(dur_s),
            'dist_km': dist_km_val,
            'avg_pace_min_km': avg_pace_val,
            'avg_hr': avg_hr_val,
            'avg_cad': avg_cad_val,
            'tag': tag,
            'start_offset_s': int(start_offset),
            'end_offset_s': int(end_offset),
            'note': note
        })
        seg_id += 1
    
    return segments
