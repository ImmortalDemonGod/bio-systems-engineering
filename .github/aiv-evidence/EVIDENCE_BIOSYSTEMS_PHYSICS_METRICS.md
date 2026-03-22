# AIV Evidence File (v1.0)

**File:** `src/biosystems/physics/metrics.py`
**Commit:** `19256af`
**Previous:** `0f705ab`
**Generated:** 2026-03-18T19:26:19Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/physics/metrics.py"
  classification_rationale: "Algorithmic fix"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T19:26:19Z"
```

## Claim(s)

1. Split sessions by cumulative elapsed time instead of sample count to handle non-uniform sampling
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/physics](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/physics)
- **Requirements Verified:** Ensure accurate aerobic drift calculation for auto-paused sessions

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`19256af`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/19256afa4c02dab82abf79193cbc3358cb1cde3c))

- [`src/biosystems/physics/metrics.py#L191-L199`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/19256afa4c02dab82abf79193cbc3358cb1cde3c/src/biosystems/physics/metrics.py#L191-L199)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`calculate_decoupling`** (L191-L199): PASS -- 3 test(s) call `calculate_decoupling` directly
  - `tests/test_physics_metrics.py::test_no_drift`
  - `tests/test_physics_metrics.py::test_positive_drift`
  - `tests/test_physics_metrics.py::test_negative_drift`

**Coverage summary:** 1/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Split sessions by cumulative elapsed time instead of sample ... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Temporal decoupling split
