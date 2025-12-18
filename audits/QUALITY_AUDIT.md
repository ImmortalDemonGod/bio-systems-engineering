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

---

## Systematic Audit Checklist

### I. Core Physics & Physiological Logic (`src/biosystems/physics/`)

*The engine room. If the math is wrong, the study is invalid.*

- [ ] **Metrics Calculation (`metrics.py`)**
    -   **Run-Only Filter:** Verify the logic `df['hr'] >= lz2`. Does it correctly handle signal noise (e.g., HR spikes during a walk)? Does it discard too much data if the user has cardiac drift?
    -   **Efficiency Factor (EF):** Verify the formula `speed / hr`. Is speed in m/s or km/h? Is HR correctly normalized?
    -   **Decoupling:** Check the split logic (first half vs. second half). Is it time-based or distance-based? (Time-based is standard for this metric).
    -   **Edge Cases:** How does it handle `div by zero` if HR drops to 0 (sensor dropout)?
- [ ] **Grade Adjusted Pace (`gap.py`)**
    -   **Minetti Implementation:** Compare code constants against the 2002 Minetti et al. paper. Are the polynomial coefficients exact?
    -   **Grade Calculation:** Verify `calculate_grade_percent`. Does it handle noisy elevation data (smoothing) before calculating grade?
    -   **Integration:** Is GAP correctly integrated into the main `run_metrics` or is it an isolated function?

### II. Data Ingestion & Parsing (`src/biosystems/ingestion/`)

*The entry point. Garbage in, garbage out.*

- [x] **GPX Parsing (`gpx.py`)**
    -   **Namespace Handling:** Does it robustly handle different GPX versions (Strava export vs. Garmin native)?
    -   **Extensions:** Verify extraction of `hr`, `cad`, and `power` from `TrackPointExtension`. Does it fail gracefully if extensions are missing?
    -   **Derived Metrics:** Check `dt` (delta time) calculation. Is it robust against paused watches (large time gaps)?
- [ ] **FIT Parsing (`fit.py`)**
    -   **Coordinate Conversion:** Verify `semicircles` to `degrees` conversion logic.
    -   **Stream Alignment:** Do GPS points align 1:1 with Heart Rate points? FIT files sometimes record these at different frequencies.

### III. Signal Processing & Classification (`src/biosystems/signal/`)

- [ ] **Walk Detection (`walk_detection.py`)**
    -   **Thresholds:** Are the hardcoded thresholds (e.g., `cad_thr=128`, `pace >= 8.7`) configurable via `RunContext` or hardcoded?
    -   **Jitter Filtering:** Does `filter_gps_jitter` effectively distinguish between "standing still with GPS drift" and "walking slowly"?
    -   **Segmentation:** verify `walk_block_segments` correctly bridges small gaps vs. creating new segments.

### IV. Privacy & Security (`tools/` & `data/`)

*Critical for public release. Zero tolerance for leaks.*

- [ ] **Sanitization Tool (`sanitize_gps.py`)**
    -   **Coordinate Removal:** Verify that `lat`/`lon` columns are physically dropped from the DataFrame, not just hidden.
    -   **Truncation:** Test the 500m start/end truncation. Does it work if the total run is < 1km?
    -   **Metadata:** Does the tool scrub device serial numbers or user IDs from FIT file headers if metadata is passed through?
- [ ] **Repository Hygiene**
    -   **Git History:** Run `git log -S "lat"` or use BFG Repo-Cleaner to ensure no GPX files were accidentally committed in the past.
    -   **Config:** Ensure `.gitignore` explicitly excludes `*.fit`, `*.gpx`, and `data/raw/*`.

### V. Reproducibility & Environment

- [ ] **Installation**
    -   **Fresh Install:** Create a clean virtualenv. Run `pip install -e .`. Do imports work immediately?
    -   **Dependencies:** Check `pyproject.toml`. Are versions pinned loosely (risk of breaking changes) or strictly?
- [ ] **Docker**
    -   **Build:** Does `docker build .` succeed without requiring files that are `.dockerignore`d?
    -   **Run:** Can the Docker container run the tests?
- [ ] **Sample Data**
    -   **Consistency:** Does `sample_run.csv` contain all columns required by `models.py` (e.g., `dt`, `pace_sec_km`)?

### VI. Documentation & Claims

- [ ] **Readme Accuracy**
    -   **Code Examples:** Copy-paste the Quick Start code into a fresh script. Does it run without modification?
    -   **Claims vs. Code:** The README claims "Heat Adjustment" is a limitation. Verify no code attempts to normalize pace by temperature (ensuring claim is accurate).
- [ ] **Scientific Reporting**
    -   **Visualizations:** Are the charts in `docs/images` generated by the scripts in `tools/`, or were they manually created? (Prefer reproducible charts).
    -   **Terminology:** Are terms like "Efficiency Factor" used consistently with Friel/TrainingPeaks definitions?

### VII. Code Quality & Testing (`tests/`)

- [ ] **Test Coverage**
    -   **Edge Cases:** Do tests cover empty DataFrames, single-point tracks, or runs with 0 distance?
    -   **Mocking:** Is the Open-Meteo API mocked in tests to prevent network dependency during CI?
- [ ] **Pydantic Models (`models.py`)**
    -   **Validation:** Do models strictly enforce types (e.g., preventing negative distance or HR > 250)?
    -   **Serialization:** Can `PhysiologicalMetrics` be serialized to JSON/dict and back without data loss?