# Publication Readiness Checklist

Target: `reports/01_longitudinal_study.md`

---

## Publication Viability Assessment

### Can it be published?

Yes, but only at the **preprint or case report tier.**

SportRxiv or arXiv will accept it after P0 fixes. A peer-reviewed case report (IJSPP, JSS) is possible but reviewers will request revisions around statistical framing. It will **not** pass desk review at MSSE, JAP, or any top-tier exercise physiology journal — N=1 without randomization, no lab-grade instrumentation validation, and two data points driving the primary claim are disqualifying regardless of writing quality.

### Would it do well?

**Depends on framing.**

The software pipeline is the strongest part. A paper framed as *"reproducible, open-source methodology for N=1 running performance analysis"* with the physiological results as a demonstration case lands well in quantified self / sports analytics / open science communities. That framing fits arXiv (cs.LG or q-bio) or a methods journal better than a physiology journal.

### Specific weaknesses a reviewer will flag

1. **18% EF improvement rests on two sessions.** EF has ±5% natural day-to-day variability. An 18% change over 103 days is meaningful — but without showing the noise floor, the argument isn't defensible. Need test-retest reliability data or within-subject CV.

2. **Confounding is uncontrolled.** Cadence increased, but so did fitness, heat adaptation, and 103 days of training volume. The cadence intervention cannot be isolated as the cause. The paper acknowledges this but doesn't quantify it.

3. **Week 23 (19.78% decoupling) is a single data point** used as the before/after thermal benchmark. One session in extreme heat is not a controlled stress test.

4. **No comparison to cadence intervention literature.** Heiderscheit (2011), Adams (2018) and others have RCTs on cadence modification. A case study that doesn't position against those reads as uninformed to a reviewer.

### Realistic outcome if published now

SportRxiv + open-source repo link: **a few hundred reads** from the running/quantified self community, some GitHub stars, occasional citation by hobbyist researchers. The code repo will likely get more attention than the paper itself.

### The one thing that would genuinely raise the ceiling

**Validation across more subjects.** Even 5–10 runners using the same pipeline and showing consistent EF response to cadence intervention transforms this from a demonstration into a finding. The paper's real current value is as the **protocol paper** that enables that follow-on study — and should probably be framed that way explicitly.

---

## P0 — Factual blockers (must resolve before any publication)

- [ ] **Temperature inconsistency**: Abstract/conclusion say final RPE 10 retest was at **36°C**; Phase IV "Confirmation" table (Week 35) says **27°C**; README header table says "Final (W32) @ 36°C". Determine the correct session (W32 or W35), the correct temperature, and the correct EF value. Update all three locations to agree.

- [ ] **Appendix A code**: `pace_min_per_km=(9.0, 9.4)` with `bpm=(160, 186)` is internally inconsistent (threshold-range HR with walking pace). Fix to match the corrected value in `data/sample/README.md`: `(4.5, 6.0)`.

---

## P1 — Required for journal submission

- [x] **Ethics / IRB statement**: Added to Declarations section — self-experimentation, Declaration of Helsinki, no IRB required.

- [x] **Conflict of interest statement**: Added to Declarations section.

- [x] **Funding statement**: Added to Declarations section.

- [x] **Data availability statement**: Concrete repo URL + `data/real_weekly_data.json` in both Declarations and Appendix B; raw .fit privacy note added.

- [ ] **Manuscript format**: Convert to double-spaced, line-numbered format with structured abstract (Background / Purpose / Methods / Results / Conclusions) and word count. Required by all target journals. **Blocked on P3 venue decision.**

- [x] **Inter-session variability**: CV = 8.0% across N=12 high-intensity sessions (HR≥178 bpm). +17% improvement = 2.1× CV. Added to Section 2.4 with a priori selection statement.

---

## P2 — Strengthens credibility

- [x] **Resolve RPE 10 session count**: N=12 high-intensity sessions (HR≥178, dist≥3km) identified across full tracking period. W17 and W32 documented as a priori selections in Section 2.4.

- [x] **Temperature verification**: Open-Meteo historical archive queried directly (Lawton OK). W23 crucible confirmed 32.3°C. W32 retest confirmed ~28°C run-time (daily max 32°C). "36°C" figure removed from paper; sourced temperatures added with citation.

- [x] **Section 2.1 EF formula**: Updated to `(total_distance_m / total_time_s) / mean_hr_bpm` with explicit reference to Run-Only Filter and §2.2.

- [x] **Cadence progression table (Phase III)**: Footnote added clarifying session-level means from Garmin FIT cadence stream; weekly mean cadence not retained in pipeline history.

---

## P3 — Target venue decision (unblocks formatting)

- [ ] Decide on submission target before doing manuscript formatting:
  - **SportRxiv preprint** — lowest friction, appropriate for software-methods paper; ready after P0 fixes + ethics/COI/funding statements (~1–2 days)
  - **IJSPP / JSS case report** — peer-reviewed, ~3–6 months; requires full P1 items + cover letter
  - **arXiv (cs.LG or q-bio)** — appropriate if framing is the software pipeline as the primary contribution

---

---

## Section-by-Section Review Findings (2026-03-30)

Each item below was identified during a full read-through of `reports/01_longitudinal_study.md`. Some may require investigation in the Holistic Performance Enhancement repo (`/Volumes/Totallynotaharddrive/Holistic-Performance-Enhancement/`) to resolve. Each item is tagged with its section, priority, and whether external investigation is needed.

### High Priority

- [x] **[§3 Phase I + §4.1] Cadence reference point inconsistency**: **RESOLVED.** Forensic investigation via Strava stream analysis with Cultivation-aligned Run-Only Filter (cadence ≥140 spm, pace <9.5 min/km) established: Phase I W17 RPE10 baseline = 164.4 spm (verified against original audit artifact). W32 RPE10 retest = 170.1 spm (verified, N=1,900 samples, SD=3.6, median=170.0). The Phase III table was fabricated (claimed 158→165 progression) — actual weekly means were flat at 157–162. Replaced with verified Strava-sourced weekly data. Discussion cadence claim updated to +5.7 spm (164.4→170.1).

- [x] **[§4.1] +10 spm claim uses inconsistent reference point**: **RESOLVED.** Updated to "+5.7 spm cadence increase (164.4 → 170.1 spm at RPE 10)" using consistent RPE10-to-RPE10 comparison. Phase III table now shows actual weekly means instead of fabricated progression. W35 restored as Phase V durability consolidation (164.5 spm sustained for 66 min).

- [x] **[References] Only 4 references — insufficient for any journal**: **RESOLVED.** Expanded to 11 references: added Heiderscheit (2011) cadence RCT, Schubert (2014) cadence systematic review, Adams (2018) cadence intervention outcomes, Allen & Coggan (2010) TSS/PMC, Zinner (2019) N=1 methodology framework, Drust (2005) within-subject CV, Open-Meteo API citation.

- [x] **[§2.3] "Morning sessions" control variable contradicts retest data**: **RESOLVED.** Removed false "time of day controlled" claim. Replaced with "Uncontrolled Variables" noting time of day varied. Added as limitation #5.

### Medium Priority

- [x] **[§3 Phase II] W23 Crucible table is incomplete**: **RESOLVED.** Added pace (4:59/km), HR (180.4), EF (0.01851), and cadence (165.4 spm) from W17-W23 audit. Removed vague "Perceived Effort: Maximal."

- [x] **[§1.1] "Plateau" claim never demonstrated**: **RESOLVED.** Replaced with data-backed pre-study trajectory table (25 high-effort sessions from Strava) showing escalating HR for marginal pace gains — establishing efficiency limiter hypothesis with verifiable data.

- [x] **[§2.5] Post-study pipeline changes need validation table or removal**: **RESOLVED.** Rewrote §2.5 with specific validation notes: decoupling <0.3pp difference on recomputation, walk detection thresholds now aligned between Cultivation and biosystems pipelines, W32 cadence verified at 170.1 spm under both pipelines.

- [x] **[§4.2] "Thermal regulation via biomechanics" mechanism is unsupported**: **RESOLVED.** Reframed to "consistent with systemic adaptation... though the specific mechanism cannot be isolated in this design."

- [x] **[§4.4] Protocol compliance not acknowledged as a limitation**: **RESOLVED.** Added as limitation #4: "Protocol compliance unverified — NME drill frequency and volume inferred from filename artifacts, not verified session logs."

### Low Priority

- [x] **[Abstract] Needs structured format for journal submission**: **RESOLVED.** Structured as Background/Purpose/Methods/Results/Conclusions. "Key Innovation" callout removed. Cadence corrected to +5.7 spm. All quantitative claims match paper body.

- [x] **[§5 Conclusions] "Strategic Implication" paragraph is marketing language**: **RESOLVED.** Replaced with factual replication statement pointing to public pipeline and data.

- [x] **[Appendix A] `run_metrics()` is undefined**: **RESOLVED.** Added inline comment describing function behavior and filter thresholds.

- [x] **[Appendix B vs Declarations] Duplication**: **RESOLVED.** Appendix B removed. All data availability information consolidated into Declarations section including privacy sanitization details.

- [ ] **[§2.1] Garmin sampling rate claim**: States "1 Hz" — may need to confirm recording mode.

---

## Done (fixed in PR #3)

- [x] EF formula in Section 2.2 code block: `speed.mean()` → `dist.sum()/dt.sum()/hr.mean()`
- [x] EF formula in README Run-Only Filter snippet
- [x] `data/sample/README.md`: `ZoneConfiguration` → `ZoneConfig`+`HeartRateZone`; `pace_min_per_km` corrected
- [x] WELLNESS.md threshold descriptions match `cache.py` implementation
- [x] Placeholder `yourusername` URLs removed from `pyproject.toml` and `CITATION.cff`
