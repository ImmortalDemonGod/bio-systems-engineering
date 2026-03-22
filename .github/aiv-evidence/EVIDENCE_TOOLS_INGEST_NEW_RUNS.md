# AIV Evidence File (v1.0)

**File:** `tools/ingest_new_runs.py`
**Commit:** `b88531e`
**Generated:** 2026-03-18T00:26:00Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tools/ingest_new_runs.py"
  classification_rationale: "New utility tool with dry-run mode - low blast radius, no existing logic modified"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T00:26:00Z"
```

## Claim(s)

1. Script processes .gpx and .fit files from data/raw/ into biosystems pipeline format
2. Walk detection identifies pace > 9.5 min/km OR cadence < 140 spm
3. Regenerates real_weekly_data.json with correct weekly aggregations
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/aiv-protocol](https://github.com/ImmortalDemonGod/aiv-protocol)
- **Requirements Verified:** AIV protocol demonstration for bio-systems-engineering project

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`b88531e`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/b88531e291ef9167c48330354f59e2b7fd9d25a5))

- [`tools/ingest_new_runs.py#L1-L464`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b88531e291ef9167c48330354f59e2b7fd9d25a5/tools/ingest_new_runs.py#L1-L464)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** Tool validated manually via dry-run and full processing test; no unit tests yet


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** Tool validated manually via dry-run and full processing test; no unit tests yet
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Add automated pipeline for processing new running data files
