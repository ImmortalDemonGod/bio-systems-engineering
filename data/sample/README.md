# Sample Data

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
