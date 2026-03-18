# AIV Evidence File (v1.0)

**File:** `src/biosystems/cli.py`
**Commit:** `f300317`
**Previous:** `3c87dbc`
**Generated:** 2026-03-18T05:14:15Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/cli.py"
  classification_rationale: "Feature expansion"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T05:14:15Z"
```

## Claim(s)

1. Add strava, backfill, and trend commands to CLI; add supporting OAuth and reproduction tools
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/advanced-analytics)
- **Requirements Verified:** Operationalize the full analytics pipeline

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`f300317`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/f300317d38dfeb4c03cf6fbd95da57853c6138df))

- [`src/biosystems/cli.py#L11`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L11)
- [`src/biosystems/cli.py#L14-L15`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L14-L15)
- [`src/biosystems/cli.py#L180`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L180)
- [`src/biosystems/cli.py#L183`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L183)
- [`src/biosystems/cli.py#L190`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L190)
- [`src/biosystems/cli.py#L198`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L198)
- [`src/biosystems/cli.py#L205-L244`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L205-L244)
- [`src/biosystems/cli.py#L247-L503`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L247-L503)
- [`src/biosystems/cli.py#L505-L671`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L505-L671)
- [`src/biosystems/cli.py#L674-L677`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L674-L677)
- [`src/biosystems/cli.py#L679-L683`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L679-L683)
- [`src/biosystems/cli.py#L685-L700`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f300317d38dfeb4c03cf6fbd95da57853c6138df/src/biosystems/cli.py#L685-L700)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** Operational CLI wrapper; integration tests require Strava API mocking which is out of scope for this commit.


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** Operational CLI wrapper; integration tests require Strava API mocking which is out of scope for this commit.
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Update CLI for advanced analytics
