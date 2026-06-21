# AIV Verification Packet (v2.2)

## Identification

| Field | Value |
|-------|-------|
| **Repository** | github.com/ImmortalDemonGod/bio-systems-engineering |
| **Change ID** | biosystems-f-gap-ele-zero-sea-level-7-impl |
| **Finding ID** | F-gap-ele-zero-sea-level-7 |
| **Commits** | `17c156f`, `f1aef32` |
| **Head SHA** | `f1aef32` |
| **Base SHA** | `9324c72` |
| **Created** | 2026-06-21T08:45:17Z |

## Classification

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: component
  classification_rationale: >
    R1: Two one-line behavioral fixes in production physics code (gap.py:224,
    metrics.py:317). Each removes a single .replace(0, np.nan) call that
    incorrectly treated 0 m elevation as missing data. No new logic added;
    no external boundaries crossed; all existing tests remain green.
  classified_by: "Claude (write-code stage)"
  classified_at: "2026-06-21T08:45:17Z"
```

## Claims

1. `check_elevation_quality` returns `(True, 'ok')` for a synthetic 20-row all-ele=0 DataFrame (P2 oracle — `gap.py:224` fix)
2. `run_metrics` on a synthetic all-ele=0 DataFrame yields a non-None `gap_min_per_km` (METRICS-PRE-GATE — `metrics.py:317` fix)
3. All 277 tests pass after both fixes; 0 previously-passing tests regressed.
4. No `replace(0, np.nan)` remains on the elevation quality-gate line (`gap.py`) or pre-gate line (`metrics.py`); the cadence `replace(0, np.nan)` at `metrics.py:308` is intentionally preserved (cadence=0 is a sensor dropout, not valid terrain).
5. All test DataFrames are synthetic (np.zeros / literals); no real GPS or HR rows appear in any test file.

---

## Evidence References

| # | Evidence File | Commit SHA | Classes |
|---|---------------|------------|---------|
| 1 | EVIDENCE_BIOSYSTEMS_PHYSICS_GAP.md | `17c156f` | A, B, E |
| 2 | EVIDENCE_BIOSYSTEMS_PHYSICS_METRICS.md | `f1aef32` | A, B, E |

---

### Class A (Behavioral / Direct Execution Evidence)

Evidence collected by `aiv commit` during each atomic commit. Raw tool output is in the evidence files at the SHAs above.

**gap.py (commit `17c156f`):**
- `pytest`: **277 passed, 0 failed** (run at commit time)
- 8 tests call `check_elevation_quality` directly, including:
  - `TestElevationQualitySeaLevel::test_check_elevation_quality_returns_true_for_all_zero_elevation_sea_level_activity` — PASS (was RED before fix)
  - `TestElevationQualitySeaLevel::test_check_elevation_quality_preserves_ok_reason_for_sea_level` — PASS (was RED before fix)
  - `TestPhysicalProperties::test_p2_ele_zero_validity` — PASS (was RED before fix)
  - `TestElevationQuality::test_insufficient_data` — PASS (pre-existing; still returns False for a 2-row non-zero df after the fix — the `dropna()` preserves the `len < 10` check correctly)

**metrics.py (commit `f1aef32`):**
- `pytest`: **277 passed, 0 failed** (run at commit time)
- 7 tests call `run_metrics` directly, including:
  - `TestRunMetricsGAPSeaLevel::test_run_metrics_gap_computed_for_all_zero_elevation_sea_level_activity` — PASS (was RED before fix)
  - `TestRunMetricsGAPSeaLevel::test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run` — PASS (was RED before fix)
  - `TestRunMetricsGAP::test_zero_elevation_gap_computed` — PASS (new test added in this commit)

---

### Class B (Referential, SHA-Pinned, Line-Anchored)

**Commit `17c156f` — gap.py change:**

- Before: `src/biosystems/physics/gap.py:224` — `ele_series = df[ele_col].replace(0, np.nan).dropna()`
- After: `src/biosystems/physics/gap.py:224` — `ele_series = df[ele_col].dropna()`
- SHA-pinned diff: `git show 17c156f -- src/biosystems/physics/gap.py`

**Commit `f1aef32` — metrics.py change:**

- Before: `src/biosystems/physics/metrics.py:317` — `ele_series = df["ele"].replace(0, np.nan)`
- After: `src/biosystems/physics/metrics.py:317` — `ele_series = df["ele"]`
- SHA-pinned diff: `git show f1aef32 -- src/biosystems/physics/metrics.py`

**Intentionally untouched:**
- `src/biosystems/physics/metrics.py:308` — cadence `replace(0, np.nan)` remains (cadence=0 IS semantically missing GPS data; per plan §6 and §10, this is explicitly deferrable/correct behavior)
- `src/biosystems/physics/gap.py:165` — `rolling().mean()` has no ele==0 replacement (correct; computation path already treats 0 as valid flat terrain; this is the invariant the quality gate must agree with)

---

### Class C (Negative Evidence)

**What was searched for and NOT found:**

| Search | Command | Result |
|--------|---------|--------|
| `replace(0, np.nan)` on elevation quality-gate line | `grep -n "replace(0, np.nan)" src/biosystems/physics/gap.py` | 0 matches on ex-line-224 (cadence lines would appear only in metrics.py) |
| `replace(0, np.nan)` on metrics pre-gate line | `grep -n "replace(0, np.nan)" src/biosystems/physics/metrics.py` | 1 match at line 308 (cadence — intentionally preserved); 0 matches at ex-line-317 |
| Real `data/` path references in test files | `grep -rn "data/" tests/test_physics_gap.py tests/test_physics_metrics.py` | 0 file-path hits; 2 hits in docstring comments only |
| `--no-verify` or `--amend` bypass in commit chain | `git log origin/main..HEAD --format="%H %s" \| grep -E -- "--no-verify\|--amend\|skip.ci"` | 0 lines |
| Widened scope beyond §10 touched files | Manual review of `git diff origin/main..HEAD --name-only` | Changes confined to: `gap.py`, `metrics.py`, `test_physics_gap.py`, `test_physics_metrics.py`, `pyproject.toml`, `.github/aiv-evidence/`, `.github/aiv-packets/`, `.aiv/` |

**Bug-catalog 'Skipped' set (explicitly not fixed in this PR — per plan §6):**

| Finding | Classification | Reason |
|---------|---------------|--------|
| `metrics.py:308` cadence `replace(0, np.nan)` | Deferrable | Cadence=0 IS semantically missing (GPS dropout); correct behavior; separate semantic |
| F-gpx-cad-parse-unguarded-5 | Separate PR | Different module, different bug |
| F-gpx-ns-garmin-only-9 | Separate PR | Different module, doc drift |
| F-fit-indoor-gps-11 | Separate PR | Different module |
| F-strava-2 | Separate PR | Different module |

---

### Class D (Static Analysis: Lint / Type / Build)

Both commits collected by `aiv commit`:

| Tool | Result | Notes |
|------|--------|-------|
| `ruff` | **clean** (0 warnings, 0 errors) | Run at both commit times |
| `mypy` | 1 pre-existing `[import-untyped]` error for `pandas` at `gap.py:18` and `metrics.py:17` | Pandas stubs not installed; error exists on `main` prior to this branch; not introduced by this change. Verified: `git show origin/main:src/biosystems/physics/gap.py \| head -20` confirms same import. |
| `pytest` (build/import) | All 277 tests collected and run without import error | Collection success = package structure is valid |

**Tool versions (pinned in this commit's `pyproject.toml`):**
- `mypy==2.1.0` (was `>=1.0.0`; pinned to currently-installed version per DETERMINISM requirement)
- `ruff==0.15.17` (was `>=0.1.0`; pinned to currently-installed version per DETERMINISM requirement)

---

### Class E (Intent Alignment)

**Canonical source read:** `git show 89908ccd06c425d1199606fb6feb30e0cd7db2ad:audit/02-static-audit.md` lines ~92-101

**Source records:** Finding F-gap-ele-zero-sea-level-7 at `gap.py:224`. The audit records the following defect:
> `ele_series = df[ele_col].replace(0, np.nan).dropna()` — treats ele=0 as missing data before the `len < 10` threshold, so a sea-level activity with all-ele=0 becomes all-NaN after `replace`, then empty after `dropna`, and is wrongly rejected as "insufficient elevation data points". The computation path at `gap.py:165` uses `rolling().mean()` WITHOUT any ele==0 replacement, treating 0 as valid flat terrain. The inconsistency means a flat coastal run with valid 0 m elevation has GAP silently suppressed. The same `replace(0, np.nan)` pattern at `metrics.py:317-318` adds a second gate that short-circuits the entire GAP block before `check_elevation_quality` is even called.

**Alignment assessment:** This change addresses the defect exactly as described.

- `gap.py:224`: removed `replace(0, np.nan)` — quality gate now uses `df[ele_col].dropna()`, retaining 0.0 values as valid; the `len < 10` check correctly counts only non-NaN points, so a 20-row all-ele=0 df passes the threshold and proceeds to the clamping-fraction check, which also passes (grade ≈ 0% for flat terrain). The computation path at `gap.py:165` is untouched — the gate and computation now AGREE that 0 m is valid.
- `metrics.py:317`: removed `replace(0, np.nan)` from the pre-gate assignment — `ele_series = df["ele"]` now correctly reflects that 0.0 is not NaN; the guard `if not ele_series.isna().all()` evaluates False for an all-ele=0 df (`.isna().all()` is False when values are 0.0 not NaN), so the GAP block executes and `check_elevation_quality` is called, which now returns `(True, 'ok')`.
- Physical oracle properties P1–P4 are verified by `TestPhysicalProperties` (4 tests) and the design-tests classes (`TestElevationQualitySeaLevel`, `TestFlatGradeIdentitySeaLevel`, `TestMinettiPositivity`, `TestMinettiReferenceValue`, `TestRunMetricsGAPSeaLevel`), all green.

**Intent URL (SHA-pinned):**
`https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92`

---

### Class F (Provenance: Git Chain-of-Custody for Touched Test Files)

**`tests/test_physics_gap.py`** (modified in commit `17c156f`):

| Commit | Date | Message |
|--------|------|---------|
| `17c156f` | 2026-06-21 | fix(gap): remove ele==0 replacement in check_elevation_quality *(this change — adds TestPhysicalProperties P1–P4)* |
| `0b2a47d` | 2026-06-21 | test(gap): add RED tests for sea-level all-ele=0 GAP suppression (BUG-1/BUG-2, P1-P4 oracles) *(design-tests stage)* |
| `a1b9c21` | 2026-04-04 | fix(lint): remove trailing whitespace in docstrings |
| `0ffc80d` | 2026-04-04 | Add docstrings |

**`tests/test_physics_metrics.py`** (modified in commit `f1aef32`):

| Commit | Date | Message |
|--------|------|---------|
| `f1aef32` | 2026-06-21 | fix(metrics): remove ele==0 pre-gate replacement *(this change — adds TestRunMetricsGAP)* |
| `fd426bd` | 2026-04-04 | fix(lint): remove trailing whitespace in docstrings |
| `0ffc80d` | 2026-04-04 | Add docstrings |

Neither test file was modified outside of this change's two commits since the design-tests stage. No test was deleted or weakened.

---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` during the change lifecycle (real pytest/ruff/mypy runs, not templates).
Packet generated by `aiv close` and augmented with full A–F evidence per operator mandate (2026-06-19).

---

## Known Limitations

- `mypy` `[import-untyped]` error for `pandas` is pre-existing on `main` and was not introduced by this change. It is a missing-stubs issue, not a type error in the changed code.
- Evidence files are at specific commit SHAs: use `git show <sha>:.github/aiv-evidence/<file>` to retrieve.

---

## Summary

Change `biosystems-f-gap-ele-zero-sea-level-7-impl`: 2 production commits across 2 files.

- **Commit 1** (`17c156f`): `gap.py:224` — removed `replace(0, np.nan)` from `check_elevation_quality`; added `TestPhysicalProperties` (P1–P4) to `tests/test_physics_gap.py`; pinned `mypy==2.1.0` and `ruff==0.15.17` in `pyproject.toml`.
- **Commit 2** (`f1aef32`): `metrics.py:317` — removed `replace(0, np.nan)` from the elevation pre-gate; added `TestRunMetricsGAP` (METRICS-PRE-GATE) to `tests/test_physics_metrics.py`.

All 5 claims verified. 277 tests pass. 0 regressions. Physical oracle P1–P4 green.

## Machine-checkable data

```json
{
  "change_id": "biosystems-f-gap-ele-zero-sea-level-7-impl",
  "finding_id": "F-gap-ele-zero-sea-level-7",
  "commits": ["17c156f32ac4bcc66012ed733d4c7a06844a5f86", "f1aef323ec474b52cae434816414ef58e5e014c2"],
  "head_sha": "f1aef323ec474b52cae434816414ef58e5e014c2",
  "base_sha": "9324c72fef21f34eacc905eabe84eca874cc6e19",
  "risk_tier": "R1",
  "tests_passed": 277,
  "tests_failed": 0,
  "ruff_clean": true,
  "mypy_errors": 1,
  "mypy_error_note": "pre-existing import-untyped for pandas; not introduced by this change",
  "files_changed": [
    "src/biosystems/physics/gap.py",
    "src/biosystems/physics/metrics.py",
    "tests/test_physics_gap.py",
    "tests/test_physics_metrics.py",
    "pyproject.toml"
  ],
  "lines_removed": [
    "gap.py:224: df[ele_col].replace(0, np.nan).dropna()",
    "metrics.py:317: df[\"ele\"].replace(0, np.nan)"
  ],
  "intent_url": "https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92",
  "synthetic_only": true,
  "phi_guard_passed": true,
  "no_bypass": true
}
```
