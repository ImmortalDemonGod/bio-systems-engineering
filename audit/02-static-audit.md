# 02 — Static Audit

Coverage: visited **89/174** surface items.
All surface items visited.

## Findings (101, falsification-survivors)

### [CRITICAL] F-doc-01 — doc_drift
- **Location:** `README.md:21,reports/01_longitudinal_study.md:212,data/real_weekly_data.json:100`
- **What:** The README top-level results table claims the final (W32) environmental condition was '36°C (extreme heat)', while the scientific report clearly states '~28°C (daily max 32°C)' based on Open-Meteo historical archive data. The PUBLICATION_CHECKLIST.md P0 blocker remains unchecked. The data/real_weekly_data.json W32 note also still carries '36°C heat'. Only the report was corrected; README and JSON were not updated. A reader of the README receives a materially different thermal-stress narrative than the report.
- **Evidence:** README.md:21 confirmed: '20°C (mild) | 36°C (extreme heat)'. reports/01_longitudinal_study.md:19 confirmed: 'conducted in summer heat (~28°C)'; line 212 confirmed: '~28°C (daily max 32°C)'. data/real_weekly_data.json line 100 confirmed: note field 'RPE_10 Final Retest run EF = 0.02122 (36°C heat)'. docs/PUBLICATION_CHECKLIST.md P0 item (line 43) is unchecked [ ]; P2 item (line 69) is checked [x] stating '36°C figure removed from paper'. README and JSON were not updated when the report was corrected.
- **Survived adversarial pass:** yes

### [HIGH] F-strava-1 — bug
- **Location:** `src/biosystems/ingestion/strava.py:92`
- **What:** The Retry-After header in an HTTP 429 response may legally contain an HTTP-date string (e.g. 'Sat, 01 Jan 2026 00:00:00 GMT') per RFC 7231 §7.1.3. Calling int() on a date string raises ValueError, which is not caught anywhere in _get_with_backoff(). The exception propagates unhandled through every caller (fetch_activity_streams, fetch_recent_runs, etc.) and aborts the API call chain. This path can be triggered by any Strava 429 that uses the date-format variant, which is permitted by the spec.
- **Evidence:** Verified at line 92: `retry_after = int(resp.headers.get('Retry-After', 60))`. The default is integer 60 (safe), but when the header IS present with an HTTP-date string, `int()` raises ValueError. The entire _get_with_backoff body (lines 80-98) has no try/except — no exception handler anywhere in the function. ValueError propagates unhandled through all callers. RFC 7231 §7.1.3 permits both integer-seconds and HTTP-date formats. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [HIGH] F-pii-1 — security
- **Location:** `data/subjective.csv`
- **What:** Personal health data (resting heart rate, HRV, RPE, ankle pain) for the N=1 study subject is committed to the git repository. The .gitignore does not exclude data/*.csv, so this file is tracked in git history and would appear in any public clone. For a study with a single identifiable athlete, this constitutes PHI committed to a codebase intended for open-source publication (LICENSE is MIT). The data must be either explicitly consented-to as public, anonymized, or gitignore-excluded before the repository is made public.
- **Evidence:** data/subjective.csv confirmed present and tracked by git (git ls-files returned the path). File contains header 'date,rest_hr,hrv,rpe,ankle_pain' with real health values (rest_hr=50, hrv=90, rpe=3, ankle_pain). .gitignore grep for '*.csv' and 'subjective' returned no matches — no exclusion rule exists for this file. File is committed to repository history.
- **Survived adversarial pass:** yes

### [HIGH] F-doc-02 — doc_drift
- **Location:** `README.md:17,reports/01_longitudinal_study.md:19,data/real_weekly_data.json:99`
- **What:** The W32 RPE 10 retest Efficiency Factor is reported as 0.0212 (+18%) in the README, 0.0211 (+17%) in the scientific report, and 0.02122 in real_weekly_data.json. CITATION.cff uses a fourth value, 18.4%, which is unsupported by any committed data. No single canonical value is established across committed artifacts.
- **Evidence:** README.md:17 confirmed: '0.0212 | +18%'. reports/01_longitudinal_study.md:19 confirmed: 'EF improved +17% (0.0180 → 0.0211)'; line 213 confirmed: '0.0211 | +17%'. data/real_weekly_data.json line 99 confirmed: '"rpe10_ef": 0.02122'. CITATION.cff:25 confirmed: '18.4% improvement in running Efficiency Factor'. Arithmetic: (0.02122-0.01801)/0.01801 = 17.8% — matches none of the four stated values.
- **Survived adversarial pass:** yes

### [HIGH] F-doc-03 — doc_drift
- **Location:** `README.md:18,data/real_weekly_data.json`
- **What:** The README headline results table uses baseline decoupling 7.7% and final decoupling 3.8% (claiming -50.6% reduction). Neither value matches the committed weekly aggregate data: W17 decoupling_mean=8.1 (not 7.7) and W32 decoupling_mean=12.05 (not 3.8). The report's primary decoupling comparison uses a completely different comparison set (W23 vs W35) than the README. The README comparison has unknown data provenance.
- **Evidence:** README.md:18 confirmed: '7.7% | 3.8% | -50.6%'. data/real_weekly_data.json W17 (line 6) confirmed: 'decoupling_mean: 8.1' (not 7.7). data/real_weekly_data.json W32 (line 98) confirmed: 'decoupling_mean: 12.05' (not 3.8). README body text (line 37) confirmed: W23 (19.78%) to W35 (4.71%) — a completely different comparison set than the headline table. The values 7.7% and 3.8% appear in no committed artifact.
- **Survived adversarial pass:** yes

### [HIGH] F-repro-01 — reproducibility
- **Location:** `tools/reproduce_study_analysis.py:49,147`
- **What:** The reproduction script requires per-session *_gpx_full.csv files in data/processed/ but this directory is gitignored and not committed. Without the original .fit activity files or the processed CSVs, any external party running reproduce_study_analysis.py will immediately fail. The report's reproducibility claim applies only to the code and aggregate JSON, not to re-running the metric pipeline.
- **Evidence:** reproduce_study_analysis.py:49 confirmed: DATA_PROCESSED = ROOT / 'data' / 'processed'. Line 147 confirmed: _all_csvs = sorted(DATA_PROCESSED.glob('*_gpx_full.csv')). .gitignore confirmed: 'data/processed/' is excluded at line 51. No data/processed/ directory exists in the repository.
- **Survived adversarial pass:** yes

### [HIGH] F-doc-10 — doc_drift
- **Location:** `docs/PUBLICATION_CHECKLIST.md:43-45`
- **What:** The P2 checklist item claims the 36°C figure was removed from the paper (report) — which is accurate. But the P0 item tracking the README and data/real_weekly_data.json inconsistency remains unchecked. Two of three committed locations where the temperature appears (README.md and data/real_weekly_data.json) still contain the incorrect 36°C value. The P2 fix corrected only the report body, leaving the P0 issue unresolved. This creates a false signal that progress has been made while the publication-blocking inconsistency remains active in the most publicly visible document.
- **Evidence:** PUBLICATION_CHECKLIST.md line 43 confirmed (P0, unchecked): '- [ ] **Temperature inconsistency**' blocker still open. Line 69 confirmed (P2, checked): 'W32 retest confirmed ~28°C run-time. "36°C" figure removed from paper'. Report abstract line 19 confirmed: 'conducted in summer heat (~28°C)' — report body corrected. README.md line 21 confirmed: '| **Environmental Conditions** | 20°C (mild) | 36°C (extreme heat) |' — still 36°C. data/real_weekly_data.json W32 note confirmed: 'RPE_10 Final Retest run EF = 0.02122 (36°C heat)' — still 36°C. P2 fix corrected only the report body; P0 remains unresolved.
- **Survived adversarial pass:** yes

### [HIGH] F-new-gpx-power-unguarded-01 — bug
- **Location:** `src/biosystems/ingestion/gpx.py:126`
- **What:** In parse_gpx(), the first three power-parsing fallback paths (direct child no-namespace line 126, direct child with namespace line 131, Garmin extension namespace line 136) call int(power_node.text) with no exception guard. Only the fourth fallback (extensions child-tag loop, line 143) uses try/except. Any power text value that is not directly castable to int (e.g., '350.0', '350.5', empty string) will raise ValueError and abort parsing for the entire GPX file, discarding all data from that run.
- **Evidence:** Verified by direct read of gpx.py:121-151. Path 1 (line 126): power = int(power_node.text) — no try/except. Path 2 (line 131): power = int(power_node.text) — no try/except. Path 3 (line 136): power = int(power_node.text) — no try/except. Path 4 (lines 143-148): int(child.text) inside try/except Exception. The asymmetry is confirmed. A float-string power value such as '350.0' raises ValueError in paths 1-3, propagating up and aborting parse_gpx() for the entire file.
- **Survived adversarial pass:** yes

### [HIGH] F-new-garmin-sleep-never-fetched-12 — bug
- **Location:** `src/biosystems/wellness/habitdash.py:45`
- **What:** The wellness analytics layer expects a `sleep_duration_s_garmin` column in the wellness parquet (referenced in `analytics.py:_GARMIN_METRICS`, `analytics.py:321`, `analytics.py:450-456`, `cache.py:276`), but the HabitDash client has no field ID or column mapping registered for Garmin sleep duration. `fetch_all_metrics()` therefore never writes this column. The `compute_sleep_debt()` Garmin branch (`analytics.py:450-461`) checks `'sleep_duration_s_garmin' in df.columns` first; the column is never present, so the branch is unreachable and sleep debt always uses the Whoop path (or returns empty if Whoop data is also absent). The `cache.py` fallback to `sleep_duration_s_garmin` always resolves to NaN.
- **Evidence:** `FIELD_IDS['garmin']` at lines 45-53 has 7 entries (resting_hr, body_battery, steps, active_time_s, avg_stress, respiratory_rate, vo2max) — no sleep_duration key confirmed by direct read. `COLUMN_MAP` at lines 58-76 has no `('garmin', 'sleep_duration_s')` entry confirmed. `fetch_all_metrics()` at line 179 iterates exclusively over `FIELD_IDS`. Grep of src/ confirms `analytics.py:49` lists `'sleep_duration_s_garmin'` in `_GARMIN_METRICS`; `analytics.py:321` uses `_mean(garmin_df, 'sleep_duration_s_garmin')`; `analytics.py:450-456` checks `'sleep_duration_s_garmin' in df.columns` before combining; `cache.py:276` calls `_val(today_row, 'sleep_duration_s_garmin')` as sleep fallback. All references confirmed at cited locations.
- **Survived adversarial pass:** yes

### [MEDIUM] F-decoupling-empty-half-1 — bug
- **Location:** `src/biosystems/physics/metrics.py:199-213`
- **What:** calculate_decoupling raises ZeroDivisionError when work_df has one row (or when the first row's cumulative elapsed time exceeds the midpoint). The cumsum-based midpoint split makes first_half empty, causing 0.0/0.0 in the ef_1 computation. The guard at lines 191-192 falls back to hr_df if the Z2-filtered set is small, but if hr_df itself has only 1 row the bug is still reachable.
- **Evidence:** Verified at metrics.py:199-201: elapsed = work_df["dt"].cumsum(); midpoint_s = elapsed.iloc[-1] / 2.0; first_half = work_df[elapsed <= midpoint_s]. For a 1-row work_df with dt=5: elapsed=[5], midpoint_s=2.5, first_half = work_df[5 <= 2.5] = empty DataFrame. Lines 205-208: ef_1 = float(0.0)/float(0.0)/float(hr) — float(0.0)/float(0.0) raises ZeroDivisionError. The guard at lines 191-192 falls back to hr_df only if work_df is empty or <120 rows, but does not require hr_df itself to have >=120 rows; a 1-row hr_df passes the guard and triggers the bug.
- **Survived adversarial pass:** yes

### [MEDIUM] F-cadence-doubling-2 — intent_mismatch
- **Location:** `src/biosystems/ingestion/strava.py:359-363 vs src/biosystems/ingestion/fit.py:157-159 vs src/biosystems/ingestion/gpx.py:119`
- **What:** Cadence convention documented inconsistently across parsers: strava.py explicitly doubles single-foot RPM and claims this 'matches FIT convention', while fit.py comment says FIT stores 'rpm for run' (single-foot). Garmin FIT SDK documents total SPM, making fit.py comment wrong. GPX parser passes cadence through raw with no doubling, potentially producing half-values relative to Strava/FIT output.
- **Evidence:** Confirmed at strava.py:359-361: comment 'Strava reports running cadence as single-foot RPM. Multiply by 2 to get total steps per minute, matching FIT file convention' and df["cadence"] = ... * 2. Confirmed at fit.py:90: comment 'Cadence (spm, but stored as rpm for run)' — 'rpm' here implies single-foot stride rate, directly contradicting strava.py which claims FIT stores total SPM and that doubling matches FIT convention. fit.py lines 158-159 perform no doubling. gpx.py:119: cad = int(cad_node.text) if cad_node is not None else np.nan — no doubling. The strava.py claim that doubling 'matches FIT file convention' is internally inconsistent with fit.py's comment about FIT storing rpm (single-foot) for runs; the GPX parser has no doubling at all.
- **Survived adversarial pass:** yes

### [MEDIUM] F-run-only-walks-leak-3 — intent_mismatch
- **Location:** `src/biosystems/physics/report.py:464-469 and src/biosystems/physics/metrics.py:285-293`
- **What:** run_only_metrics in build_run_report is labeled as the walk-filtered version but only walk-filters EF and decoupling (inside their helper functions). Basic statistics — distance_km, duration_min, avg_pace_min_per_km, avg_hr — are computed from the full df including walk segments, producing the same values as session_metrics. The run_only / session distinction is therefore only meaningful for EF and decoupling fields.
- **Evidence:** Confirmed at report.py:465: df_session = df.drop(columns=["is_walk"], errors="ignore"); line 466: session_metrics = run_metrics(df_session.copy(), ...); line 469: run_only_metrics = run_metrics(df.copy(), ...) passes df WITH is_walk column. In run_metrics (metrics.py:285-287): total_dist_m = float(df["dist"].sum()), secs = float(df["dt"].sum()), avg_hr = float(df["hr"].mean()) — all computed on the full df before any walk filtering. Walk filtering only happens inside calculate_efficiency_factor (line 134: base_df = df[~df["is_walk"].astype(bool)]) and calculate_decoupling (line 181). Therefore distance_km, duration_min, avg_pace_min_per_km, avg_hr are identical in both session_metrics and run_only_metrics.
- **Survived adversarial pass:** yes

### [MEDIUM] F-gpx-hr-parse-unguarded-4 — bug
- **Location:** `src/biosystems/ingestion/gpx.py:104-106`
- **What:** GPX HR value is cast with int() without exception handling. A malformed or empty text node in the gpxtpx:hr element causes TypeError or ValueError, aborting the entire file parse rather than gracefully substituting NaN for that trackpoint. Same unguarded pattern appears for cadence (gpx.py:119).
- **Evidence:** Confirmed at gpx.py:103-106: hr_node = pt.find(".//gpxtpx:hr", ns); if hr_node is not None: hr_val = int(hr_node.text). No try/except wraps int(). If hr_node.text is None (self-closing tag <gpxtpx:hr/>), int(None) raises TypeError. If hr_node.text is '' or non-numeric, int() raises ValueError. Either exception propagates out of the loop and aborts parse_gpx for the entire file rather than substituting NaN for that trackpoint.
- **Survived adversarial pass:** yes

### [MEDIUM] F-gpx-cad-parse-unguarded-5 — bug
- **Location:** `src/biosystems/ingestion/gpx.py:119`
- **What:** GPX cadence parsing has the same unguarded int() cast as HR. A non-integer or empty cadence text value raises ValueError or TypeError, failing the entire file parse instead of falling back to NaN for that trackpoint.
- **Evidence:** Confirmed at gpx.py:119: cad = int(cad_node.text) if cad_node is not None else np.nan. No try/except. If cad_node.text is None (self-closing tag), int(None) raises TypeError. If cad_node.text is a decimal string like '90.5' (non-Garmin device), int('90.5') raises ValueError. Both propagate and abort the entire file parse instead of substituting NaN for the affected trackpoint.
- **Survived adversarial pass:** yes

### [MEDIUM] F-gap-ele-zero-sea-level-7 — bug
- **Location:** `src/biosystems/physics/gap.py:224`
- **What:** Elevation quality check treats ele=0 as missing data (replace with NaN before counting), falsely penalizing coastal or sea-level activities where 0 m is a correct reading. The computation path does not filter ele=0, so the data is valid for computation but the quality gate rejects it, silently suppressing GAP for legitimate activities.
- **Evidence:** Confirmed at gap.py:224: ele_series = df[ele_col].replace(0, np.nan).dropna(). Line 225: if len(ele_series) < 10 returns (False, 'insufficient elevation data points'). A sea-level activity with all ele=0 is also suppressed at metrics.py:317-318 (same replace(0, np.nan) pattern: if not ele_series.isna().all() gates the check_elevation_quality call). The computation path at gap.py:165 uses df[ele_col].rolling(...).mean() without any ele==0 replacement — ele=0 is treated as valid data in computation but the quality check treats it as missing. The inconsistency means a flat coastal run with valid 0m elevation has GAP silently suppressed.
- **Survived adversarial pass:** yes

### [MEDIUM] F-gpx-ns-garmin-only-9 — doc_drift
- **Location:** `src/biosystems/ingestion/gpx.py:79-83`
- **What:** parse_gpx docstring claims 'multiple possible XML locations' for sensor extraction. This is accurate only for power (4 fallback paths implemented). Heart rate and cadence are Garmin-namespace-only; non-Garmin GPX files from Polar, Suunto, or Wahoo produce hr=NaN and cadence=NaN silently despite potentially containing valid sensor data in a different namespace.
- **Evidence:** Confirmed at gpx.py:79-82: ns dict registers only 'http://www.topografix.com/GPX/1/1' and 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'. HR (line 103) and cadence (line 118) use only gpxtpx namespace. Power tries 4 fallback paths (lines 121-150: direct child no-namespace, .//power, gpxtpx:power, and extensions child scan). Non-namespaced fallback at lines 157-169 sets hr=np.nan and cad=np.nan unconditionally. Docstring at line 55 says 'attempts to extract elevation, heart rate, cadence, and power from multiple possible XML locations' — accurate for power but not for HR/cadence. Non-Garmin HR/cadence data is silently discarded as NaN.
- **Survived adversarial pass:** yes

### [MEDIUM] F-fit-indoor-gps-11 — bug
- **Location:** `src/biosystems/ingestion/fit.py:207-208`
- **What:** add_derived_metrics requires GPS latitude/longitude. For treadmill or indoor FIT activities, GPS is absent. The FIT file's native 'distance' (cumulative metres) and 'speed' (m/s) streams are parsed into the DataFrame by parse_fit() but never used as a fallback; instead, add_derived_metrics unconditionally raises ValueError, making FIT ingestion unusable for indoor activities.
- **Evidence:** Confirmed at fit.py:207-208: if 'latitude' not in df.columns or 'longitude' not in df.columns: raise ValueError('DataFrame must have latitude and longitude columns'). Confirmed that parse_fit() field_names list at lines 85-95 includes 'speed' and 'distance' which are parsed into the DataFrame when present. add_derived_metrics() unconditionally raises ValueError without checking for these native fields as fallbacks. A treadmill FIT file lacks position_lat/position_long (never converted to latitude/longitude) but may have valid speed/distance streams that are parsed but then unused.
- **Survived adversarial pass:** yes

### [MEDIUM] F-strava-2 — security
- **Location:** `src/biosystems/ingestion/strava.py:91-95`
- **What:** There is no upper bound on the Retry-After sleep duration. A misconfigured or adversarial upstream response with an arbitrarily large integer (e.g. Retry-After: 86400) causes the process to hang indefinitely without a cap. By contrast, habitdash.py lines 106-109 correctly applies min(int(reset_secs)+1, 3600). This is a local denial-of-service vector: any tool that embeds or wraps biosystems (e.g. the daily_running_brief cron job) can be stalled by a single API response.
- **Evidence:** Verified at lines 91-93: `retry_after = int(resp.headers.get('Retry-After', 60))` then `time.sleep(retry_after)` with no upper bound. Verified in habitdash.py lines 106-107: `wait = min(int(reset_secs) + 1, 3600)` shows the capped pattern exists in the codebase but is absent from strava.py. No cap on the sleep duration in the strava path confirmed. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [MEDIUM] F-weather-1 — security
- **Location:** `src/biosystems/environment/weather.py:337`
- **What:** GPS coordinates at 4-decimal-place precision (~11m accuracy) are written to stderr on weather fetch failure. Per CLAUDE.md, the daily brief runs via cron at 20:00; cron daemons typically email stderr to root or a configured address, or write it to system logs. This creates a persistent, plaintext GPS location leak in system mail/logs on every weather fetch failure, even when the associated run data has been sanitized for publication.
- **Evidence:** Verified at lines 294-295: `lat_r = round(lat, 4)` and `lon_r = round(lon, 4)` — 4 decimal places (~11m precision). Verified at line 337: `print(f'[Weather] Failed after {max_retries} retries for lat={lat_r}, lon={lon_r}, time={dt}', file=sys.stderr)` — GPS coordinates written to stderr on exhausted-retry failure. CLAUDE.md confirms cron at 20:00 captures this output. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [MEDIUM] F-sanitize-1 — bug
- **Location:** `tools/sanitize_gps.py:50-51`
- **What:** sanitize_dataframe() mutates the caller's DataFrame in-place by assigning the computed distance_cumulative_m column before any copy is made. The guarding copy at line 74 (df_truncated = df[mask].copy()) applies only to the truncated slice, not the original df. A caller that passes a DataFrame expecting it to be unchanged will find it silently modified with a new column, breaking subsequent processing that assumes a clean input.
- **Evidence:** Verified at lines 50-51: `if 'distance_cumulative_m' not in df.columns and 'dist' in df.columns: df['distance_cumulative_m'] = df['dist'].cumsum()` — column assignment on `df` (the parameter reference) mutates the caller's DataFrame in-place. The guard at line 74 `df_truncated = df[mask].copy()` creates a copy of only the filtered slice; it does not protect the original `df` from the column mutation at line 51. Mutation is real and conditional only on column absence, not prevented. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [MEDIUM] F-sanitize-2 — doc_drift
- **Location:** `tools/sanitize_gps.py:1-16`
- **What:** The module-level 'Security Guarantees' section claims to protect location privacy by removing lat/lon and truncating endpoints, but does not acknowledge that the preserved elevation (ele) column can fingerprint a route via its terrain profile. Unique elevation signatures (hills, bridges, tunnels) allow route identification without lat/lon. The guarantees section is what users rely on before publishing data; this omission creates a false sense of complete anonymization.
- **Evidence:** Verified at lines 11-15: the 'Security Guarantees' section lists 'Removes lat/lon columns completely', '500m endpoint truncation', and 'Preserves: distance, elevation, HR, cadence, pace, power'. No acknowledgment of elevation as a re-identification vector appears anywhere in lines 1-16 or in the sanitize_dataframe docstring. Elevation profiles with unique terrain signatures allow route fingerprinting without lat/lon. The omission from an explicit security guarantees section is a meaningful doc_drift. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [MEDIUM] F-test-1 — test_gap
- **Location:** `tests/test_strava.py`
- **What:** The strava.py test suite covers rate-limit responses but has no test for the date-format Retry-After header path. The _get_with_backoff() implementation at line 92 uses bare int() conversion; if Strava returns a date-format Retry-After string, a ValueError propagates uncaught to the caller. Without this test, the crash is undetected by CI.
- **Evidence:** tests/test_strava.py:219 confirmed: resp.headers = {"Retry-After": "0"} — the existing rate-limit test uses a numeric string. strava.py line 92 confirmed: retry_after = int(resp.headers.get("Retry-After", 60)) — bare int() conversion with no try/except. A date-format Retry-After string (e.g. 'Mon, 01 Jan 2026 00:00:00 GMT') would raise ValueError uncaught. Full test file search for 'strptime', 'date.*format', 'Mon.*Jan' returned no matches. No test case exercises the date-format path.
- **Survived adversarial pass:** yes

### [MEDIUM] F-doc-04 — doc_drift
- **Location:** `CHANGELOG.md:16,pyproject.toml:6,src/biosystems/__init__.py:31`
- **What:** The CHANGELOG documents a v1.1.0 release dated 2026-03-22 that adds Strava ingestion, the wellness module, FullRunReport, PMC trending, and a full CLI. However, pyproject.toml, __init__.py, and CITATION.cff all still declare version 1.0.0. A user installing the package via pip or calling biosystems.__version__ receives '1.0.0' even though substantially more functionality than the initial release is present. This breaks semantic versioning.
- **Evidence:** CHANGELOG.md:16 confirmed: '## [1.1.0] - 2026-03-22' with substantive additions (Strava API, Wellness intelligence, FullRunReport, PMC, CLI). pyproject.toml:6 confirmed: 'version = "1.0.0"'. src/biosystems/__init__.py:31 confirmed: '__version__ = "1.0.0"'. CITATION.cff:5 confirmed: 'version: 1.0.0'. All three runtime/packaging/citation artifacts declare v1.0.0 despite CHANGELOG documenting a v1.1.0 release.
- **Survived adversarial pass:** yes

### [MEDIUM] F-intent-01 — intent_mismatch
- **Location:** `src/biosystems/physics/metrics.py:306-310`
- **What:** The study report explicitly states that cadence values were computed using the Run-Only Filter. But in run_metrics(), avg_cadence is computed from the full df parameter before any walk-detection or HR filtering, while EF and decoupling calculations use walk-filtered, HR-thresholded work_df. PhysiologicalMetrics.avg_cadence is methodologically inconsistent with the paper's stated methodology.
- **Evidence:** metrics.py:307-310 confirmed: 'if "cadence" in df.columns: cadence_series = df["cadence"].replace(0, np.nan); avg_cadence = int(cadence_series.mean())' — uses raw df, not walk-filtered base_df or HR-filtered work_df. calculate_efficiency_factor() lines 133-153 confirmed: uses base_df = df[~df["is_walk"].astype(bool)], then work_df filtered by HR. reports/01_longitudinal_study.md:217 confirmed: 'Cadence computed using the Run-Only Filter (N=1,900 samples, SD=3.6 spm, median=170.0 spm).'
- **Survived adversarial pass:** yes

### [MEDIUM] F-doc-05 — doc_drift
- **Location:** `README.md:182-198`
- **What:** The README presents a simplified 3-line code snippet as 'The Run-Only Filter from biosystems/physics/metrics.py' but the actual function has four distinct steps: (1) is_walk pre-filter, (2) HR dropna, (3) Z2 HR threshold filter, (4) fallback to full HR-valid data when fewer than 120 qualifying rows exist. A reader attempting to replicate the filter from the README would implement an incomplete algorithm that differs from the actual code in edge cases involving walk detection or short aerobic segments.
- **Evidence:** README.md:182-188 confirmed: 3-line snippet showing only lz2 assignment, work_df HR filter, and ef calculation. Actual metrics.py:133-153 confirmed four steps: (1) base_df = df[~df['is_walk'].astype(bool)] walk pre-filter; (2) hr_df = base_df.dropna(subset=['hr']); (3) work_df = hr_df[hr_df['hr'] >= lz2]; (4) fallback 'if work_df.empty or len(work_df) < 120: work_df = hr_df if not hr_df.empty else base_df'. README omits steps 1, 2, and 4.
- **Survived adversarial pass:** yes

### [MEDIUM] F-doc-06 — doc_drift
- **Location:** `reports/01_longitudinal_study.md:17,82-86`
- **What:** The report's §2.2 description of the Run-Only Filter is ambiguous: the abstract/methods paragraph says cadence/pace thresholds define the filter, but §2.2's code block shows only an HR threshold filter. In reality these are two separate stages: walk_detection classifies rows via pace/cadence thresholds (adding is_walk column), then calculate_efficiency_factor strips is_walk rows and separately applies the HR≥Z2 filter. The report description misrepresents this two-stage process as a single filter, making methodology replication harder.
- **Evidence:** Verified at source. Report abstract line 17 reads 'custom Run-Only Filter (cadence ≥140 spm, pace <9.5 min/km)'. §2.2 (lines 79-88) header is 'The Run-Only Filter'; code block (lines 82-86) shows only 'work_df = df[df["hr"] >= lz2]' — no cadence/pace threshold. §1.3 line 56 likewise shows only the HR threshold: 'work_df = df[df["hr"] >= zone2_lower_bound]'. The cadence/pace thresholds are a separate walk-detection preprocessing stage not described in §2.2. Conflation confirmed at source.
- **Survived adversarial pass:** yes

### [MEDIUM] F-doc-07 — doc_drift
- **Location:** `CITATION.cff:23-28`
- **What:** CITATION.cff is the machine-readable citation record that academic tools (Zenodo, GitHub, etc.) read to populate reference databases. It claims 18.4% EF improvement, a value that appears nowhere in the report, README, or raw data. The true improvement is approximately 17.8% based on the committed real_weekly_data.json. The four-way disagreement (17%, 18%, 18.4%, 17.8%) across citation record, README, report, and data means any downstream citation will contain an inaccurate headline claim.
- **Evidence:** CITATION.cff line 25 confirmed: 'demonstrating an 18.4% improvement in running Efficiency Factor'. README.md line 17 confirmed: '+18%'. Report line 19 confirmed: 'EF improved +17% (0.0180 → 0.0211)'. data/real_weekly_data.json confirmed W17 rpe10_ef=0.01801, W32 rpe10_ef=0.02122. True calculation: (0.02122-0.01801)/0.01801 ≈ 17.82%. The 18.4% value in CITATION.cff is not derivable from any committed data point and matches no other document.
- **Survived adversarial pass:** yes

### [MEDIUM] F-repro-02 — reproducibility
- **Location:** `reports/01_longitudinal_study.md:16-19,README.md:15-22`
- **What:** The README's primary results table presents heterogeneous metrics: EF from identifiable RPE10 test sessions, but decoupling from sources that cannot be matched to any row in the committed weekly aggregate data or to the values cited in the report. The -50.6% decoupling headline depends on unverifiable 7.7% and 3.8% values. A reader cannot reproduce these numbers from the public repository.
- **Evidence:** README.md line 18 confirmed: '| **Aerobic Decoupling** | 7.7% | 3.8% | -50.6% |'. data/real_weekly_data.json confirmed W17 decoupling_mean=8.1 (not 7.7%); W32 decoupling_mean=12.05 (not 3.8%). Report line 19 confirmed: 'Aerobic decoupling dropped from 19.78% (W23, 32°C) to 4.71% (W35, 27°C)'. The README's 7.7% and 3.8% values match nothing in committed data or the report. The -50.6% calculation is unverifiable from any committed artifact.
- **Survived adversarial pass:** yes

### [MEDIUM] F-cli-skip-4 — bug
- **Location:** `src/biosystems/cli.py:639-644`
- **What:** The `backfill_streams` skip-existing guard uses `not existing_stream_ids` to enable a date-string fallback. Once any entry in history has a `strava_activity_id`, `existing_stream_ids` is non-empty and `not existing_stream_ids` is False, permanently disabling the date-based fallback for the entire run of the command. Consequently, activities represented in history as date-only entries (e.g. those written by `backfill_efforts` with a minimal stub that lacks `strava_activity_id`) are re-fetched and re-processed even though their date already exists in history. This creates a second id-keyed entry for the same calendar date alongside the existing date-keyed entry, silently producing duplicate records that both survive `load_history()` deduplication (because they have different keys: `"id:12345"` vs `"2025-06-01"`).
- **Evidence:** Confirmed at lines 614-623: `existing_stream_ids` is built before the loop from `load_history()` entries where source=="biosystems_strava" and strava_activity_id is present; it is never mutated inside the loop body (lines 630-715). Confirmed at lines 639-644: `if skip_existing and (activity_id in existing_stream_ids or (not existing_stream_ids and run_date in existing_stream_dates))`. Once any prior history entry contributes an ID to `existing_stream_ids`, `not existing_stream_ids` is permanently False for the entire iteration, disabling the date-string fallback even for entries that were stored without a strava_activity_id (e.g. those written by backfill_efforts with no id field). Such entries appear in `existing_stream_dates` but are never checked, causing re-fetch and a duplicate id-keyed record.
- **Survived adversarial pass:** yes

### [MEDIUM] F-testcov-1 — test_gap
- **Location:** `tests/test_cli_integration.py:14-15`
- **What:** The only CLI integration test (`test_cli_analyze_gpx`) unconditionally skips in every CI run because it requires a file from `data/raw/`, which is excluded by `.gitignore` and is therefore absent in any clean checkout. The CI matrix runs `pytest` on a fresh clone with no raw data. As a result, the full end-to-end path of `biosystems analyze <gpx_file>` (including zone config loading, GPX parsing, haversine distance, run_metrics, and JSON serialization) has zero executable test coverage in CI. A synthetic fixture using a tiny synthetic GPX file in `data/sample/` (which IS committed) would allow this test to run unconditionally.
- **Evidence:** Confirmed at lines 12-15: `gpx_file = Path("data/raw/20250503_..._anklepain_2.gpx")` followed by `if not gpx_file.exists(): pytest.skip(f"Test file {gpx_file} not found")`. The file path is under `data/raw/` which is gitignored, guaranteeing a skip on every clean checkout. The full end-to-end CLI path has zero executable coverage in CI.
- **Survived adversarial pass:** yes

### [MEDIUM] F-testcov-3 — test_gap
- **Location:** `tests/test_physics_metrics.py:112-152`
- **What:** The three `TestCalculateDecoupling` tests exercise steady-state, increasing-HR, and decreasing-HR scenarios — none of which produces a work_df with fewer than 2 rows. The critical crash path identified in the prior audit (F-decoupling-empty-half-1): when `work_df` has exactly 1 row, `elapsed = work_df["dt"].cumsum()` is a 1-element Series `[dt_value]`, `midpoint_s = dt_value / 2`, and `first_half = work_df[elapsed <= midpoint_s]` is empty (since `dt_value > dt_value / 2`). Then `float(first_half["dt"].sum())` is 0.0 and the division in `ef_1 = ... / float(first_half["dt"].sum())` raises `ZeroDivisionError`. A test calling `calculate_decoupling` on a single-row DataFrame would expose this crash and confirm (or refute) the finding.
- **Evidence:** Confirmed at lines 112-152: `test_no_drift` uses `sample_activity_df` (100 rows), `test_positive_drift` uses a 600-row DataFrame, `test_negative_drift` uses a 600-row DataFrame. None of the three tests passes a work_df with a single row to `calculate_decoupling`. The ZeroDivisionError crash path when `first_half` is empty (1-row input) is unexercised by any test in the file.
- **Survived adversarial pass:** yes

### [MEDIUM] F-sleep-merge-priority-1 — intent_mismatch
- **Location:** `src/biosystems/wellness/analytics.py:451`
- **What:** compute_sleep_debt() merges Whoop and Garmin sleep-duration columns with the wrong priority. The comment says 'Garmin wins when both exist,' but combine_first() gives Whoop (the caller) priority over Garmin (the argument). For dates in the overlap window where both Whoop and Garmin report sleep duration, the Whoop value is silently kept and the Garmin value is discarded. The correct call should be df["sleep_duration_s_garmin"].combine_first(df["sleep_duration_s"]).
- **Evidence:** Confirmed at line 451: `combined = df["sleep_duration_s"].combine_first(df["sleep_duration_s_garmin"])`. Comment at lines 448-449 reads '# Garmin wins when both exist for a date; Whoop fills earlier history.' `pandas.Series.combine_first()` fills NaN positions in the caller with values from the argument; caller is `sleep_duration_s` (Whoop), so Whoop wins when both sources have data for the same date — the opposite of the stated intent. The fix is to swap caller and argument: `df["sleep_duration_s_garmin"].combine_first(df["sleep_duration_s"])`.
- **Survived adversarial pass:** yes

### [MEDIUM] F-rr-sigma-none-crash-2 — bug
- **Location:** `src/biosystems/wellness/cache.py:393,441`
- **What:** If all Garmin respiratory-rate readings over the calibration window are identical (std=0), calibrate_thresholds() writes a valid but zero-std rr_thresholds dict with amber=red=mean. In compute_wellness_context(), rr_sigma remains None (the rr_std > 0 guard at line 345 blocks assignment). Later at lines 393 and 441, the format expression {rr_sigma:.1f} in an f-string with rr_sigma=None raises TypeError, crashing compute_wellness_context() and by extension the daily brief pipeline. The crash is entered whenever resp_rate >= rr_red (i.e. resp_rate >= mean, which is always true when std=0 and resp_rate equals the constant value).
- **Evidence:** Confirmed. analytics.py:294-300 writes `result["respiratory_rate"] = {"mean": rr_mean, "std": round(rr_std, 2), "amber": rr_mean + 1.5*rr_std, "red": rr_mean + 2.5*rr_std, ...}`. When std=0.0, this dict is non-empty and truthy; amber and red both equal rr_mean. In cache.py line 345: `if rr_mean and rr_std and rr_std > 0:` — `rr_std=0.0` is falsy, so `rr_sigma` stays None. At line 392: `if rr_red and resp_rate >= rr_red:` fires when `rr_red=rr_mean` and `resp_rate >= rr_mean` (guaranteed when std=0 and all readings are constant). Then `f"+{rr_sigma:.1f}σ"` at line 393 with rr_sigma=None raises TypeError. Same crash path at line 441.
- **Survived adversarial pass:** yes

### [MEDIUM] F-iso-week-no-year-4 — bug
- **Location:** `tools/ingest_new_runs.py:281-284`
- **What:** regenerate_weekly_json() builds week_data keyed by ISO week number (1-52) without the year. The study covered W17-W36 of 2025, so no collision has occurred yet. Post-study, as the athlete continues using biosystems (per README intent), runs from 2026 onward will collide with 2025 study data when week numbers repeat. The resulting ef_mean and decoupling_mean aggregates in real_weekly_data.json would silently blend 2025 study sessions with 2026 post-study sessions, corrupting the longitudinal record. Fix: use `f"{dt.isocalendar().year}-W{iso_week:02d}"` as the key.
- **Evidence:** Verified at line 284: `iso_week = dt.isocalendar().week` returns bare int 1-52. Line 304: `week_data.setdefault(iso_week, []).append({"ef": ef, "dec": dec})` keys dict by bare integer. Line 311: `records.append({"week": week, ...})` writes bare integer to output JSON. No year component anywhere in week_data or records dict keying. Post-study 2026 week numbers will collide with 2025 study data.
- **Survived adversarial pass:** yes

### [MEDIUM] F-history-backfill-existing-stale — bug
- **Location:** `src/biosystems/analytics/history.py:230-236`
- **What:** backfill_from_strava() constructs the set of already-known dates once before iterating over Strava summaries. It never updates that set after writing a new entry. When two activities share the same local date, both pass the `run_date in existing` guard; the second call to append_run() silently overwrites the first because the backfill entry has no strava_activity_id, causing append_run to fall back to date-keyed dedup. No warning is emitted and the return value (new_entries) includes both, masking the data loss.
- **Evidence:** Verified at line 230: `existing = {e["date"] for e in load_history()}` built once. Loop at lines 234-264 never updates `existing` after calling `append_run(entry)` at line 263. Entry dict (lines 254-262) contains no `strava_activity_id` field. append_run (line 125) then uses date as the dedup key: `by_key[entry["date"]] = entry`, so the second call overwrites the first. Both entries appear in new_entries (line 264), masking the data loss.
- **Survived adversarial pass:** yes

### [MEDIUM] F-brief-openai-no-fallback — design_defect
- **Location:** `daily_running_brief/daily_running_brief.py:1108-1135`
- **What:** The _chat() fallback chain advertises three providers (OpenRouter -> OpenAI -> Anthropic) but only the first level has exception handling. If OpenAI's chat.completions.create() at line 1124 raises any exception (network timeout, rate limit, invalid model ID, quota), it propagates unhandled and the Anthropic fallback at line 1137 is never reached. The daily running brief cron job (20:00 per CLAUDE.md) therefore fails entirely rather than falling back to Anthropic whenever OpenAI is unavailable.
- **Evidence:** Verified at lines 1108-1112: ImportError-only guard for openai import. Second `if openai_key:` block at line 1113 re-enters outside any try/except. API call at line 1124 (`resp = client.chat.completions.create(**kwargs)`) is entirely unprotected. OpenRouter block (lines 1079-1106) correctly wraps both import and API call in `try: ... except Exception: pass`. Line 1135 returns directly after the API call; Anthropic fallback at line 1137 is unreachable if OpenAI raises any runtime exception.
- **Survived adversarial pass:** yes

### [MEDIUM] F-report-dynamics-keyerror — bug
- **Location:** `src/biosystems/physics/report.py:140`
- **What:** _compute_dynamics() calls dropna(subset=["hr", "pace_min_per_km"]) without first verifying the column exists. Two sibling functions in the same file guard against this case explicitly. When pace_min_per_km is missing, dropna raises KeyError, crashing build_run_report() and surfacing an unhelpful exception instead of returning dynamics=None.
- **Evidence:** Verified at line 140: `valid = run_df.dropna(subset=["hr", "pace_min_per_km"])` with no prior column existence check. Sibling function _compute_stride_splits (line 100) guards: `if "pace_min_per_km" not in df.columns: return []`. The pace_dist block at lines 512-515 guards: `_percentile_stats(run_df["pace_min_per_km"]) if "pace_min_per_km" in run_df.columns else None`. Two siblings explicitly handle the absent-column case; _compute_dynamics does not, and pandas dropna raises KeyError when a subset column is missing.
- **Survived adversarial pass:** yes

### [MEDIUM] F-habitdash-int-crash — bug
- **Location:** `src/biosystems/wellness/habitdash.py:106`
- **What:** _get() calls int() on the x-ratelimit-remaining header value after confirming the header is present but without confirming it is a valid integer string. If a CDN proxy or malformed API response sets x-ratelimit-remaining to a non-numeric string, int() raises ValueError that escapes the try/except (which catches only requests.exceptions.RequestException), aborting the wellness-sync pipeline entirely.
- **Evidence:** Verified at line 106: `if remaining is not None and int(remaining) == 0 and reset_secs is not None:`. The `remaining is not None` guard confirms the header is present but not that it is numeric. The surrounding try/except at line 123 catches only `requests.exceptions.RequestException`. A malformed header value causes `int()` to raise ValueError, which is not a subclass of RequestException and propagates unhandled through _get() and all callers.
- **Survived adversarial pass:** yes

### [MEDIUM] F-cli-analyze-no-walk-filter — intent_mismatch
- **Location:** `src/biosystems/cli.py:102-163`
- **What:** The `biosystems analyze <file>` CLI command computes EF and decoupling from the full DataFrame without adding an is_walk column. The strava and backfill-streams commands both add is_walk before calling run_metrics, so walk segments are excluded from EF and decoupling in those paths. The analyze command omits this step, producing metrics that include warm-up and walk-segment data, contradicting the study's stated Run-Only Filter methodology. The discrepancy is silent — no warning is emitted.
- **Evidence:** Verified at lines 127-143: the analyze command calls parse_fit or parse_gpx, then add_derived_metrics (for .fit), then run_metrics at line 143 — never adding is_walk to df. The strava command (line 287) adds `df["is_walk"] = (df["pace_min_per_km"] > 9.5) | (df["cadence"].fillna(999) < 140)` before calling run_metrics. The analyze command omits this step, meaning EF and decoupling are computed from the full DataFrame including walk segments in that path.
- **Survived adversarial pass:** yes

### [MEDIUM] F-cache-rhr-era-boundary — intent_mismatch
- **Location:** `src/biosystems/wellness/cache.py:271,296`
- **What:** During the Whoop-to-Garmin transition window (approximately 2026-01-01 to 2026-01-06), compute_wellness_context() computed rhr_7d_delta by subtracting a Garmin today-RHR from a Whoop 7-day-mean. The _7d_mean fallback tries Whoop first; for dates within 7 days of the final Whoop reading (2025-12-26 per analytics.py:28), _7d_mean('resting_hr_whoop') returned a non-None Whoop-era value, so rhr_7d_mean never fell through to the Garmin mean. The resulting delta was a cross-device comparison subject to systematic inter-device bias. The specific active window has passed (today 2026-06-17), but the structural issue remains for any future device transition. The _WHOOP_ERA_END constant lives in analytics.py:28, not cache.py.
- **Evidence:** Confirmed cache.py:271-272: rhr_today = (_val(today_row, "resting_hr_whoop") or _val(today_row, "resting_hr_garmin")). Confirmed cache.py:296: rhr_7d_mean = _7d_mean("resting_hr_whoop") or _7d_mean("resting_hr_garmin"). Confirmed cache.py:299-300: rhr_7d_delta = ((rhr_today - rhr_7d_mean) if (rhr_today and rhr_7d_mean) else None). No era gate present; _WHOOP_ERA_END is not imported in cache.py. The or-chain at line 296 means any date where _7d_mean("resting_hr_whoop") returns non-None (i.e., within 7 days of the last Whoop reading) will supply a Whoop-era mean regardless of what device supplied rhr_today, producing a cross-device delta during the transition window.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-avgpace-zdiv-01 — bug
- **Location:** `src/biosystems/physics/metrics.py:292-293`
- **What:** run_metrics() raises ZeroDivisionError when total_dist_m is zero (secs>0). The guard at line 288 only covers zero elapsed time, not zero distance. When the Strava 'distance' stream is absent (strava.py writes df['dist']=np.nan), float(df['dist'].sum()) returns 0.0, avg_speed=0.0, and the unguarded line 293 divides by zero.
- **Evidence:** Confirmed metrics.py:285-293: total_dist_m = float(df["dist"].sum()); secs = float(df["dt"].sum()); if secs <= 0: raise ValueError(...). Guard covers only secs<=0, not zero total_dist_m. avg_speed = total_dist_m / secs at line 292 yields 0.0 when all dist values are NaN (pandas .sum() of all-NaN returns 0.0 in pandas). avg_pace = 1000 / avg_speed / 60 at line 293 then raises ZeroDivisionError. No guard on zero total_dist_m before this division.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-repro-week-no-year-02 — reproducibility
- **Location:** `tools/reproduce_study_analysis.py:85`
- **What:** reproduce_study_analysis.py:85 returns dt.isocalendar()[1] (ISO week number only, 1-53) without the year. If any 2026 processed CSVs exist in data/processed/, runs will hash to the same week-number bucket as 2025 study weeks, silently blending post-study sessions into the study's week-aggregate metrics. The fix is to return a 'YYYY-WNN' string key. This is a distinct occurrence from the analogous defect in ingest_new_runs.py with independent impact on the reproduction script.
- **Evidence:** Confirmed reproduce_study_analysis.py:79-87: function parse_week() returns dt.isocalendar()[1] — a bare integer (1-53) with no year component. The function is 9 lines; no year suffix is appended anywhere in or after the return. If 2026 CSVs with matching YYYYMMDD filenames exist in data/processed/, week 17 of 2026 hashes to key 17, identical to study week 17 of 2025, causing silent blending.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-report-no-tests-04 — test_gap
- **Location:** `src/biosystems/physics/report.py`
- **What:** src/biosystems/physics/report.py has zero test coverage: no test file exists for build_run_report() or any of its internal helpers (_compute_dynamics, _compute_aev, _detect_strides, _parse_km_splits, _parse_laps, _compute_walk_summary, _compute_ef_reliability). This is the most complex integration function in the library and the critical output layer for the daily-use strava command. Multiple independently-catalogued crash paths in this file are entirely undetected by CI.
- **Evidence:** Confirmed via Glob of tests/**/*.py (16 test files found, none named test_report.py or test_physics_report.py) and Grep across all test files for 'from biosystems.physics.report' and 'build_run_report|_compute_dynamics|_compute_aev|_parse_km_splits|_parse_laps' — zero matches in all 16 test files. report.py is the most complex integration function in the library and the critical output layer for the daily-use strava command. Multiple crash paths documented in this audit have zero CI coverage.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-cli-zdiv-summary-01 — bug
- **Location:** `src/biosystems/cli.py:812-817`
- **What:** The summary CLI command builds all_efs and all_decs as independent list comprehensions with different filter predicates. The only guard before the format string at line 817 is 'if all_efs:', which does not ensure all_decs is non-empty. When entries contain EF values but no decoupling values (common for runs where EF was computable but decoupling was not), sum(all_decs)/len(all_decs) raises ZeroDivisionError, crashing the summary command.
- **Evidence:** Confirmed cli.py:812: all_efs = [e["ef"] for e in entries if e.get("ef")]; cli.py:813: all_decs = [e["decoupling_pct"] for e in entries if e.get("decoupling_pct") is not None]; cli.py:814: if all_efs:; cli.py:817: sum(all_decs)/len(all_decs). The guard tests only all_efs; all_decs is not independently guarded. If every entry has an EF value but none has decoupling_pct, all_decs=[] and len([])=0 raises ZeroDivisionError.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-report-dynamics-rangeidx-03 — intent_mismatch
- **Location:** `src/biosystems/physics/report.py:144-147`
- **What:** _compute_dynamics() claims to split the run at its temporal midpoint to measure HR drift. The midpoint arithmetic is correct for DatetimeIndex inputs (FIT/Strava) but degenerates to a sample-count midpoint for RangeIndex inputs (GPX DataFrames from parse_gpx()). GPX data commonly has variable sample intervals, so a sample-count split can place the midpoint at a different elapsed time than intended, producing incorrect HR drift and pace strategy values for GPX-sourced runs. In current production, build_run_report is only called from Strava paths; the defect is latent for future GPX integration.
- **Evidence:** Confirmed report.py:144-147: midpoint = valid.index[0] + (valid.index[-1] - valid.index[0]) / 2. For DatetimeIndex (Strava), this yields a calendar temporal midpoint (Timestamp + Timedelta/2 = Timestamp). For RangeIndex integers (GPX after reset_index(drop=True) at gpx.py:178), index[0]=0 and index[-1]=n-1 (ints), giving midpoint=(n-1)/2.0 — a sample-count midpoint, not a temporal one. No error is raised; the arithmetic silently produces semantically wrong HR drift and pace strategy values for variable-interval GPX files. build_run_report is currently only called from Strava paths (cli.py:333, cli.py:670); defect is latent.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-walk-rangeidx-crash-05 — bug
- **Location:** `src/biosystems/signal/walk_detection.py:199-217`
- **What:** walk_block_segments() assumes its input DataFrame has a DatetimeIndex (docstring line 168 confirms). GPX DataFrames have a RangeIndex because parse_gpx() calls reset_index(drop=True). The cast() calls at lines 203-204 and 209-210 are no-ops at runtime; when idx is an integer, the subtraction yields an int and .total_seconds() raises AttributeError. The error is caught and discarded by the caller's broad except clause, so GPX activity walk detection silently returns nothing rather than raising a visible error. In current production, build_run_report is only invoked from Strava paths, making this a latent rather than active bug.
- **Evidence:** Confirmed walk_detection.py:199-217: for _, (idx, row) in enumerate(gpx_df.iterrows()); cast() calls at lines 203-204 and 209-210 are type-annotation-only no-ops at runtime. Confirmed walk_detection.py:224-226: session_start = gpx_df.index[0]; session_end = gpx_df.index[-1]; session_duration = (session_end - session_start).total_seconds(). For RangeIndex integers, (n-1 - 0) yields an int; .total_seconds() on int raises AttributeError. Additionally, at line 210, (cast(pd.Timestamp, idx) - last_walk_idx).total_seconds() would be int subtraction, also raising AttributeError for integer idx. Error swallowed by report.py:267 broad except. build_run_report currently only called from Strava paths (DatetimeIndex); defect is latent.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-strava-name-lost-02 — design_defect
- **Location:** `src/biosystems/cli.py:330`
- **What:** When the user runs biosystems strava <id> (specific-activity fetch), activity_name is always serialized as null in the history entry and run report. The Strava API returns name in every activity response, but fetch_activity_streams() in src/biosystems/ingestion/strava.py:489-502 constructs activity_meta without including activity['name'], and cli.py:330 explicitly nullifies the name for any ID-specific call. The run name field is silently lost for all direct-ID analyses.
- **Evidence:** Verified: cli.py:330 reads activity_name_str = summary.get('name') if activity_id is None else None — name is unconditionally set to None for direct-ID calls. strava.py:489-502 (fetch_activity_streams) builds activity_meta with keys: best_efforts, splits_metric, max_heartrate, max_speed, calories, total_elevation_gain, perceived_exertion, workout_type, device_name, description, laps, pr_count — 'name' is absent. The activity response variable 'activity' at line 484 contains name (used for start_date etc.) but it is never extracted into activity_meta. cli.py:358 writes 'activity_name': activity_name_str, always None for biosystems strava <id> calls.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-brief-reasoning-flag-05 — intent_mismatch
- **Location:** `daily_running_brief/daily_running_brief.py:57`
- **What:** The _REASONING_PREFIXES tuple includes the prefix 'gpt-5' to handle hypothetical future GPT-5 reasoning models (analogous to o1/o3/o4). However, _OPENAI_MODEL = 'gpt-5-mini' starts with 'gpt-5', so is_reasoning=True is set for a standard auto-regressive model. The effect is that temperature=0 is never passed, causing all narrative sections of the daily brief to be generated at the model's default stochastic temperature. The same run analyzed twice in a row may produce different text, which undermines reproducibility of the brief's interpretations.
- **Evidence:** Verified: _OPENAI_MODEL = 'gpt-5-mini' at line 56. _REASONING_PREFIXES = ('o1', 'o3', 'o4', 'gpt-5') appears identically at lines 1086 (openrouter branch) and 1116 (openai branch). 'gpt-5-mini'.startswith('gpt-5') evaluates to True in both branches, so is_reasoning=True. At lines 1092-1093 and 1122-1123, temperature=0 is only set when not is_reasoning, so it is never set for gpt-5-mini. The prefix 'gpt-5' is overly broad, accidentally capturing gpt-5-mini, which is a standard autoregressive model that accepts temperature.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-metrics-pace-keyerror-06 — bug
- **Location:** `src/biosystems/physics/metrics.py:302`
- **What:** In run_metrics(), the call to compute_training_zones() passes df['pace_sec_km'] directly with no column existence guard. The column must be derived (via add_derived_metrics() for FIT files, or computed inline for GPX). A caller who passes a raw FIT DataFrame gets an unhelpful KeyError with no hint that add_derived_metrics() must be called first. A similar guard is already present for other optional columns (e.g., 'cadence' at line 307, 'ele' at line 315).
- **Evidence:** Verified: at lines 301-303, compute_training_zones(df['hr'], df['pace_sec_km'], zone_config) accesses df['pace_sec_km'] directly with no prior column existence check. The function body shows guarded column accesses for 'cadence' (line 307: if 'cadence' in df.columns) and 'ele' (line 315: if 'ele' in df.columns), making the absence of a guard for 'pace_sec_km' a clear inconsistency. A caller with a raw FIT DataFrame that has not yet had pace_sec_km derived gets an unhelpful KeyError.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-walk-heart-rate-col-07 — bug
- **Location:** `src/biosystems/signal/walk_detection.py:259`
- **What:** In walk_block_segments(), the heart-rate aggregation for each segment checks for the column name 'heart_rate', but both parsers (GPX at gpx.py:176 and FIT at fit.py:146-147) produce the column as 'hr'. As a result, WalkSegment.avg_hr and the max_hr field in summarize_walk_segments() are always NaN regardless of whether heart-rate data is present in the activity. The avg_cad check immediately below uses the correct column name 'cadence', making the HR check the only mismatch. Test fixtures happen to use 'heart_rate', so tests pass while production always silently drops HR data for walk segments.
- **Evidence:** Verified: walk_detection.py:259 checks 'heart_rate' in grp_df.columns. gpx.py:176 creates the DataFrame with columns=['time', 'lat', 'lon', 'ele', 'hr', 'cadence', 'power'] — column is 'hr'. fit.py:145-147 renames heart_rate -> hr ('if heart_rate in df.columns: df = df.rename(columns={heart_rate: hr})') — column is also 'hr' after renaming. Both parsers produce 'hr', not 'heart_rate'. test_walk_detection_fix.py:14 and test_signal.py:190 both use 'heart_rate' as the column name in their constructed DataFrames, so tests pass but production GPX/FIT data always results in avg_hr=NaN. The avg_cad check at line 261 correctly checks 'cadence' (which matches both parsers), making the 'heart_rate' check the sole column-name mismatch.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-walk-fillna-intent-10 — intent_mismatch
- **Location:** `src/biosystems/cli.py:287`
- **What:** The production walk-classification in cli.py uses fillna(999) to handle missing cadence values, treating sensor-dropout points as high-cadence (running) unless pace alone flags them as walks. The test file test_walk_classification.py documents the intended behavior as fillna(0) (NaN cadence treated as 0 spm → < 140 → walk) and asserts that test_nan_cadence_is_walk should pass. Because the test file defines its own local classify_walk() instead of importing from production code, this discrepancy is never caught by the test suite. Whether fillna(0) or fillna(999) is correct determines whether all sensor-dropout points are systematically misclassified as run or walk, affecting EF and decoupling calculations.
- **Evidence:** Verified: cli.py:287 uses df['cadence'].fillna(999) < 140 and cli.py:657 uses the identical fillna(999) pattern. tests/test_walk_classification.py:26 defines the local classify_walk() using df['cadence'].fillna(0) < 140. The docstring at line 21-24 explicitly states 'Missing cadence values are treated as 0.' test_nan_cadence_is_walk at lines 60-67 asserts a row with pace_min_per_km=5.0 and cadence=NaN must be is_walk=True. With fillna(0): 0 < 140 → True → walk. With production fillna(999): 999 < 140 → False, and pace 5.0 < 9.5 → False, so is_walk=False — a sensor-dropout point is classified as running, contradicting the test's documented intent. The test's local classify_walk() does not import from production code, so this divergence is never caught.
- **Survived adversarial pass:** yes

### [MEDIUM] F-new-ingest-nan-cadence-study-14 — reproducibility
- **Location:** `tools/ingest_new_runs.py:101`
- **What:** The `_add_walk_flag()` in the study-data ingestion tool classifies cadence-sensor-dropout rows as running because the bare `< 140` comparison silently returns False for NaN. This is distinct from the cli.py variant (F-new-walk-fillna-intent-10, which uses `fillna(999)`) because this tool was used to produce `real_weekly_data.json`, the ground-truth weekly EF values against which the reproducibility analysis validates. If any training runs had cadence dropouts, those sections are counted as running in the published study data, systematically under-counting walk time and inflating per-run EF values in the study record.
- **Evidence:** Direct read of `_add_walk_flag()` confirms `df['is_walk'] = (df['pace_min_per_km'] > 9.5) | (df['cadence'] < 140)` at line 101 with no `.fillna()` preceding the cadence comparison (lines 96-104 show only `df = df.copy()` and `df['is_walk'] = False` before the assignment). `regenerate_weekly_json()` at line 259 reads all `*_summary.csv` files, and `main()` at line 452 calls it unconditionally unless `--no-weekly` is passed, confirming this tool produces `real_weekly_data.json`.
- **Survived adversarial pass:** yes

### [LOW] F-ef-zero-dt-6 — bug
- **Location:** `src/biosystems/physics/metrics.py:148-151`
- **What:** calculate_efficiency_factor can divide by zero if work_df's dt.sum() is 0. The run_metrics caller guards the full-df case but not the filtered work_df case. Pathological inputs (all dt=0 after walk/zone filtering) produce ZeroDivisionError instead of a clear ValueError.
- **Evidence:** Confirmed at metrics.py:148-151: secs = float(work_df["dt"].sum()); avg_speed = total_dist_m / secs. The outer guard at metrics.py:288-289 checks the FULL df secs ('if secs <= 0: raise ValueError'), not work_df's secs inside calculate_efficiency_factor. If all rows in work_df have dt=0 after walk/zone filtering, secs=0.0 and division by zero raises ZeroDivisionError. The guard does not protect the filtered work_df path.
- **Survived adversarial pass:** yes

### [LOW] F-gap-loop-perf-8 — perf
- **Location:** `src/biosystems/physics/gap.py:171-185`
- **What:** GAP computation uses two Python for-loops with .iloc[i] indexing. Complexity is O(n) not O(n²) as previously claimed (.iloc is O(1)). However, Python-loop-over-pandas is 10-100x slower than equivalent vectorized operations. For long-distance events this is the hot path in the strava CLI command and could be meaningfully improved via vectorized grade and Minetti computations.
- **Evidence:** Confirmed at gap.py:171-186: two Python for-loops over range(len(df)) using .iloc[i] for reads and writes. .iloc is O(1) integer-position access, making each loop O(n) total — the original O(n²) claim was incorrect. However, Python-loop-over-pandas incurs substantially higher per-row overhead than vectorized numpy operations due to Python call overhead and type boxing. For a typical 3600-point activity the absolute time is acceptable, but for long-distance events (10000+ points) this is the hot path.
- **Survived adversarial pass:** yes

### [LOW] F-cadence-int-truncation-10 — bug
- **Location:** `src/biosystems/physics/metrics.py:310`
- **What:** Average cadence is computed with int() which truncates rather than rounds. For typical running cadence (160-180 spm), a mean of 163.8 reports as 163 instead of 164. Inconsistent with all other metrics in run_metrics which use round(). The avg_cadence field in PhysiologicalMetrics is declared as int | None, so rounding before int() conversion is the appropriate pattern.
- **Evidence:** Confirmed at metrics.py:310: avg_cadence = int(cadence_series.mean()). Confirmed at metrics.py:334-341: all other PhysiologicalMetrics fields use round() — distance_km=round(...,2), duration_min=round(...,1), avg_pace_min_per_km=round(...,2), avg_hr=round(...,1), efficiency_factor=round(...,5), decoupling_pct=round(...,2), hr_tss=round(...,1). int() truncates toward zero; a mean of 179.9 spm reports as 179. Confirmed at models.py:154: avg_cadence: int | None = Field(None, gt=0), matching the int return type but not the truncation semantics relative to all other rounded fields.
- **Survived adversarial pass:** yes

### [LOW] F-decoupling-ef1-small-12 — bug
- **Location:** `src/biosystems/physics/metrics.py:217`
- **What:** calculate_decoupling divides by ef_1 at line 217 without guarding against zero values. A GPS dropout during the first half of work data (watch records HR but dist=0) produces ef_1=0.0, causing ZeroDivisionError. Unlike F-decoupling-empty-half-1 (empty first_half), this bug fires at the final division step when first_half is non-empty but all-zero-distance.
- **Evidence:** Confirmed at metrics.py:217: decouple_pct = abs(ef_2 - ef_1) / ef_1 * 100. No guard for ef_1==0. Distinct from F-decoupling-empty-half-1: this fires when first_half is non-empty but all rows have dist=0 (GPS dropout during first half). ef_1 = float(0.0) / float(dt_sum) / float(hr_mean) = 0.0 when dt_sum > 0 and hr_mean > 0 (no ZeroDivisionError at this step). Then abs(ef_2 - 0.0) / 0.0 * 100 raises ZeroDivisionError. No clamp or guard at line 217 or anywhere in calculate_decoupling for this case.
- **Survived adversarial pass:** yes

### [LOW] F-stride-endpoint-inclusive-13 — bug
- **Location:** `src/biosystems/physics/report.py:116-117`
- **What:** Stride segment extraction uses df.loc[start_idx:idx] where idx is the first row NOT in the stride. Because DatetimeIndex label slicing is inclusive on both ends, the ending non-stride row is included in seg_df. This overestimates stride duration by one dt interval and biases average stride pace slightly slower (the terminating non-fast row is included in the mean). The correct slice should be df.loc[start_idx:idx].iloc[:-1] or use exclusive slicing.
- **Evidence:** Verified at lines 108-133. Line 115 elif triggers when `not is_fast and in_stride`, so `idx` is the first NON-stride row. Line 116: `seg_df = df.loc[start_idx:idx]` — pandas label-based .loc on a DatetimeIndex is inclusive on both ends, confirmed by direct inspection. The terminating non-stride row at `idx` is included in the slice. Lines 117-119 compute `seg_df['dt'].sum()` and `seg_df['pace_min_per_km'].mean()` over the enlarged set. No off-by-one compensation exists. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-maxhr-walk-semantics-14 — intent_mismatch
- **Location:** `src/biosystems/signal/walk_detection.py:129-139`
- **What:** summarize_walk_segments returns max_hr as max(segment_avg_hrs) — the maximum of per-segment average heart rates — not the maximum instantaneous HR observed during any walk segment. This value is stored as WalkSummary.max_hr and displayed in CLI output as if it were peak HR. For a walk segment with avg_hr=130 bpm but transient peak of 150 bpm (common after a running burst), the reported max_hr=130 significantly understates physiological load.
- **Evidence:** Verified at lines 129-131: `hrs = [s['avg_hr'] for s in valid_segments if ...]` collects per-segment average HRs from segment dicts. Line 139: `max_hr = max(hrs) if hrs else np.nan` returns the maximum of those averages. walk_block_segments docstring at line 184 explicitly labels avg_hr as 'Mean heart rate (rounded to 1 decimal)', confirming avg_hr is a mean, not a peak. No peak or instantaneous HR is ever stored in segment dicts. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-fit-pace-unsmoothed-15 — intent_mismatch
- **Location:** `src/biosystems/ingestion/fit.py:225-230 vs src/biosystems/ingestion/gpx.py:204-207`
- **What:** GPX-derived pace_sec_km uses a 5-point centered rolling mean of speed_mps, producing smoothed pace values suitable for zone classification and walk detection. FIT-derived pace_sec_km uses raw per-segment speed (instantaneous haversine distance / dt), which is noisy for the typical 1-second sampling of Garmin devices. This inconsistency means the same pace threshold (e.g. 9.5 min/km walk cutoff) is applied to smooth data for GPX but to noisy data for FIT, potentially causing spurious walk/run misclassifications in FIT-sourced activities.
- **Evidence:** Verified in fit.py lines 225-230: `df['speed_mps'] = df['dist'] / df['dt'].replace(0, np.nan)` at line 226, backfill at line 227, and `df['pace_sec_km'] = 1000 / df['speed_mps'].replace(0, np.nan)` at line 230 — no rolling smoothing applied. Verified in gpx.py lines 202-207: same raw speed calculation followed by `df['speed_mps_smooth'] = df['speed_mps'].rolling(window=5, center=True, min_periods=1).mean()` at line 204, and pace at line 207 uses the smoothed column. Asymmetry confirmed. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-strava-3 — bug
- **Location:** `src/biosystems/ingestion/strava.py:345`
- **What:** Line 345 is a bare expression statement: len(streams['time']). The computed integer is immediately discarded with no side effects. This is a no-op that looks like a debugging artifact — likely the remnant of a now-removed variable assignment (e.g. n = len(...)). It wastes a dict lookup and function call on every stream parse and will confuse future readers searching for its purpose.
- **Evidence:** Verified at line 345: `len(streams['time'])` is a standalone expression statement. Line 346 creates a DataFrame from `timestamps` without referencing the computed length. The integer result is computed and immediately discarded with no assignment, assertion, print, or side effect. Confirmed dead code. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-strava-4 — bug
- **Location:** `src/biosystems/ingestion/strava.py:163`
- **What:** _refresh_access_token() accesses resp.json()['access_token'] without confirming the key exists. Although raise_for_status() guards against HTTP error codes, an OAuth2 error response that arrives with a 2xx status (some providers do this) or a future API change would raise an uninformative KeyError: 'access_token' rather than a meaningful credential error. CLI callers (cli.py:213-218) catch generic Exception and surface the raw exception text, so the user would see the opaque KeyError.
- **Evidence:** Verified at lines 162-163: `resp.raise_for_status()` then `return resp.json()['access_token']` with no .get() or key-existence check. raise_for_status() only guards HTTP error codes; a 2xx response without 'access_token' raises uninformative KeyError. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-habitdash-1 — design_defect
- **Location:** `src/biosystems/wellness/habitdash.py:106-108`
- **What:** The x-ratelimit-reset header is parsed as seconds-until-reset, but many REST APIs use this header as a Unix epoch timestamp of when the window resets (e.g. GitHub, Twitter/X). If HabitDash uses epoch semantics, int(reset_secs) yields ~1.7 billion; the min(..., 3600) cap always fires, causing the client to sleep 1 hour every time x-ratelimit-remaining reaches 0. Without HabitDash API documentation confirming seconds vs. epoch semantics, the interpretation is unverifiable from the source alone.
- **Evidence:** Verified at lines 105-107: `reset_secs = resp.headers.get('x-ratelimit-reset')` and `wait = min(int(reset_secs) + 1, 3600)`. If x-ratelimit-reset is a Unix epoch timestamp (~1.7B), `min(1700000001, 3600)` always returns 3600, causing a 1-hour sleep on every rate-limit exhaustion. No comment or documentation in the source clarifies whether HabitDash uses seconds-until-reset or epoch-timestamp semantics. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-weather-2 — design_defect
- **Location:** `src/biosystems/environment/weather.py:234`
- **What:** datetime.utcnow() is deprecated since Python 3.12 and emits DeprecationWarning. The CI matrix includes Python 3.12 (per .github/workflows/test.yml). The correct modern replacement is datetime.now(timezone.utc); the timezone import is already present in the module at line 12, making this a trivial fix.
- **Evidence:** Verified at line 234: `now = datetime.utcnow()`. Verified at line 12: `from datetime import datetime, timedelta, timezone` — timezone is imported. Verified in .github/workflows/test.yml line 17: `python-version: ['3.10', '3.11', '3.12']` — Python 3.12 is in the CI matrix. `datetime.utcnow()` is deprecated since Python 3.12 and emits DeprecationWarning. Location, evidence, severity, and class verified accurate.
- **Survived adversarial pass:** yes

### [LOW] F-sanitize-3 — design_defect
- **Location:** `tools/sanitize_gps.py:217-265`
- **What:** The CLI does not validate that output_path differs from input_path. Running `sanitize_gps.py data/ data/ --recursive` would overwrite original GPS-containing files with sanitized versions, destroying raw data with no warning prompt, confirmation flag, or dry-run check before the overwrite. This is particularly dangerous because the tool is safety-critical: a mistaken invocation can silently and irreversibly destroy the athlete's original raw activity files.
- **Evidence:** Lines 217-218 confirmed: input_path = Path(args.input) / output_path = Path(args.output) with no subsequent equality check. Directory loop at lines 252-258 confirmed: output_file = output_path / relative_path — when output_path==input_path this resolves to the original file path. No guard, confirmation flag, warning, or dry-run option exists anywhere in main() between lines 215-269.
- **Survived adversarial pass:** yes

### [LOW] F-brief-1 — doc_drift
- **Location:** `daily_running_brief/daily_running_brief.py:27`
- **What:** The module docstring states 'OpenAI is primary, Anthropic is fallback' and lists only ANTHROPIC_API_KEY and OPENAI_API_KEY as requirements. However, _chat() (lines 1075-1106) actually tries OPENROUTER_API_KEY first, then OPENAI_API_KEY, then ANTHROPIC_API_KEY. The OPENROUTER_API_KEY variable is not mentioned anywhere in the docstring or in the error message at line 1158. OpenRouter users receive no documentation of their option.
- **Evidence:** Line 26 confirmed: 'ANTHROPIC_API_KEY  (or OPENAI_API_KEY — OpenAI is primary, Anthropic is fallback)'. Lines 1075-1106 confirmed: _chat() tries OPENROUTER_API_KEY first (line 1075), then OPENAI_API_KEY (line 1108), then ANTHROPIC_API_KEY (line 1137). Error message at lines 1157-1158 confirmed: 'No API key found. Set OPENAI_API_KEY (preferred, cheaper) or ANTHROPIC_API_KEY.' — OPENROUTER_API_KEY is omitted from both the module docstring and the error message.
- **Survived adversarial pass:** yes

### [LOW] F-test-2 — test_gap
- **Location:** `src/biosystems/wellness/habitdash.py`
- **What:** No test file exists for habitdash.py. The HabitDashClient._get() retry logic, proactive rate-limit header handling, and the silent-empty-return on exhausted retries are all untested. Silent data loss on network failure — where fetch_all_metrics() returns [] with only a log.error() call — has no regression coverage.
- **Evidence:** Glob of tests/*.py confirmed no test_habitdash.py exists. Grep for 'habitdash' across all tests/ files returned no matches. habitdash.py confirmed present with _MAX_RETRIES=3 at line 25 and _RETRY_WAIT=60.0 at line 26; retry logic and fetch_all_metrics() silent-empty-return on exhausted retries are all untested.
- **Survived adversarial pass:** yes

### [LOW] F-doc-08 — doc_drift
- **Location:** `README.md:311`
- **What:** The README states 161 tests at two locations (lines 238 and 311) but pytest currently collects 185. Tests have been added since the README was last updated with this count. While a minor issue, it creates a credibility gap if reviewers attempt to reproduce CI numbers.
- **Evidence:** README.md line 238 confirmed: 'tests/ # Automated test suite (161 tests)'. README.md line 311 confirmed: 'Comprehensive Test Suite - 161 tests across Python 3.10/3.11/3.12 with automated CI validation'. Both locations undercounting; Stage-1 pytest collection reported 185 tests. README discrepancy confirmed at both cited lines. The 185 figure is inherited from Stage-1 and was not independently verified by running pytest in this batch.
- **Survived adversarial pass:** yes

### [LOW] F-intent-02 — intent_mismatch
- **Location:** `src/biosystems/models.py:294,src/biosystems/signal/walk_detection.py:267-277`
- **What:** The WalkSegment model defines 'pause' as a valid tag value via regex pattern, but the walk_block_segments() implementation never emits it. Short mid-session micro-stops are labeled 'mid-session' with a 'pause?' note field instead. The model contract (which documents what values are valid) and the producing code are out of sync, creating confusion about how to interpret the 'pause' option in the model for future callers.
- **Evidence:** models.py line 294 confirmed: 'tag: str = Field(..., pattern="^(warm-up|mid-session|cool-down|pause)$")'. walk_detection.py lines 268-273 confirmed: assigns only 'warm-up' (start_offset < 60s), 'cool-down' (session_duration - end_offset < 120s), or 'mid-session' (else branch). Lines 276-278 confirmed: sets note='pause?' on short mid-session segments (dur_s<30, dist_km<0.05) but tag remains 'mid-session'. No code path in the function ever assigns tag='pause'. Verified by direct read of both files.
- **Survived adversarial pass:** yes

### [LOW] F-design-01 — design_defect
- **Location:** `src/biosystems/ingestion/fit.py:225-230,src/biosystems/ingestion/gpx.py:202-207`
- **What:** The GPX parser smooths speed with a 5-point centered rolling mean before computing pace_sec_km, suppressing GPS noise. The FIT parser's add_derived_metrics() computes raw instantaneous speed with no smoothing. The same activity file in FIT vs GPX format would produce different pace_sec_km distributions, leading to different EF and decoupling values. This asymmetry is undocumented.
- **Evidence:** gpx.py lines 202-207 confirmed: speed_mps computed, then speed_mps_smooth via 5-point centered rolling mean (min_periods=1), then pace_sec_km = 1000 / speed_mps_smooth.replace(0, np.nan). fit.py lines 225-230 confirmed: speed_mps = dist / dt.replace(0, np.nan) with bfill, then pace_sec_km = 1000 / speed_mps.replace(0, np.nan) — no rolling average applied. Asymmetry confirmed at source in both files.
- **Survived adversarial pass:** yes

### [LOW] F-bug-01 — bug
- **Location:** `src/biosystems/analytics/history.py:211`
- **What:** The backfill_from_strava() function has a type annotation referencing ZoneConfig which is not imported in history.py. The 'from __future__ import annotations' at line 12 defers evaluation, preventing a runtime error at import time, but any tool that calls get_type_hints() (e.g., Pydantic, doc generators, runtime type checkers) would raise NameError. The acknowledged suppression comment confirms this is a known broken annotation rather than an intentional forward reference.
- **Evidence:** history.py top-level imports confirmed (lines 1-19): only 'import json', 'import os', 'from pathlib import Path', 'from typing import Any', 'from filelock import FileLock'. No ZoneConfig import anywhere in the file. history.py line 12 confirmed: 'from __future__ import annotations'. backfill_from_strava() function signature confirmed at line 211: 'zone_config: ZoneConfig,  # type: ignore[name-defined]  # noqa: F821'. The suppression comment explicitly acknowledges the broken annotation.
- **Survived adversarial pass:** yes

### [LOW] F-cli-dead-1 — bug
- **Location:** `src/biosystems/cli.py:415`
- **What:** Line 415 computes a list comprehension whose result is immediately discarded — the expression is a bare statement with no assignment. This is a no-op and appears to be the remnant of a refactor where a variable (e.g. `first_bests`) was removed but the comprehension was not cleaned up. The surrounding context suggests the variable was intended to control whether a 'first recorded' header was printed; that logic is now handled inline by the `elif bb.is_new_best:` branch at line 427, so the dead expression serves no purpose.
- **Evidence:** cli.py line 414 confirmed: 'new_bests = [bb for bb in report.block_bests if bb.is_new_best and bb.prev_best_s is not None]'. Line 415 confirmed: '[bb for bb in report.block_bests if bb.is_new_best and bb.prev_best_s is None]' as a bare expression with no assignment. Line 427 confirmed: 'elif bb.is_new_best:' handles first-recorded entries inline. Dead comprehension verified at source.
- **Survived adversarial pass:** yes

### [LOW] F-cli-dead-2 — bug
- **Location:** `src/biosystems/cli.py:526`
- **What:** Inside the `backfill_efforts` command, line 526 calls `summary.get("moving_time", 0)` as a bare expression whose return value is never assigned or used. This is a silent no-op. The moving_time value was presumably needed to compute pace or log duration for a minimal history entry, but the variable assignment was removed without removing the access. The per-entry output at line 539 confirms moving_time is never used.
- **Evidence:** cli.py line 525 confirmed: 'dist_km = round(summary.get("distance", 0) / 1000, 2)'. Line 526 confirmed: 'summary.get("moving_time", 0)' as a bare expression — return value never assigned or used. Entry dict built at lines 528-535 without moving_time. Line 539 confirmed: output format does not include moving_time. Bare expression is a verified no-op.
- **Survived adversarial pass:** yes

### [LOW] F-cli-types-3 — design_defect
- **Location:** `src/biosystems/cli.py:1109-1110`
- **What:** The `wellness_sync` command parameters `date_start` and `date_end` are annotated as `str` but their defaults are `None`, making the annotation incorrect — both should be `str | None`. This inconsistency causes mypy to flag a type error and misleads callers about valid argument types. Comparable parameters in the same file use the correct annotation. The Typer library uses the annotation to choose how to convert CLI input, so an incorrect annotation can affect option parsing behavior in edge cases.
- **Evidence:** cli.py lines 1109-1110 confirmed: 'date_start: str = typer.Option(None, "--from", help="Start date YYYY-MM-DD (overrides --days)")' and 'date_end: str = typer.Option(None, "--to", help="End date YYYY-MM-DD (default: today)")'. Both annotated as 'str' but default to None. Annotation should be 'str | None' to be type-correct.
- **Survived adversarial pass:** yes

### [LOW] F-cli-date-5 — design_defect
- **Location:** `src/biosystems/cli.py:751`
- **What:** The `--since` / `--after` date filters in the `summary`, `efforts`, `top`, and `backfill-streams` commands compare ISO date strings lexicographically against an unvalidated user-supplied string. If a user passes a non-zero-padded date (e.g. `--since 2025-1-1` instead of `--since 2025-01-01`), string comparison is incorrect: `"2025-01-05" >= "2025-1-1"` evaluates to `False` because `'0' < '1'` in ASCII, silently excluding valid entries. No datetime parsing, format validation, or user-facing error is applied to the `--since` / `--after` option values. The help text specifies YYYY-MM-DD but there is no enforcement.
- **Evidence:** Confirmed at line 751: `entries = [e for e in entries if e.get("date", "") >= since]`. The `since` variable is the raw string from the `--since` typer Option with no parsing or validation applied before this comparison. String comparison `"2025-01-05" >= "2025-1-1"` evaluates to False because `'0' < '1'` in ASCII. No datetime parsing, format enforcement, or error occurs for non-zero-padded input.
- **Survived adversarial pass:** yes

### [LOW] F-history-fwd-6 — design_defect
- **Location:** `src/biosystems/analytics/history.py:211`
- **What:** `backfill_from_strava()` annotates its `zone_config` parameter as `ZoneConfig` but `ZoneConfig` is not imported anywhere in `history.py`. The `# type: ignore[name-defined]` comment silences mypy and `# noqa: F821` silences flake8, so the error is never surfaced in CI. Under `from __future__ import annotations` (line 12), Python defers evaluation of annotations so no runtime `NameError` occurs, but the intent to enforce the ZoneConfig contract is completely nullified — any object with a `.threshold_hr` attribute passes silently. The pattern used in the call site (`cli.py:1060`) imports ZoneConfig from `biosystems.models` and passes a validated instance, so there is no runtime defect today, but the suppressed import creates a maintenance trap.
- **Evidence:** Confirmed: `from __future__ import annotations` is at line 12; imports block (lines 13-19) imports json, os, Path, Any, and FileLock only — no ZoneConfig present. Line 211 reads `zone_config: ZoneConfig,  # type: ignore[name-defined]  # noqa: F821`, exactly as described. Under PEP 563 deferred evaluation, no NameError fires at runtime. The suppression comments confirm the import was intentionally omitted while the annotation was retained.
- **Survived adversarial pass:** yes

### [LOW] F-analytics-dead-7 — bug
- **Location:** `src/biosystems/wellness/analytics.py:74`
- **What:** In `compute_coverage()`, line 74 computes the total index span in days as `(df.index.max() - df.index.min()).days + 1` but the result is assigned to nothing — it is a bare expression statement that is immediately discarded. The per-metric span computed at line 83 (`span = (end - start).days + 1`) is the one actually used for `pct_coverage`. This appears to be a remnant of a refactor that removed a `total_span` variable, leaving the dead computation in place.
- **Evidence:** Confirmed at line 74: bare expression statement `(df.index.max() - df.index.min()).days + 1` with no assignment or side effect. Line 75 is `rows = []`. The per-metric span at line 83 (`span = (end - start).days + 1`) is the only span variable actually consumed in the function body. The total-index computation at line 74 is dead code.
- **Survived adversarial pass:** yes

### [LOW] F-fit-perf-8 — perf
- **Location:** `src/biosystems/ingestion/fit.py:214-222`
- **What:** `add_derived_metrics` computes segment distances via a Python list comprehension with four `.iloc[i]` calls per iteration. For a 3,600-row (60-min, 1 Hz) FIT activity, this performs 14,400 pandas row-index accesses. A vectorized approach using `df["latitude"].shift(1)` and `df["longitude"].shift(1)` would compute all consecutive pairs in two O(n) pandas operations, eliminating the Python-loop overhead. The analogous pattern in the GPX parser (gpx.py:204) was separately identified; this is a lower-severity variant because `.iloc` in a list comprehension has O(1) per access rather than O(n), but the Python-loop overhead is still substantial for long activities.
- **Evidence:** Confirmed at lines 214-222: `seg_dist = [0.0] + [_haversine(df["latitude"].iloc[i - 1], df["longitude"].iloc[i - 1], df["latitude"].iloc[i], df["longitude"].iloc[i]) for i in range(1, len(df))]`. Four `.iloc[i]` accesses per iteration in a Python loop over all rows. Vectorized alternatives using `.shift(1)` exist but are not used.
- **Survived adversarial pass:** yes

### [LOW] F-testcov-2 — test_gap
- **Location:** `tests/test_cli_integration.py:17-22`
- **What:** The subprocess.run call passes `env={"PYTHONPATH": "src"}` which creates a completely new environment with only one variable, discarding PATH, HOME, USER, and all other inherited env vars. While `sys.executable` is used directly (avoiding PATH resolution for Python itself), the `dotenv.load_dotenv()` call in cli.py relies on finding `.env` relative to the CWD or its parents; `HOME` is needed on some systems to locate the XDG config path; and any C extension loaded by numpy/pandas/fitdecode may rely on LD_LIBRARY_PATH or equivalent. The correct pattern is `env={**os.environ, "PYTHONPATH": "src"}` to inherit the parent environment while overriding only PYTHONPATH.
- **Evidence:** Confirmed at lines 17-22: `subprocess.run([sys.executable, "-m", "biosystems.cli", "analyze", str(gpx_file)], capture_output=True, text=True, env={"PYTHONPATH": "src"})`. The `env` kwarg is a new dict containing only `PYTHONPATH`, replacing the entire inherited environment. `sys.executable` avoids PATH-based Python lookup, but PATH, HOME, LD_LIBRARY_PATH, and other env vars inherited from the test runner are discarded.
- **Survived adversarial pass:** yes

### [LOW] F-testcov-4 — test_gap
- **Location:** `tests/test_physics_metrics.py:265`
- **What:** `test_with_cadence` asserts `metrics.avg_cadence == 170` using an input fixture where all cadence values are exactly 170. The calculation in metrics.py:310 uses `int(cadence_series.mean())` which truncates rather than rounds. A test with cadence values that produce a mean of e.g. 179.9 would catch the truncation-vs-rounding discrepancy (int(179.9)=179, round(179.9)=180). Because the fixture uses a whole number, the int() truncation goes undetected. The finding F-cadence-int-truncation-10 from the prior audit cannot be confirmed or refuted by the current test.
- **Evidence:** Confirmed at line 265: `assert metrics.avg_cadence == 170`. The `sample_activity_df` fixture supplies uniform cadence values of 170, making `int(mean)` and `round(mean)` produce the same result (both 170), rendering the truncation behavior completely undetectable by this assertion.
- **Survived adversarial pass:** yes

### [LOW] F-walk-debug-print-3 — design_defect
- **Location:** `src/biosystems/signal/walk_detection.py:251-255`
- **What:** A '[SANITY DEBUG]' diagnostic print statement was left in production code inside walk_block_segments(). It fires whenever a walk block >=60s has missing or zero distance_cumulative_km data — a plausible condition for FIT/GPX files without cumulative distance columns. Since the biosystems strava pipeline and daily brief run as cron jobs (CLAUDE.md), every such occurrence emits debug noise to cron stderr output, adding operational clutter and potentially masking real error output.
- **Evidence:** Confirmed at lines 250-255: condition `if dur_s >= 60 and (pd.isnull(dist_km) or dist_km <= 0):` followed by `print(f'[SANITY DEBUG] SKIPPING BAD SEGMENT seg_id={seg_id}, dur_s={dur_s}, dist_km={dist_km}', file=sys.stderr)` then `continue`. The text '[SANITY DEBUG]' is present verbatim in the production source. This fires on any walk block >=60s with missing or zero cumulative distance — a plausible condition for FIT/GPX files without cumulative distance columns.
- **Survived adversarial pass:** yes

### [LOW] F-walk-pace-unweighted-6 — intent_mismatch
- **Location:** `src/biosystems/signal/walk_detection.py:137`
- **What:** summarize_walk_segments() aggregates per-segment average pace with an unweighted np.mean(). The resulting avg_pace field is labelled and displayed as the average walk pace, but it over-weights short high-pace segments relative to long low-pace segments. The methodologically correct aggregation is a time-weighted mean: sum(dur_s * avg_pace) / sum(dur_s). The same function correctly uses dur_s for time totals but ignores it for pace aggregation, creating an internal inconsistency.
- **Evidence:** Verified at line 137: `avg_pace = np.mean(paces) if paces else np.nan`. The `paces` list is built at lines 124-128 from `s["avg_pace_min_km"]` values of valid_segments with no duration weighting. Line 120 correctly computes `total_walk_time = sum(s["dur_s"] for s in valid_segments)` but dur_s is never applied as a weight for pace aggregation. Unweighted mean across variable-duration segments confirmed.
- **Survived adversarial pass:** yes

### [LOW] F-gpx-fallback-zero-latlon-7 — bug
- **Location:** `src/biosystems/ingestion/gpx.py:159-161`
- **What:** The non-namespaced GPX fallback parser (invoked when the Garmin-namespaced parse yields no rows) uses `get('lat', 0)` and `get('lon', 0)` as defaults for missing GPS attributes. A trkpt with absent or empty lat/lon resolves to the coordinate origin (Gulf of Guinea), producing enormous haversine distances that corrupt dist, speed_mps, pace_sec_km, and all derived metrics for that trackpoint. No warning is emitted and no NaN is propagated.
- **Evidence:** Verified at lines 160-161 (non-namespaced fallback block): `lat = float(pt.attrib.get("lat", 0))` and `lon = float(pt.attrib.get("lon", 0))`. A trkpt missing lat or lon attributes silently produces (0.0, 0.0). Lines 190-198 then call _haversine() with these 0.0 coordinates, generating large spurious distances. The namespaced primary path would raise KeyError on missing attributes, confirming the two branches have inconsistent error handling.
- **Survived adversarial pass:** yes

### [LOW] F-walk-filter-nan-drop — bug
- **Location:** `src/biosystems/signal/walk_detection.py:32-34`
- **What:** filter_gps_jitter() uses boolean comparisons on pace_col and cad_col that may contain NaN. Rows with NaN in both columns are silently excluded regardless of GPS quality. Points at the boundary of walk and run segments are most likely to have sensor dropouts and are precisely those most important for accurate walk detection.
- **Evidence:** Verified at lines 32-34: `pace_flag = df[pace_col] <= 12.0; cad_flag = df[cad_col] >= cad_thr; return df[pace_flag | cad_flag]`. In pandas, comparison of NaN with any scalar yields False. A row with NaN in both pace_col and cad_col will have pace_flag=False and cad_flag=False and is excluded from the filtered result. Called from walk_block_segments (line 192) on already-walk-labeled rows, this silently drops walk points with simultaneous sensor dropouts in both channels.
- **Survived adversarial pass:** yes

### [LOW] F-cli-zone-silent-drop — design_defect
- **Location:** `src/biosystems/cli.py:82-91`
- **What:** load_zone_config() silently drops YAML zone entries that are missing either `bpm` or `pace_min_per_km` keys. A user who configures zones using only HR (no pace boundaries) or only pace (no HR boundaries) will find those zones absent from ZoneConfig with no error message, causing silent misconfiguration of zone time distributions and walk-detection thresholds.
- **Evidence:** Verified at line 84: `if not isinstance(data, dict) or "bpm" not in data or "pace_min_per_km" not in data: continue`. The `continue` silently skips any zone missing either key with no warning, log, or exception. A user configuring zones by HR-only or pace-only will find those zones absent from ZoneConfig with no feedback.
- **Survived adversarial pass:** yes

### [LOW] F-walk-block-iterrows-perf — perf
- **Location:** `src/biosystems/signal/walk_detection.py:199-218`
- **What:** walk_block_segments() iterates over the full input DataFrame (gpx_df) via iterrows() even though only the walk-classified subset drives the output. Every non-walk row is visited to be skipped by the is_walk_col guard. For a 60-minute run with 10% walk time, 90% of iterations are wasted Python-level row visits. This is the same O(n) Python-loop anti-pattern identified at F-gap-loop-perf-8 and F-fit-perf-8; this finding names a third independent location.
- **Evidence:** Verified at line 199: `for _, (idx, row) in enumerate(gpx_df.iterrows()):` iterates the full gpx_df. The pre-filtered walk_df (line 192) is used only for membership check at line 201: `if row[is_walk_col] and idx in walk_df.index:`. Non-walk rows are visited to detect gap closure (max_gap_s check at line 214), but this requires only the index/timestamp, not the full row. Every non-walk row incurs Python-level pd.Series construction overhead via iterrows.
- **Survived adversarial pass:** yes

### [LOW] F-report-kmsplit-zero-pace — design_defect
- **Location:** `src/biosystems/physics/report.py:350-354`
- **What:** _parse_km_splits() stores pace_min_per_km=0.0 for splits with absent or zero average_speed (e.g. paused auto-laps). The KmSplit model has no gt=0 validator, so Pydantic accepts the 0.0 value without error. The CLI renders it as '0.00/km' — a nonsensical value implying infinite speed. The sibling function _parse_laps() skips zero-speed laps with 'continue', showing the intent is to exclude them; _parse_km_splits should similarly skip or use None for zero-speed splits.
- **Evidence:** Confirmed report.py:350-354: avg_speed = s.get("average_speed"); if avg_speed and float(avg_speed) > 0: pace_min_per_km = round((1000.0 / 60.0) / float(avg_speed), 2); else: pace_min_per_km = 0.0. Confirmed report.py:400: _parse_laps uses 'continue  # skip laps with no speed data' at that branch. The asymmetry is real — km-splits store 0.0 while laps skip. KmSplit model validator was not independently inspected but no gt=0 constraint is apparent from the append at lines 370-380.
- **Survived adversarial pass:** yes

### [LOW] F-pmc-samename-drop — design_defect
- **Location:** `src/biosystems/analytics/trending.py:69-72`
- **What:** In compute_pmc(), when two activities on the same date have identical activity_name values, the 'curr_name != prev_name' guard at line 71 evaluates False and the name concatenation is skipped. The second session's name is silently dropped from the PMC metadata. For double training days where Strava assigns the same default name to both sessions, PMC output represents the combined day as a single named activity rather than the intended compound label. The TSS summation is not affected; only the activity_name metadata in the PMC output is wrong.
- **Evidence:** Confirmed trending.py:69-72: prev_name = prev.get("activity_name") or ""; curr_name = e.get("activity_name") or ""; if curr_name and curr_name != prev_name: prev["activity_name"] = ... When curr_name == prev_name (non-empty), the condition curr_name != prev_name is False; the branch is skipped and the second session name is silently dropped. TSS summation at line 60 is unaffected; only the activity_name metadata is wrong.
- **Survived adversarial pass:** yes

### [LOW] F-new-aev-keyerror-03 — bug
- **Location:** `src/biosystems/physics/report.py:195`
- **What:** _compute_aev() at report.py:195 selects run_df[["hr", "pace_min_per_km"]] without first verifying the column exists, raising KeyError when absent. The sibling _detect_strides() already guards this at line 100. All current CLI callers add pace_min_per_km before invoking build_run_report, so no crash occurs in production. The risk is latent: any new test or library consumer that calls build_run_report without the CLI's walk-detection block (which adds the column at cli.py:286/656) will trigger a KeyError.
- **Evidence:** Confirmed report.py:195: valid = run_df[["hr", "pace_min_per_km"]].dropna() — no column existence check before the double-bracket selection. Pandas raises KeyError when a listed column is absent. Confirmed _detect_strides at report.py:100 has explicit guard: 'if "pace_min_per_km" not in df.columns: return []'. All current CLI callers of build_run_report (cli.py:333 and cli.py:670) add pace_min_per_km before the call, so production is safe. Risk is latent for library consumers.
- **Survived adversarial pass:** yes

### [LOW] F-new-cli-efforts-mislabel-02 — design_defect
- **Location:** `src/biosystems/cli.py:886,919-920`
- **What:** The efforts CLI command sets improvement_s=None both when there is exactly one recording (first==best by definition) and when the first recording remains the fastest across all recordings. The display branch at lines 919-920 does not distinguish between these two cases: it always prints '(only recording)' when improvement_s is None, even if recording_count > 1. This misrepresents a regression/plateau (no improvement despite multiple runs) as a data-sparsity artifact.
- **Evidence:** Confirmed cli.py:886: improvement_s = first_t - best_t if first_date != best_date or first_t != best_t else None. By De Morgan's law, improvement_s is None when first_date == best_date AND first_t == best_t — this covers both the single-recording case AND the multi-recording case where the first run is the personal best. Confirmed cli.py:897: recording_count=len(times) is populated. Confirmed cli.py:919-920: if row["improvement_s"] is None: typer.echo(f"    First: {fm}:{fs:02d}  on {row['first_date']}  (only recording)") — recording_count is never consulted. A user whose first recorded effort is still their personal best will see '(only recording)' despite having multiple recorded races.
- **Survived adversarial pass:** yes

### [LOW] F-new-gpx-loop-haversine-04 — perf
- **Location:** `src/biosystems/ingestion/gpx.py:190-198`
- **What:** parse_gpx() computes inter-sample haversine distances via a Python list comprehension iterating over every row, using df.at[] for each element access. This incurs Python interpreter overhead proportional to track length. The same pattern was already identified in the FIT parser. A vectorized implementation using shifted numpy arrays would eliminate the per-row Python overhead.
- **Evidence:** Confirmed gpx.py:190-198: seg_dist = [0.0] + [_haversine(df.at[i - 1, "lat"], df.at[i - 1, "lon"], df.at[i, "lat"], df.at[i, "lon"]) for i in range(1, len(df))]. Python list comprehension iterating over all rows, using df.at[] (label-based scalar lookup) twice per iteration. This is the same anti-pattern as the FIT parser finding. A vectorized shifted-array approach (np.vectorize or lat/lon shift via df.shift()) would eliminate per-row Python overhead.
- **Survived adversarial pass:** yes

### [LOW] F-new-test-gap-walk-rangeidx-06 — test_gap
- **Location:** `tests/test_walk_detection_fix.py:1-47,tests/test_signal.py:174-294`
- **What:** No test exercises walk_block_segments() with a RangeIndex input, which is the index type produced by parse_gpx(). Both test_walk_detection_fix.py and test_signal.py TestWalkBlockSegments exclusively use DatetimeIndex inputs. The integer-index crash path is therefore exercised only in production when a GPX activity triggers walk detection. A fixture mirroring parse_gpx() output (RangeIndex, 'time' column) would have caught the error before production.
- **Evidence:** Verified: test_walk_detection_fix.py:11 uses pd.date_range — DatetimeIndex. test_signal.py:196 uses pd.date_range('2024-01-01 10:00:00', periods=n_points, freq='s') — DatetimeIndex. test_signal.py:276 (test_no_walk_periods) also uses pd.date_range — DatetimeIndex. No test constructs a DataFrame with a RangeIndex and calls walk_block_segments(). walk_detection.py:199-210 iterates with iterrows() using idx from the index; at line 210 computes (cast(pd.Timestamp, idx) - last_walk_idx).total_seconds() — cast() is a no-op type hint, so with RangeIndex idx is an integer and subtraction with a pd.Timestamp yields a TypeError, not AttributeError. Lines 224-226 access gpx_df.index[0] and gpx_df.index[-1] which would return integers, and line 226 (session_end - session_start).total_seconds() would also fail on integers. The crash path is real and untested.
- **Survived adversarial pass:** yes

### [LOW] F-new-brief-runtime-msg-04 — doc_drift
- **Location:** `daily_running_brief/daily_running_brief.py:1157`
- **What:** The RuntimeError raised when all providers are exhausted lists only OPENAI_API_KEY and ANTHROPIC_API_KEY in the message, omitting OPENROUTER_API_KEY which is tried first (line 1079). A user who sets only OPENROUTER_API_KEY will see an error message that effectively tells them to set a key they don't need, masking the real cause (e.g., a network error or import failure in the openrouter path at line 1105 which silently falls through via bare except: pass).
- **Evidence:** Verified: line 1157-1158 raises RuntimeError('No API key found. Set OPENAI_API_KEY (preferred, cheaper) or ANTHROPIC_API_KEY.'). Provider priority confirmed: OPENROUTER_API_KEY checked first at line 1079, then OPENAI_API_KEY at line 1108, then ANTHROPIC_API_KEY at line 1137. OPENROUTER_API_KEY is absent from the error message. The openrouter branch at lines 1104-1106 contains bare except: pass, meaning any error (import failure, network error, auth failure) silently falls through and could cause the RuntimeError to fire even when OPENROUTER_API_KEY is set and the key is valid.
- **Survived adversarial pass:** yes

### [LOW] F-new-reproduce-iso-week-08 — reproducibility
- **Location:** `tools/reproduce_study_analysis.py:85`
- **What:** The parse_week() helper in tools/reproduce_study_analysis.py extracts only the ISO week number from the run filename, discarding the year. If the study dataset ever spans a year boundary (or if future analysis reuses the tool for multi-year data), runs from the same calendar week in different years are aggregated into the same bucket. The per-week EF means and the validation comparison against real_weekly_data.json would silently mix data across years, producing erroneous reproducibility results.
- **Evidence:** Verified: at line 85, return dt.isocalendar()[1] returns only the ISO week number (1-53), discarding the year component. dt.isocalendar() returns a named tuple (year, week, weekday); index [1] is the week number alone. The current study dataset spans W17-W36 within 2025 so no collision exists in current data, but the code is structurally vulnerable to multi-year reuse.
- **Survived adversarial pass:** yes

### [LOW] F-new-fit-haversine-loop-09 — perf
- **Location:** `src/biosystems/ingestion/fit.py:214`
- **What:** In add_derived_metrics() for FIT files, segment distances are computed via a Python list comprehension that calls _haversine() once per row using .iloc[] indexing. This is an O(N) Python loop with per-element pandas overhead. A vectorized haversine using numpy broadcasting would compute all distances in a single C-level operation. For an activity with 7200 samples (2 h at 1 Hz), the loop runs 7199 iterations at Python speed. This function is called for every FIT activity ingested.
- **Evidence:** Verified: fit.py:213-222 computes seg_dist via a Python list comprehension calling _haversine() per row with df['latitude'].iloc[i-1] / df['longitude'].iloc[i-1] / df['latitude'].iloc[i] / df['longitude'].iloc[i] for i in range(1, len(df)). This is O(N) Python-level iteration with per-element pandas .iloc[] overhead. The identical anti-pattern exists in gpx.py:190-198 using .at[] (same algorithmic cost). A vectorized numpy haversine using shifted arrays would run entirely in C.
- **Survived adversarial pass:** yes

### [LOW] F-new-weather-cache-nodup-11 — design_defect
- **Location:** `src/biosystems/environment/weather.py:200`
- **What:** The in-memory and on-disk Parquet cache in WeatherCache has no deduplication guard in set(). If set() is called multiple times for the same (lat, lon, date_str), the cache grows with duplicate rows and get() always returns the oldest entry. The Parquet file on disk grows unboundedly with duplicate rows. A simple pre-check or drop-duplicates on write would fix both issues.
- **Evidence:** Verified: WeatherCache.set() at lines 184-218 constructs a new_row DataFrame and unconditionally appends it via pd.concat([self.cache, new_row], ignore_index=True) at line 214 with no prior check for an existing (lat, lon, date_str) row. WeatherCache.get() at line 174 returns cached.iloc[0] (first match only). A duplicate key written twice results in two rows; get() always returns the first (older) entry. The Parquet file also grows with duplicate rows on every redundant set() call.
- **Survived adversarial pass:** yes

### [LOW] F-new-sanitize-stdout-print-13 — design_defect
- **Location:** `tools/sanitize_gps.py:90`
- **What:** When `sanitize_dataframe()` or `sanitize_parquet_file()` is imported and called as a library function (e.g., from a pipeline or notebook), all four progress lines are unconditionally written to stdout. This pollutes any caller that captures stdout for structured output. The function has no `verbose=False` guard and does not use the standard `logging` module that the rest of the codebase uses. The CLI wrapper in `main()` passes no flag to suppress output, so there is no established suppression path.
- **Evidence:** Direct read confirms 4 unconditional `print()` calls at lines 90-93 in `sanitize_dataframe()`. `sanitize_parquet_file()` has further unconditional prints at line 159 (`\nProcessing: ...`), line 169 (`Summary: ...`), line 174 (`✓ Saved to: ...`), and line 179 (`✗ Error: ...`). No `verbose` parameter exists anywhere in the module and `import logging` is absent — only `import sys` is present at line 19.
- **Survived adversarial pass:** yes

### [LOW] F-new-walk-segment-unused-model-15 — design_defect
- **Location:** `src/biosystems/models.py:262`
- **What:** The `WalkSegment` Pydantic model and its validation constraints are never enforced in the production pipeline because no production code path constructs a `WalkSegment` instance — walk segment dicts flow through the pipeline as plain Python dicts. The model IS tested in the test suite (`test_models.py`, `test_walk_detection_fix.py`), so it is not entirely dead code, but the validation gap in production remains: invalid values such as a negative duration, zero heart rate, or unrecognised tag string would pass silently at runtime. The `FullRunReport.walk_segments: list[dict]` annotation diverges from the model's intent.
- **Evidence:** `class WalkSegment(BaseModel)` defined at lines 262-294 confirmed by direct read. `FullRunReport.walk_segments` typed `list[dict]` confirmed at `models.py:377`. Grep of `src/` for `WalkSegment(` returns only the class definition — no production code instantiates it. `walk_detection.py:37` uses `list[dict]` type annotations throughout. NOTE: The original evidence claim 'Grepping the full repository for WalkSegment( returns no instantiation sites' is INCORRECT — tests DO instantiate the model (`tests/test_walk_detection_fix.py:37`, `tests/test_models.py:224`, `tests/test_models.py:239`). The model is exercised in tests but bypassed in the production pipeline.
- **Survived adversarial pass:** yes

### [INFO] F-doc-09 — doc_drift
- **Location:** `pyproject.toml:17`
- **What:** The package classifier 'Development Status :: 4 - Beta' conflicts with the declared version 1.0.0 (which by semantic versioning implies stable API) and the README's 'Publication-Ready' status claim. Any PyPI or package index search for stable running-analysis packages would demote this library below packages correctly classified as stable, even though the project's own documentation claims publication readiness.
- **Evidence:** pyproject.toml line 17 confirmed: '"Development Status :: 4 - Beta"'. pyproject.toml line 7 confirmed: 'version = "1.0.0"'. README.md line 340 confirmed: '**Status:** ✅ Active Development | 📊 Publication-Ready | 🔬 Research Artifact'. Mismatch between Beta classifier, 1.0.0 version, and Publication-Ready claim confirmed at source.
- **Survived adversarial pass:** yes

### [INFO] F-tsb-docstring-typo-5 — doc_drift
- **Location:** `src/biosystems/analytics/trending.py:48`
- **What:** The compute_pmc() return-value docstring misspells the tsb field's expansion as 'CTB = CTL - ATL' instead of 'TSB = CTL - ATL'. This is inconsistent with the module-level definitions at lines 12-14 and with established Banister model terminology. The error could mislead a reader implementing downstream consumers of the PMC output who rely on the docstring for field semantics.
- **Evidence:** Verified at line 48: `- \`tsb\` (float): CTB = CTL - ATL (rounded to 0.1) computed before that day's load`. Module-level definition at line 14 correctly states `TSB (Training Stress Balance) = CTL - ATL`. The field is named `tsb`, the module docs use TSB, but the per-field docstring reads 'CTB'. Typo is real and unambiguous.
- **Survived adversarial pass:** yes

### [INFO] F-new-brief-dead-pct-rank-03 — design_defect
- **Location:** `daily_running_brief/daily_running_brief.py:148`
- **What:** Inside _compute_history_stats() a nested function _pct_rank is defined but never invoked. The caller _ef_percentile at line 175 calls the module-level _pct_rank_inner instead. The nested function object is created on every call to _compute_history_stats() and immediately discarded, adding dead bytecode and creating confusion about which implementation is canonical.
- **Evidence:** Verified: at line 148-153, def _pct_rank(value, sorted_list) is defined as a nested function inside _compute_history_stats(). Read of lines 140-172 (full body of _compute_history_stats) shows no call to _pct_rank anywhere in the function body. Module-level _pct_rank_inner is defined at lines 179-183 and is called by _ef_percentile at line 176. The nested _pct_rank closure is created on every invocation of _compute_history_stats and immediately goes out of scope, never called.
- **Survived adversarial pass:** yes

### [INFO] F-new-trending-roll-closure-loop-16 — design_defect
- **Location:** `src/biosystems/analytics/trending.py:165`
- **What:** The `_roll` helper is re-created as a new closure on each pass of the history loop in `compute_rolling_metrics()`. Because it closes over only `window` (a constant for the whole call), moving the `def _roll` statement above the `for` loop would produce identical behaviour with one object allocation instead of N. The current placement gives a misleading impression that the closure captures loop-local state. This is a minor performance and readability issue, not a correctness defect.
- **Evidence:** Direct read of `compute_rolling_metrics()` confirms `def _roll(buf: list[float]) -> float | None:` is defined at line 165 inside the `for e in run_entries:` loop body (loop starts at line 153). The function body at lines 166-167 references only `window` (a parameter of the enclosing function, not any loop variable) and the `buf` argument. An identical function object is re-created and discarded on every loop iteration.
- **Survived adversarial pass:** yes


_Generated 2026-06-17T20:11:42.965Z · branch claude/epic-goldberg-hebvrp_
