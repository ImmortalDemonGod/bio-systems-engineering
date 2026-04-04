# AIV Evidence File (v1.0)

**File:** `src/biosystems/cli.py`
**Commit:** `b4571b5`
**Previous:** `cfa8d6d`
**Generated:** 2026-04-04T18:39:19Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/cli.py"
  classification_rationale: "behavioral change to run/walk boundary affecting EF, cadence, and all downstream analytics"
  classified_by: "Miguel Ingram"
  classified_at: "2026-04-04T18:39:19Z"
```

## Claim(s)

1. is_walk now uses cadence<140 OR pace>9.5 matching Cultivation; avg_cadence persisted in history.jsonl for both ingest and backfill-streams paths
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** Walk classification must produce cadence metrics consistent with original Cultivation pipeline analysis; cadence must be queryable from history

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`b4571b5`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/b4571b5fd1657592c80b77d6ad834165ef5450ff))

- [`src/biosystems/cli.py#L264`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L264)
- [`src/biosystems/cli.py#L266`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L266)
- [`src/biosystems/cli.py#L268`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L268)
- [`src/biosystems/cli.py#L336`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L336)
- [`src/biosystems/cli.py#L640`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L640)
- [`src/biosystems/cli.py#L642`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L642)
- [`src/biosystems/cli.py#L644`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L644)
- [`src/biosystems/cli.py#L679`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/b4571b5fd1657592c80b77d6ad834165ef5450ff/src/biosystems/cli.py#L679)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`strava`** (L264): FAIL -- WARNING: No tests import or call `strava`
- **`backfill_streams`** (L266): FAIL -- WARNING: No tests import or call `backfill_streams`

**Coverage summary:** 0/2 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 209 error(s)
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | is_walk now uses cadence<140 OR pace>9.5 matching Cultivatio... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Update is_walk thresholds (cad<140 OR pace>9.5), always apply cadence check even with Strava moving flag, add avg_cadence to history_entry
