# AIV Evidence File (v1.0)

**File:** `tests/test_sanitize_gps_fix.py`
**Commit:** `07c0000`
**Generated:** 2026-03-18T03:16:39Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_sanitize_gps_fix.py"
  classification_rationale: "New test"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T03:16:39Z"
```

## Claim(s)

1. Verifies sanitize_dataframe handles short activities
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/openclaw-integration](https://github.com/ImmortalDemonGod/bio-systems-engineering/issues/openclaw-integration)
- **Requirements Verified:** Validate GPS sanitization safety

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`07c0000`](https://github.com/ImmortalDemonGod/bio-systems-engineering/tree/07c00006b8733c929f731e58bb4158d19fcec540))

- [`tests/test_sanitize_gps_fix.py#L1-L21`](https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/07c00006b8733c929f731e58bb4158d19fcec540/tests/test_sanitize_gps_fix.py#L1-L21)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`test_sanitize_dataframe_short_activity`** (L1-L21): FAIL -- WARNING: No tests import or call `test_sanitize_dataframe_short_activity`

**Coverage summary:** 0/1 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 50 error(s)
- **mypy:** Found 3 errors in 1 file (checked 1 source file)

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | Verifies sanitize_dataframe handles short activities | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Add GPS sanitization fix test
