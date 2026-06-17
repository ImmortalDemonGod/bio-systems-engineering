# 01 — Comprehensive Understanding

## Provisional intent
PROVISIONAL: This repository serves a dual purpose: (1) a reusable open-source Python analytics library (`biosystems`, v1.0.0, MIT) for running-physiology data pipelines accepting Garmin .fit/.gpx files and Strava API data, computing physiological metrics (Efficiency Factor, aerobic decoupling, GAP, hrTSS, PMC), and integrating wearable wellness telemetry (Whoop + Garmin via HabitDash); and (2) the primary data artifact of a 103-day N=1 longitudinal self-experiment (2025 W17-W36) in which a single athlete applied targeted cadence-modification drills (NME drills) under Zone 2 aerobic training, achieving an 18% EF improvement and 50.6% decoupling reduction. The repo is simultaneously a production daily-use system (the athlete continues to use `biosystems strava` and the LLM daily brief post-study) and a scientific report (`reports/01_longitudinal_study.md`) approaching publication readiness (see `docs/PUBLICATION_CHECKLIST.md`). The AIV commit protocol enforces falsifiable evidence with each code change. The forensic audit pipeline (`audit/forensic-audit.mjs`) is an active meta-layer running on top of the codebase.

## Architecture
The repository is organized as a Python library (src/biosystems/) with 7 subsystems, a CLI layer, operational tools, and a post-run LLM briefing pipeline.

SUBSYSTEMS:

1. models (src/biosystems/models.py): Pydantic v2 data contracts that flow between all other subsystems. Key types: HeartRateZone, ZoneConfig (HR zone configuration), RunContext (temperature, weather, HRV, RHR, sleep for a given run), PhysiologicalMetrics (EF, decoupling, hrTSS, distance, pace, cadence), FullRunReport (comprehensive report combining session+run-only metrics, walk analysis, zone distributions, dynamics, splits, laps, best efforts, block bests). All other subsystems consume these contracts.

2. ingestion (src/biosystems/ingestion/): Three parsers producing a normalized pandas DataFrame with UTC DatetimeIndex and columns: hr, cadence, speed_mps, dist, dt, pace_sec_km, ele, latitude, longitude, moving. Parsers: fit.py (Garmin binary via fitdecode; semicircle->degree conversion), gpx.py (XML via stdlib; haversine distance from GPS coordinates), strava.py (Strava V3 REST API with OAuth2 refresh-token flow; fetches streams, activity metadata, laps, splits, best efforts, device info; exponential backoff on HTTP 429/5xx).

3. physics (src/biosystems/physics/): Pure-computation algorithms on DataFrames. gap.py: Minetti et al. energy-cost polynomial for Grade Adjusted Pace; elevation quality check (suppresses GAP when elevation data is unreliable). metrics.py: calculate_efficiency_factor (speed_mps/HR, walk-filtered), calculate_decoupling (Pa:HR split by time), calculate_hr_tss (hrTSS from zone threshold and duration), compute_training_zones, run_metrics() (top-level compositor returning PhysiologicalMetrics). report.py: build_run_report() assembles FullRunReport by calling run_metrics on both the full session and walk-filtered run-only data, adding GAP-adjusted EF, EF CV (reliability), AeV (aerobic efficiency velocity via linear regression at reference HR), zone time distributions, walk segment analysis, stride detection, within-run dynamics (HR drift, pace strategy), km splits, laps, block bests vs recorded history.

4. signal (src/biosystems/signal/): walk_detection.py classifies each row as is_walk using dual threshold (pace>9.5 min/km OR cadence<140 spm); also respects Strava moving flag when present. walk_block_segments() extracts contiguous walk segments, tags them (warm-up/mid-session/cool-down/pause), and collects HR recovery rate. filter_gps_jitter() removes noise from walk segments.

5. analytics (src/biosystems/analytics/): Longitudinal persistence and trending. history.py: append-only JSON Lines file at ~/.biosystems/history.jsonl; filelock-protected writes; deduplication by strava_activity_id (primary) or date (fallback); also provides backfill_from_strava() and detect_block_bests(). trending.py: compute_pmc() implements ATL (7-day EMA) and CTL (42-day EMA) from the Banister Impulse-Response model; compute_rolling_stats(); summarize_trend().

6. environment (src/biosystems/environment/): weather.py fetches historical hourly weather from Open-Meteo API for a given lat/lon/datetime; caches JSON responses to disk (WeatherCache); maps WMO weather codes to human-readable descriptions. Used by the strava CLI command to auto-enrich RunContext.

7. wellness (src/biosystems/wellness/): habitdash.py is a REST client for the HabitDash aggregation API (Whoop + Garmin biometrics; stable field IDs for HRV, RHR, sleep, body battery, strain, VO2max, respiratory rate; 15s inter-request delay; 3 retries on 429). cache.py manages ~/.biosystems/wellness.parquet: sync_wellness() pulls N days from HabitDash and merges; compute_wellness_context() returns a dict with raw values, 1d/7d deltas, G/A/R readiness signal (two flavors: all-signal and overnight-only), staleness warning, and calibrated thresholds; enrich_run_context() injects wellness data into RunContext. analytics.py: pure-computation analytics (no biosystems imports) covering coverage per metric, era stats (Whoop era ends 2025-12-25; Garmin-only era from 2026-01-01), cross-metric correlation matrix, calibrated G/A/R thresholds (personal p20/p40/p75/p90 vs clinical fallbacks), longitudinal RHR/VO2max trends, sleep debt.

DATA FLOW:
Raw activity (.fit/.gpx) or Strava API --> ingestion parsers --> normalized DataFrame
--> signal.walk_detection (add is_walk column)
--> physics.metrics.run_metrics() [walk-filtered] --> PhysiologicalMetrics
--> physics.report.build_run_report() --> FullRunReport (Pydantic, JSON-serializable)
--> analytics.history.append_run() --> ~/.biosystems/history.jsonl
--> analytics.trending.compute_pmc() + compute_rolling_stats() --> PMC + trends

Parallel enrichment paths:
- environment.weather.fetch_weather_open_meteo() --> RunContext.temperature_c / weather_code
- wellness.cache.enrich_run_context() --> RunContext.hrv_rmssd / rest_hr / sleep_score

CLI LAYER: src/biosystems/cli.py registers a Typer app with 12 commands grouped into Data Ingestion, Analytics, and Wellness panels. The biosystems console_scripts entry point (pyproject.toml:58) makes it available as `biosystems` on PATH.

OPERATIONAL LAYER: tools/ scripts for one-time setup (strava_auth.py), batch ingestion (ingest_new_runs.py), privacy sanitization (sanitize_gps.py), reproducibility verification (reproduce_study_analysis.py), chart generation, and installation verification.

POST-RUN BRIEFING: daily_running_brief/daily_running_brief.py (run from ~/.openclaw/workspace/scripts/ via cron at 20:00) calls `biosystems strava --list` and per-run fetches, pre-computes all numeric comparisons in Python, then drives OpenAI (gpt-4o-mini primary) or Anthropic (claude-sonnet-4-6 fallback) to write a narrative running brief to ~/.openclaw/workspace/memory/intelligence/.

FORENSIC AUDIT: audit/forensic-audit.mjs is a Node.js orchestrator that runs the current audit pipeline (five stages, each a schema-validated `claude -p` worker).

## Coverage
- denominator (total files): **174** · classified: **174** · unknown: **0**

## Entry points (33)
| name | kind | location | description |
|---|---|---|---|
| `biosystems (CLI entry point)` | cli | `pyproject.toml:58` | console_scripts registration: biosystems = biosystems.cli:app; installs the `biosystems` command on PATH |
| `analyze` | cli | `src/biosystems/cli.py:102` | Parse a .fit or .gpx activity file and output PhysiologicalMetrics as JSON or text |
| `strava` | cli | `src/biosystems/cli.py:166` | Fetch a Strava activity (or list recent), compute FullRunReport with auto-weather/wellness enrichment, persist to history |
| `backfill-efforts` | cli | `src/biosystems/cli.py:475` | Backfill Strava best-effort times (400m, 1K, 5K, etc.) for the last N runs into the local history store |
| `backfill-streams` | cli | `src/biosystems/cli.py:544` | Backfill full GPS+HR stream metrics (EF, decoupling, hrTSS) for all runs since a given date; rate-limited at 18s/run |
| `summary` | cli | `src/biosystems/cli.py:723` | Period-aggregated statistics (month/week/all) from history: run count, EF mean/best, decoupling, HR, pace, TSS |
| `efforts` | cli | `src/biosystems/cli.py:822` | Best-effort progression by distance (first recorded -> current best, improvement) from strava_efforts in history |
| `top` | cli | `src/biosystems/cli.py:939` | Rank top N runs by EF, decoupling, pace, TSS, or distance from local history |
| `trend` | cli | `src/biosystems/cli.py:1014` | Longitudinal fitness trends: PMC (ATL/CTL/TSB), rolling EF/decoupling stats, optional Strava backfill |
| `wellness-sync` | cli | `src/biosystems/cli.py:1106` | Pull HabitDash wellness metrics (Whoop + Garmin) into ~/.biosystems/wellness.parquet for N days |
| `wellness-show` | cli | `src/biosystems/cli.py:1143` | Show G/A/R readiness signal plus raw HRV, RHR, sleep, body battery with 1d/7d deltas for a given date |
| `wellness-analyze` | cli | `src/biosystems/cli.py:1260` | Coverage report, era baselines (Whoop vs Garmin), calibrated G/A/R thresholds, and metric correlations |
| `wellness-trends` | cli | `src/biosystems/cli.py:1381` | Monthly RHR and VO2max longitudinal trends with trend label and per-month means |
| `biosystems package` | library_export | `src/biosystems/__init__.py:35` | Top-level exports: models module, __version__='1.0.0'; __all__=['models', '__version__'] |
| `biosystems.ingestion` | library_export | `src/biosystems/ingestion/__init__.py:12` | Exports parse_gpx, parse_fit, add_derived_metrics; __all__ defined |
| `biosystems.physics` | library_export | `src/biosystems/physics/__init__.py:14` | Exports run_metrics, calculate_efficiency_factor, calculate_decoupling, calculate_hr_tss, compute_training_zones, lower_z2_bpm, and all GAP functions; __all__ defined |
| `biosystems.signal` | library_export | `src/biosystems/signal/__init__.py:13` | Exports walk_block_segments, summarize_walk_segments, filter_gps_jitter; __all__ defined |
| `biosystems.environment` | library_export | `src/biosystems/environment/__init__.py:13` | Exports WeatherCache, fetch_weather_open_meteo, get_weather_description; __all__ defined |
| `biosystems.wellness` | library_export | `src/biosystems/wellness/__init__.py:1` | Package marker with docstring only; no __all__; submodules (cache, analytics, habitdash) imported directly by callers |
| `tools/ingest_new_runs.py` | script | `tools/ingest_new_runs.py:1` | Batch ingest: scans data/raw/ for unprocessed .gpx/.fit, runs full pipeline, writes _gpx_full.csv/_gpx_summary.csv, regenerates real_weekly_data.json |
| `tools/sanitize_gps.py` | script | `tools/sanitize_gps.py:1` | Privacy tool to strip lat/lon and truncate start/end from activity DataFrames before publication |
| `tools/strava_auth.py` | script | `tools/strava_auth.py:1` | One-time Strava OAuth2 helper: opens browser for authorization, prints refresh token for .env |
| `tools/verify_installation.py` | script | `tools/verify_installation.py:1` | Installation sanity check: attempts import of all core biosystems modules and reports pass/fail |
| `tools/reproduce_study_analysis.py` | script | `tools/reproduce_study_analysis.py:1` | Reproducibility check: re-runs study pipeline over committed processed CSVs and compares to real_weekly_data.json (±5% EF tolerance) |
| `tools/generate_charts_real_only.py` | script | `tools/generate_charts_real_only.py:1` | Generate matplotlib charts from data/real_weekly_data.json only; refuses interpolation/fabrication |
| `tools/generate_readme_charts.py` | script | `tools/generate_readme_charts.py:1` | Generate publication-quality charts for embedding in README.md |
| `tools/generate_from_real_data.py` | script | `tools/generate_from_real_data.py:1` | Generate charts from hardcoded historical weekly data (W17-W20 real; W21-W33 partially estimated) |
| `tools/generate_sample_data.py` | script | `tools/generate_sample_data.py:1` | Generate synthetic but realistic GPS/HR/cadence CSV sample data for demos and tests |
| `daily_running_brief/daily_running_brief.py` | script | `daily_running_brief/daily_running_brief.py:1` | Post-run LLM synthesis pipeline: calls biosystems strava CLI, pre-computes stats, drives OpenAI (primary) / Anthropic (fallback) to write a narrative brief to ~/.openclaw/workspace/memory/intelligence/ |
| `audit/forensic-audit.mjs` | main | `audit/forensic-audit.mjs:1` | Node.js headless orchestrator for five-stage forensic audit: spawns claude -p workers, validates JSON schema output, commits and pushes per stage; supports --fresh, --stage N, --no-push flags |
| `.github/workflows/test.yml` | script | `.github/workflows/test.yml:1` | CI: ruff lint, mypy type check (non-blocking), pytest on Python 3.10/3.11/3.12 matrix; uploads htmlcov artifact on 3.11 |
| `.github/workflows/readme-validation.yml` | script | `.github/workflows/readme-validation.yml:1` | CI: validates README code examples via test_readme_examples.py on push/PR to main/develop |
| `.github/workflows/installation-test.yml` | script | `.github/workflows/installation-test.yml:1` | CI: tests pip install (3.10/3.11/3.12) and Docker build/test on changes to pyproject.toml, Dockerfile, requirements.txt |

## File inventory by role

### asset (6)
- `data/real_weekly_data.json`
- `data/sample/sample_run.csv`
- `data/sample/weekly_metrics.csv`
- `data/subjective.csv`
- `docs/images/aerobic_decoupling.png`
- `docs/images/ef_progression.png`

### config (17)
- `.aiv.yml`
- `.aiv/change.json`
- `.claude/settings.local.json`
- `.env.example`
- `.github/aiv-evidence/.gitkeep`
- `.github/aiv-packets/.gitkeep`
- `.github/workflows/installation-test.yml`
- `.github/workflows/readme-validation.yml`
- `.github/workflows/test.yml`
- `.gitignore`
- `Dockerfile`
- `audit/.gitignore`
- `daily_running_brief/requirements.txt`
- `data/raw/.gitkeep`
- `data/zones_personal.yml`
- `pyproject.toml`
- `requirements.txt`

### dead (1)
- `tools/generate_sample_data.py.OLD`

### doc (100)
- `.github/aiv-evidence/EVIDENCE_.ENV.EXAMPLE.md`
- `.github/aiv-evidence/EVIDENCE_.GITHUB_WORKFLOWS_TEST.YML.md`
- `.github/aiv-evidence/EVIDENCE_.GITIGNORE.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_ANALYTICS_HISTORY.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_ANALYTICS_TRENDING.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_CLI.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_ENVIRONMENT_WEATHER.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_INGESTION_FIT.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_INGESTION_GPX.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_INGESTION_STRAVA.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_MODELS.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_PHYSICS_GAP.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_PHYSICS_METRICS.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_SIGNAL_WALK_DETECTION.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_WELLNESS_ANALYTICS.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_WELLNESS_CACHE.md`
- `.github/aiv-evidence/EVIDENCE_BIOSYSTEMS_WELLNESS___INIT__.md`
- `.github/aiv-evidence/EVIDENCE_CHANGELOG.MD.md`
- `.github/aiv-evidence/EVIDENCE_CITATION.CFF.md`
- `.github/aiv-evidence/EVIDENCE_CLAUDE.MD.md`
- `.github/aiv-evidence/EVIDENCE_DAILY_RUNNING_BRIEF_DAILY_RUNNING_BRIEF.md`
- `.github/aiv-evidence/EVIDENCE_DAILY_RUNNING_BRIEF_README.MD.md`
- `.github/aiv-evidence/EVIDENCE_DATA_REAL_WEEKLY_DATA.JSON.md`
- `.github/aiv-evidence/EVIDENCE_DATA_SAMPLE_README.MD.md`
- `.github/aiv-evidence/EVIDENCE_DOCS_PUBLICATION_CHECKLIST.MD.md`
- `.github/aiv-evidence/EVIDENCE_DOCS_WELLNESS.MD.md`
- `.github/aiv-evidence/EVIDENCE_PYPROJECT.TOML.md`
- `.github/aiv-evidence/EVIDENCE_README.MD.md`
- `.github/aiv-evidence/EVIDENCE_REPORTS_01_LONGITUDINAL_STUDY.MD.md`
- `.github/aiv-evidence/EVIDENCE_REQUIREMENTS.TXT.md`
- `.github/aiv-evidence/EVIDENCE_SCRIPTS_NIGHTLY_TRAINING_BRIEF.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_CLI_INTEGRATION.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_ENVIRONMENT.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_INGESTION_FIT.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_INGESTION_GPX.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_MODELS.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_PHYSICS_GAP.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_PHYSICS_METRICS.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_README_EXAMPLES.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_SANITIZE_GPS_FIX.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_SIGNAL.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_TRENDING.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_WALK_CLASSIFICATION.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_WALK_DETECTION_FIX.md`
- `.github/aiv-evidence/EVIDENCE_TESTS_TEST_WELLNESS_CACHE.md`
- `.github/aiv-evidence/EVIDENCE_TOOLS_INGEST_NEW_RUNS.md`
- `.github/aiv-evidence/EVIDENCE_TOOLS_SANITIZE_GPS.md`
- `.github/aiv-packets/PACKET_advanced_analytics.md`
- `.github/aiv-packets/PACKET_advanced_analytics_v2.md`
- `.github/aiv-packets/PACKET_advanced_wellness.md`
- `.github/aiv-packets/PACKET_briefing_pipeline_v2.md`
- `.github/aiv-packets/PACKET_briefing_pipeline_v3.md`
- `.github/aiv-packets/PACKET_ci_and_test_improvements.md`
- `.github/aiv-packets/PACKET_ci_ruff_nonblocking.md`
- `.github/aiv-packets/PACKET_cli_enterprise_polish.md`
- `.github/aiv-packets/PACKET_cli_expansion.md`
- `.github/aiv-packets/PACKET_coderabbit_review_fixes.md`
- `.github/aiv-packets/PACKET_doc_accuracy_fixes.md`
- `.github/aiv-packets/PACKET_docstring_whitespace_fixes.md`
- `.github/aiv-packets/PACKET_final_paper_completeness.md`
- `.github/aiv-packets/PACKET_final_polishing.md`
- `.github/aiv-packets/PACKET_fix_all_ruff_errors.md`
- `.github/aiv-packets/PACKET_ingest_tool_verification.md`
- `.github/aiv-packets/PACKET_nan_assert_compat.md`
- `.github/aiv-packets/PACKET_openclaw_integration.md`
- `.github/aiv-packets/PACKET_operational_tools.md`
- `.github/aiv-packets/PACKET_pandas_compat.md`
- `.github/aiv-packets/PACKET_paper_review_fixes.md`
- `.github/aiv-packets/PACKET_physics_elevation_hardening.md`
- `.github/aiv-packets/PACKET_physics_hardening.md`
- `.github/aiv-packets/PACKET_pre_study_trajectory.md`
- `.github/aiv-packets/PACKET_quality_hardening.md`
- `.github/aiv-packets/PACKET_system_hardening.md`
- `.github/aiv-packets/PACKET_systematic_fixes.md`
- `.github/aiv-packets/PACKET_training_deep_dive_and_ops_docs.md`
- `.github/aiv-packets/PACKET_walk_detection_and_cadence_fixes.md`
- `.github/aiv-packets/PACKET_wellness_dual_signal.md`
- `.github/aiv-packets/PACKET_wellness_integration.md`
- `CHANGELOG.md`
- `CITATION.cff`
- `CLAUDE.md`
- `LICENSE`
- `README.md`
- `audits/META_AUDIT_DEC_18.md`
- `audits/QUALITY_AUDIT.md`
- `daily_running_brief/README.md`
- `data/sample/README.md`
- `docs/DATA_PREPARATION.md`
- `docs/PUBLICATION_CHECKLIST.md`
- `docs/WELLNESS.md`
- `docs/internal/CLEANUP_SUMMARY.md`
- `docs/internal/DEVELOPMENT_ARCHIVE.md`
- `docs/internal/FEEDBACK_ANALYSIS.md`
- `docs/internal/INFRASTRUCTURE_FIX_COMPLETE.md`
- `docs/internal/README.md`
- `docs/internal/README_ADDITIONAL_FAILURES.md`
- `docs/internal/README_FIX_COMPLETE.md`
- `docs/internal/README_VERIFICATION_FAILURES.md`
- `docs/internal/REPOSITORY_CLEANUP.md`
- `reports/01_longitudinal_study.md`

### source (33)
- `audit/forensic-audit.mjs`
- `daily_running_brief/daily_running_brief.py`
- `src/biosystems/__init__.py`
- `src/biosystems/analytics/__init__.py`
- `src/biosystems/analytics/history.py`
- `src/biosystems/analytics/trending.py`
- `src/biosystems/cli.py`
- `src/biosystems/environment/__init__.py`
- `src/biosystems/environment/weather.py`
- `src/biosystems/ingestion/__init__.py`
- `src/biosystems/ingestion/fit.py`
- `src/biosystems/ingestion/gpx.py`
- `src/biosystems/ingestion/strava.py`
- `src/biosystems/models.py`
- `src/biosystems/physics/__init__.py`
- `src/biosystems/physics/gap.py`
- `src/biosystems/physics/metrics.py`
- `src/biosystems/physics/report.py`
- `src/biosystems/signal/__init__.py`
- `src/biosystems/signal/walk_detection.py`
- `src/biosystems/wellness/__init__.py`
- `src/biosystems/wellness/analytics.py`
- `src/biosystems/wellness/cache.py`
- `src/biosystems/wellness/habitdash.py`
- `tools/generate_charts_real_only.py`
- `tools/generate_from_real_data.py`
- `tools/generate_readme_charts.py`
- `tools/generate_sample_data.py`
- `tools/ingest_new_runs.py`
- `tools/reproduce_study_analysis.py`
- `tools/sanitize_gps.py`
- `tools/strava_auth.py`
- `tools/verify_installation.py`

### test (17)
- `tests/__init__.py`
- `tests/test_cli_integration.py`
- `tests/test_environment.py`
- `tests/test_history.py`
- `tests/test_ingestion_fit.py`
- `tests/test_ingestion_gpx.py`
- `tests/test_models.py`
- `tests/test_physics_gap.py`
- `tests/test_physics_metrics.py`
- `tests/test_readme_examples.py`
- `tests/test_sanitize_gps_fix.py`
- `tests/test_signal.py`
- `tests/test_strava.py`
- `tests/test_trending.py`
- `tests/test_walk_classification.py`
- `tests/test_walk_detection_fix.py`
- `tests/test_wellness_cache.py`


_Generated 2026-06-17T14:19:44.969Z · branch claude/epic-goldberg-hebvrp_
