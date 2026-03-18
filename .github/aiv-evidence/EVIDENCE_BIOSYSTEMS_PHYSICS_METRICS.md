# AIV Evidence File (v1.0)

**File:** `src/biosystems/physics/metrics.py`
**Commit:** `6e294c3`
**Generated:** 2026-03-18T00:29:11Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R2
  sod_mode: S1
  critical_surfaces: []
  blast_radius: "src/biosystems/physics/metrics.py"
  classification_rationale: "Core physiological metric calculations - high impact on study results accuracy"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T00:29:11Z"
```

## Claim(s)

1. calculate_efficiency_factor excludes is_walk==True rows before computing avg_speed/avg_hr
2. calculate_decoupling excludes is_walk==True rows before midpoint split
3. EF calculation accuracy improved by filtering out walking segments with elevated post-run HR
4. Both functions add dropna(subset=['hr']) to handle missing HR data robustly
5. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/aiv-protocol](https://github.com/ImmortalDemonGod/aiv-protocol)
- **Requirements Verified:** EF and decoupling metrics must match cultivation pipeline walk-excluded calculations

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`6e294c3`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/6e294c364b881b46256fdc32af5af44e4a14d977))

- [`src/biosystems/physics/metrics.py#L13`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L13)
- [`src/biosystems/physics/metrics.py#L18`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L18)
- [`src/biosystems/physics/metrics.py#L22`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L22)
- [`src/biosystems/physics/metrics.py#L30`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L30)
- [`src/biosystems/physics/metrics.py#L35`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L35)
- [`src/biosystems/physics/metrics.py#L42`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L42)
- [`src/biosystems/physics/metrics.py#L48-L49`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L48-L49)
- [`src/biosystems/physics/metrics.py#L52`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L52)
- [`src/biosystems/physics/metrics.py#L61`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L61)
- [`src/biosystems/physics/metrics.py#L73-L74`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L73-L74)
- [`src/biosystems/physics/metrics.py#L82`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L82)
- [`src/biosystems/physics/metrics.py#L89-L90`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L89-L90)
- [`src/biosystems/physics/metrics.py#L98`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L98)
- [`src/biosystems/physics/metrics.py#L101-L102`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L101-L102)
- [`src/biosystems/physics/metrics.py#L106`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L106)
- [`src/biosystems/physics/metrics.py#L108`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L108)
- [`src/biosystems/physics/metrics.py#L112`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L112)
- [`src/biosystems/physics/metrics.py#L115`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L115)
- [`src/biosystems/physics/metrics.py#L117`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L117)
- [`src/biosystems/physics/metrics.py#L124`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L124)
- [`src/biosystems/physics/metrics.py#L130-L136`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L130-L136)
- [`src/biosystems/physics/metrics.py#L139-L141`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L139-L141)
- [`src/biosystems/physics/metrics.py#L143-L147`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L143-L147)
- [`src/biosystems/physics/metrics.py#L149-L150`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L149-L150)
- [`src/biosystems/physics/metrics.py#L153`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L153)
- [`src/biosystems/physics/metrics.py#L156`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L156)
- [`src/biosystems/physics/metrics.py#L159`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L159)
- [`src/biosystems/physics/metrics.py#L164`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L164)
- [`src/biosystems/physics/metrics.py#L171`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L171)
- [`src/biosystems/physics/metrics.py#L177-L182`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L177-L182)
- [`src/biosystems/physics/metrics.py#L185-L187`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L185-L187)
- [`src/biosystems/physics/metrics.py#L189-L190`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L189-L190)
- [`src/biosystems/physics/metrics.py#L195`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L195)
- [`src/biosystems/physics/metrics.py#L198-L200`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L198-L200)
- [`src/biosystems/physics/metrics.py#L203-L205`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L203-L205)
- [`src/biosystems/physics/metrics.py#L207`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L207)
- [`src/biosystems/physics/metrics.py#L210-L211`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L210-L211)
- [`src/biosystems/physics/metrics.py#L214`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L214)
- [`src/biosystems/physics/metrics.py#L217`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L217)
- [`src/biosystems/physics/metrics.py#L220`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L220)
- [`src/biosystems/physics/metrics.py#L227`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L227)
- [`src/biosystems/physics/metrics.py#L233-L237`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L233-L237)
- [`src/biosystems/physics/metrics.py#L240-L241`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L240-L241)
- [`src/biosystems/physics/metrics.py#L245`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L245)
- [`src/biosystems/physics/metrics.py#L249`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L249)
- [`src/biosystems/physics/metrics.py#L255`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L255)
- [`src/biosystems/physics/metrics.py#L264`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L264)
- [`src/biosystems/physics/metrics.py#L269`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L269)
- [`src/biosystems/physics/metrics.py#L277-L279`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L277-L279)
- [`src/biosystems/physics/metrics.py#L282`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L282)
- [`src/biosystems/physics/metrics.py#L287`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L287)
- [`src/biosystems/physics/metrics.py#L290`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L290)
- [`src/biosystems/physics/metrics.py#L292-L295`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L292-L295)
- [`src/biosystems/physics/metrics.py#L298-L299`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L298-L299)
- [`src/biosystems/physics/metrics.py#L302`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L302)
- [`src/biosystems/physics/metrics.py#L305`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L305)
- [`src/biosystems/physics/metrics.py#L307`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L307)
- [`src/biosystems/physics/metrics.py#L311`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L311)
- [`src/biosystems/physics/metrics.py#L318`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L318)
- [`src/biosystems/physics/metrics.py#L329`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/6e294c364b881b46256fdc32af5af44e4a14d977/src/biosystems/physics/metrics.py#L329)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`_as_series`** (L13): FAIL -- WARNING: No tests import or call `_as_series`
- **`lower_z2_bpm`** (L18): PASS -- 2 test(s) call `lower_z2_bpm` directly
  - `tests/test_physics_metrics.py::test_extracts_z2_lower`
  - `tests/test_physics_metrics.py::test_missing_z2`
- **`compute_training_zones`** (L22): PASS -- 2 test(s) call `compute_training_zones` directly
  - `tests/test_physics_metrics.py::test_zone_classification`
  - `tests/test_physics_metrics.py::test_handles_nan`
- **`zone_hr`** (L30): FAIL -- WARNING: No tests import or call `zone_hr`
- **`zone_pace`** (L35): FAIL -- WARNING: No tests import or call `zone_pace`
- **`zone_effective`** (L42): FAIL -- WARNING: No tests import or call `zone_effective`
- **`calculate_efficiency_factor`** (L48-L49): PASS -- 3 test(s) call `calculate_efficiency_factor` directly
  - `tests/test_physics_metrics.py::test_steady_state_run`
  - `tests/test_physics_metrics.py::test_filters_warmup`
  - `tests/test_physics_metrics.py::test_all_below_z2`
- **`calculate_decoupling`** (L52): PASS -- 3 test(s) call `calculate_decoupling` directly
  - `tests/test_physics_metrics.py::test_no_drift`
  - `tests/test_physics_metrics.py::test_positive_drift`
  - `tests/test_physics_metrics.py::test_negative_drift`
- **`calculate_hr_tss`** (L61): PASS -- 2 test(s) call `calculate_hr_tss` directly
  - `tests/test_physics_metrics.py::test_threshold_pace`
  - `tests/test_physics_metrics.py::test_easy_pace`
- **`run_metrics`** (L73-L74): PASS -- 4 test(s) call `run_metrics` directly
  - `tests/test_physics_metrics.py::test_complete_analysis`
  - `tests/test_physics_metrics.py::test_with_cadence`
  - `tests/test_physics_metrics.py::test_without_elevation`
  - `tests/test_readme_examples.py::test_quick_start_example`

**Coverage summary:** 6/10 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

### Class C (Negative Evidence)

**Search methodology:** Ran `git diff --cached` and scanned for regression indicators.

- Test file deletions: **none**
- Test file modifications: **none**
- Deleted assertions (`assert` removals in diff): **none found**
- Added skip markers (`@pytest.mark.skip`, `@unittest.skip`): **none found**

### Class F (Provenance Evidence)

**Test file chain-of-custody:**

| File | Commits | Created By | Last Modified By | Assertions |
|------|---------|------------|------------------|------------|
| `tests/test_physics_metrics.py` | 1 | openhands (e2910a1) | openhands (e2910a1) | 28 |
| `tests/test_readme_examples.py` | 1 | openhands (3a02600) | openhands (3a02600) | 17 |

**Recent test directory history** (`git log --oneline -5 -- tests/`):

```
3a02600 fix: systematic README validation and CI/CD implementation
e2910a1 test: add comprehensive test suite (64% coverage → 70%+ target)
```

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | calculate_efficiency_factor excludes is_walk==True rows befo... | symbol | 3 test(s) call `calculate_efficiency_factor` | PASS VERIFIED |
| 2 | calculate_decoupling excludes is_walk==True rows before midp... | symbol | 3 test(s) call `calculate_decoupling` | PASS VERIFIED |
| 3 | EF calculation accuracy improved by filtering out walking se... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 4 | Both functions add dropna(subset=['hr']) to handle missing H... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 5 | No existing tests were modified or deleted during this chang... | structural | Class C: all structural indicators clean | PASS VERIFIED |

**Verdict summary:** 3 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (6/10 symbols verified), anti-cheat scan.
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Filter walking segments from efficiency factor and decoupling calculations
