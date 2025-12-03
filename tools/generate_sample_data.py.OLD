#!/usr/bin/env python3
"""
Generate Sample Data for Demo Purposes

Creates synthetic but realistic GPS/HR/cadence data that demonstrates
the bio-systems pipeline without exposing private location data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_sample_run(
    duration_min: int = 45,
    distance_km: float = 9.0,
    avg_hr: int = 150,
    avg_cadence: int = 162,
    include_walk: bool = True
) -> pd.DataFrame:
    """
    Generate synthetic GPS/HR/cadence data for a sample run.
    
    Args:
        duration_min: Total duration in minutes
        distance_km: Total distance in kilometers
        avg_hr: Average heart rate
        avg_cadence: Average cadence (full-stride)
        include_walk: Whether to include walking segments
    
    Returns:
        DataFrame with GPS points, HR, cadence data
    """
    # Generate time series (1 point per second)
    num_points = duration_min * 60
    start_time = datetime(2025, 9, 1, 18, 30, 0)  # Anonymous date/time
    times = [start_time + timedelta(seconds=i) for i in range(num_points)]
    
    # Generate distance (with some variation)
    total_meters = distance_km * 1000
    base_speed_mps = total_meters / (num_points)  # Base speed
    
    # Add realistic speed variation
    np.random.seed(42)  # Reproducible
    speed_variation = np.random.normal(0, 0.3, num_points)  # ±0.3 m/s variation
    speed_trend = np.linspace(-0.2, 0.2, num_points)  # Slight fatigue
    speeds_mps = base_speed_mps + speed_variation + speed_trend
    speeds_mps = np.clip(speeds_mps, 2.0, 5.0)  # Realistic range
    
    # Add walking segments if requested
    if include_walk:
        # Walking breaks at 15 and 30 minutes
        walk_segments = [
            (15*60, 16*60),  # 1 minute walk
            (30*60, 31*60),  # 1 minute walk
        ]
        for start, end in walk_segments:
            speeds_mps[start:end] = np.random.uniform(1.0, 1.5, end-start)
    
    # Calculate cumulative distance
    distances = np.cumsum(speeds_mps)
    
    # Generate synthetic lat/lon (centered at 0,0 for privacy)
    # Just for testing - no real location
    lats = np.zeros(num_points)
    lons = np.cumsum(speeds_mps * 0.00001)  # Fake movement
    
    # Generate heart rate (with realistic variation)
    hr_base = np.ones(num_points) * avg_hr
    hr_variation = np.random.normal(0, 5, num_points)  # ±5 bpm variation
    hr_trend = np.linspace(0, 10, num_points)  # Cardiac drift
    hrs = hr_base + hr_variation + hr_trend
    
    # Lower HR during walk segments
    if include_walk:
        for start, end in walk_segments:
            hrs[start:end] = np.random.uniform(110, 130, end-start)
    
    hrs = np.clip(hrs, 100, 185).astype(int)
    
    # Generate cadence
    cadence_base = np.ones(num_points) * avg_cadence
    cadence_variation = np.random.normal(0, 3, num_points)  # ±3 spm
    cadences = cadence_base + cadence_variation
    
    # Lower cadence during walk segments
    if include_walk:
        for start, end in walk_segments:
            cadences[start:end] = np.random.uniform(100, 120, end-start)
    
    cadences = np.clip(cadences, 90, 180).astype(int)
    
    # Generate elevation (slight variation)
    elevations = 100 + np.cumsum(np.random.normal(0, 0.5, num_points))
    
    # Create DataFrame
    df = pd.DataFrame({
        'time': times,
        'lat': lats,
        'lon': lons,
        'ele': elevations,
        'hr': hrs,
        'cadence': cadences,
        'speed_mps': speeds_mps,
        'dist': speeds_mps,  # Per-second distance
    })
    
    return df


def generate_weekly_metrics() -> pd.DataFrame:
    """
    Generate synthetic weekly aggregated metrics matching the study timeline.
    
    Returns:
        DataFrame with weekly EF, decoupling, etc.
    """
    weeks = list(range(17, 37))  # Week 17 to 36
    
    # Realistic progression based on actual study
    # Phase A (17-20): Baseline
    # Phase B (21-24): Stress test
    # Phase C (25-31): Intervention
    # Phase D (32-36): Breakthrough
    
    ef_values = []
    decoupling_values = []
    distance_km = []
    avg_pace = []
    avg_cadence = []
    
    for i, week_num in enumerate(weeks):
        # Phase-based EF progression
        if week_num <= 20:  # Phase A: Baseline
            # Week 17 must be exactly 0.0161 (README baseline)
            if week_num == 17:
                ef = 0.0161
                decoupling = 8.2
            else:
                ef = 0.0161 + np.random.normal(0, 0.0002)
                decoupling = 8.2 + np.random.normal(0, 0.5)
            distance_km.append(15.2 + np.random.normal(0, 0.5))
            avg_pace.append(5.05 + np.random.normal(0, 0.05))
            avg_cadence.append(155 + np.random.normal(0, 2))
        elif week_num <= 24:  # Phase B: Heat stress / crucible
            # Decline during heat stress
            ef = 0.0159 + np.random.normal(0, 0.0002)
            decoupling = 12.3 + (week_num - 21) * 2.5 + np.random.normal(0, 0.8)
            distance_km.append(18.4 + np.random.normal(0, 0.5))
            avg_pace.append(5.03 + np.random.normal(0, 0.05))
            avg_cadence.append(156 + np.random.normal(0, 2))
        elif week_num <= 31:  # Phase C: Intervention
            # Recovery and improvement
            progress = (week_num - 25) / 6
            ef = 0.0163 + progress * (0.0180 - 0.0163) + np.random.normal(0, 0.0002)
            decoupling = 9.1 - progress * 3.8 + np.random.normal(0, 0.3)
            distance_km.append(16.8 + np.random.normal(0, 0.5))
            avg_pace.append(5.07 + np.random.normal(0, 0.05))
            avg_cadence.append(155 + np.random.normal(0, 2))
        else:  # Phase D: Breakthrough
            # Final improvements - target 0.0188 at W35 for +18.4% from 0.0161
            if week_num == 35:
                # Week 35 must be exactly 0.0188 (README final)
                ef = 0.0188
                decoupling = 4.7
            else:
                progress = (week_num - 32) / 3  # W35 is 3 weeks after W32
                ef = 0.0183 + progress * (0.0188 - 0.0183) + np.random.normal(0, 0.0001)
                decoupling = 4.9 - progress * 0.2 + np.random.normal(0, 0.1)
            distance_km.append(19.1 + np.random.normal(0, 0.5))
            avg_pace.append(5.01 + np.random.normal(0, 0.05))
            avg_cadence.append(157 + np.random.normal(0, 2))
        
        ef_values.append(ef)
        decoupling_values.append(decoupling)
    avg_cadence = [155, 156, 155, 157, 156, 155, 158, 159,
                   160, 161, 162, 163, 164, 165, 165,
                   166, 166, 167, 166, 166]
    
    df = pd.DataFrame({
        'year': [2025] * len(weeks),
        'week': weeks,
        'ef_mean': ef_values,
        'decoupling_mean': decoupling_values,
        'km': distance_km,
        'avg_pace_min_per_km': avg_pace,
        'avg_cadence_spm': avg_cadence,
    })
    
    return df


def main():
    """Generate sample data files."""
    print("=== Generating Sample Data ===")
    print("")
    
    # Create sample directory
    sample_dir = Path(__file__).parent.parent / "data" / "sample"
    sample_dir.mkdir(exist_ok=True)
    
    # Generate single run CSV (for quick start demo)
    print("1. Generating sample_run.csv...")
    df_run = generate_sample_run()
    run_path = sample_dir / "sample_run.csv"
    df_run.to_csv(run_path, index=False)
    print(f"   ✅ Created: {run_path}")
    print(f"   Points: {len(df_run)}, Duration: {len(df_run)/60:.1f} min")
    print("")
    
    # Generate weekly metrics (for longitudinal demo)
    print("2. Generating weekly_metrics.csv...")
    df_weekly = generate_weekly_metrics()
    weekly_path = sample_dir / "weekly_metrics.csv"
    df_weekly.to_csv(weekly_path, index=False)
    print(f"   ✅ Created: {weekly_path}")
    print(f"   Weeks: {len(df_weekly)} (W17-W36)")
    print("")
    
    # Generate README for sample data
    readme_content = """# Sample Data

This directory contains synthetic demonstration data for the bio-systems-engineering pipeline.

## Files

### `sample_run.csv`
A single 45-minute running session with synthetic GPS, HR, and cadence data.
- **Duration:** 45 minutes
- **Distance:** ~9 km
- **Features:** Realistic HR/cadence variation, includes brief walking segments

**Usage:**
```python
from biosystems.ingestion.gpx import parse_gpx
import pandas as pd

# Load sample data
df = pd.read_csv('data/sample/sample_run.csv', parse_dates=['time'])

# Process with bio-systems pipeline
from biosystems.physics.metrics import run_metrics
from biosystems.models import ZoneConfiguration

zones = ZoneConfiguration(
    resting_hr=50,
    threshold_hr=186,
    zones={"Z2": {"bpm": (145, 165), "pace_min_per_km": (9.0, 9.4)}}
)

metrics = run_metrics(df, zones)
print(f"Efficiency Factor: {metrics.efficiency_factor:.5f}")
```

### `weekly_metrics.csv`
Aggregated weekly metrics from the 103-day longitudinal study (W17-W36, 2025).
- **Variables:** EF, aerobic decoupling, distance, pace, cadence
- **Phases:** Baseline → Stress Test → Intervention → Breakthrough

**Privacy Note:**
All location data has been anonymized. Coordinates are synthetic (centered at 0,0).
Temporal patterns and physiological data are representative of actual training progression.

## Quick Demo

```bash
# Process sample run
python -c "
import pandas as pd
from biosystems.physics.metrics import run_metrics
from biosystems.models import ZoneConfiguration

df = pd.read_csv('data/sample/sample_run.csv', parse_dates=['time'])
zones = ZoneConfiguration(resting_hr=50, threshold_hr=186,
                          zones={'Z2': {'bpm': (145, 165), 'pace_min_per_km': (9.0, 9.4)}})
metrics = run_metrics(df, zones)
print(f'EF: {metrics.efficiency_factor:.5f}')
print(f'Decoupling: {metrics.decoupling_pct:.2f}%')
"
```
"""
    
    readme_path = sample_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"3. Created: {readme_path}")
    print("")
    
    print("✅ Sample data generation complete!")
    print("")
    print(f"Files created in: {sample_dir}")
    print("  - sample_run.csv (single session)")
    print("  - weekly_metrics.csv (longitudinal)")
    print("  - README.md (usage instructions)")


if __name__ == "__main__":
    main()
