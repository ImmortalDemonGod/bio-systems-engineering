# AIV Evidence File (v1.0)

**File:** `src/biosystems/signal/walk_detection.py`
**Commit:** `b41e0ff`
**Previous:** `36acda3`
**Generated:** 2026-04-04T18:38:55Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/signal/walk_detection.py"
  classification_rationale: "behavioral change to walk segment cleanup filter"
  classified_by: "Miguel Ingram"
  classified_at: "2026-04-04T18:38:55Z"
```

## Claim(s)

1. filter_gps_jitter now uses pace<=12 and cad>=100 for walk-segment jitter cleanup, with docstring noting primary classification uses Cultivation thresholds
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** Walk segment jitter filter must not be conflated with primary run/walk classification

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`b41e0ff`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/b41e0ff012051a8a65ea8f0fec1b73ade9c3a39e))

- [`src/biosystems/signal/walk_detection.py#L17`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b41e0ff012051a8a65ea8f0fec1b73ade9c3a39e/src/biosystems/signal/walk_detection.py#L17)
- [`src/biosystems/signal/walk_detection.py#L21-L28`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b41e0ff012051a8a65ea8f0fec1b73ade9c3a39e/src/biosystems/signal/walk_detection.py#L21-L28)
- [`src/biosystems/signal/walk_detection.py#L39`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b41e0ff012051a8a65ea8f0fec1b73ade9c3a39e/src/biosystems/signal/walk_detection.py#L39)
- [`src/biosystems/signal/walk_detection.py#L46`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b41e0ff012051a8a65ea8f0fec1b73ade9c3a39e/src/biosystems/signal/walk_detection.py#L46)
- [`src/biosystems/signal/walk_detection.py#L172`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b41e0ff012051a8a65ea8f0fec1b73ade9c3a39e/src/biosystems/signal/walk_detection.py#L172)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`filter_gps_jitter`** (L17): PASS -- 3 test(s) call `filter_gps_jitter` directly
  - `tests/test_signal.py::test_removes_gps_jitter`
  - `tests/test_signal.py::test_keeps_real_walk_points`
  - `tests/test_signal.py::test_keeps_fast_pace`
- **`walk_block_segments`** (L21-L28): PASS -- 6 test(s) call `walk_block_segments` directly
  - `tests/test_signal.py::test_detects_walk_blocks`
  - `tests/test_signal.py::test_classifies_warmup`
  - `tests/test_signal.py::test_classifies_cooldown`
  - `tests/test_signal.py::test_respects_min_duration`
  - `tests/test_signal.py::test_no_walk_periods`
  - `tests/test_walk_detection_fix.py::test_walk_block_segments_none_fallback`

**Coverage summary:** 2/2 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 26 error(s)
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | filter_gps_jitter now uses pace<=12 and cad>=100 for walk-se... | symbol | 3 test(s) call `filter_gps_jitter` | PASS VERIFIED |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 1 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Separate jitter filter (secondary) from is_walk classification (primary); update default cad_thr to 140 in walk_block_segments
