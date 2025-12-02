# Data Preparation for Publication

**CRITICAL:** This document outlines the privacy-safe data preparation workflow before ANY public release.

## Privacy Principles

1. **No Absolute Coordinates** - All lat/lon must be removed
2. **Truncate Endpoints** - Remove 500m from start/end to obscure home/destinations
3. **Preserve Relative Data** - Keep distance, elevation, HR, cadence
4. **Summary Only** - Publish aggregated statistics, not individual points
5. **Review Every File** - Manual audit before release

---

## Data Sanitization Workflow

### Step 1: Identify Files to Sanitize

```bash
# List all raw data files
find data/raw -name "*.gpx" -o -name "*.fit"

# Check what would be sanitized
ls data/processed/*.parquet
```

### Step 2: Run Sanitization Tool

```bash
# Sanitize a single activity
python tools/sanitize_gps.py \
    data/processed/run_2024_01_15.parquet \
    data/sanitized/run_2024_01_15_safe.parquet

# Batch process entire directory
python tools/sanitize_gps.py \
    data/processed/ \
    data/sanitized/ \
    --recursive

# Custom truncation (remove 1km from each end)
python tools/sanitize_gps.py \
    data/processed/run.parquet \
    data/sanitized/run_safe.parquet \
    --start 1000 \
    --end 1000
```

### Step 3: Verify Sanitization

```python
import pandas as pd

# Load sanitized file
df = pd.read_parquet('data/sanitized/run_safe.parquet')

# CRITICAL CHECKS
assert 'lat' not in df.columns, "ERROR: lat column still present!"
assert 'lon' not in df.columns, "ERROR: lon column still present!"
assert 'latitude' not in df.columns, "ERROR: latitude column still present!"
assert 'longitude' not in df.columns, "ERROR: longitude column still present!"

# Verify truncation
print(f"Data points: {len(df)}")
print(f"Distance range: {df['distance_cumulative_m'].iloc[0]:.0f}m to {df['distance_cumulative_m'].iloc[-1]:.0f}m")

# Check safe columns are preserved
safe_columns = ['distance_cumulative_m', 'ele', 'hr', 'cadence', 'pace_sec_km']
for col in safe_columns:
    if col in df.columns:
        print(f"✓ {col}: {df[col].notna().sum()} valid values")
```

---

## Safe vs. Unsafe Data

### ✅ SAFE to Publish
- Relative distance (metres, km)
- Elevation changes (metres)
- Heart rate (bpm)
- Cadence (spm)
- Pace (min/km)
- Power (watts)
- Time intervals (seconds, minutes)
- Aggregate statistics (mean, median, percentiles)
- Anonymized IDs (e.g., "Run #42")

### ❌ NEVER Publish
- Absolute GPS coordinates (lat/lon)
- Timestamps with dates (use relative time only)
- First/last 500m of any activity
- Garmin device IDs
- API keys or tokens
- Personal identifiers (name, email, age, exact location)
- Raw GPX/FIT files

---

## Example: Safe Data Structure

```python
# After sanitization, data looks like this:
{
    'distance_cumulative_m': [0, 10, 20, ...],      # ✓ Relative
    'ele': [100, 101, 102, ...],                    # ✓ Relative
    'hr': [145, 147, 148, ...],                     # ✓ Safe
    'cadence': [168, 170, 169, ...],                # ✓ Safe
    'pace_sec_km': [320, 318, 322, ...],            # ✓ Safe
    'dt': [1.0, 1.0, 1.0, ...],                     # ✓ Time intervals
    # NO lat/lon columns!
}

# Safe summary statistics:
{
    'total_distance_km': 10.5,
    'duration_min': 65.3,
    'elevation_gain_m': 145,
    'avg_hr_bpm': 162,
    'avg_pace_min_km': 6.2
}
```

---

## Pre-Publication Checklist

Before committing ANY data to Git or publishing:

- [ ] Run sanitization tool on all data files
- [ ] Verify NO lat/lon columns in output
- [ ] Confirm 500m+ truncation from endpoints
- [ ] Check .gitignore blocks raw GPX/FIT files
- [ ] Review all summary statistics for identifiable info
- [ ] Test that code works with sanitized data only
- [ ] Audit commit history for accidental raw data
- [ ] Get second review of data privacy

---

## Example Usage

```bash
# Full workflow from raw GPX to safe publication data

# 1. Parse raw data (not committed to Git)
python -c "
from biosystems.ingestion import parse_gpx
df = parse_gpx('data/raw/activity.gpx')
df.to_parquet('data/processed/activity.parquet')
"

# 2. Sanitize for publication
python tools/sanitize_gps.py \
    data/processed/activity.parquet \
    data/sanitized/activity_safe.parquet

# 3. Generate analysis from SAFE data only
python -c "
from biosystems.physics import run_metrics
from biosystems.models import ZoneConfig
import pandas as pd

df = pd.read_parquet('data/sanitized/activity_safe.parquet')
zones = ZoneConfig(...)
metrics = run_metrics(df, zones)
print(metrics)
"

# 4. Commit ONLY sanitized data
git add data/sanitized/activity_safe.parquet
git commit -m 'data: add sanitized activity for analysis'
```

---

## File Organization

```
data/
├── raw/                    # ❌ NEVER commit (in .gitignore)
│   ├── *.gpx
│   └── *.fit
├── processed/              # ⚠️  CAUTION: May contain GPS
│   └── *.parquet
└── sanitized/              # ✅ SAFE for publication
    └── *_safe.parquet
```

---

## Emergency: Data Leak Response

If GPS coordinates are accidentally committed:

1. **DO NOT** just delete the file in a new commit
2. **IMMEDIATELY** rewrite Git history:
   ```bash
   # Remove file from entire history
   git filter-branch --force --index-filter \
       "git rm --cached --ignore-unmatch path/to/sensitive/file" \
       --prune-empty --tag-name-filter cat -- --all
   
   # Force push (if already pushed)
   git push origin --force --all
   ```
3. Consider the data permanently exposed if pushed to public repo
4. Rotate any exposed credentials
5. Notify collaborators

---

## Questions?

**Q: Can I publish approximate location (city/country)?**  
A: Yes, but only as broad as "City, Country" level. Never neighborhood or street.

**Q: What about elevation data?**  
A: Relative elevation changes are safe. Absolute altitude above sea level should be avoided.

**Q: Can I share pace/HR data by segment?**  
A: Yes, if segments are defined by distance markers (e.g., "km 5-6") not GPS coordinates.

**Q: How to handle multi-activity analysis?**  
A: Use anonymized IDs ("Run #1", "Run #2") and aggregate statistics only.

---

**Remember:** When in doubt, DON'T publish. Privacy > Publication.
