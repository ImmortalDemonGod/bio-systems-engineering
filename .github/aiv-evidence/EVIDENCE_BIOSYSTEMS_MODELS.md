# AIV Evidence File (v1.0)

**File:** `src/biosystems/models.py`
**Commit:** `beb4bae`
**Generated:** 2026-03-18T00:28:34Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/models.py"
  classification_rationale: "Core model validation fix affecting zone loading - medium impact"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T00:28:34Z"
```

## Claim(s)

1. HeartRateZone validates bpm=(0, 145) without error for Z1 Recovery zone
2. Validation rejects negative lower bounds but allows zero as sentinel value
3. Import statements reordered for consistency
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/aiv-protocol](https://github.com/ImmortalDemonGod/aiv-protocol)
- **Requirements Verified:** Z1 zone must accept 0 as lower bound sentinel per zones_personal.yml

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`beb4bae`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/beb4baed45b7b1d12a6c35340eea84a517fdcc8f))

- [`src/biosystems/models.py#L14-L15`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L14-L15)
- [`src/biosystems/models.py#L20`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L20)
- [`src/biosystems/models.py#L30`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L30)
- [`src/biosystems/models.py#L32-L35`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L32-L35)
- [`src/biosystems/models.py#L37`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L37)
- [`src/biosystems/models.py#L41-L42`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L41-L42)
- [`src/biosystems/models.py#L44-L45`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L44-L45)
- [`src/biosystems/models.py#L47`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L47)
- [`src/biosystems/models.py#L59`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L59)
- [`src/biosystems/models.py#L71`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L71)
- [`src/biosystems/models.py#L74-L77`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L74-L77)
- [`src/biosystems/models.py#L81`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L81)
- [`src/biosystems/models.py#L89`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L89)
- [`src/biosystems/models.py#L92`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L92)
- [`src/biosystems/models.py#L108-L114`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L108-L114)
- [`src/biosystems/models.py#L120`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L120)
- [`src/biosystems/models.py#L122`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L122)
- [`src/biosystems/models.py#L146`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L146)
- [`src/biosystems/models.py#L154-L158`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L154-L158)
- [`src/biosystems/models.py#L164`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L164)
- [`src/biosystems/models.py#L172`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L172)
- [`src/biosystems/models.py#L174`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L174)
- [`src/biosystems/models.py#L188`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L188)
- [`src/biosystems/models.py#L193`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L193)
- [`src/biosystems/models.py#L199`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L199)
- [`src/biosystems/models.py#L219`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L219)
- [`src/biosystems/models.py#L226-L227`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L226-L227)
- [`src/biosystems/models.py#L232`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/beb4baed45b7b1d12a6c35340eea84a517fdcc8f/src/biosystems/models.py#L232)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`HeartRateZone`** (L14-L15): PASS -- 7 test(s) call `HeartRateZone` directly
  - `tests/test_models.py::test_valid_zone`
  - `tests/test_models.py::test_bpm_validation_negative`
  - `tests/test_models.py::test_bpm_validation_zero_lower_allowed`
  - `tests/test_models.py::test_reversed_bpm_range`
  - `tests/test_models.py::test_valid_config`
  - `tests/test_physics_metrics.py::test_missing_z2`
  - `tests/test_readme_examples.py::test_zone_config_api`
- **`HeartRateZone.validate_bpm_range`** (L20): FAIL -- WARNING: No tests import or call `validate_bpm_range`
- **`HeartRateZone.validate_pace_range`** (L30): FAIL -- WARNING: No tests import or call `validate_pace_range`
- **`ZoneConfig`** (L32-L35): PASS -- 5 test(s) call `ZoneConfig` directly
  - `tests/test_models.py::test_valid_config`
  - `tests/test_models.py::test_invalid_resting_hr`
  - `tests/test_models.py::test_invalid_threshold_hr`
  - `tests/test_physics_metrics.py::test_missing_z2`
  - `tests/test_readme_examples.py::test_zone_config_api`
- **`ZoneConfig.validate_threshold_above_resting`** (L37): FAIL -- WARNING: No tests import or call `validate_threshold_above_resting`
- **`RunContext`** (L41-L42): PASS -- 2 test(s) call `RunContext` directly
  - `tests/test_models.py::test_valid_context`
  - `tests/test_models.py::test_invalid_rest_hr`
- **`PhysiologicalMetrics`** (L44-L45): PASS -- 4 test(s) call `PhysiologicalMetrics` directly
  - `tests/test_models.py::test_valid_metrics`
  - `tests/test_models.py::test_validation_negative_distance`
  - `tests/test_models.py::test_validation_zero_duration`
  - `tests/test_models.py::test_valid_summary`
- **`PhysiologicalMetrics.validate_decoupling_reasonable`** (L47): FAIL -- WARNING: No tests import or call `validate_decoupling_reasonable`
- **`ActivitySummary`** (L59): PASS -- 1 test(s) call `ActivitySummary` directly
  - `tests/test_models.py::test_valid_summary`
- **`WalkSegment`** (L71): PASS -- 2 test(s) call `WalkSegment` directly
  - `tests/test_models.py::test_optional_fields`
  - `tests/test_models.py::test_valid_segment`

**Coverage summary:** 6/10 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | HeartRateZone validates bpm=(0, 145) without error for Z1 Re... | symbol | 7 test(s) call `HeartRateZone` | PASS VERIFIED |
| 2 | Validation rejects negative lower bounds but allows zero as ... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | Import statements reordered for consistency | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 4 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 3 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (6/10 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Fix Z1 zone validation to allow zero lower bound
