# 04 — Goal + External Research

## Long-term goal candidates (kept plural)

### G1 — grounded
Publish the 103-day N=1 cadence-modification longitudinal study as a peer-reviewed scientific paper, with internally consistent headline numbers across all committed artifacts, a reproducible pipeline, and privacy-safe data release.

**Falsifiable success signals:**
- All P0 items in docs/PUBLICATION_CHECKLIST.md are checked [x], including the temperature-inconsistency blocker that currently remains unchecked. — _evidence:_ `audit/02-static-audit.json:F-doc-01 (PUBLICATION_CHECKLIST.md line 43 P0 item confirmed unchecked; README.md:21 still shows 36°C; data/real_weekly_data.json W32 note still shows 36°C heat)`
- README.md, reports/01_longitudinal_study.md, data/real_weekly_data.json, and CITATION.cff all state the same EF improvement percentage, arithmetically derivable from the committed W17/W32 rpe10_ef values in real_weekly_data.json. — _evidence:_ `audit/02-static-audit.json:F-doc-02, F-doc-07 (four-way disagreement: README +18%, report +17%, CITATION.cff 18.4%, data-derived ~17.82%; CITATION.cff:25 value unsupported by any committed data point)`
- data/subjective.csv PHI (rest_hr, HRV, RPE, ankle_pain) is removed from git history, gitignore-excluded, or explicitly published with documented athlete consent before the repository is made public. — _evidence:_ `audit/02-static-audit.json:F-pii-1 (data/subjective.csv committed and tracked by git; .gitignore has no exclusion rule for data/*.csv; MIT LICENSE implies public release intent)`
- tools/reproduce_study_analysis.py runs to completion on a clean checkout without requiring the gitignored data/processed/ directory, meaning per-session processed CSVs are either committed or replaced with a documented sample fixture. — _evidence:_ `audit/02-static-audit.json:F-repro-01 (reproduce_study_analysis.py:49 DATA_PROCESSED = ROOT/'data'/'processed'; .gitignore line 51 excludes data/processed/; directory absent from repo)`

### G2 — grounded
Release biosystems as a stable, publicly installable open-source Python library for running-physiology data pipelines, with consistent semantic versioning, a CLI that exercises real .fit/.gpx files in CI, and coverage of the full FullRunReport assembly path.

**Falsifiable success signals:**
- pyproject.toml version field, CHANGELOG.md latest release heading, and src/biosystems/__init__.__version__ all agree on the same semantic version string that reflects the post-v1.0.0 functionality (Strava API, wellness module, FullRunReport, PMC) described in the CHANGELOG. — _evidence:_ `audit/02-static-audit.json:F-doc-04 (CHANGELOG.md:16 documents v1.1.0 dated 2026-03-22; pyproject.toml:6 and src/biosystems/__init__.py:31 still declare 1.0.0; CITATION.cff:5 also 1.0.0)`
- CI test matrix (.github/workflows/test.yml) passes with zero failures across Python 3.10/3.11/3.12, with physics/report.py (build_run_report, FullRunReport) achieving >0% test coverage. — _evidence:_ `audit/03-execution.json:unexecuted_regions (src/biosystems/physics/report.py: 276 stmts, 276 missed, 0% coverage; no test_report.py exists in test suite)`
- The end-to-end CLI path biosystems analyze <file>.gpx is exercised by an unconditional CI test using a committed synthetic fixture, not the data/raw/ file that is absent in every clean checkout. — _evidence:_ `audit/03-execution.json:F-testcov-1 (tests/test_cli_integration.py:14-15 guards with pytest.skip when data/raw/ GPX absent; test SKIPPED in every CI run; cli.py remains at 0% coverage)`
- README.md documented test count matches the output of pytest --collect-only on the committed test suite. — _evidence:_ `audit/02-static-audit.json:F-doc-08 (README.md:238 and README.md:311 both state 161 tests; audit/03-execution.json test_result shows 185 collected; 24-test discrepancy)`

### G3 — grounded
Operate as a personal daily-use sports science coaching system for the athlete post-study, with a production-stable pipeline: nightly post-run LLM briefings via cron, crash-free wellness telemetry ingestion across Whoop-to-Garmin device transition, and resilient Strava API integration.

**Falsifiable success signals:**
- daily_running_brief.py runs nightly via cron at 20:00 without crashing, writing a narrative brief to ~/.openclaw/workspace/memory/intelligence/, as confirmed by absence of cron error mail. — _evidence:_ `audit/01-understanding.json (entry_points: daily_running_brief/daily_running_brief.py description 'Post-run LLM synthesis pipeline... drives OpenAI/Anthropic... writes to ~/.openclaw/workspace/memory/intelligence/'); CLAUDE.md cron entry at 20:00`
- biosystems strava executes without unhandled exception when the Strava API returns any RFC 7231-compliant Retry-After header format, including the HTTP-date string variant that currently causes an uncaught ValueError. — _evidence:_ `audit/02-static-audit.json:F-strava-1 (ingestion/strava.py:92: bare int(resp.headers.get('Retry-After',60)); no try/except; date-string Retry-After raises ValueError through all callers)`
- compute_wellness_context() in src/biosystems/wellness/cache.py completes without TypeError when Garmin respiratory-rate readings over the calibration window all have identical values (std=0), which sets rr_sigma=None and then crashes the f-string formatter. — _evidence:_ `audit/02-static-audit.json:F-rr-sigma-none-crash-2 (cache.py:393 and cache.py:441: f'{rr_sigma:.1f}σ' with rr_sigma=None raises TypeError; triggered when calibrate_thresholds produces std=0 rr_thresholds)`
- The Whoop-to-Garmin sleep-duration merge in compute_sleep_debt() applies Garmin-wins priority, matching the documented intent, rather than the current inverted Whoop-wins behavior from the swapped combine_first caller/argument. — _evidence:_ `audit/02-static-audit.json:F-sleep-merge-priority-1 (wellness/analytics.py:451: combine_first() caller is sleep_duration_s (Whoop), argument is sleep_duration_s_garmin; comment at lines 448-449 states 'Garmin wins' but Whoop wins)`

### G4 — grounded
Demonstrate a falsifiable-evidence-enforced software engineering methodology (AIV commit protocol plus multi-stage forensic audit) as a replicable practice for N=1 personal-science projects, where every code change and every claim is machine-verifiable against a committed evidence chain.

**Falsifiable success signals:**
- Every committed source file has a corresponding .github/aiv-evidence/ record that links the commit to a falsifiable claim (-c field) and a URL evidence pointer (-i field), with no source files lacking coverage. — _evidence:_ `audit/01-understanding.json (.github/aiv-evidence/ contains 30+ EVIDENCE_*.md files covering ingestion, physics, signal, wellness, analytics, CLI, tests, reports, and config modules)`
- audit/forensic-audit.mjs completes all five pipeline stages and produces schema-valid JSON artifacts for each stage with zero validation failures, as confirmed by the stage-gate logic in the orchestrator. — _evidence:_ `audit/01-understanding.json (audit/forensic-audit.mjs role: 'Node.js headless claude-CLI orchestrator: five-stage forensic audit pipeline with schema validation and git push per stage'; .github/aiv-packets/ contains 25+ PACKET_*.md verification records)`
- .aiv.yml strict_mode and functional_prefixes configuration causes aiv commit to reject any commit that omits a falsifiable claim (-c), evidence URL (-i), or requirement field, with zero bypasses absent explicit --skip-checks. — _evidence:_ `audit/01-understanding.json (.aiv.yml role: 'config: strict_mode, hook functional_prefixes for biosystems'); CLAUDE.md aiv commit syntax block documenting all required flags`

## External research 


- **Tau-U and Baseline-Corrected Tau (Tau-BC) as effect size statistics for N=1 longitudinal training intervention analysis** — The 103-day biosystems study has a clear baseline (W17 pre-intervention) and intervention phase (W17-W36). Tau-U combines nonoverlap between phases with intervention-phase trend correction and requires no distributional assumptions, making it the statistically appropriate effect size for the EF improvement and decoupling reduction claims. The online calculator at singlecaseresearch.org and the R SingleCaseES package provide ready-to-use implementations. Reporting Tau-U alongside visual analysis would satisfy SCED reporting standards for the methods paper.
  - Combining Nonoverlap and Trend for Single-Case Research: Tau-U (ResearchGate) <https://www.researchgate.net/publication/51054492_Combining_Nonoverlap_and_Trend_for_Single-Case_Research_Tau-U>
  - Selecting the proper Tau-U measure for single-case experimental designs: Development and application of a decision flowchart (ResearchGate) <https://www.researchgate.net/publication/353995616_Selecting_the_proper_Tau-U_measure_for_single-_case_experimental_designs_Development_and_application_of_a_decision_flowchart>
  - Tau-U Calculator — Single Case Research <https://singlecaseresearch.org/calculators/tau-u/>
  - SingleCaseES R Package — Tau_U documentation <https://rdrr.io/cran/SingleCaseES/man/Tau_U.html>
  - Determining the Effects of a 6-Week Training Intervention on Reactive Strength: A Single-Case Experimental Design Approach (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC12194246/>

- **Bayesian estimation for small effects in N=1 / serial-measurement sports science (Bayesian interrupted time series)** — The biosystems study's 18% EF improvement is a single-athlete effect that cannot be tested with conventional null-hypothesis significance testing. Bayesian posterior estimation (as advocated by Mengersen et al. 2016 in PLOS One) yields probabilistic statements about the magnitude of adaptation that are directly interpretable for a methods paper. PyMC provides an accessible Python implementation for Bayesian interrupted time series, consistent with the project's Python stack. A 2025 medRxiv preprint directly applies individualistic probabilistic Bayesian methods to serial athlete performance testing, providing a citable precedent.
  - Bayesian Estimation of Small Effects in Exercise and Sports Science (PLOS One) <https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0147311>
  - Bayesian Estimation of Small Effects in Exercise and Sports Science (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC4830602/>
  - Did a true change occur? Improving analytical decisions for serial performance testing in sport (medRxiv 2025) <https://www.medrxiv.org/content/10.1101/2025.09.22.25336149v1.full>
  - Bayesian Interrupted Time Series — PyMC example gallery <https://www.pymc.io/projects/examples/en/latest/causal_inference/interrupted_time_series.html>
  - Randomized single-case AB phase designs: Prospects and pitfalls (Behavior Research Methods, Springer) <https://link.springer.com/article/10.3758/s13428-018-1084-x>

- **SCED (Single-Case Experimental Design) as an accepted evidence-generation framework in sports science — formal design standards and visual analysis requirements** — The nof1sced.org framework and PMC literature establish that SCEDs require: (1) at minimum 5 baseline data points, (2) visual analysis of level/trend/variability, and (3) quantitative effect sizes (Tau-U or NAP). The biosystems 103-day study can be formally framed as an AB SCED. Citing PMC11729724 (role of SCED in evidence-based practice) and PMC10016625 (family of SCEDs) would give the methods paper a rigorous design-methods foundation, distinguishing it from an anecdotal case report.
  - The role of single case experimental designs in evidence-based practice (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC11729724/>
  - The Family of Single-Case Experimental Designs (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC10016625/>
  - Randomized Single-Case Experimental Designs in rehabilitation (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC6955662/>
  - N=1 SCED analysis resources — nof1sced.org <https://www.nof1sced.org/analysis>

- **Person-as-Population causal inference framework for self-tracked N=1 health data (Hekler et al. 2019 arXiv)** — This arXiv paper proposes treating longitudinal N=1 data as a population of repeated measurements from one person, enabling causal inference from self-tracked wearable data — exactly the biosystems use case with 103 days of Garmin/Whoop data. It provides theoretical grounding for the study's claim that intra-individual longitudinal effects (EF improvement) are meaningful without a control group.
  - [uncorroborated] Person as Population: A Longitudinal View of Single-Subject Causal Inference for Analyzing Self-Tracked Health Data (arXiv) <https://arxiv.org/pdf/1901.03423>

- **DFA-alpha1 (fractal correlation of HRV) as a wearable-based aerobic threshold detector, with validated 0.75 threshold mapping to VT1** — DFA-alpha1 can be computed from Garmin chest-strap HRV data already collected in the biosystems dataset, providing a non-invasive, field-based aerobic threshold estimate for each session. This would: (1) validate that Zone 2 training was truly sub-threshold across the study, (2) contextualize the EF improvement as an aerobic adaptation rather than drift artifact, and (3) position biosystems for a future DFA-alpha1 module. Rogers et al. (2021) validated the 0.75 threshold against VT1 via incremental treadmill testing; Frontiers Physiology (2022, 2024) and a Journal of Sports Sciences paper (2023) provide multi-study corroboration.
  - A New Detection Method Defining the Aerobic Threshold Based on Fractal Correlation Properties of HRV (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC7845545/>
  - Fractal Correlation Properties of HRV as Biomarker for Intensity Distribution — Update (Frontiers in Physiology 2022) <https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2022.879071/full>
  - Reliability and validity of DFA-alpha1 to determine intensity thresholds (Frontiers in Physiology 2024 / PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC10875128/>
  - Correlation properties of HRV to assess the first ventilatory threshold in runners (Journal of Sports Sciences 2023) <https://www.tandfonline.com/doi/full/10.1080/02640414.2023.2277034>
  - Validation of DFA-alpha1 for aerobic/anaerobic thresholds in women (European Journal of Applied Physiology 2022) <https://link.springer.com/article/10.1007/s00421-022-05050-x>
  - DFA alpha1 HRV-based threshold estimation — AI Endurance practical guide <https://aiendurance.com/blog/dfa-alpha-1-thresholds-from-heart-rate-variability>

- **Efficiency Factor (EF) and aerobic decoupling (Pa:HR) as practitioner metrics — Friel/TrainingPeaks origin, lack of peer-reviewed validity studies, and gap that biosystems can help close** — The EF and Pa:HR metrics used in biosystems originate from Joe Friel's practice-based framework, implemented in TrainingPeaks. Peer-reviewed validity studies for EF specifically are absent from the literature — the TrainingPeaks blog and Friel's own website are the primary sources. This is simultaneously a limitation to disclose in the methods paper and a research opportunity: publishing biosystems with a reproducible EF/decoupling pipeline on real longitudinal data provides the first open, reproducible computation of these metrics at scale, inviting future validation studies.
  - The Efficiency Factor in Running — Joe Friel <https://joefrieltraining.com/the-efficiency-factor-in-running-2/>
  - Efficiency Factor and Decoupling — TrainingPeaks Blog <https://www.trainingpeaks.com/blog/efficiency-factor-and-decoupling/>
  - Aerobic Decoupling (Pw:Hr and Pa:HR) and EF — TrainingPeaks Help Center <https://help.trainingpeaks.com/hc/en-us/articles/204071724-Aerobic-Decoupling-Pw-Hr-and-Pa-HR-and-Efficiency-Factor-EF>
  - Calculating Efficiency Factor in R — quantixed blog (independent EF implementation) <https://quantixed.org/2020/05/19/running-free-calculating-efficiency-factor-in-r/>

- **Journal of Open Source Software (JOSS) as primary publication venue for the biosystems Python library** — JOSS has an established track record for sports-analytics software: floodlight (sports performance analysis framework, JOSS 2022) and Athlytics (longitudinal exercise physiology metrics from wearables, JOSS 2025) are direct precedents. Athlytics is built in R and targets Strava API data; biosystems is Python-native and computes metrics Athlytics does not (EF, Pa:HR aerobic decoupling, Minetti GAP, hrTSS, PMC). JOSS review focuses on software quality (tests, docs, CI, license) rather than novel scientific findings, making it suitable even for a methods/tools paper. Submission is free and the review is GitHub-based.
  - Journal of Open Source Software: floodlight — sports analytics framework (JOSS 2022) <https://joss.theoj.org/papers/10.21105/joss.04588>
  - Journal of Open Source Software: Athlytics — longitudinal exercise physiology metrics from wearables (JOSS 2025) <https://joss.theoj.org/papers/d65ecdbea8f4c464c7ed106b63b9c703>
  - Athlytics preprint — bioRxiv 2025 <https://www.biorxiv.org/content/10.1101/2025.05.01.651597v2.full>
  - About the Journal of Open Source Software <https://joss.theoj.org/about>
  - JOSS papers tagged physiology <https://joss.theoj.org/papers/tagged/physiology>

- **IJSPP (International Journal of Sports Physiology and Performance) for the N=1 experimental findings paper, separate from the JOSS software paper** — IJSPP explicitly publishes work with direct practical applications in sport performance and is an appropriate venue for the 103-day cadence modification / EF improvement findings. A two-paper strategy — JOSS for the software library, IJSPP for the N=1 physiological findings — separates software and scientific claims, satisfying both communities. IJSPP impact factor and scope are well-matched to the study's exercise physiology content.
  - International Journal of Sports Physiology and Performance — Human Kinetics overview <https://journals.humankinetics.com/view/journals/ijspp/ijspp-overview.xml>
  - IJSPP — Research.com 2026 impact factor and scope <https://research.com/journal/international-journal-of-sports-physiology-and-performance>

- **OpenGPS platform vision: privacy-preserving GPS data archiving and sharing for reproducible sports science** — The biosystems study involves 103 days of GPS run files. Publishing anonymized GPS traces (start/home location obscured, first/last segments stripped) on OSF alongside the code would satisfy open-data requirements for JOSS and PLOS ONE. The OpenGPS paper (ScienceDirect/PMC 2025) outlines a multi-tier access, encryption, and anonymization pipeline specifically for GPS tracking research, providing a citable framework for the data-sharing section of the biosystems methods paper.
  - How can we make GPS tracking studies more open, reproducible, and collaborative? A vision for the OpenGPS platform (ScienceDirect) <https://www.sciencedirect.com/science/article/pii/S235234092500335X>
  - OpenGPS platform (PMC) <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12136898/>
  - OSF Registries — preregistration for prospective studies <https://www.cos.io/products/osf-registries>

- **Minetti 2002 polynomial for Grade Adjusted Pace — scientific basis and known limitation (n=10 elite male mountain runners)** — The biosystems GAP implementation uses the Minetti energy cost polynomial. The original sample was n=10 elite male mountain runners, a significant limitation for generalizability to recreational runners. The methods paper should cite Minetti et al. 2002 and acknowledge this limitation; it also creates an opportunity to compare biosystems GAP output against Strava's improved empirical GAP model to validate the polynomial approach on the N=1 dataset.
  - Grade Adjusted Pace — Minetti polynomial explanation (RunDida) <https://rundida.com/tools/gap-calculator/>
  - An Improved GAP Model — Strava Engineering blog (empirical refinement of Minetti) <https://medium.com/strava-engineering/an-improved-gap-model-8b07ae8886c3>
  - Reverse-engineering Strava's Grade Adjusted Pace <https://aaron-schroeder.github.io/reverse-engineering/grade-adjusted-pace.html>

- **Cadence modification: systematic review evidence that 5-10% cadence increase reduces ground reaction forces and may improve running economy without increasing VO2** — Directly validates the neuromuscular efficiency drill protocol in the biosystems study. A 2025 PMC systematic review (PMC12440572) found consistent biomechanical improvements from moderate cadence increases (reduced vertical GRF, lower loading rates, shorter stride length) with metabolically neutral or slightly improved oxygen cost. This corroborates the mechanism by which the study's cadence drills could drive the observed EF improvement and supports the biological plausibility claim in the methods paper.
  - The Influence of Running Cadence on Biomechanics and Injury Prevention: A Systematic Review (PMC 2025) <https://pmc.ncbi.nlm.nih.gov/articles/PMC12440572/>
  - Running Economy Changes Alter Predicted Running Speed and Performance in Collegiate Runners (PMC 2024) <https://pmc.ncbi.nlm.nih.gov/articles/PMC11382781/>
  - Quantifying Running Economy in Amateur Runners — VO2 and Energy Cost (PMC 2025) <https://pmc.ncbi.nlm.nih.gov/articles/PMC12418179/>

- **Critical Power / W'bal model for running as a theoretically grounded training-load alternative to hrTSS/PMC, with sweatpy providing a Python reference implementation** — The PMC critical power review (PMC5371646) establishes that the CP/W'bal model captures energy-system-specific strain that single-number metrics like TSS cannot. The three-dimensional impulse-response model (PMC12880663) extends Banister's ATL/CTL framework to CP/W'/Pmax axes. Adding a Critical Velocity / W'bal module to biosystems (sweatpy already has w_prime_balance.py as a reference) would materially advance the library beyond hrTSS and position it for a follow-on paper.
  - The Critical Power Concept: Applications to Sports — PMC <https://pmc.ncbi.nlm.nih.gov/articles/PMC5371646/>
  - The three-dimensional impulse-response model: energy system-specific training adaptation (PMC 2025) <https://pmc.ncbi.nlm.nih.gov/articles/PMC12880663/>
  - The three-dimensional impulse-response model (arXiv preprint) <https://arxiv.org/pdf/2503.14841>
  - sweatpy W'bal implementation — GoldenCheetah/sweatpy GitHub <https://github.com/GoldenCheetah/sweatpy/blob/master/sweat/pdm/w_prime_balance.py>
  - Implementing the Banister Impulse-Response Model in GoldenCheetah (Liversedge blog) <http://markliversedge.blogspot.com/2019/01/implementing-banister-impulse-response.html>

- **sweatpy (GoldenCheetah Python library) and scikit-sports as the closest existing open-source Python endurance analytics tools — and the differentiation gap for biosystems** — sweatpy provides FIT/TCX/GPX parsing, W'bal, and mean-max power but does not implement EF, Pa:HR aerobic decoupling, Minetti GAP, hrTSS, wearable wellness integration (Whoop/Garmin HRV/RHR/sleep), or PMC from HR data alone. sweatpy is cycling-centric and its Critical Power calculation was an open GitHub issue. scikit-sports is essentially abandoned. biosystems fills the running-specific analytics gap, particularly for athletes without power meters.
  - sweatpy — GoldenCheetah Python endurance analytics library (GitHub) <https://github.com/GoldenCheetah/sweatpy>
  - scikit-sports — GoldenCheetah sports analysis library for Python (GitHub) <https://github.com/GoldenCheetah/scikit-sports>
  - Calculate athlete Critical Power? — open sweatpy GitHub issue <https://github.com/GoldenCheetah/sweatpy/issues/25>
  - PySport open-source sports analytics ecosystem — Talk Python podcast episode <https://talkpython.fm/episodes/show/416/open-source-sports-analytics-with-pysport>

- **OSF preregistration and Registered Reports as mechanisms for N=1 prospective study credibility and open-science compliance** — Preregistering the analysis plan on OSF (even retrospectively via a time-stamped protocol) strengthens the methods paper's credibility claims and aligns with open science standards increasingly required by IJSPP, Frontiers, and PLOS ONE. The COS Registered Reports program (active at 300+ journals) allows in-principle acceptance before results are known. For the N=1 SCED design, the OSF registration can specify the primary outcome (EF), analysis plan (Tau-U, Bayesian ITS), and data sharing plan.
  - OSF Registries — Center for Open Science <https://www.cos.io/products/osf-registries>
  - Registered Reports — Center for Open Science 2022 Impact Report <https://www.cos.io/impact/2022/registered-reports>
  - Choosing the Right Preregistration Template — COS blog <https://www.cos.io/blog/choosing-preregistration-template-guide-for-researchers>
  - Demystifying Open Science: Registered Reports and Data Notes (PMC) <https://pmc.ncbi.nlm.nih.gov/articles/PMC11138224/>


_Generated 2026-06-17T20:54:52.027Z · branch claude/epic-goldberg-hebvrp_
