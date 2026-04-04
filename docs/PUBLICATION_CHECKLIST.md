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

- [ ] **Ethics / IRB statement**: Add a brief statement confirming this was self-experimentation conducted in accordance with the Declaration of Helsinki. Most journals accept a one-sentence self-certification for N=1 self-study.

- [ ] **Conflict of interest statement**: Add (e.g. "The author declares no conflict of interest.").

- [ ] **Funding statement**: Add (e.g. "No external funding was received for this study.").

- [ ] **Data availability statement**: Replace the vague "contact through repository issues" with a concrete statement: public repo URL + `data/real_weekly_data.json` for the weekly aggregate dataset; raw .fit files not shared (privacy).

- [ ] **Manuscript format**: Convert to double-spaced, line-numbered format with structured abstract (Background / Purpose / Methods / Results / Conclusions) and word count. Required by all target journals.

- [ ] **Inter-session variability**: The 18% EF claim currently rests on two single sessions. Report the coefficient of variation across all RPE-matched sessions or explicitly frame as a test-retest design with appropriate caveats.

---

## P2 — Strengthens credibility

- [ ] **Resolve RPE 10 session count**: How many RPE 10 sessions were recorded total? Document that the baseline (W17) and retest (W32 or W35) were selected a priori, not cherry-picked from a larger pool.

- [ ] **Temperature verification**: Cross-reference reported temperatures against the Open-Meteo weather cache (`data/weather_cache.parquet`) to confirm values are pipeline-sourced, not manually recalled.

- [ ] **Section 2.1 EF formula**: Currently states `Speed (m/s) / Heart Rate (bpm)`. Expand to show the run-only variant explicitly used: `(dist.sum() / dt.sum()) / hr.mean()` — the section-level formula and the code block in 2.2 should match.

- [ ] **Cadence progression table (Phase III)**: Weeks 25–31 cadence values (158→165 spm) are described as "observed" but the source (weekly mean vs. session-level?) is not documented. Clarify or add a footnote.

---

## P3 — Target venue decision (unblocks formatting)

- [ ] Decide on submission target before doing manuscript formatting:
  - **SportRxiv preprint** — lowest friction, appropriate for software-methods paper; ready after P0 fixes + ethics/COI/funding statements (~1–2 days)
  - **IJSPP / JSS case report** — peer-reviewed, ~3–6 months; requires full P1 items + cover letter
  - **arXiv (cs.LG or q-bio)** — appropriate if framing is the software pipeline as the primary contribution

---

## Done (fixed in PR #3)

- [x] EF formula in Section 2.2 code block: `speed.mean()` → `dist.sum()/dt.sum()/hr.mean()`
- [x] EF formula in README Run-Only Filter snippet
- [x] `data/sample/README.md`: `ZoneConfiguration` → `ZoneConfig`+`HeartRateZone`; `pace_min_per_km` corrected
- [x] WELLNESS.md threshold descriptions match `cache.py` implementation
- [x] Placeholder `yourusername` URLs removed from `pyproject.toml` and `CITATION.cff`
