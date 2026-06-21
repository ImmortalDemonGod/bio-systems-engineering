# AIV Evidence File (v1.0)

**File:** `src/biosystems/physics/metrics.py`
**Commit:** `17c156f`
**Previous:** `f8dec15`
**Generated:** 2026-06-21T08:45:08Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/physics/metrics.py"
  classification_rationale: "R1: one-line behavioral fix in production code mirroring gap.py fix; same invariant (NaN vs 0m) at the metrics.py integration layer"
  classified_by: "Claude"
  classified_at: "2026-06-21T08:45:08Z"
```

## Claim(s)

1. run_metrics on a synthetic all-ele=0 DataFrame yields a non-None gap_min_per_km (METRICS-PRE-GATE)
2. all 277 tests pass after removing replace(0, np.nan) from metrics.py:317
3. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92)
- **Requirements Verified:** METRICS-PRE-GATE: metrics.py pre-gate must not treat 0m elevation as missing; sea-level activities must get gap_min_per_km computed

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`17c156f`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/17c156f32ac4bcc66012ed733d4c7a06844a5f86))

- [`src/biosystems/physics/metrics.py#L317`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/17c156f32ac4bcc66012ed733d4c7a06844a5f86/src/biosystems/physics/metrics.py#L317)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`run_metrics`** (L317): PASS -- 7 test(s) call `run_metrics` directly
  - `tests/test_physics_gap.py::test_run_metrics_gap_computed_for_all_zero_elevation_sea_level_activity`
  - `tests/test_physics_gap.py::test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run`
  - `tests/test_readme_examples.py::test_quick_start_example`
  - `tests/test_physics_metrics.py::test_complete_analysis`
  - `tests/test_physics_metrics.py::test_with_cadence`
  - `tests/test_physics_metrics.py::test_without_elevation`
  - `tests/test_physics_metrics.py::test_zero_elevation_gap_computed`

**Coverage summary:** 1/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Found 1 error in 1 file (checked 1 source file)

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | run_metrics on a synthetic all-ele=0 DataFrame yields a non-... | symbol | 7 test(s) call `run_metrics` | PASS VERIFIED |
| 2 | all 277 tests pass after removing replace(0, np.nan) from me... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Drop replace(0,np.nan) from metrics ele pre-gate; add METRICS-PRE-GATE integration test
