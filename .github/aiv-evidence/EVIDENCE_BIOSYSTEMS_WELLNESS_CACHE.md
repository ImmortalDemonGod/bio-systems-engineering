# AIV Evidence File (v1.0)

**File:** `src/biosystems/wellness/cache.py`
**Commit:** `1c54260`
**Generated:** 2026-03-18T20:37:27Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/wellness/cache.py"
  classification_rationale: "Algorithmic refinement"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T20:37:27Z"
```

## Claim(s)

1. Add gar_overnight classification using only sleep-measured signals (RHR, HRV, sleep metrics)
2. Explicitly flag daily-average signals (Body Battery, Stress) as not pre-run valid
3. Update documentation with signal timing and readiness interpretation guide
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/wellness](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/wellness)
- **Requirements Verified:** Distinguish morning readiness from end-of-day recovery accounting

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`1c54260`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/1c54260c89d3ea8b64a57b228bdeb0c2af43401d))

- [`src/biosystems/wellness/cache.py#L13-L25`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/1c54260c89d3ea8b64a57b228bdeb0c2af43401d/src/biosystems/wellness/cache.py#L13-L25)
- [`src/biosystems/wellness/cache.py#L388-L435`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/1c54260c89d3ea8b64a57b228bdeb0c2af43401d/src/biosystems/wellness/cache.py#L388-L435)
- [`src/biosystems/wellness/cache.py#L460`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/1c54260c89d3ea8b64a57b228bdeb0c2af43401d/src/biosystems/wellness/cache.py#L460)
- [`src/biosystems/wellness/cache.py#L463-L468`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/1c54260c89d3ea8b64a57b228bdeb0c2af43401d/src/biosystems/wellness/cache.py#L463-L468)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`compute_wellness_context`** (L13-L25): FAIL -- WARNING: No tests import or call `compute_wellness_context`

**Coverage summary:** 0/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Found 1 error in 1 file (checked 1 source file)

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Add gar_overnight classification using only sleep-measured s... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | Explicitly flag daily-average signals (Body Battery, Stress)... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | Update documentation with signal timing and readiness interp... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 4 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 4 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Add dual-signal wellness scoring
