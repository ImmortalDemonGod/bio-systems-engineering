# AIV Evidence File (v1.0)

**File:** `src/biosystems/ingestion/fit.py`
**Commit:** `8fdd2b3`
**Previous:** `056b46d`
**Generated:** 2026-03-22T03:12:23Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/ingestion/fit.py"
  classification_rationale: "Low-risk additive change — aliases added only when canonical columns exist and alias is absent; no renames"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-22T03:12:23Z"
```

## Claim(s)

1. parse_fit output DataFrame contains lat and lon columns in addition to latitude and longitude
2. FIT DataFrames can be passed to downstream functions expecting GPX-style lat/lon column names without KeyError
3. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** FIT and GPX parsers must produce interchangeable DataFrames for the same signal/physics pipeline

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`8fdd2b3`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/8fdd2b36fea7bd9ef6fbcb47e1e249414b3411bd))

- [`src/biosystems/ingestion/fit.py#L149-L155`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/8fdd2b36fea7bd9ef6fbcb47e1e249414b3411bd/src/biosystems/ingestion/fit.py#L149-L155)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`parse_fit`** (L149-L155): PASS -- 4 test(s) call `parse_fit` directly
  - `tests/test_ingestion_fit.py::test_row_count`
  - `tests/test_ingestion_fit.py::test_zero_hr_becomes_nan`
  - `tests/test_ingestion_fit.py::test_zero_cadence_becomes_nan`
  - `tests/test_ingestion_fit.py::test_empty_file_raises_value_error`

**Coverage summary:** 1/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | parse_fit output DataFrame contains lat and lon columns in a... | symbol | 4 test(s) call `parse_fit` | PASS VERIFIED |
| 2 | FIT DataFrames can be passed to downstream functions expecti... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Add lat/lon alias columns in parse_fit() after latitude/longitude are populated
