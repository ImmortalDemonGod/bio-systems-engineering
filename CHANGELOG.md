# Changelog

All notable changes to the bio-systems-engineering library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- Support for cycling power data
- Swimming pace analysis
- Multi-sport transition handling
- CLI test coverage expansion

## [1.1.0] - 2026-03-22

### Added
- **Strava API Ingestion** (`src/biosystems/ingestion/strava.py`): OAuth
  refresh-token flow, exponential backoff on 429/5xx, stream + metadata
  parsing aligned to GPX/FIT schema
- **Wellness Intelligence** (`src/biosystems/wellness/`): HabitDash API client,
  Parquet-backed sync cache, dual G/A/R pre-run/post-run signals, longitudinal
  analytics (sleep debt, recovery model, VO2max trend)
- **Advanced Reporting** (`src/biosystems/physics/report.py`): `FullRunReport`
  with dual session/run-only metrics, walk analysis, run dynamics, stride
  detection, distribution stats, per-km splits, Strava best efforts
- **Analytics layer** (`src/biosystems/analytics/`): PMC (ATL/CTL/TSB), JSON
  Lines run history with FileLock concurrency, trending EF/decoupling over
  10-run window
- **CLI** (`src/biosystems/cli.py`): Typer-based `biosystems` command exposing
  `strava`, `wellness-sync`, `wellness-show`, `wellness-analyze`,
  `wellness-trends`, `backfill-streams`
- **Operational tooling** (`tools/`): `ingest_new_runs.py` batch processor,
  `strava_auth.py` OAuth helper
- New Pydantic models: `KmSplit`, `Lap`, `BestEffort`, `BlockBest`,
  `WalkSummary`, `StrideSegment`, `RunDynamics`, `DistributionStats`
- `docs/WELLNESS.md`: signal timing guide for pre-run vs post-run gating

### Fixed
- Walk segments now excluded from EF and decoupling (previously inflating HR
  metrics)
- GAP suppressed when elevation quality check fails (>10% Minetti clamp rate)
- Minetti polynomial clamped to ±45% grade to prevent divergence on GPS glitches
- Aerobic decoupling split by elapsed time, not sample index (fixes
  variable-rate streams)
- `HeartRateZone` lower bound now accepts 0 (allows Z1 starting at rest)
- `RunContext` optional fields default to `None` (prevents NaN propagation)
- Walk detection fallback returns `None` instead of empty strings
- FIT parser forces UTC-aware timestamps
- GPS sanitization hardened for short activities
- Open-Meteo weather client uses archive endpoint for dates >3 days ago;
  reduces requests from ~891 to ≤3 per call
- `pandas` `freq='S'` deprecated string replaced with `'s'` throughout tests
- `pd.isna()` used for NaN comparisons in tests (pandas ≥ 2.2 compatibility)

### Changed
- Python CI matrix extended to 3.10 / 3.11 / 3.12
- `requirements.txt` synchronised with `pyproject.toml` dependencies
- `.gitignore` updated to exclude processed outputs, parquet caches, and
  `.cache/` from version control

## [1.0.0] - 2025-12-02

### Added
- Initial release of bio-systems-engineering library
- **Ingestion Module**: Parsers for GPX and FIT files with GPS/HR/cadence
  support
- **Physics Module**:
  - Efficiency Factor (EF) calculation with metabolic filtering
  - Aerobic Decoupling analysis
  - Grade Adjusted Pace (GAP) using Minetti's equation
  - Training Stress Score (TSS) calculation
- **Signal Module**:
  - Walk detection with dual-criterion classifier (pace + cadence)
  - GPS jitter filtering
  - Walk segment analysis
- **Models Module**: Pydantic v2 models for type-safe data validation
  - `ZoneConfig`: Heart rate and pace zone definitions
  - `PhysiologicalMetrics`: Calculated summary metrics
  - `ActivitySummary`: Per-activity summary record
- **Environment Module**: Weather data integration via Open-Meteo API
- **Tools**:
  - `sanitize_gps.py`: Privacy-preserving GPS data sanitization
  - `verify_installation.py`: Installation verification script
- Docker support for reproducible environments
- GitHub Actions CI across Python 3.10 / 3.11 / 3.12

### Features
- Type-safe data processing with Pydantic v2 validation
- Stateless, pure functional design for reproducibility
- Privacy-first architecture (no data storage in library)
- Configurable zone thresholds via `zones_personal.yml`
- Graceful degradation for incomplete data (e.g., HR-only files)
- Support for single-leg cadence auto-detection and doubling

### Documentation
- README with quick-start guide and longitudinal study results
- `DATA_PREPARATION` guide for users
- `CITATION.cff` for academic citation

### Known Limitations
- GAP calculation requires elevation data
- Weather data gracefully skipped if Open-Meteo is unreachable
- Metabolic filtering assumes Zone 2 lower bound at 130 bpm (configurable)
