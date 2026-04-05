# AIV Verification Packet (v2.2)

## Identification

| Field | Value |
|-------|-------|
| **Repository** | github.com/ImmortalDemonGod/bio-systems-engineering |
| **Change ID** | systematic-fixes |
| **Commits** | `6e294c3`, `0f705ab`, `a2268bb` |
| **Head SHA** | `09de5cc` |
| **Base SHA** | `beb4bae` |
| **Created** | 2026-03-18T00:35:10Z |

## Classification

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: component
  classification_rationale: "Documentation and code quality changes with component-level blast radius"
  classified_by: "Miguel Ingram"
  classified_at: "2026-03-18T00:35:10Z"
```

## Claims

1. HeartRateZone validates bpm=(0, 145) without error for Z1 Recovery zone
2. Validation rejects negative lower bounds but allows zero as sentinel value
3. Import statements reordered for consistency
4. No existing tests were modified or deleted during this change.
5. calculate_efficiency_factor excludes is_walk==True rows before computing avg_speed/avg_hr
6. calculate_decoupling excludes is_walk==True rows before midpoint split
7. EF calculation accuracy improved by filtering out walking segments with elevated post-run HR
8. Both functions add dropna(subset=['hr']) to handle missing HR data robustly
9. Remove duplicate test_bpm_validation_negative function definition
10. Fix whitespace and import formatting in test file

---

## Evidence References

| # | Evidence File | Commit SHA | Classes |
|---|---------------|------------|---------|
| 1 | EVIDENCE_BIOSYSTEMS_MODELS.md | `6e294c3` | A, B, E |
| 2 | EVIDENCE_BIOSYSTEMS_PHYSICS_METRICS.md | `0f705ab` | A, B, C, E, F |
| 3 | EVIDENCE_TESTS_TEST_MODELS.md | `a2268bb` | A, B, E |

### Class E (Intent Alignment)

- **Requirement:** Systematic pipeline fixes must restore correct EF calculations and zone validation per audit findings

### Class B (Referential Evidence)

**Scope Inventory** (from 99 file references across evidence files)

- `src/biosystems/models.py#L14-L15`
- `src/biosystems/models.py#L20`
- `src/biosystems/models.py#L30`
- `src/biosystems/models.py#L32-L35`
- `src/biosystems/models.py#L37`
- `src/biosystems/models.py#L41-L42`
- `src/biosystems/models.py#L44-L45`
- `src/biosystems/models.py#L47`
- `src/biosystems/models.py#L59`
- `src/biosystems/models.py#L71`
- `src/biosystems/models.py#L74-L77`
- `src/biosystems/models.py#L81`
- `src/biosystems/models.py#L89`
- `src/biosystems/models.py#L92`
- `src/biosystems/models.py#L108-L114`
- `src/biosystems/models.py#L120`
- `src/biosystems/models.py#L122`
- `src/biosystems/models.py#L146`
- `src/biosystems/models.py#L154-L158`
- `src/biosystems/models.py#L164`
- `src/biosystems/models.py#L172`
- `src/biosystems/models.py#L174`
- `src/biosystems/models.py#L188`
- `src/biosystems/models.py#L193`
- `src/biosystems/models.py#L199`
- `src/biosystems/models.py#L219`
- `src/biosystems/models.py#L226-L227`
- `src/biosystems/models.py#L232`
- `src/biosystems/physics/metrics.py#L13`
- `src/biosystems/physics/metrics.py#L18`
- `src/biosystems/physics/metrics.py#L22`
- `src/biosystems/physics/metrics.py#L30`
- `src/biosystems/physics/metrics.py#L35`
- `src/biosystems/physics/metrics.py#L42`
- `src/biosystems/physics/metrics.py#L48-L49`
- `src/biosystems/physics/metrics.py#L52`
- `src/biosystems/physics/metrics.py#L61`
- `src/biosystems/physics/metrics.py#L73-L74`
- `src/biosystems/physics/metrics.py#L82`
- `src/biosystems/physics/metrics.py#L89-L90`
- `src/biosystems/physics/metrics.py#L98`
- `src/biosystems/physics/metrics.py#L101-L102`
- `src/biosystems/physics/metrics.py#L106`
- `src/biosystems/physics/metrics.py#L108`
- `src/biosystems/physics/metrics.py#L112`
- `src/biosystems/physics/metrics.py#L115`
- `src/biosystems/physics/metrics.py#L117`
- `src/biosystems/physics/metrics.py#L124`
- `src/biosystems/physics/metrics.py#L130-L136`
- `src/biosystems/physics/metrics.py#L139-L141`
- `src/biosystems/physics/metrics.py#L143-L147`
- `src/biosystems/physics/metrics.py#L149-L150`
- `src/biosystems/physics/metrics.py#L153`
- `src/biosystems/physics/metrics.py#L156`
- `src/biosystems/physics/metrics.py#L159`
- `src/biosystems/physics/metrics.py#L164`
- `src/biosystems/physics/metrics.py#L171`
- `src/biosystems/physics/metrics.py#L177-L182`
- `src/biosystems/physics/metrics.py#L185-L187`
- `src/biosystems/physics/metrics.py#L189-L190`
- `src/biosystems/physics/metrics.py#L195`
- `src/biosystems/physics/metrics.py#L198-L200`
- `src/biosystems/physics/metrics.py#L203-L205`
- `src/biosystems/physics/metrics.py#L207`
- `src/biosystems/physics/metrics.py#L210-L211`
- `src/biosystems/physics/metrics.py#L214`
- `src/biosystems/physics/metrics.py#L217`
- `src/biosystems/physics/metrics.py#L220`
- `src/biosystems/physics/metrics.py#L227`
- `src/biosystems/physics/metrics.py#L233-L237`
- `src/biosystems/physics/metrics.py#L240-L241`
- `src/biosystems/physics/metrics.py#L245`
- `src/biosystems/physics/metrics.py#L249`
- `src/biosystems/physics/metrics.py#L255`
- `src/biosystems/physics/metrics.py#L264`
- `src/biosystems/physics/metrics.py#L269`
- `src/biosystems/physics/metrics.py#L277-L279`
- `src/biosystems/physics/metrics.py#L282`
- `src/biosystems/physics/metrics.py#L287`
- `src/biosystems/physics/metrics.py#L290`
- `src/biosystems/physics/metrics.py#L292-L295`
- `src/biosystems/physics/metrics.py#L298-L299`
- `src/biosystems/physics/metrics.py#L302`
- `src/biosystems/physics/metrics.py#L305`
- `src/biosystems/physics/metrics.py#L307`
- `src/biosystems/physics/metrics.py#L311`
- `src/biosystems/physics/metrics.py#L318`
- `src/biosystems/physics/metrics.py#L329`
- `tests/test_models.py#L44-L54`
- `tests/test_models.py#L58`
- `tests/test_models.py#L63-L69`
- `tests/test_models.py#L209-L211`
- `tests/test_models.py#L222-L223`
- `tests/test_models.py#L234-L235`
- `tests/test_models.py#L238-L239`
- `tests/test_models.py#L243`
- `tests/test_models.py#L249-L250`
- `tests/test_models.py#L252-L254`
- `tests/test_models.py#L256-L257`

---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence was collected by `aiv commit` during the change lifecycle.
Packet generated by `aiv close`.

---

## Known Limitations

- Evidence references point to Layer 1 evidence files at specific commit SHAs.
  Use `git show <sha>:.github/aiv-evidence/<file>` to retrieve.

---

## Summary

Change 'systematic-fixes': 3 commit(s) across 3 file(s).
