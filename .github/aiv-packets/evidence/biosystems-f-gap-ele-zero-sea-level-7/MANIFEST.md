# AIV Evidence Manifest — biosystems-f-gap-ele-zero-sea-level-7

Finding: F-gap-ele-zero-sea-level-7 (medium)
Cited baseline SHA: 89908ccd06c425d1199606fb6feb30e0cd7db2ad
HEAD SHA: 11e8cb8 (docs(aiv): add complete A-F evidence)
Fix commits: 17c156f (gap.py), f1aef32 (metrics.py)
Generated: 2026-06-21

| Path | sha256 | Claim proved | Cited baseline ref | AIV class |
|---|---|---|---|---|
| baseline_red.txt | c72ec40e7a1df224e2216b2a92ec753cbf5fb5e0724c2f27935809c5bb83ac2e | BUG-1/BUG-2 defect exists at 89908ccd: 5 tests FAIL (P2/BUG-1 quality gate rejects all-ele=0; BUG-2 run_metrics returns gap_min_per_km=None) | 89908ccd | A + D |
| head_green.txt | 41bb05e320730284697d189feb6a455a2aa7224b698da1b07c386237c0329310 | Defect gone at HEAD: 116 passed, 0 failed; P1/P2/P3/P4 all pass | 89908ccd (diff base) | A + D |
| source_diff.patch | d28c5bc5b78b98913f37dc63d8b3f019f6ec3ed309012b42d9330c2e37ac15d8 | Surgical two-line fix: gap.py:224 removes .replace(0,np.nan); metrics.py:317 removes .replace(0,np.nan) | 89908ccd → 11e8cb8 | D + B |

## Adversarial probe result (independent assessor, 2026-06-21)
All 5 property tests directly exercise the changed lines with no mocks/patches/stubs.
None can pass without the fix in place. Independent verdict: CONFIRMED.
Residual `replace(0, np.nan)` at metrics.py:308 is cadence (intentional; 0-cadence IS a sentinel).

## Class C negative search
Searched: `grep -n "replace(0, np.nan)" src/biosystems/physics/gap.py src/biosystems/physics/metrics.py`
Result: match only at metrics.py:308 (cadence — orthogonal). NOT present at gap.py:224 or metrics.py:317.
Scope searched: src/biosystems/physics/gap.py, src/biosystems/physics/metrics.py (the two fix sites).

## Full suite at HEAD
277 passed, 1 skipped (0 failed) — all existing tests stay green.
