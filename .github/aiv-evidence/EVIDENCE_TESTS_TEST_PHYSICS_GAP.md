# AIV Evidence File (v1.0)

**File:** `tests/test_physics_gap.py`
**Commit:** `63b4a1e`
**Previous:** `a1b9c21`
**Generated:** 2026-06-21T08:23:30Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_physics_gap.py"
  classification_rationale: "R1: new test file with behavioral assertions directly encoding the P1-P4 physical oracles"
  classified_by: "Claude"
  classified_at: "2026-06-21T08:23:30Z"
```

## Claim(s)

1. 4 new tests are RED: check_elevation_quality rejects all-ele=0 (gap.py:224 BUG-1) and run_metrics skips GAP for all-ele=0 (metrics.py:317-318 BUG-2); P1/P3/P4 characterization tests are GREEN
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92)
- **Requirements Verified:** F-gap-ele-zero-sea-level-7: P2 tests must be RED, P1/P3/P4 characterization tests must be GREEN, all existing tests must stay GREEN

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`63b4a1e`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/63b4a1ef5e36efc73eae4816c4f94f77de6ea733))

- [`tests/test_physics_gap.py#L12`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/63b4a1ef5e36efc73eae4816c4f94f77de6ea733/tests/test_physics_gap.py#L12)
- [`tests/test_physics_gap.py#L21`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/63b4a1ef5e36efc73eae4816c4f94f77de6ea733/tests/test_physics_gap.py#L21)
- [`tests/test_physics_gap.py#L250-L495`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/63b4a1ef5e36efc73eae4816c4f94f77de6ea733/tests/test_physics_gap.py#L250-L495)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`_sea_level_df`** (L12): PASS -- 3 test(s) call `_sea_level_df` directly
  - `tests/test_physics_gap.py::test_check_elevation_quality_returns_true_for_all_zero_elevation_sea_level_activity`
  - `tests/test_physics_gap.py::test_check_elevation_quality_preserves_ok_reason_for_sea_level`
  - `tests/test_physics_gap.py::test_calculate_average_gap_all_zero_elevation_equals_raw_pace_flat_grade_identity`
- **`TestElevationQualitySeaLevel`** (L21): FAIL -- WARNING: No tests import or call `TestElevationQualitySeaLevel`
- **`TestFlatGradeIdentitySeaLevel`** (L250-L495): FAIL -- WARNING: No tests import or call `TestFlatGradeIdentitySeaLevel`
- **`TestMinettiPositivity`** (unknown): FAIL -- WARNING: No tests import or call `TestMinettiPositivity`
- **`TestMinettiReferenceValue`** (unknown): FAIL -- WARNING: No tests import or call `TestMinettiReferenceValue`
- **`_flat_zone_config`** (unknown): FAIL -- WARNING: No tests import or call `_flat_zone_config`
- **`TestRunMetricsGAPSeaLevel`** (unknown): FAIL -- WARNING: No tests import or call `TestRunMetricsGAPSeaLevel`
- **`TestElevationQualitySeaLevel.test_check_elevation_quality_returns_true_for_all_zero_elevation_sea_level_activity`** (unknown): FAIL -- WARNING: No tests import or call `test_check_elevation_quality_returns_true_for_all_zero_elevation_sea_level_activity`
- **`TestElevationQualitySeaLevel.test_check_elevation_quality_preserves_ok_reason_for_sea_level`** (unknown): FAIL -- WARNING: No tests import or call `test_check_elevation_quality_preserves_ok_reason_for_sea_level`
- **`TestElevationQualitySeaLevel.test_check_elevation_quality_distinguishes_sea_level_from_genuinely_missing_elevation`** (unknown): FAIL -- WARNING: No tests import or call `test_check_elevation_quality_distinguishes_sea_level_from_genuinely_missing_elevation`
- **`TestFlatGradeIdentitySeaLevel.test_calculate_average_gap_all_zero_elevation_equals_raw_pace_flat_grade_identity`** (unknown): FAIL -- WARNING: No tests import or call `test_calculate_average_gap_all_zero_elevation_equals_raw_pace_flat_grade_identity`
- **`TestMinettiPositivity.test_minetti_energy_cost_positive_for_all_valid_grades_p3`** (unknown): FAIL -- WARNING: No tests import or call `test_minetti_energy_cost_positive_for_all_valid_grades_p3`
- **`TestMinettiReferenceValue.test_minetti_energy_cost_at_zero_grade_matches_published_3_6_joules_per_kg_per_m_p4`** (unknown): FAIL -- WARNING: No tests import or call `test_minetti_energy_cost_at_zero_grade_matches_published_3_6_joules_per_kg_per_m_p4`
- **`TestRunMetricsGAPSeaLevel.test_run_metrics_gap_computed_for_all_zero_elevation_sea_level_activity`** (unknown): FAIL -- WARNING: No tests import or call `test_run_metrics_gap_computed_for_all_zero_elevation_sea_level_activity`
- **`TestRunMetricsGAPSeaLevel.test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run`** (unknown): FAIL -- WARNING: No tests import or call `test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run`

**Coverage summary:** 1/15 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Found 4 errors in 1 file (checked 1 source file)

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | 4 new tests are RED: check_elevation_quality rejects all-ele... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/15 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

RED tests for sea-level zero-elevation GAP suppression (BUG-1 unit + BUG-2 integration)
