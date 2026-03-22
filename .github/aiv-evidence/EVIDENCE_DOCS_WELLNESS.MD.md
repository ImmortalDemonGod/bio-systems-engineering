# AIV Evidence File (v1.0)

**File:** `docs/WELLNESS.md`
**Commit:** `f6ba567`
**Previous:** `9763666`
**Generated:** 2026-03-22T03:33:27Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "docs/WELLNESS.md"
  classification_rationale: "HRV and RHR were described as sigma-based when code uses absolute deltas; Body Battery fallback was undocumented"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-22T03:33:27Z"
```

## Claim(s)

1. HRV threshold documented as percentage drop (20%/10%) not sigma, matching _HRV_DROP_RED/AMBER constants
2. RHR threshold documented as absolute bpm delta (+8/+5 bpm) not sigma, matching _RHR_SPIKE_RED/AMBER constants
3. Body Battery and Avg Stress rows document both fallback absolute values and calibrated percentile values
4. Calibration section documents exact fallback constants for all signals
5. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** Threshold documentation must match cache.py constants so operators can reason about signal behavior without reading source

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`f6ba567`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/f6ba56790b829765ec29ec9310d6429415116ae5))

- [`docs/WELLNESS.md#L66-L67`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f6ba56790b829765ec29ec9310d6429415116ae5/docs/WELLNESS.md#L66-L67)
- [`docs/WELLNESS.md#L70-L72`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f6ba56790b829765ec29ec9310d6429415116ae5/docs/WELLNESS.md#L70-L72)
- [`docs/WELLNESS.md#L78-L84`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f6ba56790b829765ec29ec9310d6429415116ae5/docs/WELLNESS.md#L78-L84)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** Documentation-only change, no source code affected


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** Documentation-only change, no source code affected
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Fix threshold table and expand Calibration section in docs/WELLNESS.md to match cache.py constants
