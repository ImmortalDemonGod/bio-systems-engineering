# AIV Evidence File (v1.0)

**File:** `src/biosystems/models.py`
**Commit:** `3497c44`
**Previous:** `19ae248`
**Generated:** 2026-03-18T06:26:36Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/models.py"
  classification_rationale: "Robustness fix"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T06:26:36Z"
```

## Claim(s)

1. Allow any decoupling value in models; add zero-variance HR guard in analytics report calculation
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics)
- **Requirements Verified:** Harden pipeline against anomalous data states

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`3497c44`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/3497c44abd2f5a9ec9861ce80629f3857f32884a))

- [`src/biosystems/models.py#L161`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/3497c44abd2f5a9ec9861ce80629f3857f32884a/src/biosystems/models.py#L161)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`PhysiologicalMetrics`** (L161): PASS -- 4 test(s) call `PhysiologicalMetrics` directly
  - `tests/test_models.py::test_valid_metrics`
  - `tests/test_models.py::test_validation_negative_distance`
  - `tests/test_models.py::test_validation_zero_duration`
  - `tests/test_models.py::test_valid_summary`
- **`PhysiologicalMetrics.validate_decoupling_reasonable`** (unknown): FAIL -- WARNING: No tests import or call `validate_decoupling_reasonable`

**Coverage summary:** 1/2 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Allow any decoupling value in models; add zero-variance HR g... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Update models and report hardening
