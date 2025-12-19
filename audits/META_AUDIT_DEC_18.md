 # Meta Audit (Dec 18, 2025): Coverage Gaps in `QUALITY_AUDIT.md`
 
 **Purpose:** Produce a single, coverage-focused document that identifies which parts of the `bio-systems-engineering` repository were **not** covered (explicitly or implicitly) by `audits/QUALITY_AUDIT.md`.
 
 **Non-goals:**
 - This document does **not** re-audit the code.
 - This document does **not** restate findings already recorded in `QUALITY_AUDIT.md`.
 
 ---
 
 ## 1) How “Covered” Is Defined
 
 This meta-audit uses two tiers:
 
 - **Explicit coverage**
   The file/module is named in:
   - the `QUALITY_AUDIT.md` checklist, or
   - the `QUALITY_AUDIT.md` findings log.
 
 - **Implicit coverage**
   The file/module is not directly reviewed in `QUALITY_AUDIT.md`, but is indirectly exercised/validated via:
   - import smoke tests (`tools/verify_installation.py`),
   - README example tests (`tests/test_readme_examples.py`),
   - a full `pytest` execution.
 
 **Important:** If something was explored informally but not reflected in `QUALITY_AUDIT.md`, it is treated as **not covered** here (because future readers can’t rely on undocumented work).
 
 ---
 
 ## 2) Repository Inventory (What Exists)
 
 **Top-level files / folders present:**
 - `src/` (package code)
 - `tests/` (test suite)
 - `tools/` (utility scripts)
 - `docs/` (documentation)
 - `reports/` (study narrative)
 - `data/` (sample + study artifacts)
 - `.github/workflows/` (CI)
 - `pyproject.toml`, `requirements.txt`, `Dockerfile`, `.gitignore`
 - `CHANGELOG.md`, `CITATION.cff`, `LICENSE`
 
 **Deliberately excluded from meta-coverage:**
 - local/ephemeral artifacts: `.coverage`, `htmlcov/`, `.pytest_cache/`, `.DS_Store`, `__pycache__/`, `biosystems.egg-info/`
 
 ---
 
 ## 3) Coverage Map (Repo vs. `QUALITY_AUDIT.md`)
 
 **Covered explicitly (Quality Audit names it):**
 - `src/biosystems/ingestion/{gpx.py, fit.py}`
 - `src/biosystems/physics/{metrics.py, gap.py}`
 - `src/biosystems/signal/walk_detection.py`
 - `src/biosystems/environment/weather.py`
 - `src/biosystems/models.py`
 - `tools/sanitize_gps.py`
 - `tools/generate_from_real_data.py`
 - `tools/generate_sample_data.py` and `tools/generate_sample_data.py.OLD`
 - `README.md`
 - `pyproject.toml`, `requirements.txt`, `Dockerfile`
 - `.github/workflows/*`
 - `tests/*` (as a category)
 
 **Covered only implicitly (validated indirectly, but not audited as an artifact):**
 - Package API surface:
   - `src/biosystems/__init__.py`
   - `src/biosystems/*/__init__.py`
 - Verification tool:
   - `tools/verify_installation.py`
 - Chart generation tools:
   - `tools/generate_readme_charts.py`
   - `tools/generate_charts_real_only.py`
 
 ---
 
 ## 4) Uncovered / Under-Covered Areas (Primary Output)
 
 ### A) Documentation Outside `README.md` (Not Covered)
 
 Files not explicitly audited:
 - `docs/DATA_PREPARATION.md`
 - `docs/internal/*`
 
 **Risk:** Hidden assumptions about data schema, ETL steps, privacy posture, or reproducibility steps can drift from code.
 
 **Suggested checklist addition:** “Docs consistency audit” covering `docs/DATA_PREPARATION.md` and any externally referenced procedures.
 
 ### B) Study Report Traceability (Not Covered)
 
 Not explicitly audited:
 - `reports/01_longitudinal_study.md`
 
 **Risk:** Narrative claims may not be reproducible from committed code + committed data.
 
 **Suggested checklist addition:** “Report ↔ code/data traceability” (tie each headline number/chart to a script + committed dataset).
 
 ### C) Data Lineage / Provenance (Partially Covered)
 
 Covered:
 - `data/sample/sample_run.csv` privacy + column consistency (explicit)
 
 Not covered explicitly:
 - `data/real_weekly_data.json` provenance and generation procedure
 - `data/sample/weekly_metrics.csv` provenance (synthetic vs measured labeling; generator script)
 - `data/processed/` expectations (what outputs should appear; whether generated outputs are stable)
 
 **Risk:** Confusion between synthetic vs measured artifacts; inability to reproduce plots/metrics.
 
 **Suggested checklist addition:** “Data provenance + labeling audit” (every committed artifact should be labeled measured vs synthetic and point to a generator).
 
 ### D) Packaging / Distribution & Release Metadata (Not Covered)
 
 The quality audit discusses dependency strategy, but does not explicitly cover:
 - `pip install .` (non-editable) behavior
 - building an sdist/wheel (`python -m build`) and verifying included files
 - correctness of `project.urls` (currently placeholders)
 - release metadata consistency across:
   - `pyproject.toml` version
   - `src/biosystems/__init__.py` version
   - `CHANGELOG.md`
 - citation/licensing completeness:
   - `CITATION.cff`
   - `LICENSE`
 
 **Risk:** Repository appears “reproducible” locally but is not actually distributable/releasable.
 
 **Suggested checklist addition:** “Release readiness audit” (build artifacts, metadata, version consistency, citation/licensing).
 
 ### E) CI as a Quality Gate (Under-Covered)
 
 CI workflows are mentioned in findings, but `QUALITY_AUDIT.md` lacks a dedicated section that:
 - inventories workflows
 - states what each workflow guarantees
 - ensures essential gates exist (full test suite, packaging checks, lint/type checks if desired)
 
 **Risk:** “CI exists” but doesn’t enforce correctness for most of the codebase.
 
 **Suggested checklist addition:** “CI gate audit” (what’s enforced on PR; what’s enforced on release).
 
 ### F) Public API Stability / Export Surface (Not Covered)
 
 `__init__.py` exports define the user-facing API, but are not audited for:
 - consistency with README imports
 - backwards compatibility
 - “supported surface area” vs internal modules
 
 **Risk:** Users import from “convenience” modules that are not treated as stable.
 
 **Suggested checklist addition:** “Public API audit” (document supported imports and enforce them with tests).
 
 ---
 
 ## 5) Recommended Minimal Additions to Close the Biggest Blind Spots
 
 - **Docs + report traceability**
   - Audit `docs/DATA_PREPARATION.md` + `reports/01_longitudinal_study.md` for reproducibility links to code/data.
 
 - **Data provenance labeling**
   - Explicitly classify each artifact in `data/` as “measured” vs “synthetic”, and identify the generating script.
 
 - **Release readiness**
   - Validate packaging build, metadata, versioning, `CHANGELOG.md`, `CITATION.cff`, `LICENSE`.
 
 - **CI gate audit**
   - Inventory workflows + ensure at least one job runs full `pytest`.
