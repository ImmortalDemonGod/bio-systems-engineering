 # Meta Audit (Dec 18, 2025): Coverage Gaps in `QUALITY_AUDIT.md`
 
 **Purpose:** Produce a single, coverage-focused document that identifies which parts of the `bio-systems-engineering` repository were **not** covered (explicitly or implicitly) by `audits/QUALITY_AUDIT.md`.
 
 **Non-goals:**
 - This document does **not** re-audit the code.
 - This document does **not** restate findings already recorded in `QUALITY_AUDIT.md`.
 
 ---
 
 ## 1) How “Covered” Is Defined
 
 This meta-audit uses three coverage levels:
 
 - **Reviewed (explicit)**
   The file/module is treated as a first-class artifact in `QUALITY_AUDIT.md` (file-specific checklist item and/or a concrete finding).
 
 - **Mentioned (partial)**
   The file/module is only referenced indirectly (examples, globs like `.github/workflows/*`, or general checklist questions), without file-specific review.
 
 - **Implicit (automation-only)**
   The file/module is not referenced in `QUALITY_AUDIT.md`, but is exercised by CI or verification steps (e.g., README example tests, full `pytest`, install/import checks).
 
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
 
 **Reviewed explicitly (Quality Audit treats as a first-class artifact):**
 - `src/biosystems/ingestion/{gpx.py, fit.py}`
 - `src/biosystems/physics/{metrics.py, gap.py}`
 - `src/biosystems/signal/walk_detection.py`
 - `src/biosystems/environment/weather.py`
 - `src/biosystems/models.py`
 - `tools/sanitize_gps.py`
 - `tools/generate_from_real_data.py`
 - `tools/generate_sample_data.py` and `tools/generate_sample_data.py.OLD`
 - `tests/test_ingestion_gpx.py`
 - `tests/test_models.py`
 - `data/sample/sample_run.csv`
 - `README.md`
 - `pyproject.toml`, `requirements.txt`, `Dockerfile`
 - `.gitignore`
 
 ## 3.1) Coverage Gaps (File-by-File)
 
 This table intentionally lists **only** files/areas that are **under-covered** (mentioned only at a category/glob/checklist level) or **uncovered** (not mentioned).
 
 **Key:**
 - **Partial:** referenced by category/glob/checklist, but not audited as a specific file.
 - **Uncovered:** not referenced in `QUALITY_AUDIT.md`.
 
 | Path | Coverage | Evidence in `QUALITY_AUDIT.md` | Why this is a gap |
 | :--- | :--- | :--- | :--- |
 | `src/biosystems/__init__.py` | Uncovered | — | Public API/export surface not reviewed as a first-class artifact. |
 | `src/biosystems/environment/__init__.py` | Uncovered | — | Public API/export surface not reviewed as a first-class artifact. |
 | `src/biosystems/ingestion/__init__.py` | Uncovered | — | Public API/export surface not reviewed as a first-class artifact. |
 | `src/biosystems/physics/__init__.py` | Uncovered | — | Public API/export surface not reviewed as a first-class artifact. |
 | `src/biosystems/signal/__init__.py` | Uncovered | — | Public API/export surface not reviewed as a first-class artifact. |
 | `tools/verify_installation.py` | Uncovered | — | Important QA artifact, but the audit does not reference it or validate it. |
 | `tools/generate_readme_charts.py` | Partial | Checklist VI → “Visualizations” | Script that generates published charts is not reviewed for reproducibility/inputs. |
 | `tools/generate_charts_real_only.py` | Partial | Checklist VI → “Visualizations” | Script that generates published charts is not reviewed for reproducibility/inputs. |
 | `docs/images/ef_progression.png` | Partial | Checklist VI → “Visualizations” | Image exists, but provenance (script+inputs) is not documented/validated. |
 | `docs/images/aerobic_decoupling.png` | Partial | Checklist VI → “Visualizations” | Image exists, but provenance (script+inputs) is not documented/validated. |
 | `docs/DATA_PREPARATION.md` | Uncovered | — | ETL/data assumptions can drift from code without detection. |
 | `docs/internal/CLEANUP_SUMMARY.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/DEVELOPMENT_ARCHIVE.md` | Uncovered | — | Internal process/history docs not covered. |
 | `docs/internal/FEEDBACK_ANALYSIS.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/INFRASTRUCTURE_FIX_COMPLETE.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/README.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/README_ADDITIONAL_FAILURES.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/README_FIX_COMPLETE.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/README_VERIFICATION_FAILURES.md` | Uncovered | — | Internal process docs not covered. |
 | `docs/internal/REPOSITORY_CLEANUP.md` | Uncovered | — | Internal process docs not covered. |
 | `reports/01_longitudinal_study.md` | Uncovered | — | Narrative claims are not tied to scripts+data (traceability gap). |
 | `data/sample/weekly_metrics.csv` | Partial | Checklist IV → “Sample Data” | Sample artifact provenance/labeling is not audited (synthetic vs measured). |
 | `data/sample/README.md` | Partial | Checklist IV → “Sample Data” | Sample README not checked for API correctness or drift. |
 | `data/real_weekly_data.json` | Partial | Findings log (`tools/generate_from_real_data.py`) | Provenance/schema stability not audited. |
 | `data/processed/` | Uncovered | — | Expected generated outputs and stability are not documented. |
 | `data/raw/` | Partial | Checklist IV → “Repository Hygiene” | Folder is implied by `.gitignore`, but provenance/handling policy not audited. |
 | `.github/workflows/installation-test.yml` | Partial | Findings log (`.github/workflows/*`) | Workflow is referenced as a category, not audited line-by-line as a guarantee. |
 | `.github/workflows/readme-validation.yml` | Partial | Findings log (`.github/workflows/*`) | Workflow is referenced as a category, not audited line-by-line as a guarantee. |
 | `tests/test_environment.py` | Partial | Findings log (`.github/workflows/*`) | Mentioned as missing from CI full-suite, but test adequacy not reviewed. |
 | `tests/test_signal.py` | Partial | Findings log (`.github/workflows/*`) | Mentioned as missing from CI full-suite, but test adequacy not reviewed. |
 | `tests/test_physics_gap.py` | Partial | Checklist VII → “Test Coverage” | Not reviewed as a test artifact (only implementation file reviewed). |
 | `tests/test_physics_metrics.py` | Partial | Checklist VII → “Test Coverage” | Not reviewed as a test artifact (only implementation file reviewed). |
 | `tests/test_readme_examples.py` | Partial | Checklist VI → “Readme Accuracy” | CI depends on this file, but the audit does not mention it as an artifact/contract. |
 | `CHANGELOG.md` | Uncovered | — | Release/version narrative is not audited for consistency with code+metadata. |
 | `CITATION.cff` | Uncovered | — | Citation metadata is not audited for correctness/completeness. |
 | `LICENSE` | Uncovered | — | License file is not audited (compatibility/completeness). |
 
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

 ### G) Tooling That Drives Outputs (Under-Covered)

 Scripts that directly shape “published” artifacts (charts, demos, smoke checks) are not explicitly audited:
 - `tools/verify_installation.py`
 - `tools/generate_readme_charts.py`
 - `tools/generate_charts_real_only.py`

 **Risk:** These scripts can drift from the public API and silently make outputs non-reproducible (or misleading) without failing CI.

 **Suggested checklist addition:** “Tooling audit” covering all `tools/*.py` scripts that generate docs/images/data or act as QA gates.
 
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

 - **Tooling audit**
   - Treat `tools/verify_installation.py` and chart generators as audited deliverables, not just convenience scripts.
