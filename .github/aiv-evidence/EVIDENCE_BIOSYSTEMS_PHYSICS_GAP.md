# AIV Evidence File (v1.0)

**File:** `src/biosystems/physics/gap.py`
**Commit:** `19ae248`
**Generated:** 2026-03-18T05:11:34Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/physics/gap.py"
  classification_rationale: "Algorithmic refinement"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T05:11:34Z"
```

## Claim(s)

1. Minetti's polynomial is sensitive to GPS noise; a 5-point rolling average is applied to elevation before differencing to improve GAP accuracy
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics)
- **Requirements Verified:** Improve Grade Adjusted Pace (GAP) reliability

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`19ae248`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/19ae2484cbf856df56c105890cf1e161b5a46c23))

- [`src/biosystems/physics/gap.py#L151-L154`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/19ae2484cbf856df56c105890cf1e161b5a46c23/src/biosystems/physics/gap.py#L151-L154)
- [`src/biosystems/physics/gap.py#L160-L166`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/19ae2484cbf856df56c105890cf1e161b5a46c23/src/biosystems/physics/gap.py#L160-L166)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`calculate_gap_from_dataframe`** (L151-L154): PASS -- 3 test(s) call `calculate_gap_from_dataframe` directly
  - `tests/test_physics_gap.py::test_simple_dataframe`
  - `tests/test_physics_gap.py::test_flat_dataframe`
  - `tests/test_physics_gap.py::test_missing_values`

**Coverage summary:** 1/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Minetti's polynomial is sensitive to GPS noise; a 5-point ro... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Smooth elevation for GAP
