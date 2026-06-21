# Bug Catalog — `src/biosystems/physics/gap.py` + `src/biosystems/physics/metrics.py`

Finding: F-gap-ele-zero-sea-level-7 (medium)  
Audit source (Class E):
https://github.com/ImmortalDemonGod/bio-systems-engineering/blob/89908ccd06c425d1199606fb6feb30e0cd7db2ad/audit/02-static-audit.md#L92

## Code summary

**Public interface**
- `check_elevation_quality(df, ele_col, dist_col, clamp_fraction_threshold)` → `(bool, str)`  
  Quality gate: decides whether elevation is reliable enough for GAP.
- `calculate_gap_from_dataframe(df, pace_col, ele_col, dist_col)` → `pd.Series`  
  Computation path: applies Minetti adjustment per segment.
- `calculate_average_gap(df, pace_col, ele_col, dist_col, dt_col)` → `float`  
  Time-weighted average GAP for whole activity.
- `minetti_energy_cost(grade_percent)` → `float`  
  Normalized energy multiplier from Minetti 2002 polynomial; 1.0 at flat grade.
- `calculate_gap_segment(pace_sec_km, grade_percent)` → `float`  
  Per-segment GAP: `pace / minetti_energy_cost(grade)`.
- `run_metrics(df, zone_config)` → `PhysiologicalMetrics` (in `metrics.py`)  
  Integration orchestrator; conditionally calls `check_elevation_quality` then `calculate_average_gap`.

**Load-bearing comments**
- `gap.py:68–71`: Clamping note — ±45% domain guard for Minetti polynomial; GPS altimeter glitches can produce grades far beyond real terrain; clamping is mandatory.
- `gap.py:162–163`: Smoothing note — raw GPS elevation has ±5–10 m accuracy; 5-point rolling mean suppresses jitter before differencing.

**IO boundaries**
- Both `check_elevation_quality` and `calculate_gap_from_dataframe` consume a caller-supplied DataFrame; no filesystem or network IO.
- `run_metrics` calls both; it is the integration boundary between production data ingestion and GAP computation.

**Branching points**
- `gap.py:224`: `replace(0, np.nan).dropna()` — zero treated as missing before length check.
- `gap.py:225`: `if len(ele_series) < 10` — gate on effective non-zero data length.
- `gap.py:175`: `if i == 0 or pd.isna(ele_val) or dist_val == 0` — computation path treats `ele_val==0` as valid (no special case).
- `metrics.py:317-318`: `replace(0, np.nan)` + `if not ele_series.isna().all()` — second gate, same anti-pattern.

**Magic-string / type contracts**
- Return value of `check_elevation_quality`: `(True, "ok")` on success; `(False, <reason>)` on failure. No enum — plain string.
- `minetti_energy_cost` returns a dimensionless multiplier (`ec / 3.6`); the raw polynomial constant 3.6 encodes J/kg/m from Minetti 2002.

**Existing tests**
- `TestElevationQuality.test_insufficient_data` — 2-row DataFrame → expects False + "insufficient elevation data"; does NOT test the all-zero case.
- `TestMinettiEnergyCost.test_flat_ground_baseline` — tests `minetti_energy_cost(0.0) ≈ 1.0` within 1%; covers P4 incidentally but not framed as a reference-value property.
- No test for all-zero elevation going through the full path.

---

## Bug catalog

### BUG-1 — `check_elevation_quality` wrongly rejects valid sea-level (all-ele=0) activities

**The failure mode**: `check_elevation_quality` returns `(False, "insufficient elevation data points")` for
a DataFrame where every elevation reading is 0 m (valid sea-level). A flat coastal run is silently
rejected as having "missing" elevation.

**Blast radius**: Every activity recorded at or near sea level (elevation ≈ 0 m) has its GAP silently
suppressed. The athlete sees `gap_min_per_km=None`, indistinguishable from a GPS dropout. Any training
analysis pipeline that gates on GAP availability is blind to sea-level runs.

**Why it's plausible**: Line 224 (`replace(0, np.nan).dropna()`) was written to exclude rows where the
GPS receiver lost satellite lock and output 0 as a sentinel — but 0 m is also a legitimate elevation for
sea-level terrain. The code conflates two physically distinct cases: a genuine missing reading (GPS
dropout) and a genuine 0 m terrain reading.

**Root inconsistency**: The COMPUTATION path (`gap.py:165`, `rolling().mean()`) performs NO such
replacement — it treats 0 m elevation as valid flat terrain and computes grade = 0. The QUALITY GATE
(`gap.py:224`) applies the opposite logic. They must agree.

**Test type**: Captured bug / contract pin (P2 — ELE=0 VALIDITY)  
**Oracle**: `check_elevation_quality(df_all_zero_ele) == (True, ...)`  
**Layer**: UNIT — supply the all-zero DataFrame explicitly; do not depend on production ingestion.  
**Status after writing test**: **RED** (test fails against current code)

---

### BUG-2 — `run_metrics` integration gate silently skips GAP for all-zero elevation

**The failure mode**: `metrics.py:317-318` applies the same `replace(0, np.nan)` anti-pattern as a
guard before calling `check_elevation_quality`. Even if BUG-1 were fixed in isolation, `run_metrics`
would still not compute GAP for an all-zero-elevation DataFrame because it never reaches the
`check_elevation_quality` call.

**Blast radius**: Same as BUG-1 — sea-level activities never get a `gap_min_per_km` value through the
integration path. Two separate code sites must both be fixed.

**Why it's plausible**: The `replace(0, np.nan)` pattern was copied from the same mental model (0 =
missing). The condition `if not ele_series.isna().all()` is intended to skip GAP when there is NO
elevation data, but over-fires when all elevation is legitimately 0.

**Test type**: Decision table / contract pin (P2 — ELE=0 VALIDITY, integration layer)  
**Oracle**: `run_metrics(df_all_zero_ele, zone_cfg).gap_min_per_km is not None`  
**Layer**: INTEGRATION — `run_metrics` is the production caller that produces the GAP decision.  
**Status after writing test**: **RED** (test fails against current code)

---

### BUG-3 (characterized, not yet red) — Inconsistency between quality gate and computation path is masking a correct flat-grade result

**The failure mode**: The COMPUTATION path correctly treats all-ele=0 as flat terrain (grade = 0%,
Minetti multiplier = 1.0, GAP = raw pace). This is confirmed by calling `calculate_average_gap`
directly, bypassing the quality gate, on an all-zero elevation DataFrame — it returns exactly the mean
raw pace. This is the CORRECT behavior. The quality gate (BUG-1) and integration gate (BUG-2) are
what suppress it.

**Blast radius**: Indirect — the correct computation is hidden behind two broken gates.

**Why it's plausible**: Demonstrates that the computation path is already correct; both fixes are pure
gate fixes, not algorithmic changes.

**Test type**: Invariant (P1 — FLAT-GRADE IDENTITY)  
**Oracle**: `calculate_average_gap(df_all_zero_ele) ≈ mean_raw_pace` within 1%  
**Layer**: UNIT — call `calculate_average_gap` directly (bypasses quality gate).  
**Status after writing test**: **GREEN** (computation path is already correct; pins this behavior)

---

### BUG-4 — Minetti polynomial positivity in valid grade range

**The failure mode (theoretical)**: If the polynomial coefficients were miscopied, `minetti_energy_cost`
could return ≤ 0 for some grades in [-40, +40], causing `calculate_gap_segment` to divide by zero or
return a negative GAP.

**Why it's plausible**: The polynomial is a 5th-degree fit transcribed from a paper; coefficient-copy
errors are a real source of subtle bugs.

**Test type**: Property (P3 — MINETTI POSITIVITY)  
**Oracle**: `minetti_energy_cost(g) > 0` for all g in range(-40, 41)  
**Layer**: UNIT  
**Status after writing test**: **GREEN** (current coefficients are correct; pins this)

---

### BUG-5 — Minetti reference constant mismatch with Minetti 2002

**The failure mode (theoretical)**: The normalization constant in `minetti_energy_cost` (currently 3.6)
could diverge from the published value. If someone changed the divisor without updating the
polynomial, all GAP values would be systematically wrong.

**Test type**: Captured bug / reference pin (P4 — REFERENCE VALUE)  
**Oracle**: `minetti_energy_cost(0.0) * 3.6 ≈ 3.6 J/kg/m` within 5%  
**Layer**: UNIT  
**Status after writing test**: **GREEN** (current constant matches; pins this)

---

## Skipped (negative space)

| Bug / scenario | Reason skipped |
|---|---|
| GPS-dropout case (partial NaN in ele column) | Out of scope for this finding; existing tests cover `test_missing_values`. The fix must NOT break the NaN-dropout detection for rows that are genuinely missing. |
| `replace(0, np.nan)` in cadence calculation (`metrics.py:308`) | Same pattern but cadence 0 is plausibly sentinel (watch not recording); not elevation; different contract. |
| Minetti outside ±45% (clamped domain) | Clamping guard (`gap.py:73`) is explicit and commented; behavior beyond ±45% is intentionally bounded. |
| Floating-point exactness of Minetti at non-zero grades | Covered by existing `TestMinettiEnergyCost` suite; not part of this finding. |
| `calculate_gap_from_dataframe` with mixed zero/nonzero elevation | Deferred; finding scope is the all-zero case. Mixed case works differently and the fix must not break it. |
| `check_elevation_quality` clamp-fraction threshold correctness | Out of scope; finding is about the zero-elevation gate, not the downstream clamp check. |

---

## Self-critique

### BUG-1 test (P2 unit)
- **What catalog bug does this catch?** BUG-1 — quality gate incorrectly returns False for all-zero elevation.
- **Would this pass for wrong-but-stable output?** No — the assertion checks `is_ok is True`, which fails today.
- **Would this fail under a behavior-preserving refactor?** No — asserts on the public contract `(bool, str)`, not on internal implementation.

### BUG-2 test (P2 integration)
- **What catalog bug does this catch?** BUG-2 — `run_metrics` integration gate skips GAP for all-zero elevation.
- **Would this pass for wrong-but-stable output?** No — `gap_min_per_km is not None` fails today and would fail for any wrong-but-None output.
- **Would this fail under a behavior-preserving refactor?** No — asserts on the public `PhysiologicalMetrics` output, not on internal call order.

### BUG-3 test (P1)
- **What catalog bug does this catch?** Characterizes the correct behavior of the computation path to prevent regression during the fix.
- **Would this pass for wrong-but-stable output?** No — asserts numeric proximity (within 1%) to the raw pace, not just "not NaN."
- **Would this fail under a behavior-preserving refactor?** No — asserts on the mathematical identity, not on internal rolling-window implementation.

### BUG-4 test (P3)
- **What catalog bug does this catch?** Polynomial positivity invariant — pins that Minetti coefficients are correct across full valid range.
- **Would this pass for wrong-but-stable output?** Only if miscopied coefficients happened to still be positive — true but the test documents the constraint.
- **Would this fail under a behavior-preserving refactor?** No — asserts on mathematical property, not on internal code structure.

### BUG-5 test (P4)
- **What catalog bug does this catch?** Reference constant — pins that normalization by 3.6 matches Minetti 2002.
- **Would this pass for wrong-but-stable output?** No — 5% tolerance around 3.6 J/kg/m is the oracle.
- **Would this fail under a behavior-preserving refactor?** No — asserts on the published physical constant, not on code shape.

---

## Post-writing evaluation (to be filled after tests are run)

| Metric | Count |
|---|---|
| Bugs caught (test RED first run, fix needed) | TBD |
| Bugs characterized (test GREEN first run) | TBD |
| Bugs discovered during writing not in original catalog | TBD |
