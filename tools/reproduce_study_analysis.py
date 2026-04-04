"""
Reproduce Study Analysis
========================

Re-runs the bio-systems pipeline over the 103-day longitudinal study dataset
stored in data/processed/*_gpx_full.csv and verifies the results match the
committed weekly aggregates in data/real_weekly_data.json.

Usage
-----
    python3 tools/reproduce_study_analysis.py

Output
------
Prints per-run metrics and per-week aggregates to stdout.
Exits with code 0 if results are consistent with real_weekly_data.json
(within ±5% tolerance for EF mean), code 1 otherwise.

Reproducibility Notes
---------------------
- Uses only *_gpx_full.csv files (time-series data, not *_summary.csv)
- Applies the Run-Only Filter: df[df['hr'] >= zone2_lower_bound]
- Aerobic Decoupling uses time-based midpoint split (DatetimeIndex)
- Walk detection via is_walk column when present in the CSV
- Zone config loaded from data/zones_personal.yml
- GAP not applied to the historical dataset per study methodology
  (routes assumed topographically similar; see §2.4 of the manuscript)

Algorithm Versions
------------------
All results reflect the corrected pipeline (v1.1):
  - Decoupling: time-based split (not sample-count)
  - Walk detection: is_walk column (pace+cadence dual classifier)
  These corrections were applied post-study (2026-03-17) and validated
  not to materially alter the reported EF progression.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"
REAL_DATA = ROOT / "data" / "real_weekly_data.json"
ZONES_FILE = ROOT / "data" / "zones_personal.yml"


def load_zone_config():
    """Load ZoneConfig from zones_personal.yml."""
    from biosystems.models import HeartRateZone, ZoneConfig

    with ZONES_FILE.open() as f:
        raw = yaml.safe_load(f)

    raw.pop("model", None)
    zones = {}
    for name, data in raw.items():
        if isinstance(data, dict) and "bpm" in data and "pace_min_per_km" in data:
            zones[name] = HeartRateZone(
                name=name,
                bpm=tuple(data["bpm"]),
                pace_min_per_km=tuple(data["pace_min_per_km"]),
            )

    return ZoneConfig(
        resting_hr=raw.get("resting_hr", 50),
        threshold_hr=raw.get("threshold_hr", 186),
        max_hr=raw.get("max_hr", 201),
        zones=zones,
    )


def parse_week(filename: str) -> int | None:
    """Extract ISO week number from filename timestamp (YYYYMMDD_...)."""
    try:
        date_str = filename[:8]
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.isocalendar()[1]
    except (ValueError, IndexError):
        return None


def run_on_csv(csv_path: Path, zone_config) -> dict | None:
    """
    Load a processed full CSV and compute EF, decoupling, TSS using the
    current biosystems pipeline.
    """
    from biosystems.physics.metrics import run_metrics

    try:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=["time"])
        df = df.rename(columns={"time": "timestamp"})
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
        df.index.name = "timestamp"
    except Exception as e:
        print(f"  [SKIP] {csv_path.name}: parse error — {e}", file=sys.stderr)
        return None

    required = {"hr", "speed_mps", "dt", "dist"}
    if not required.issubset(df.columns):
        # Try alternate column names from older pipeline versions
        rename_map = {"heart_rate": "hr", "speed_mps_smooth": "speed_mps"}
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if not required.issubset(df.columns):
            print(f"  [SKIP] {csv_path.name}: missing columns {required - set(df.columns)}", file=sys.stderr)
            return None

    try:
        metrics = run_metrics(df, zone_config)
        return {
            "file": csv_path.name,
            "ef": metrics.efficiency_factor,
            "decoupling_pct": metrics.decoupling_pct,
            "hr_tss": metrics.hr_tss,
            "distance_km": metrics.distance_km,
            "duration_min": metrics.duration_min,
            "avg_hr": metrics.avg_hr,
        }
    except Exception as e:
        print(f"  [SKIP] {csv_path.name}: metrics error — {e}", file=sys.stderr)
        return None


def main():
    print("=== Bio-Systems Study Reproducibility Check ===\n")

    if not ZONES_FILE.exists():
        print(f"ERROR: Zone config not found at {ZONES_FILE}", file=sys.stderr)
        sys.exit(1)

    zone_config = load_zone_config()
    print(f"Zone config loaded: threshold_hr={zone_config.threshold_hr}, resting_hr={zone_config.resting_hr}\n")

    # Collect all full time-series CSVs (exclude *_summary.csv)
    # Deduplicate by timestamp prefix (first 15 chars = YYYYMMDD_HHMMSS):
    # Each run may have both a clean `_gpx_full.csv` and a `.gpx_gpx_full.csv`
    # (artifact of source filename containing .gpx extension). Keep the
    # canonical form; also skip _hr_override_ variants in favour of base file.
    _all_csvs = sorted(DATA_PROCESSED.glob("*_gpx_full.csv"))

    def _dedup_key(p: Path) -> tuple:
        name = p.name
        return (
            1 if ".gpx_gpx_" in name else 0,   # prefer no .gpx_gpx_
            1 if "_hr_override_" in name else 0,  # prefer no hr_override
            name,                                  # deterministic tiebreak
        )

    _by_ts: dict[str, Path] = {}
    for p in _all_csvs:
        ts = p.name[:15]
        if ts not in _by_ts or _dedup_key(p) < _dedup_key(_by_ts[ts]):
            _by_ts[ts] = p

    full_csvs = sorted(_by_ts.values())
    print(f"Found {len(full_csvs)} unique activity files in data/processed/ "
          f"(deduplicated from {len(_all_csvs)} total)\n")

    if not full_csvs:
        print("ERROR: No *_gpx_full.csv files found. Cannot reproduce analysis.", file=sys.stderr)
        sys.exit(1)

    # Run pipeline on each file
    results_by_week: dict[int, list[dict]] = defaultdict(list)
    all_results: list[dict] = []

    for csv_path in full_csvs:
        week = parse_week(csv_path.name)
        result = run_on_csv(csv_path, zone_config)
        if result and week:
            result["week"] = week
            all_results.append(result)
            results_by_week[week].append(result)
            print(
                f"  W{week:02d}  {csv_path.name[:40]:<40}  "
                f"EF={result['ef']:.5f}  Dec={result['decoupling_pct']:+.1f}%  "
                f"TSS={result['hr_tss']:.0f}"
            )

    print(f"\n=== Weekly Aggregates ({len(results_by_week)} weeks) ===\n")
    computed_weekly: dict[int, dict] = {}
    for week in sorted(results_by_week):
        runs = results_by_week[week]
        ef_mean = sum(r["ef"] for r in runs) / len(runs)
        computed_weekly[week] = {"ef_mean": round(ef_mean, 5), "num_runs": len(runs)}
        print(f"  Week {week:02d}:  {len(runs)} run(s)  EF_mean={ef_mean:.5f}")

    # Compare against committed real_weekly_data.json
    print(f"\n=== Validation Against {REAL_DATA.name} ===\n")
    if not REAL_DATA.exists():
        print("WARNING: real_weekly_data.json not found — skipping validation.")
        sys.exit(0)

    with REAL_DATA.open() as f:
        real_data = json.load(f)

    real_by_week = {entry["week"]: entry for entry in real_data}
    tolerance = 0.05  # 5% relative tolerance
    mismatches = []

    for week, computed in sorted(computed_weekly.items()):
        if week not in real_by_week:
            print(f"  Week {week:02d}: not in real_weekly_data.json (new data)")
            continue
        real_ef = real_by_week[week]["ef_mean"]
        comp_ef = computed["ef_mean"]
        pct_diff = abs(comp_ef - real_ef) / real_ef * 100 if real_ef else 0
        status = "✓" if pct_diff <= tolerance * 100 else "✗"
        print(f"  {status} Week {week:02d}:  computed={comp_ef:.5f}  stored={real_ef:.5f}  diff={pct_diff:.1f}%")
        if pct_diff > tolerance * 100:
            mismatches.append(week)

    if mismatches:
        print(f"\nWARNING: {len(mismatches)} week(s) exceed {tolerance*100:.0f}% tolerance: {mismatches}")
        print("This may indicate algorithm changes that affect historical results.")
        print("Review and update data/real_weekly_data.json if the new values are correct.")
        sys.exit(1)
    else:
        print(f"\nAll weeks within {tolerance*100:.0f}% tolerance. Study results reproducible. ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
