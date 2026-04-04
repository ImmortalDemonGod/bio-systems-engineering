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

- [ ] **[References] Only 4 references — insufficient for any journal**: Missing at minimum: Heiderscheit et al. (2011) on cadence modification and running economy (the primary RCT in this space); Adams et al. (2018) or equivalent cadence intervention outcome study; a source validating EF as a performance metric; Open-Meteo citation (now used as a data source); at least one N=1 / single-subject methodology paper to justify the design.

- [ ] **[§2.3] "Morning sessions" control variable contradicts retest data**: Section 2.3 lists "Time of day controlled (morning sessions)" as a control variable. The W32 retest run file is `20250806_030140` UTC = ~22:00 CDT — a night run. This is a direct factual contradiction. Either the control was not maintained for the retest, or "morning sessions" was not an actual control variable. **Requires clarification — may need to remove or reframe this control claim.**

### Medium Priority

- [ ] **[§3 Phase II] W23 Crucible table is incomplete**: The crucible table only shows temperature, decoupling, and perceived effort. Phase I and Phase IV tables show cadence, EF, and pace. A reviewer will expect the same metrics across all phases for direct comparison. EF, pace, and HR for the W23 session should be added if the data exists. **Requires data investigation.**

- [ ] **[§1.1] "Plateau" claim never demonstrated**: The introduction states the athlete plateaued under volume-based training, but no data is presented to show stagnation prior to W17. The paper jumps straight to the baseline without establishing that a plateau existed. Needs either pre-study trend data or reframing to "the athlete sought to address biomechanical inefficiency" without the plateau claim.

- [ ] **[§2.5] Post-study pipeline changes need validation table or removal**: Section 2.5 discloses pipeline algorithm changes post-study but only asserts "do not alter the core findings" without proof. A reviewer will ask for a comparison of old vs. new values on the key sessions (W17 baseline, W23 crucible, W32 retest). Either add a validation table or remove this section and move the disclosure to a footnote.

- [ ] **[§4.2] "Thermal regulation via biomechanics" mechanism is unsupported**: The Discussion concludes the intervention created "systemic adaptation beyond just mechanical efficiency — improved thermal regulation through biomechanical optimization." This is a strong mechanistic claim with no supporting evidence in the paper. Should be reframed as "data are consistent with systemic adaptation" without asserting the mechanism.

- [ ] **[§4.4] Protocol compliance not acknowledged as a limitation**: The paper describes the NME protocol (2-3 sessions/week, 20-30% mileage) but never verifies it was executed as planned. The "Evidence of Systematic Training" (filename artifacts, manual notes) is thin. Lack of compliance verification should be explicitly listed as a study limitation.

### Low Priority

- [ ] **[Abstract] Needs structured format for journal submission**: Background/Purpose/Methods/Results/Conclusions structure required by IJSPP, JSS. The "Key Innovation" callout is non-standard. **Blocked on P3 venue decision.**

- [ ] **[§5 Conclusions] "Strategic Implication" paragraph is marketing language**: "Bridging the gap between casual Quantified Self tracking and formal exercise physiology" is not conclusion language appropriate for a peer-reviewed paper. Remove or replace with a factual implication statement.

- [ ] **[Appendix A] `run_metrics()` is undefined**: The code block calls `run_metrics(df, zones)` but the function is never described. A reader cannot reproduce the result without reading the source. Add a one-line comment explaining what the function returns.

- [ ] **[Appendix B vs Declarations] Duplication**: Data availability information now appears in both the Declarations section and Appendix B. For journal submission, one location is sufficient. Collapse Appendix B into Declarations or remove the redundancy.

- [ ] **[§2.1] Garmin sampling rate claim**: States "1 Hz (GPS/HR/cadence)" — Garmin devices use smart recording by default (variable rate). Should specify "1 Hz or Garmin smart recording mode" unless the device was confirmed to be in 1-second recording mode throughout the study.

---

## Done (fixed in PR #3)

- [x] EF formula in Section 2.2 code block: `speed.mean()` → `dist.sum()/dt.sum()/hr.mean()`
- [x] EF formula in README Run-Only Filter snippet
- [x] `data/sample/README.md`: `ZoneConfiguration` → `ZoneConfig`+`HeartRateZone`; `pace_min_per_km` corrected
- [x] WELLNESS.md threshold descriptions match `cache.py` implementation
- [x] Placeholder `yourusername` URLs removed from `pyproject.toml` and `CITATION.cff`
