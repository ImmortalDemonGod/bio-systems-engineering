# AIV Evidence File (v1.0)

**File:** `src/biosystems/cli.py`
**Commit:** `f728357`
**Previous:** `9b0a008`
**Generated:** 2026-04-04T23:25:49Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/biosystems/cli.py"
  classification_rationale: "import reordering and dead code removal affects module load order"
  classified_by: "Miguel Ingram"
  classified_at: "2026-04-04T23:25:49Z"
```

## Claim(s)

1. ruff check src/ tests/ now passes with zero errors
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering](https://github.com/ImmortalDemonGod/bio-systems-engineering)
- **Requirements Verified:** CI ruff check must pass as a blocking gate

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`f728357`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/f7283571ac7c61961bbce3d62ccc641f547ca54e))

- [`src/biosystems/cli.py#L15-L20`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L15-L20)
- [`src/biosystems/cli.py#L394`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L394)
- [`src/biosystems/cli.py#L510`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L510)
- [`src/biosystems/cli.py#L729-L730`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L729-L730)
- [`src/biosystems/cli.py#L1070`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1070)
- [`src/biosystems/cli.py#L1077`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1077)
- [`src/biosystems/cli.py#L1137`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1137)
- [`src/biosystems/cli.py#L1167-L1168`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1167-L1168)
- [`src/biosystems/cli.py#L1181-L1184`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1181-L1184)
- [`src/biosystems/cli.py#L1236`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1236)
- [`src/biosystems/cli.py#L1238-L1241`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1238-L1241)
- [`src/biosystems/cli.py#L1243`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1243)
- [`src/biosystems/cli.py#L1354`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1354)
- [`src/biosystems/cli.py#L1356`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/f7283571ac7c61961bbce3d62ccc641f547ca54e/src/biosystems/cli.py#L1356)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`strava`** (L15-L20): FAIL -- WARNING: No tests import or call `strava`
- **`backfill_efforts`** (L394): FAIL -- WARNING: No tests import or call `backfill_efforts`
- **`summary`** (L510): FAIL -- WARNING: No tests import or call `summary`
- **`trend`** (L729-L730): FAIL -- WARNING: No tests import or call `trend`
- **`wellness_show`** (L1070): FAIL -- WARNING: No tests import or call `wellness_show`
- **`_row`** (L1077): FAIL -- WARNING: No tests import or call `_row`
- **`_delta`** (L1137): FAIL -- WARNING: No tests import or call `_delta`
- **`wellness_analyze`** (L1167-L1168): FAIL -- WARNING: No tests import or call `wellness_analyze`
- **`wellness_trends`** (L1181-L1184): FAIL -- WARNING: No tests import or call `wellness_trends`

**Coverage summary:** 0/9 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** All checks passed
- **mypy:** Success: no issues found in 1 source file

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | ruff check src/ tests/ now passes with zero errors | tooling | Class A: ruff: clean | PASS VERIFIED |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 1 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/9 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Move imports above dotenv.load_dotenv(), remove unused first_ever/moving_s/n/total_days, convert lambdas to defs
