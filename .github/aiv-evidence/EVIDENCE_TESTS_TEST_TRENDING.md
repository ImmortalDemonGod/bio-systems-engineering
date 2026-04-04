# AIV Evidence File (v1.0)

**File:** `tests/test_trending.py`
**Commit:** `95b1ee7`
**Generated:** 2026-04-04T22:42:06Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_trending.py"
  classification_rationale: "new test file covering previously untested analytics module"
  classified_by: "Miguel Ingram"
  classified_at: "2026-04-04T22:42:06Z"
```

## Claim(s)

1. 12 tests covering compute_pmc (including same-day multi-run aggregation fix), compute_rolling_stats, and summarize_trend; trending.py coverage from 0% to tested
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** PMC computation must be tested including the multi-run aggregation fix

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`95b1ee7`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/95b1ee70259b241ff4037a773eaf55368f18ff8e))

- [`tests/test_trending.py#L1-L142`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/95b1ee70259b241ff4037a773eaf55368f18ff8e/tests/test_trending.py#L1-L142)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`TestComputePMC`** (L1-L142): FAIL -- WARNING: No tests import or call `TestComputePMC`
- **`TestComputeRollingStats`** (unknown): FAIL -- WARNING: No tests import or call `TestComputeRollingStats`
- **`TestSummarizeTrend`** (unknown): FAIL -- WARNING: No tests import or call `TestSummarizeTrend`
- **`TestComputePMC.test_empty_input`** (unknown): FAIL -- WARNING: No tests import or call `test_empty_input`
- **`TestComputePMC.test_single_entry`** (unknown): FAIL -- WARNING: No tests import or call `test_single_entry`
- **`TestComputePMC.test_rest_days_filled`** (unknown): FAIL -- WARNING: No tests import or call `test_rest_days_filled`
- **`TestComputePMC.test_tsb_computed_before_load`** (unknown): FAIL -- WARNING: No tests import or call `test_tsb_computed_before_load`
- **`TestComputePMC.test_same_day_multi_run_aggregation`** (unknown): FAIL -- WARNING: No tests import or call `test_same_day_multi_run_aggregation`
- **`TestComputePMC.test_same_day_single_run_unchanged`** (unknown): FAIL -- WARNING: No tests import or call `test_same_day_single_run_unchanged`
- **`TestComputePMC.test_ctl_atl_direction`** (unknown): FAIL -- WARNING: No tests import or call `test_ctl_atl_direction`
- **`TestComputeRollingStats.test_empty_input`** (unknown): FAIL -- WARNING: No tests import or call `test_empty_input`
- **`TestComputeRollingStats.test_rolling_requires_minimum_data`** (unknown): FAIL -- WARNING: No tests import or call `test_rolling_requires_minimum_data`
- **`TestComputeRollingStats.test_rolling_computes_after_threshold`** (unknown): FAIL -- WARNING: No tests import or call `test_rolling_computes_after_threshold`
- **`TestSummarizeTrend.test_empty_pmc`** (unknown): FAIL -- WARNING: No tests import or call `test_empty_pmc`
- **`TestSummarizeTrend.test_returns_latest_values`** (unknown): FAIL -- WARNING: No tests import or call `test_returns_latest_values`

**Coverage summary:** 0/15 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 24 error(s)
- **mypy:** Found 1 error in 1 file (checked 1 source file)

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | 12 tests covering compute_pmc (including same-day multi-run ... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/15 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Test empty/single/multi-day PMC, same-day aggregation, TSB ordering, ATL/CTL decay rates, rolling stats minimum data
