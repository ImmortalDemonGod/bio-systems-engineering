# AIV Evidence File (v1.0)

**File:** `pyproject.toml`
**Commit:** `a7bbe84`
**Previous:** `e7d8eba`
**Generated:** 2026-03-22T03:05:41Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "pyproject.toml"
  classification_rationale: "Trivial placeholder substitution in project metadata — zero runtime impact"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-22T03:05:41Z"
```

## Claim(s)

1. pyproject.toml [project.urls] all four entries point to ImmortalDemonGod/bio-systems-engineering
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** Package metadata must reference the real repository for PyPI and pip install discovery

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`a7bbe84`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/a7bbe8488506442610accfb5625f9a99a777fcfd))

- [`pyproject.toml#L52-L55`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/a7bbe8488506442610accfb5625f9a99a777fcfd/pyproject.toml#L52-L55)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** URL-only change in metadata table, no installable logic affected


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** URL-only change in metadata table, no installable logic affected
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Replace yourusername with ImmortalDemonGod in all four pyproject.toml project URLs
