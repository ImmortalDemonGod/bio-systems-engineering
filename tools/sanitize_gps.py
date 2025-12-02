#!/usr/bin/env python3
"""
GPS Data Sanitization Tool
===========================

Removes absolute GPS coordinates from activity files while preserving
relative distance, elevation, and physiological data.

This tool is CRITICAL for privacy protection before publishing any data.

Security Guarantees:
- Removes lat/lon columns completely
- Truncates first/last 500m to obscure start/end locations
- Preserves: distance, elevation, HR, cadence, pace, power
- Generates privacy-safe summary statistics
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np


def sanitize_dataframe(
    df: pd.DataFrame,
    truncate_start_m: float = 500,
    truncate_end_m: float = 500
) -> pd.DataFrame:
    """
    Remove GPS coordinates and truncate start/end from activity DataFrame.
    
    Parameters
    ----------
    df : pd.DataFrame
        Activity DataFrame with lat, lon, and distance columns
    truncate_start_m : float
        Distance to remove from start (metres)
    truncate_end_m : float
        Distance to remove from end (metres)
        
    Returns
    -------
    pd.DataFrame
        Sanitized DataFrame with GPS removed and endpoints truncated
    """
    # Calculate cumulative distance if not present
    if 'distance_cumulative_m' not in df.columns and 'dist' in df.columns:
        df['distance_cumulative_m'] = df['dist'].cumsum()
    
    # Find truncation points
    total_distance = df['distance_cumulative_m'].iloc[-1]
    start_cutoff = truncate_start_m
    end_cutoff = total_distance - truncate_end_m
    
    # Filter to middle portion
    mask = (
        (df['distance_cumulative_m'] >= start_cutoff) &
        (df['distance_cumulative_m'] <= end_cutoff)
    )
    df_truncated = df[mask].copy()
    
    # Remove absolute position columns
    privacy_columns = ['lat', 'lon', 'latitude', 'longitude']
    for col in privacy_columns:
        if col in df_truncated.columns:
            df_truncated = df_truncated.drop(columns=[col])
    
    # Reset distance to start from 0
    if 'distance_cumulative_m' in df_truncated.columns:
        min_dist = df_truncated['distance_cumulative_m'].min()
        df_truncated['distance_cumulative_m'] = df_truncated['distance_cumulative_m'] - min_dist
    
    # Reset index
    df_truncated = df_truncated.reset_index(drop=True)
    
    print(f"  Original points: {len(df)}")
    print(f"  After truncation: {len(df_truncated)}")
    print(f"  Removed: {len(df) - len(df_truncated)} points ({len(df) - len(df_truncated)}/len(df)*100:.1f}%)")
    print(f"  Distance preserved: {df_truncated['distance_cumulative_m'].iloc[-1]/1000:.2f} km")
    
    return df_truncated


def create_safe_summary(df: pd.DataFrame) -> dict:
    """
    Create privacy-safe summary statistics from activity data.
    
    Only includes aggregate statistics, no individual points that could
    reveal location.
    
    Parameters
    ----------
    df : pd.DataFrame
        Sanitized activity DataFrame
        
    Returns
    -------
    dict
        Safe summary statistics
    """
    summary = {
        'total_distance_km': round(df['distance_cumulative_m'].iloc[-1] / 1000, 2) if 'distance_cumulative_m' in df.columns else None,
        'duration_min': round(df['dt'].sum() / 60, 1) if 'dt' in df.columns else None,
        'elevation_gain_m': round(df['ele'].diff().clip(lower=0).sum(), 1) if 'ele' in df.columns else None,
        'elevation_loss_m': round(abs(df['ele'].diff().clip(upper=0).sum()), 1) if 'ele' in df.columns else None,
        'avg_hr_bpm': round(df['hr'].mean(), 1) if 'hr' in df.columns else None,
        'max_hr_bpm': round(df['hr'].max(), 1) if 'hr' in df.columns else None,
        'avg_cadence_spm': round(df['cadence'].replace(0, np.nan).mean(), 1) if 'cadence' in df.columns else None,
        'avg_pace_min_km': round(df['pace_sec_km'].mean() / 60, 2) if 'pace_sec_km' in df.columns else None,
        'data_points': len(df),
    }
    
    return {k: v for k, v in summary.items() if v is not None}


def sanitize_parquet_file(
    input_path: Path,
    output_path: Path,
    truncate_start_m: float = 500,
    truncate_end_m: float = 500
) -> bool:
    """
    Sanitize a Parquet file containing activity data.
    
    Parameters
    ----------
    input_path : Path
        Path to input Parquet file
    output_path : Path
        Path to output sanitized Parquet file
    truncate_start_m : float
        Distance to remove from start
    truncate_end_m : float
        Distance to remove from end
        
    Returns
    -------
    bool
        True if successful, False otherwise
    """
    try:
        print(f"\nProcessing: {input_path.name}")
        
        # Load data
        df = pd.read_parquet(input_path)
        
        # Sanitize
        df_safe = sanitize_dataframe(df, truncate_start_m, truncate_end_m)
        
        # Create summary
        summary = create_safe_summary(df_safe)
        print(f"  Summary: {summary}")
        
        # Save sanitized version
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_safe.to_parquet(output_path, index=False)
        print(f"  ✓ Saved to: {output_path}")
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main entry point for GPS sanitization tool."""
    parser = argparse.ArgumentParser(
        description="Sanitize GPS data for privacy protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sanitize a single file
  python sanitize_gps.py input.parquet output.parquet
  
  # Sanitize with custom truncation
  python sanitize_gps.py input.parquet output.parquet --start 1000 --end 1000
  
  # Process directory of files
  python sanitize_gps.py input_dir/ output_dir/ --recursive

Security:
  - Removes ALL lat/lon coordinates
  - Truncates 500m from start/end by default
  - Preserves only relative distance and physiological data
        """
    )
    
    parser.add_argument('input', type=str, help='Input Parquet file or directory')
    parser.add_argument('output', type=str, help='Output Parquet file or directory')
    parser.add_argument('--start', type=float, default=500,
                        help='Metres to truncate from start (default: 500)')
    parser.add_argument('--end', type=float, default=500,
                        help='Metres to truncate from end (default: 500)')
    parser.add_argument('--recursive', action='store_true',
                        help='Process directory recursively')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    print("=" * 60)
    print("GPS DATA SANITIZATION TOOL")
    print("=" * 60)
    print(f"Truncating: {args.start}m from start, {args.end}m from end")
    print()
    
    # Process single file
    if input_path.is_file():
        success = sanitize_parquet_file(
            input_path,
            output_path,
            args.start,
            args.end
        )
        sys.exit(0 if success else 1)
    
    # Process directory
    elif input_path.is_dir():
        if not args.recursive:
            print("Error: --recursive required for directory processing")
            sys.exit(1)
        
        pattern = "**/*.parquet" if args.recursive else "*.parquet"
        files = list(input_path.glob(pattern))
        
        if not files:
            print(f"No Parquet files found in {input_path}")
            sys.exit(1)
        
        print(f"Found {len(files)} file(s) to process")
        print()
        
        success_count = 0
        for file_path in files:
            relative_path = file_path.relative_to(input_path)
            output_file = output_path / relative_path
            
            if sanitize_parquet_file(file_path, output_file, args.start, args.end):
                success_count += 1
        
        print()
        print("=" * 60)
        print(f"Processed: {success_count}/{len(files)} files successfully")
        print("=" * 60)
        
        sys.exit(0 if success_count == len(files) else 1)
    
    else:
        print(f"Error: {input_path} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
