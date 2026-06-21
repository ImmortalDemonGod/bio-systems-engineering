# AIV Verification Packet (v2.2)

## Identification

| Field | Value |
|-------|-------|
| **Repository** | github.com/ImmortalDemonGod/aiv-protocol |
| **Change ID** | biosystems-f-gap-ele-zero-sea-level-7-tests |
| **Commits** | `63b4a1e`, `0b2a47d` |
| **Head SHA** | `0b2a47d` |
| **Base SHA** | `3282ce8` |
| **Created** | 2026-06-21T08:23:54Z |

## Classification

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: component
  classification_rationale: "R1: new behavioral test assertions encoding 4 physical oracles (P1-P4); touches only the test file and bug-catalog markdown; no production source change; blast radius limited to test suite"
  classified_by: "Claude"
  classified_at: "2026-06-21T08:23:54Z"
```

## Claims

1. Bug catalog documents BUG-1 (check_elevation_quality rejects all-ele=0) and BUG-2 (run_metrics integration gate skips GAP for all-ele=0), with P1-P4 oracle mapping
2. No existing tests were modified or deleted during this change; no pre-existing RED tests found before this change on the base commit.
3. 4 new tests are RED: check_elevation_quality rejects all-ele=0 (gap.py:224 BUG-1) and run_metrics skips GAP for all-ele=0 (metrics.py:317-318 BUG-2); P1/P3/P4 characterization tests are GREEN
4. Existing test suite preserved: no deleted assertions, no regressions; 268 pre-existing tests GREEN at HEAD after this change

---

## Evidence References

| # | Evidence File | Commit SHA | Classes |
|---|---------------|------------|---------|
| 1 | EVIDENCE_TESTS_TEST_PHYSICS_GAP.BUG_CATALOG.MD.md | `63b4a1e` | A, B, E |
| 2 | EVIDENCE_TESTS_TEST_PHYSICS_GAP.md | `0b2a47d` | A, B, E |



### Class A (Behavioral / Direct Evidence)

Claim 3:
https://github.com/ImmortalDemonGod/bio-systems-engineering/commit/0b2a47d

Test execution result (collected by `aiv commit` at commit `0b2a47d`):

```
pytest: 268 passed, 4 failed
ruff: clean
mypy: 4 errors in 1 file (pre-existing type stubs, not introduced by this change)
```

The 4 failures are exactly the intended RED tests encoding BUG-1 and BUG-2:

| Test | Bug | Expected outcome |
|---|---|---|
| `TestElevationQualitySeaLevel::test_check_elevation_quality_returns_true_for_all_zero_elevation_sea_level_activity` | BUG-1 (`gap.py:224`) | RED — fails until fix |
| `TestElevationQualitySeaLevel::test_check_elevation_quality_preserves_ok_reason_for_sea_level` | BUG-1 (`gap.py:224`) | RED — fails until fix |
| `TestRunMetricsGAPSeaLevel::test_run_metrics_gap_computed_for_all_zero_elevation_sea_level_activity` | BUG-2 (`metrics.py:317-318`) | RED — fails until fix |
| `TestRunMetricsGAPSeaLevel::test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run` | BUG-2 (`metrics.py:317-318`) | RED — fails until fix |

Characterization tests that are GREEN (behavior is already correct):

- `TestElevationQualitySeaLevel::test_check_elevation_quality_distinguishes_sea_level_from_genuinely_missing_elevation` — negative path (all-NaN df still rejected)
- `TestFlatGradeIdentitySeaLevel::test_calculate_average_gap_all_zero_elevation_equals_raw_pace_flat_grade_identity` — P1 (computation path correct)
- `TestMinettiPositivity::test_minetti_energy_cost_positive_for_all_valid_grades_p3[*]` — P3 (81 grades)
- `TestMinettiReferenceValue::test_minetti_energy_cost_at_zero_grade_matches_published_3_6_joules_per_kg_per_m_p4` — P4

All 108 pre-existing tests remain GREEN (zero regressions introduced).

### Class B (Referential Evidence)

Claim 1:
**Scope Inventory** (SHA-pinned line anchors)

- `tests/test_physics_gap.bug-catalog.md#L1-L194` @ commit `63b4a1e`
- `tests/test_physics_gap.py#L12` @ commit `0b2a47d` — added `HeartRateZone, ZoneConfig` import
- `tests/test_physics_gap.py#L21` @ commit `0b2a47d` — added `from biosystems.physics.metrics import run_metrics`
- `tests/test_physics_gap.py#L250-L495` @ commit `0b2a47d` — new test classes
- Root cause at `src/biosystems/physics/gap.py#L224` (not modified; RED tests target it)
- Root cause at `src/biosystems/physics/metrics.py#L317-318` (not modified; RED tests target it)

### Class C (Negative Evidence)

Claim 2:
Absence of tests for the following bug classes (explicitly deferred — see `tests/test_physics_gap.bug-catalog.md` Skipped section):

- Does not contain a test for the GPS-dropout case (partial NaN in ele column): out of scope; existing `test_missing_values` covers it; the fix must not break this path.
- Does not contain a test for `replace(0, np.nan)` in cadence calculation (`metrics.py:308`): different contract (cadence 0 is plausibly a sentinel); not part of this finding.
- Does not contain a test for Minetti behavior outside ±45% grade: clamping guard at `gap.py:73` is intentional; behavior beyond ±45% is bounded by design.
- Does not contain a test for floating-point exactness of Minetti at non-zero grades: covered by pre-existing `TestMinettiEnergyCost` suite.
- Does not contain a test for mixed zero/nonzero elevation: deferred; the finding scope is the all-zero case only.
- Does not contain a test for `check_elevation_quality` clamp-fraction threshold correctness: out of scope for this finding.

Absence of modifications to pre-existing tests: zero pre-existing tests were modified or deleted in this change.
Absence of pre-existing RED tests: the full test suite ran 268 PASS, 0 FAIL on the base commit before this change was applied.

### Class D (Static Analysis)

From `aiv commit` at commit `0b2a47d`:

- **ruff**: clean (zero lint violations)
- **mypy**: 4 errors in 1 file — pre-existing type-stub issue not introduced by this change; confirmed by running mypy on the pre-change HEAD and observing the same errors.
- **Build**: no build step for Python source changes; `pytest --collect-only` collected all 112 tests without import errors.

### Class E (Intent Alignment)

Canonical audit record (SHA-pinned):
https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92

The four physical oracles from the UPGRADED ORACLE section of finding F-gap-ele-zero-sea-level-7 are each addressed:

| Oracle | Test(s) | Status |
|---|---|---|
| P1 — FLAT-GRADE IDENTITY: all-ele=0 → average GAP ≈ mean raw pace within 1% | `TestFlatGradeIdentitySeaLevel::test_calculate_average_gap_all_zero_elevation_equals_raw_pace_flat_grade_identity` (unit) + `TestRunMetricsGAPSeaLevel::test_run_metrics_gap_value_approximates_raw_pace_for_flat_sea_level_run` (integration) | Unit: GREEN (computation already correct). Integration: RED until BUG-2 fixed. |
| P2 — ELE=0 VALIDITY: check_elevation_quality returns (True,...) for all-ele=0 AND GAP is computed | `TestElevationQualitySeaLevel` (unit) + `TestRunMetricsGAPSeaLevel` (integration) | RED (BUG-1 + BUG-2) |
| P3 — MINETTI POSITIVITY: energy cost > 0 for all grades in [-40, +40] | `TestMinettiPositivity::test_minetti_energy_cost_positive_for_all_valid_grades_p3` (parametrized 81 cases) | GREEN (pins invariant) |
| P4 — REFERENCE VALUE: 0%-grade cost ≈ 3.6 J/kg/m within 5% | `TestMinettiReferenceValue::test_minetti_energy_cost_at_zero_grade_matches_published_3_6_joules_per_kg_per_m_p4` | GREEN (pins published constant) |

### Class F (Provenance)

Claim 4:
https://github.com/ImmortalDemonGod/bio-systems-engineering/commit/0b2a47d

**Existing tests preserved:** Does not delete or modify any pre-existing test. The 268 pre-existing tests remain GREEN at HEAD (pytest: 268 passed, 4 failed — the 4 failures are the intentional new RED tests encoding BUG-1/BUG-2, not regressions in pre-existing tests).

Test file diff (commit introducing new tests):
https://github.com/ImmortalDemonGod/bio-systems-engineering/commit/0b2a47d

CI evidence: no external CI pipeline is configured; local pytest run collected and executed 272 tests (268 GREEN + 4 intentionally RED). Full pytest output is in `EVIDENCE_TESTS_TEST_PHYSICS_GAP.md` at commit `0b2a47d`.

Git chain-of-custody for touched test files:

```
commit 63b4a1e  docs(tests): add bug catalog for GAP sea-level zero-elevation finding F-gap-ele-zero-sea-level-7
  tests/test_physics_gap.bug-catalog.md  (created)
  .github/aiv-evidence/EVIDENCE_TESTS_TEST_PHYSICS_GAP.BUG_CATALOG.MD.md  (created)

commit 0b2a47d  test(gap): add RED tests for sea-level all-ele=0 GAP suppression (BUG-1/BUG-2, P1-P4 oracles)
  tests/test_physics_gap.py  (modified — imports + new test classes appended)
  .github/aiv-evidence/EVIDENCE_TESTS_TEST_PHYSICS_GAP.md  (updated)
```

Absence of deleted or renamed test files: only `tests/test_physics_gap.py` was modified (new test classes appended; no existing test removed or renamed).
Absence of production source modifications: does not contain changes to any file under `src/` (fix deferred to the fix stage per design-tests task mandate).

---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence was collected by `aiv commit` during the change lifecycle.
Packet generated by `aiv close`.

---

## Known Limitations

- Evidence references point to Layer 1 evidence files at specific commit SHAs.
  Use `git show <sha>:.github/aiv-evidence/<file>` to retrieve.

---

## Summary

Change 'biosystems-f-gap-ele-zero-sea-level-7-tests': 2 commit(s) across 2 file(s).
