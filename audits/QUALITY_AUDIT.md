# Bio-Systems Engineering Quality & Integrity Audit

**Auditor:** `Cascade`
**Date Started:** `2025-12-18`
**Repository:** `bio-systems-engineering`
**Scope:** Full codebase, documentation, and scientific logic verification.

This document serves as the master checklist for auditing the `bio-systems-engineering` library. Given the project's nature (scientific N=1 study, performance optimization), this audit prioritizes **mathematical correctness**, **privacy safety**, and **reproducibility** over standard stylistic concerns.

---

## Audit Findings Log

*Use this table to log specific issues found during the audit process.*

| Component | Category | Finding / Observation | Severity | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `README.md` | Reproducibility | (Example) Quick Start code fails on fresh install due to missing `dt` column in sample data (fixed in recent patch). | High | Ensure CI pipeline runs README examples exactly as written. |
| `physics/gap.py` | Logic | (Hypothetical) Minetti equation returns negative cost for extreme downhill grades. | Medium | Clamp energy cost output to a minimum realistic floor (e.g., 0.5). |
| `sanitize_gps.py` | Privacy | Does the tool strip timestamps or just shift them? Absolute time can leak location via sun position analysis. | Low | Verify absolute timestamps are shifted to relative time `0.0`. |
| `ingestion/gpx.py` | Robustness | Namespaced parsing is hardcoded to GPX 1.1 (`http://www.topografix.com/GPX/1/1`). The fallback (`.//trkpt`) only works for fully un-namespaced GPX; it will not match GPX 1.0 / alternate namespace URIs, potentially yielding a misleading `No <trkpt>` error. | High | Make trackpoint search namespace-agnostic (e.g., match element local-name `trkpt`) or dynamically detect the namespace from `root.tag`. |
| `ingestion/gpx.py` | Error Handling | Timestamp is treated as required, but code calls `pt.find(...).text` without a `None` check; missing `<time>` will raise `AttributeError` instead of a clear `ValueError`. | Medium | Validate required fields (`time`, `lat`, `lon`) explicitly and raise an informative error with trackpoint index/context. |
| `ingestion/gpx.py` | Data Quality | `dt` is computed as raw diff and used directly for speed; large gaps (paused watch / auto-pause / tunnel GPS dropout) are not handled and can skew `speed_mps`, `pace_sec_km`, and downstream metrics. | Medium | Detect and handle large time gaps (clip, drop, or segment). Consider making the threshold configurable. |
| `tests/test_ingestion_gpx.py` | Testing | Coverage is focused on a minimal GPX 1.1 happy path + missing HR. It does not test alternate GPX namespaces (1.0), missing `<time>`, large `dt` gaps, cadence/power extraction variants, or multi-segment tracks. | Low | Add targeted regression tests for namespace variation + gap handling + extension variants. |
| `ingestion/fit.py` | Correctness | Semicircles→degrees conversion formula is correct, but there is no runtime validation that values land in plausible ranges (lat ∈ [-90, 90], lon ∈ [-180, 180]). If an upstream library ever returns already-converted degrees, the current code would silently “double convert” and yield near-zero coordinates. | Medium | Add sanity checks for coordinate ranges and fail loudly (or skip conversion) if coordinates appear already in degrees. |
| `ingestion/fit.py` | Consistency | FIT timestamps are converted via `pd.to_datetime(df['timestamp'])` without forcing `utc=True`, while GPX parsing uses `utc=True`. This can yield a mixture of tz-aware vs tz-naive timestamps across ingestion paths. | Medium | Standardize to timezone-aware UTC for all ingested timestamps (either in ingestion or a normalization layer). |
| `ingestion/fit.py` | Data Model | FIT schema differs from GPX schema (`latitude/longitude` vs `lat/lon`, index named `timestamp` vs column `time`). This increases risk of downstream functions silently expecting one schema. | Medium | Provide a single canonical schema (or a normalization helper) used by all downstream metrics/signal pipelines. |
| `ingestion/fit.py` | Robustness | `parse_fit()` only consumes `record` messages. FIT files can contain sensor streams at different frequencies and/or missing GPS fields on some records; the parser does not align/resample streams, and `add_derived_metrics()` will fail if lat/lon are missing. | Low | Document assumptions clearly and/or implement optional alignment/resampling (e.g., forward-fill GPS within a tolerance, or drop records without GPS for distance/pace computation). |
| `tests/` | Testing | No dedicated tests exist for FIT parsing or for `add_derived_metrics()`. | Low | Add unit tests with a small fixture FIT file (or a mocked `fitdecode.FitReader`) covering coordinate conversion, missing fields, and derived metrics. |
| `physics/metrics.py` | Correctness | EF/decoupling computations do not guard against `secs == 0`, `avg_hr == 0`, or all-NaN HR (sensor dropout). This can yield `inf`/`NaN` silently and propagate into `PhysiologicalMetrics`. | High | Validate inputs early (required columns, positive `dt`, non-empty non-NaN HR) and handle divide-by-zero explicitly (raise or return `NaN` + warning). |
| `physics/metrics.py` | Logic | Run-only filter uses `df['hr'] >= lz2` and a row-count heuristic (`len(work_df) < 120`) that assumes ~1 Hz sampling. HR spikes during walking/rest could be incorrectly included, and variable sampling rates make the “2 minutes” logic inaccurate. | Medium | Use duration-based thresholds (`work_df['dt'].sum()`) and consider combining HR threshold with pace/cadence constraints to reduce false “work” segments. |
| `physics/metrics.py` | Logic | Decoupling split is described as “time-based” but implemented as midpoint of the DataFrame index. With GPX ingestion the index is an integer RangeIndex (not timestamps), so the split is sample-count-based, not time-based. | Medium | Split using cumulative elapsed time (e.g., `df['dt'].cumsum()`) or require a datetime index and validate it. |
| `physics/metrics.py` | Robustness | `compute_training_zones()` uses `np.isnan()` inside `apply()`. If HR/pace contain `None` (object dtype), `np.isnan(None)` raises, and zone classification can crash. | Low | Coerce to numeric (`pd.to_numeric(..., errors='coerce')`) before classification or guard `None` explicitly. |
 | `physics/metrics.py` | API/Side Effects | `run_metrics()` mutates the input DataFrame by adding `zone_*` columns, which can surprise callers and complicate reuse. | Low | Either document the mutation clearly or operate on a copy (or return zone columns separately). |
 | `physics/gap.py` | Data Quality | Grade is computed from raw point-to-point elevation diffs without smoothing; elevation noise can produce extreme grades and unstable GAP values. | Medium | Smooth elevation (and/or grade) over a window before applying Minetti, and consider capping grade to a plausible range (e.g., [-20%, 20%]). |
 | `physics/gap.py` | Numerical Stability | Minetti polynomial can yield non-physical values (including negative energy cost) at extreme grades; `calculate_gap_segment()` divides by `energy_multiplier` without clamping. | Low | Clamp `energy_multiplier` to a small positive minimum and optionally clamp grade to a reasonable domain. |
 | `physics/metrics.py` | Observability | GAP calculation errors are swallowed (`except Exception: pass`), making failures non-diagnosable during analysis. | Low | Catch narrower exceptions and/or surface a warning/debug signal when GAP calculation fails. |
 | `signal/walk_detection.py` | Correctness | `filter_gps_jitter()` uses `pace >= 8.7` (min/km). This keeps slow-pace points and will not remove slow+low-cadence jitter; it likely fails `tests/test_signal.py::TestFilterGPSJitter::test_removes_slow_low_cadence`. | High | Align the filter predicate with intended semantics (drop slow pace + low cadence), and make the pace threshold configurable.
 | `signal/walk_detection.py` | Integration | `walk_block_segments()` assumes a datetime index and columns `pace_min_per_km`, `distance_cumulative_km`, and `heart_rate`. Ingestion outputs (`parse_gpx`) provide `time` (as a column), `pace_sec_km`, `dist`, and `hr`, so end-to-end integration is currently brittle (segments may be empty/NaN or skipped). | Medium | Define a canonical activity schema or implement an explicit normalization layer; accept common aliases (`hr` vs `heart_rate`) and compute distance from `dist` when cumulative distance is missing.
 | `signal/walk_detection.py` | Configurability | Several thresholds are hardcoded (pace 8.7, warm-up < 60s, cool-down last < 120s). | Low | Make thresholds parameters (or part of a config object) to support different athletes/sessions.
 | `signal/walk_detection.py` | Observability | Unconditional `print()` in the sanity check leaks debug output in library usage. | Low | Replace with a logger and a verbosity flag, or remove.
 | `signal/walk_detection.py` | Maintainability | `WalkSegment` is imported but not used; API returns `List[dict]` with mixed types (numbers and empty strings). | Low | Return structured `WalkSegment` objects (or a consistent typed dict) and remove unused imports.
 | `tools/sanitize_gps.py` | Privacy | Truncation logic fails for short runs: if `total_distance < truncate_start_m + truncate_end_m`, the mask yields an empty DataFrame and later `iloc[-1]`/`.min()` calls can raise. | High | Add guardrails: if total distance is too short, reduce truncation amounts proportionally or skip truncation with a clear warning.
 | `tools/sanitize_gps.py` | Privacy | Absolute timestamps are not scrubbed/normalized. The tool resets the DataFrame index but does not remove/shift `time`/`timestamp` columns if present. | Medium | Drop absolute time columns or normalize to a relative elapsed time column (e.g., `t_s` from 0) in the sanitized output.
 | `tools/sanitize_gps.py` | Correctness | The printed “Removed %” calculation appears incorrect due to missing parentheses in the f-string arithmetic. | Low | Compute `pct_removed = (len(df) - len(df_truncated)) / len(df) * 100` and print that value.
 | `.gitignore` | Privacy | Repository ignores raw GPS and device files (`data/raw/**`, `*.fit`, `*.gpx`). This is a strong default protection against accidental commits. | Low | Keep as-is; consider also ignoring `*.tcx` if you ever export TCX.
 | `data/sample/sample_run.csv` | Privacy | Sample data contains `lat`/`lon` columns but values appear synthetic (lat is 0.0; lon is very small around 0). This matches the stated privacy note. | Low | Keep synthetic coordinates, but ensure documentation makes it explicit that `lat`/`lon` are not real-world locations.
 | `requirements.txt` | Reproducibility | `requirements.txt` and `pyproject.toml` duplicate dependency declarations and appear inconsistent. `ruff>=0.0.2860` is likely a non-existent version, and Docker builds install from `requirements.txt`, risking a broken container build. | High | Pick a single source of truth (prefer `pyproject.toml` + a compiled lock/constraints file) and fix the ruff pin.
 | `pyproject.toml` | Reproducibility | Runtime deps are unbounded above (`numpy`, `pandas`, `pydantic`). `requirements.txt` has upper bounds, but `pip install -e ".[dev]"` uses `pyproject.toml` and could break on major upgrades. | Medium | Add upper bounds and/or adopt a lockfile/constraints strategy for reproducible installs.
 | `environment/weather.py` | Correctness | `WeatherCache.set()` no-ops when `cache_path` is `None`, but tests treat `WeatherCache(None)` as an in-memory cache. This indicates code/tests are out of sync. | High | Decide on intended behavior (support in-memory caching or require a path) and align both implementation + tests.
 | `environment/weather.py` | Robustness | `fetch_weather_open_meteo()` can attempt ~891 HTTP requests per retry attempt (lat/lon/time variations) and uses the forecast endpoint for historical datetimes. This is likely slow/fragile and may not work as intended outside of mocked tests. | Medium | Reduce search space, use the proper historical endpoint for past dates, and replace `print()` with structured logging.
 | `tests/test_models.py` | Testing | Test suite expectations do not match `models.py` (e.g., reversed zone bounds, wrong `ActivitySummary` fields, wrong `WalkSegment` fields). This likely makes tests fail and undermines the “data contracts” guarantee. | High | Update tests to match the models (or revert models to match the tests), treating the public API contract as authoritative.
 | `tools/generate_from_real_data.py` | Scientific Integrity | Script explicitly interpolates/perturbs unmeasured weeks (“for now, interpolating based on phases”). Ensure anything generated from it is clearly labeled synthetic and not conflated with `data/real_weekly_data.json`. | Medium | Use one authoritative data source per artifact and clearly label synthetic vs. measured datasets.
 | `environment/weather.py` | Reproducibility | `WeatherCache` uses `pd.read_parquet`/`to_parquet`, but the project does not declare a Parquet engine dependency (`pyarrow` or `fastparquet`). Full test runs (and runtime caching) can fail with an ImportError on fresh installs. | High | Add `pyarrow` (recommended) or `fastparquet` as an optional dependency (e.g., `.[weather]`) and include it in `dev` if tests require Parquet.
 | `.github/workflows/*` | Testing | CI currently validates installation and README examples, but does not run the full unit test suite (e.g., `tests/test_environment.py`, `tests/test_models.py`, `tests/test_signal.py`). Regressions in non-README paths can ship unnoticed. | Medium | Add a CI job that runs `pytest` (full suite) on at least one Python version, and keep README validation as a separate fast signal.
 | `tools/generate_sample_data.py` | Maintainability | File is empty, which can confuse contributors and suggests a partially removed feature. | Low | Remove it or implement it; if keeping, ensure README/docs do not reference it.
 | `tools/generate_sample_data.py.OLD` | Maintainability | Archived script contains stale API references (e.g., `ZoneConfiguration` instead of `ZoneConfig`) and embedded sample README text that no longer matches the current public API. If reused, it would generate misleading docs/data. | Low | If you keep an archived version, clearly label it as historical-only and ensure it cannot be mistaken for a supported generator; otherwise delete it.

---

## Systematic Audit Checklist

### I. Core Physics & Physiological Logic (`src/biosystems/physics/`)

*The engine room. If the math is wrong, the study is invalid.*

 - [x] **Metrics Calculation (`metrics.py`)**
    -   **Run-Only Filter:** Verify the logic `df['hr'] >= lz2`. Does it correctly handle signal noise (e.g., HR spikes during a walk)? Does it discard too much data if the user has cardiac drift?
    -   **Efficiency Factor (EF):** Verify the formula `speed / hr`. Is speed in m/s or km/h? Is HR correctly normalized?
    -   **Decoupling:** Check the split logic (first half vs. second half). Is it time-based or distance-based? (Time-based is standard for this metric).
    -   **Edge Cases:** How does it handle `div by zero` if HR drops to 0 (sensor dropout)?
 - [x] **Grade Adjusted Pace (`gap.py`)**
    -   **Minetti Implementation:** Compare code constants against the 2002 Minetti et al. paper. Are the polynomial coefficients exact?
    -   **Grade Calculation:** Verify `calculate_grade_percent`. Does it handle noisy elevation data (smoothing) before calculating grade?
    -   **Integration:** Is GAP correctly integrated into the main `run_metrics` or is it an isolated function?

### II. Data Ingestion & Parsing (`src/biosystems/ingestion/`)

*The entry point. Garbage in, garbage out.*

- [x] **GPX Parsing (`gpx.py`)**
    -   **Namespace Handling:** Does it robustly handle different GPX versions (Strava export vs. Garmin native)?
    -   **Extensions:** Verify extraction of `hr`, `cad`, and `power` from `TrackPointExtension`. Does it fail gracefully if extensions are missing?
    -   **Derived Metrics:** Check `dt` (delta time) calculation. Is it robust against paused watches (large time gaps)?
- [x] **FIT Parsing (`fit.py`)**
    -   **Coordinate Conversion:** Verify `semicircles` to `degrees` conversion logic.
    -   **Stream Alignment:** Do GPS points align 1:1 with Heart Rate points? FIT files sometimes record these at different frequencies.

### III. Signal Processing & Classification (`src/biosystems/signal/`)

 - [x] **Walk Detection (`walk_detection.py`)**
    -   **Thresholds:** Are the hardcoded thresholds (e.g., `cad_thr=128`, `pace >= 8.7`) configurable via `RunContext` or hardcoded?
    -   **Jitter Filtering:** Does `filter_gps_jitter` effectively distinguish between "standing still with GPS drift" and "walking slowly"?
    -   **Segmentation:** verify `walk_block_segments` correctly bridges small gaps vs. creating new segments.

### IV. Privacy & Security (`tools/` & `data/`)

*Critical for public release. Zero tolerance for leaks.*

 - [x] **Sanitization Tool (`sanitize_gps.py`)**
    -   **Coordinate Removal:** Verify that `lat`/`lon` columns are physically dropped from the DataFrame, not just hidden.
    -   **Truncation:** Test the 500m start/end truncation. Does it work if the total run is < 1km?
    -   **Metadata:** Does the tool scrub device serial numbers or user IDs from FIT file headers if metadata is passed through?
 - [x] **Repository Hygiene**
     -   **Git History:** Checked git history for tracked `*.gpx` / `*.fit` / `*.tcx` files — none found.
     -   **Config:** `.gitignore` excludes `*.fit`, `*.gpx`, and `data/raw/**` — Verified.
 - [x] **Sample Data**
    -   **Consistency:** Does `sample_run.csv` contain all columns required by `models.py` (e.g., `dt`, `pace_sec_km`)?
    -   **Privacy:** Verify synthetic coordinates are used and not real-world locations.

### V. Reproducibility & Environment

- [x] **Installation**
    -   **Fresh Install:** Create a clean virtualenv. Run `pip install -e .`. Do imports work immediately? — Executed: PASS
    -   **Dependencies:** Check `pyproject.toml`. Are versions pinned loosely (risk of breaking changes) or strictly? — Audited (see findings log for dependency strategy issues)
 - [ ] **Docker**
     -   **Build:** Does `docker build .` succeed without requiring files that are `.dockerignore`d?
     -   **Run:** Can the Docker container run the tests?
     -   **Local status:** Attempted locally but could not run (Docker daemon not running; `docker-buildx` plugin missing).

### VI. Documentation & Claims

- [x] **Readme Accuracy**
    -   **Code Examples:** Copy-paste the Quick Start code into a fresh script. Does it run without modification?
    -   **Claims vs. Code:** The README claims "Heat Adjustment" is a limitation. Verify no code attempts to normalize pace by temperature (ensuring claim is accurate).
- [x] **Scientific Reporting**
    -   **Visualizations:** Are the charts in `docs/images` generated by the scripts in `tools/`, or were they manually created? (Prefer reproducible charts).
    -   **Terminology:** Are terms like "Efficiency Factor" used consistently with Friel/TrainingPeaks definitions?

### VII. Code Quality & Testing (`tests/`)

- [x] **Test Coverage**
    -   **Edge Cases:** Do tests cover empty DataFrames, single-point tracks, or runs with 0 distance?
    -   **Mocking:** Is the Open-Meteo API mocked in tests to prevent network dependency during CI?
- [x] **Pydantic Models (`models.py`)**
    -   **Validation:** Do models strictly enforce types (e.g., preventing negative distance or HR > 250)?
    -   **Serialization:** Can `PhysiologicalMetrics` be serialized to JSON/dict and back without data loss?

### VIII. Prioritized Remediation Backlog

- **P0 (Must-fix before trusting results)**
    -   Align `tests/test_models.py` with `src/biosystems/models.py` (or revert models to match tests). Right now the “data contract” guarantee is undermined by mismatched expectations.
    -   Fix `tools/sanitize_gps.py` short-run truncation crash risk.
    -   Consolidate dependency management (`pyproject.toml` vs `requirements.txt`) and fix the invalid `ruff` pin to prevent broken installs and Docker builds.

- **P1 (Reliability + reproducibility)**
    -   Add a Parquet engine dependency strategy for `WeatherCache` (`pyarrow`/`fastparquet`), and decide whether caching supports in-memory mode (`WeatherCache(None)`).
    -   Add a CI job running the full `pytest` suite (keep README validation as a separate, fast job).
    -   Reduce the request explosion in `fetch_weather_open_meteo()` and use the appropriate Open-Meteo endpoint for historical dates.

- **P2 (Maintainability / cleanup)**
    -   Remove or restore `tools/generate_sample_data.py` (empty file) and clarify the status of `generate_sample_data.py.OLD`.
    -   Replace library `print()` statements with structured logging.

### IX. Remaining Verification (Executed vs Pending)

- **Fresh install smoke test** (`pip install -e .` + basic imports) — Executed: PASS
- **Full test run** (`pytest`) — Executed: **11 failed**, **93 passed**
    - Failed: `tests/test_environment.py` (3)
    - Failed: `tests/test_models.py` (5)
    - Failed: `tests/test_physics_gap.py::TestCalculateGAPFromDataFrame::test_flat_dataframe`
    - Failed: `tests/test_signal.py` (2)
- **Docker build + test run** (`docker build .` then `docker run … pytest`) — Attempted: FAIL (Docker daemon not running; `docker-buildx` plugin missing)
- **Installation verification script** (`python tools/verify_installation.py`) — Executed: PASS