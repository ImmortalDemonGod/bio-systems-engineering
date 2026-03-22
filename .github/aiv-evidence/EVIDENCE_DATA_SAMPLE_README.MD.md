# AIV Evidence File (v1.0)

**File:** `data/sample/README.md`
**Commit:** `a0fe0ce`
**Generated:** 2026-03-22T03:32:12Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "data/sample/README.md"
  classification_rationale: "ZoneConfiguration was a draft name never shipped; the broken import would immediately fail any user following the sample docs"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-22T03:32:12Z"
```

## Claim(s)

1. data/sample/README.md uses ZoneConfig and HeartRateZone (correct class names) instead of ZoneConfiguration (does not exist)
2. pace_min_per_km updated from (9.0, 9.4) to (4.5, 6.0) to match the athlete pace profile used throughout the project
3. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** Sample documentation must be copy-paste runnable without ImportError

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`a0fe0ce`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/a0fe0cef4d9ff4e18cb48fccc430c98942aefa1f))

- [`data/sample/README.md#L16-L17`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/a0fe0cef4d9ff4e18cb48fccc430c98942aefa1f/data/sample/README.md#L16-L17)
- [`data/sample/README.md#L22-L23`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/a0fe0cef4d9ff4e18cb48fccc430c98942aefa1f/data/sample/README.md#L22-L23)
- [`data/sample/README.md#L26`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/a0fe0cef4d9ff4e18cb48fccc430c98942aefa1f/data/sample/README.md#L26)
- [`data/sample/README.md#L48`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/a0fe0cef4d9ff4e18cb48fccc430c98942aefa1f/data/sample/README.md#L48)
- [`data/sample/README.md#L52-L55`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/a0fe0cef4d9ff4e18cb48fccc430c98942aefa1f/data/sample/README.md#L52-L55)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** Documentation-only change in sample data README, no source code affected


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** Documentation-only change in sample data README, no source code affected
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Replace ZoneConfiguration with ZoneConfig+HeartRateZone and fix pace zone values in data/sample/README.md
