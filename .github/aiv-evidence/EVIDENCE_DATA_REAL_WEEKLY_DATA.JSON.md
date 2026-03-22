# AIV Evidence File (v1.0)

**File:** `data/real_weekly_data.json`
**Commit:** `77b4785`
**Generated:** 2026-03-18T05:15:19Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "data/real_weekly_data.json"
  classification_rationale: "Data restoration"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T05:15:19Z"
```

## Claim(s)

1. Restore ground-truth weekly data with corrected means and RPE10 test results
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics)
- **Requirements Verified:** Maintain verified study dataset

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`77b4785`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/77b47853ae29795e55a2dd42537033554e838ff0))

- [`data/real_weekly_data.json#L4`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/77b47853ae29795e55a2dd42537033554e838ff0/data/real_weekly_data.json#L4)
- [`data/real_weekly_data.json#L6-L8`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/77b47853ae29795e55a2dd42537033554e838ff0/data/real_weekly_data.json#L6-L8)
- [`data/real_weekly_data.json#L96`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/77b47853ae29795e55a2dd42537033554e838ff0/data/real_weekly_data.json#L96)
- [`data/real_weekly_data.json#L98-L100`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/77b47853ae29795e55a2dd42537033554e838ff0/data/real_weekly_data.json#L98-L100)

### Class A (Execution Evidence)

**WARNING:** No tests found that directly import or reference the changed file.
This file has no claim-specific execution evidence.

### Code Quality (Linting & Types)

- **ruff:** 12 error(s)
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Restore ground-truth weekly data with corrected means and RP... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), pytest (no claim-specific tests found).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Restore weekly data
