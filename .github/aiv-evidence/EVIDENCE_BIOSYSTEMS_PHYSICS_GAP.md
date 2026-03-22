# AIV Evidence File (v1.0)

**File:** `src/biosystems/physics/gap.py`
**Commit:** `c38db0b`
**Previous:** `19256af`
**Generated:** 2026-03-18T20:39:39Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/physics/gap.py"
  classification_rationale: "Robustness fix"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T20:39:39Z"
```

## Claim(s)

1. Add check_elevation_quality to detect GPS/barometric corruption (clamping >10%)
2. Suppress GAP/EF_GAP when elevation is unreliable and surface reason via gap_quality_note
3. Extend data models to capture and propagate GAP quality metadata
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/physics](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/physics)
- **Requirements Verified:** Harden physiological metrics against nonsensical GPS vertical jitter

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`c38db0b`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/c38db0bfeccba1ebf734a73f482970310ae051da))

- [`src/biosystems/physics/gap.py#L190-L257`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/c38db0bfeccba1ebf734a73f482970310ae051da/src/biosystems/physics/gap.py#L190-L257)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`check_elevation_quality`** (L190-L257): PASS -- 4 test(s) call `check_elevation_quality` directly
  - `tests/test_physics_gap.py::test_reliable_elevation`
  - `tests/test_physics_gap.py::test_corrupted_jitter`
  - `tests/test_physics_gap.py::test_insufficient_data`
  - `tests/test_physics_gap.py::test_missing_columns`

**Coverage summary:** 1/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Found 1 error in 1 file (checked 1 source file)

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Add check_elevation_quality to detect GPS/barometric corrupt... | symbol | 4 test(s) call `check_elevation_quality` | PASS VERIFIED |
| 2 | Suppress GAP/EF_GAP when elevation is unreliable and surface... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | Extend data models to capture and propagate GAP quality meta... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 4 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 3 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Add elevation quality guard
