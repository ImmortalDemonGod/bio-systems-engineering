# 05 — Execution-Ready Plan

Ordered change items closing the gap between current state (01–03) and goal (04).

## P0

### C01 — `src/biosystems/physics/metrics.py:199-217, src/biosystems/models.py:152`
- **Closes:** F-decoupling-empty-half-1
- **Change:** In calculate_decoupling(), after computing first_half at line 201 (work_df[elapsed <= midpoint_s]), add: 'if first_half.empty or len(work_df) - len(first_half) == 0: return None'. Guard the ef_1==0 path at line 217: replace 'decouple_pct = abs(ef_2 - ef_1) / ef_1 * 100' with 'decouple_pct = abs(ef_2 - ef_1) / ef_1 * 100 if ef_1 != 0.0 else None'. Update run_metrics() caller at line 339 (the assignment 'decoupling_pct=round(decouple_pct, 2)') to propagate None: change to 'decoupling_pct=round(decouple_pct, 2) if decouple_pct is not None else None'. Also change models.py:152 from 'decoupling_pct: float = Field(...)' to 'decoupling_pct: float | None = Field(None)' so Pydantic accepts None without TypeError; update the @field_validator at models.py:159 to skip when the value is None.
- **Verify:** python -c "import pandas as pd; from biosystems.physics.metrics import calculate_decoupling; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); df = pd.DataFrame({'hr':[160.0],'dist':[50.0],'dt':[5.0]}); r = calculate_decoupling(df, z); print('OK, result:', r)" — must print OK (not raise ZeroDivisionError); also confirm existing tests still pass: pytest tests/test_physics_metrics.py -q
- **Depends on:** —

### C02 — `src/biosystems/physics/metrics.py:288-293`
- **Closes:** F-new-avgpace-zdiv-01
- **Change:** After the 'if secs <= 0: raise ValueError' guard at line 288, add 'if total_dist_m <= 0.0: raise ValueError(f"Activity has zero total distance (dist column may be all-NaN); got total_dist_m={total_dist_m}")'. This prevents ZeroDivisionError at line 293 (avg_pace = 1000 / avg_speed / 60) when pandas .sum() over all-NaN dist returns 0.0.
- **Verify:** python -c "import pandas as pd; import numpy as np; from biosystems.physics.metrics import run_metrics; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); df = pd.DataFrame({'hr':[160.0]*10,'dist':[np.nan]*10,'dt':[5.0]*10,'cadence':[170]*10,'pace_min_per_km':[5.0]*10,'pace_sec_km':[300.0]*10,'speed_mps':[3.3]*10}); [exec('run_metrics(df, z)') for _ in [1]] " 2>&1 | grep 'ValueError.*zero total distance' — must show the ValueError, not ZeroDivisionError
- **Depends on:** —

### C03 — `src/biosystems/cli.py:812-817`
- **Closes:** F-new-cli-zdiv-summary-01
- **Change:** After the 'if all_efs:' guard at line 814, add an independent guard before the decoupling mean: change 'sum(all_decs)/len(all_decs)' to 'sum(all_decs)/len(all_decs) if all_decs else None'. Display 'N/A' when decoupling is None to avoid the ZeroDivisionError that fires when all_efs is non-empty but all_decs is empty.
- **Verify:** Construct a minimal history.jsonl with entries that have ef values but no decoupling_pct field, then run 'biosystems summary' — must print the EF line and show 'N/A' or skip the decoupling line without raising ZeroDivisionError.
- **Depends on:** —

### C04 — `src/biosystems/physics/report.py:138-140`
- **Closes:** F-report-dynamics-keyerror
- **Change:** At the start of _compute_dynamics() (function definition at line 138, before the dropna call at line 140), add a column existence guard matching the sibling functions: 'if "pace_min_per_km" not in df.columns or "hr" not in df.columns: return None'. This mirrors the guard at _detect_strides() (line 100) and _compute_aev() fix (see C50).
- **Verify:** python -c "import pandas as pd; from biosystems.physics.report import _compute_dynamics; df = pd.DataFrame({'hr':[160.0]*10,'dist':[50.0]*10,'dt':[5.0]*10}); r = _compute_dynamics(df, None); print('OK:', r)" — must print OK without KeyError
- **Depends on:** —

### C05 — `src/biosystems/wellness/cache.py:393,441`
- **Closes:** F-rr-sigma-none-crash-2
- **Change:** At lines 393 and 441, replace the unguarded f-string 'f"+{rr_sigma:.1f}σ"' with a conditional: 'f"+{rr_sigma:.1f}σ" if rr_sigma is not None else ""'. Also fix the rr_sigma assignment logic at line 345: change the condition from 'if rr_mean and rr_std and rr_std > 0:' to 'if rr_mean and rr_std is not None and rr_std > 0:' to correctly distinguish zero from None.
- **Verify:** python -c "from biosystems.wellness.cache import compute_wellness_context; print('import OK')" — module imports without error; then mock a wellness parquet with all-identical respiratory_rate values and call compute_wellness_context() — must return a dict without TypeError
- **Depends on:** —

### C06 — `src/biosystems/signal/walk_detection.py:259`
- **Closes:** F-new-walk-heart-rate-col-07
- **Change:** At line 259, change the column name check from 'heart_rate' to 'hr' to match the column name produced by both parse_gpx() (gpx.py:176, column 'hr') and parse_fit() (fit.py:146-147, renamed from 'heart_rate' to 'hr'). Change: 'if "heart_rate" in grp_df.columns:' → 'if "hr" in grp_df.columns:' and update the subsequent grp_df["heart_rate"] references at the same block to grp_df["hr"].
- **Verify:** pytest tests/test_walk_detection_fix.py tests/test_signal.py -q — all tests pass (tests use 'heart_rate' fixtures; update test fixtures to use 'hr' as well so they reflect production column names); then verify in test output that avg_hr is no longer NaN for fixtures that supply HR data.
- **Depends on:** —

### C07 — `src/biosystems/ingestion/gpx.py:126,131,136`
- **Closes:** F-new-gpx-power-unguarded-01
- **Change:** Wrap the three unguarded 'int(power_node.text)' calls at lines 126, 131, and 136 in try/except (ValueError, TypeError) that sets power = np.nan and continues. Pattern to apply at each site: 'try: power = int(power_node.text) \nexcept (ValueError, TypeError): power = np.nan'. This matches the already-guarded fourth path at lines 143-148.
- **Verify:** python -c "from biosystems.ingestion.gpx import parse_gpx; import io; gpx_with_float_power = \"<?xml version='1.0'?><gpx xmlns='http://www.topografix.com/GPX/1/1'><trk><trkseg><trkpt lat='37.0' lon='-122.0'><ele>10</ele><time>2025-01-01T10:00:00Z</time><power>350.0</power></trkpt></trkseg></trk></gpx>\"; print('no crash, rows:', len(parse_gpx(io.StringIO(gpx_with_float_power))))" — must not raise ValueError
- **Depends on:** —

### C08 — `src/biosystems/ingestion/gpx.py:104-106,119`
- **Closes:** F-gpx-hr-parse-unguarded-4
- **Change:** At line 105 (HR parse), replace 'hr_val = int(hr_node.text)' with a try/except block: 'try: hr_val = int(hr_node.text) \nexcept (ValueError, TypeError): hr_val = np.nan'. At line 119 (cadence parse), replace the inline 'int(cad_node.text)' with 'int(cad_node.text) if cad_node is not None else np.nan' → wrap with: 'try: cad = int(cad_node.text) if cad_node is not None else np.nan \nexcept (ValueError, TypeError): cad = np.nan'.
- **Verify:** pytest tests/test_ingestion_gpx.py -q — all existing tests pass. Additionally: python -c "from biosystems.ingestion.gpx import parse_gpx; import io; bad = \"<?xml version='1.0'?><gpx xmlns='http://www.topografix.com/GPX/1/1' xmlns:gpxtpx='http://www.garmin.com/xmlschemas/TrackPointExtension/v1'><trk><trkseg><trkpt lat='37.0' lon='-122.0'><ele>10</ele><time>2025-01-01T10:00:00Z</time><extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>75.5</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions></trkpt></trkseg></trk></gpx>\"; df = parse_gpx(io.StringIO(bad)); import math; assert math.isnan(df['hr'].iloc[0]); print('OK: float HR gracefully NaN')" — must print OK
- **Depends on:** —

### C09 — `src/biosystems/ingestion/strava.py:92`
- **Closes:** F-strava-1
- **Change:** At line 92, replace 'retry_after = int(resp.headers.get("Retry-After", 60))' with a try/except that handles the HTTP-date string variant: 'try: retry_after = int(resp.headers.get("Retry-After", 60)) \nexcept (ValueError, TypeError): retry_after = 60'. This prevents an uncaught ValueError when Strava returns a date-format Retry-After header per RFC 7231 §7.1.3.
- **Verify:** pytest tests/test_strava.py -q — all existing tests pass. Add a new test in tests/test_strava.py that mocks a 429 response with Retry-After: 'Mon, 01 Jan 2026 00:00:00 GMT' (date-format string) and asserts _get_with_backoff falls back to a 60-second sleep without raising ValueError.
- **Depends on:** —

### C10 — `src/biosystems/ingestion/strava.py:91-95`
- **Closes:** F-strava-2
- **Change:** After the retry_after assignment (fixed by C09), add an upper-bound cap matching the pattern in habitdash.py:107. Change 'time.sleep(retry_after)' to 'time.sleep(min(retry_after, 3600))'. This prevents a single malformed or adversarial Retry-After header from hanging the process indefinitely.
- **Verify:** python -c "import biosystems.ingestion.strava as s; import inspect; src = inspect.getsource(s._get_with_backoff); assert 'min(' in src and '3600' in src, 'cap not present'; print('cap present')" — must print 'cap present'
- **Depends on:** C09

### C11 — `src/biosystems/wellness/habitdash.py:106`
- **Closes:** F-habitdash-int-crash
- **Change:** At line 106, wrap 'int(remaining)' in try/except (ValueError, TypeError): change 'if remaining is not None and int(remaining) == 0' to 'try: rem_int = int(remaining) \nexcept (ValueError, TypeError): rem_int = -1 \nif remaining is not None and rem_int == 0'. This prevents ValueError from a non-numeric x-ratelimit-remaining header propagating through _get() and crashing wellness-sync.
- **Verify:** python -c "from biosystems.wellness.habitdash import HabitDashClient; print('import OK')" — then a mock-based test (see C46) that supplies x-ratelimit-remaining: 'not-a-number' must not raise ValueError
- **Depends on:** —

### C12 — `.gitignore`
- **Closes:** F-pii-1
- **Change:** Add 'data/subjective.csv' (or 'data/*.csv' if no other CSV in data/ should be committed) to .gitignore to prevent the file from appearing in future public clones. Document in docs/DATA_PREPARATION.md that data/subjective.csv contains real PHI (rest_hr, hrv, rpe, ankle_pain) and must not be committed to any public fork. Note: removing from git history requires 'git filter-repo --path data/subjective.csv --invert-paths' or BFG — document this requirement but do not execute it here as it is a destructive rewrite.
- **Verify:** git check-ignore -v data/subjective.csv — must print the matching .gitignore rule. Also: grep 'subjective' .gitignore — must match.
- **Depends on:** —

### C13 — `src/biosystems/environment/weather.py:337`
- **Closes:** F-weather-1
- **Change:** At line 337, replace the GPS-coordinate interpolation in the error log message with a redacted placeholder. Change the f-string from 'lat={lat_r}, lon={lon_r}' to 'lat=<redacted>, lon=<redacted>' (or use a general region descriptor). The rounded variables lat_r/lon_r are used earlier in the function for cache lookup (legitimate) and should not be emitted to stderr on failure.
- **Verify:** python -c "import inspect, biosystems.environment.weather as w; src = inspect.getsource(w.WeatherCache.fetch); assert 'lat=<redacted>' in src or 'lat_r' not in src.split('Failed')[1], 'GPS still leaks'; print('GPS redacted in error path')" — must confirm coordinates are not in the failure log message
- **Depends on:** —

### C14 — `README.md:21, data/real_weekly_data.json:100, docs/PUBLICATION_CHECKLIST.md:43`
- **Closes:** F-doc-01
- **Change:** 1) In README.md line 21, change '36°C (extreme heat)' to '~28°C (daily max 32°C)' in the Environmental Conditions row of the results table. 2) In data/real_weekly_data.json at the W32 entry note field, replace '36°C heat' with '~28°C (Open-Meteo archive). 3) In docs/PUBLICATION_CHECKLIST.md line 43, mark the P0 Temperature inconsistency item as checked: change '- [ ] **Temperature inconsistency**' to '- [x] **Temperature inconsistency**'.
- **Verify:** grep '36' README.md | grep -i 'heat\|temperature\|condition' — must return nothing. grep '28' README.md — must match the results table row. grep 'x.*Temperature' docs/PUBLICATION_CHECKLIST.md — must show the checked item.
- **Depends on:** —

### C15 — `src/biosystems/signal/walk_detection.py:199-226`
- **Closes:** F-new-walk-rangeidx-crash-05
- **Change:** In walk_block_segments(), add a DatetimeIndex guard at the start of the function (before line 199): 'if not isinstance(gpx_df.index, pd.DatetimeIndex): raise TypeError(f"walk_block_segments requires a DatetimeIndex; got {type(gpx_df.index).__name__}. Call pd.to_datetime on the time column and set it as the index first.")'. Also update build_run_report() caller in physics/report.py (line ~267) to catch this TypeError and return an empty walk list rather than silently swallowing it.
- **Verify:** python -c "import pandas as pd; from biosystems.signal.walk_detection import walk_block_segments; df = pd.DataFrame({'pace_min_per_km':[5.0]*5,'cadence':[170]*5,'hr':[155]*5,'is_walk':[0]*5,'dist':[50.0]*5,'dt':[5.0]*5}); walk_block_segments(df)" 2>&1 | grep 'TypeError.*DatetimeIndex' — must print the TypeError message, not AttributeError
- **Depends on:** —
## P1

### C16 — `src/biosystems/wellness/analytics.py:451`
- **Closes:** F-sleep-merge-priority-1
- **Change:** Swap the caller and argument of combine_first() at line 451. Change 'combined = df["sleep_duration_s"].combine_first(df["sleep_duration_s_garmin"])' to 'combined = df["sleep_duration_s_garmin"].combine_first(df["sleep_duration_s"])' so that Garmin values are used where available (caller wins in combine_first) and Whoop fills gaps, matching the documented intent at lines 448-449 ('Garmin wins when both exist').
- **Verify:** python -c "import pandas as pd; import numpy as np; from biosystems.wellness.analytics import compute_sleep_debt; df = pd.DataFrame({'sleep_duration_s_garmin':[25200.0, np.nan], 'sleep_duration_s':[21600.0, 21600.0]}, index=pd.date_range('2025-01-01', periods=2)); result = compute_sleep_debt(df); print(result)" — the first date should use garmin value 25200 (7h), not whoop value 21600 (6h)
- **Depends on:** —

### C17 — `src/biosystems/ingestion/gpx.py:160-161`
- **Closes:** F-gpx-fallback-zero-latlon-7
- **Change:** In the non-namespaced GPX fallback parser at lines 160-161, change the default values for missing lat/lon from 0 to np.nan: 'lat = float(pt.attrib.get("lat", np.nan))' and 'lon = float(pt.attrib.get("lon", np.nan))'. Then in the haversine distance computation (lines 190-198), skip rows where lat or lon is NaN by adding a filter before the comprehension.
- **Verify:** python -c "from biosystems.ingestion.gpx import parse_gpx; import io; gpx = \"<?xml version='1.0'?><gpx xmlns='http://www.topografix.com/GPX/1/1'><trk><trkseg><trkpt><ele>10</ele><time>2025-01-01T10:00:00Z</time></trkpt></trkseg></trk></gpx>\"; df = parse_gpx(io.StringIO(gpx)); print('no spurious distance:', df['dist'].dropna().tolist())" — dist must be NaN or 0, not a large spurious haversine value
- **Depends on:** —

### C18 — `src/biosystems/cli.py:127-143`
- **Closes:** F-cli-analyze-no-walk-filter
- **Change:** In the analyze CLI command, after parsing the file and before calling run_metrics() at line 143, add the same walk-detection step used by the strava command (cli.py:287). Insert: 'if "pace_min_per_km" in df.columns and "cadence" in df.columns: df["is_walk"] = (df["pace_min_per_km"] > 9.5) | (df["cadence"].fillna(0) < 140)'. Use fillna(0) for cadence (consistent with C19) rather than fillna(999).
- **Verify:** Run 'biosystems analyze data/sample/sample_run.gpx' (after creating a synthetic GPX fixture per C26 — depends on C26 for the fixture). Confirm the command exits 0 and the reported EF matches the walk-filtered value rather than the full-session value. The EF from the analyze command should match what 'biosystems strava' reports for the same activity.
- **Depends on:** C19, C26

### C19 — `src/biosystems/cli.py:287,657`
- **Closes:** F-new-walk-fillna-intent-10
- **Change:** At lines 287 and 657, change 'df["cadence"].fillna(999) < 140' to 'df["cadence"].fillna(0) < 140'. This makes the production walk-classification treat sensor-dropout (NaN cadence) as 0 spm, which is below the 140 spm walk threshold, matching the documented intent in tests/test_walk_classification.py (line 21-24: 'Missing cadence values are treated as 0') and the test assertion in test_nan_cadence_is_walk.
- **Verify:** pytest tests/test_walk_classification.py -v — all tests must pass (the test file defines its own classify_walk() so update it to import from the CLI module after this change so the test exercises production code). grep 'fillna(999)' src/biosystems/cli.py — must return nothing.
- **Depends on:** —

### C20 — `src/biosystems/cli.py:639-644`
- **Closes:** F-cli-skip-4
- **Change:** Restructure the skip logic in backfill_streams to use two independent guards instead of the compound 'not existing_stream_ids' shortcut. Replace lines 639-644 with: 'skip_by_id = activity_id in existing_stream_ids if activity_id else False; skip_by_date = run_date in existing_stream_dates and not activity_id; if skip_existing and (skip_by_id or skip_by_date): continue'. Also add 'existing_stream_ids.add(activity_id)' and 'existing_stream_dates.add(run_date)' after each successful append_run call inside the loop to keep the sets current.
- **Verify:** Create a test history.jsonl with one date-keyed entry (no strava_activity_id) and one id-keyed entry, then call the backfill_streams command with --skip-existing and verify the date-keyed entry is skipped even when existing_stream_ids is non-empty.
- **Depends on:** —

### C21 — `src/biosystems/analytics/history.py:230-264`
- **Closes:** F-history-backfill-existing-stale
- **Change:** In backfill_from_strava(), after each successful append_run(entry) call at line 263, add 'existing.add(run_date)' to update the existing set for the current date. This prevents a second same-day activity from passing the 'run_date in existing' guard and silently overwriting the first via date-keyed deduplication.
- **Verify:** python -c "from biosystems.analytics.history import backfill_from_strava; import inspect; src = inspect.getsource(backfill_from_strava); assert 'existing.add' in src, 'guard missing'; print('guard present')" — must print 'guard present'
- **Depends on:** —

### C22 — `daily_running_brief/daily_running_brief.py:1108-1135`
- **Closes:** F-brief-openai-no-fallback
- **Change:** Wrap the OpenAI API call block (lines 1113-1135) in a try/except Exception block that logs the error and falls through to the Anthropic branch at line 1137. The block starting with 'if openai_key:' through the 'return resp.choices[0].message.content' at line 1135 should be wrapped: 'try: ... return resp.choices[0].message.content \nexcept Exception as e: log.error("OpenAI call failed: %s; trying Anthropic fallback", e)'. Ensure the bare except: pass in the OpenRouter block (line 1104-1106) is changed to 'except Exception as e: log.debug("OpenRouter failed: %s", e)' for traceability.
- **Verify:** python -c "from daily_running_brief.daily_running_brief import _chat; import inspect; src = inspect.getsource(_chat); assert 'except Exception' in src.split('openai_key')[1].split('anthropic')[0], 'OpenAI branch not wrapped'; print('OK: OpenAI wrapped')" — must print OK
- **Depends on:** —

### C23 — `README.md:17, CITATION.cff:25, reports/01_longitudinal_study.md:19,213`
- **Closes:** F-doc-02
- **Change:** Establish the canonical EF improvement figure as 17.8% (arithmetic: (0.02122 - 0.01801) / 0.01801 * 100 = 17.82%, rounded to 17.8%). 1) README.md line 17: change '+18%' to '+17.8%' and '0.0212' to '0.02122' in the results table. 2) CITATION.cff line 25: change '18.4% improvement' to '17.8% improvement'. 3) reports/01_longitudinal_study.md line 19: confirm '+17%' or update to '+17.8%' for consistency; confirm line 213 shows '0.02122'. Use 0.02122 (the committed JSON value) as the canonical final EF across all four artifacts.
- **Verify:** grep -n '18.4\|+18%\|18\.' README.md CITATION.cff reports/01_longitudinal_study.md — must return no matches. grep '17.8\|0.02122' README.md CITATION.cff — must match both files.
- **Depends on:** C14

### C24 — `README.md:15-22`
- **Closes:** F-doc-03
- **Change:** Replace the README headline results table values for Aerobic Decoupling. The values 7.7% (baseline) and 3.8% (final) have no traceable provenance in committed data. Use values from the scientific report (reports/01_longitudinal_study.md:19): baseline 19.78% (W23, peak decoupling) and final 4.71% (W35). Update the row: baseline '19.78% (W23)' and final '4.71% (W35)', percentage change '-76.2%', or alternatively cite the W17 (study start) weekly aggregate 8.1% from real_weekly_data.json as the baseline with an appropriate W32/W35 comparator. Whichever values are chosen must be traceable to real_weekly_data.json or the report. Add a footnote indicating which weeks and data source back each number.
- **Verify:** grep '7.7\|3.8%' README.md | grep -i 'decoupling' — must return nothing. grep 'decoupling' README.md — must reference W-numbered weeks or explicitly cite the source JSON.
- **Depends on:** C14

### C25 — `pyproject.toml:6, src/biosystems/__init__.py:31, CITATION.cff:5`
- **Closes:** F-doc-04
- **Change:** Bump version from '1.0.0' to '1.1.0' in all three places: 1) pyproject.toml line 6: 'version = "1.1.0"'. 2) src/biosystems/__init__.py line 31: '__version__ = "1.1.0"'. 3) CITATION.cff line 5: 'version: 1.1.0'. Also update pyproject.toml classifier (line 17) from 'Development Status :: 4 - Beta' to 'Development Status :: 5 - Production/Stable' to match the v1.1.0 stable release (see F-doc-09).
- **Verify:** python -c "import biosystems; print(biosystems.__version__)" — must print '1.1.0'. grep 'version' pyproject.toml | head -3 — must show 1.1.0. grep 'version' CITATION.cff | head -2 — must show 1.1.0.
- **Depends on:** —

### C26 — `tests/test_cli_integration.py:1-30`
- **Closes:** F-testcov-1
- **Change:** Rewrite test_cli_analyze_gpx to use data/sample/sample_run.csv converted to a minimal synthetic GPX fixture committed at tests/fixtures/sample_run.gpx (or data/sample/sample_run.gpx). The synthetic GPX must have at least 20 trackpoints with latitude, longitude, elevation, time, and gpxtpx:hr extensions. Remove the 'if not gpx_file.exists(): pytest.skip(...)' guard. Also fix the subprocess env issue (F-testcov-2): change 'env={"PYTHONPATH": "src"}' to 'env={**os.environ, "PYTHONPATH": "src"}'. The test should assert: exit code 0, JSON output parseable, efficiency_factor field present.
- **Verify:** pytest tests/test_cli_integration.py -v — test_cli_analyze_gpx must show PASSED (not SKIPPED). Also confirm 'env={**os.environ' appears in the test file: grep 'os.environ' tests/test_cli_integration.py.
- **Depends on:** —

### C27 — `tests/test_report.py (new file)`
- **Closes:** F-new-report-no-tests-04
- **Change:** Create tests/test_report.py with smoke tests for build_run_report() and internal helpers. Minimum required tests: (1) test_build_run_report_smoke: construct a 600-row DatetimeIndex DataFrame with hr, dist, dt, pace_min_per_km, cadence, is_walk, pace_sec_km, speed_mps, ele columns; call build_run_report(df, zones, {}) and assert the result is a FullRunReport with non-None session_metrics. (2) test_compute_dynamics_missing_column: call _compute_dynamics with a df missing pace_min_per_km — must return None (tests C04 fix). (3) test_compute_aev_missing_column: call _compute_aev with df missing pace_min_per_km — must return None (tests C50 fix).
- **Verify:** pytest tests/test_report.py -v — all three tests pass. Coverage run: pytest --cov=biosystems.physics.report --cov-report=term-missing tests/test_report.py — coverage on physics/report.py must be >0%.
- **Depends on:** C04

### C28 — `src/biosystems/ingestion/strava.py:163`
- **Closes:** F-strava-4
- **Change:** At line 163, replace 'return resp.json()["access_token"]' with 'token = resp.json().get("access_token"); if not token: raise ValueError(f"OAuth2 response missing access_token; body keys: {list(resp.json().keys())}"); return token'. This produces a meaningful error when a 2xx OAuth response omits the access_token field rather than an opaque KeyError.
- **Verify:** python -c "import inspect; from biosystems.ingestion.strava import StravaClient; src = inspect.getsource(StravaClient._refresh_access_token); assert '.get("access_token")' in src and 'ValueError' in src; print('guard present')" — must print 'guard present'
- **Depends on:** —

### C61 — `src/biosystems/wellness/habitdash.py:45-53,58-76`
- **Closes:** F-new-garmin-sleep-never-fetched-12
- **Change:** Add a Garmin sleep_duration field ID to FIELD_IDS['garmin'] at lines 45-53. The HabitDash API field ID for Garmin sleep duration must be retrieved from the HabitDash field list endpoint (GET /fields) or documentation — use a placeholder comment 'TODO: confirm Garmin sleep field ID from HabitDash /fields endpoint' and add a skeleton entry: 'sleep_duration_s': None  # TODO: populate from HabitDash /fields. Add a corresponding entry to COLUMN_MAP at lines 58-76: ('garmin', 'sleep_duration_s'): 'sleep_duration_s_garmin'. This unblocks the Garmin sleep branch in analytics.py:450-461 and cache.py:276 that references 'sleep_duration_s_garmin'.
- **Verify:** python -c "from biosystems.wellness.habitdash import FIELD_IDS, COLUMN_MAP; assert 'sleep_duration_s' in FIELD_IDS['garmin'], 'field missing'; assert ('garmin', 'sleep_duration_s') in COLUMN_MAP, 'column map missing'; print('Garmin sleep field registered')" — must print confirmation
- **Depends on:** —

### C63 — `src/biosystems/ingestion/fit.py:90, src/biosystems/ingestion/strava.py:359-363`
- **Closes:** F-cadence-doubling-2
- **Change:** Resolve the cadence convention inconsistency. The Garmin FIT SDK specification stores running cadence as total steps per minute (SPM) in the record message 'cadence' field, contrary to the comment at fit.py:90 ('Cadence (spm, but stored as rpm for run)'). Verify by reading an actual FIT file: if the raw integer value is ~170 (consistent with running SPM), the comment is wrong and no doubling is needed. If the value is ~85 (single-foot RPM), doubling is needed to match Strava. Update the comment at fit.py:90 to accurately reflect the FIT SDK spec and either add or confirm the absence of doubling. Document the canonical convention in a code comment for all three parsers.
- **Verify:** Compare cadence values from the same run parsed via both FIT and Strava paths on a test fixture. Both must produce values in the 160-185 SPM range for a normal running cadence. grep -n 'cadence' src/biosystems/ingestion/fit.py src/biosystems/ingestion/strava.py src/biosystems/ingestion/gpx.py — comments must agree on the canonical output unit (total SPM).
- **Depends on:** —
## P2

### C29 — `tools/sanitize_gps.py:50-51`
- **Closes:** F-sanitize-1
- **Change:** At the start of sanitize_dataframe() (before line 50), add 'df = df.copy()' to prevent in-place mutation of the caller's DataFrame. Remove the conditional column assignment at lines 50-51 that mutates the original df, and instead operate on the copy from this point forward. The 'df_truncated = df[mask].copy()' at line 74 should then become 'df_truncated = df[mask]' (copy is already made at the top).
- **Verify:** python -c "import pandas as pd; from tools.sanitize_gps import sanitize_dataframe; df = pd.DataFrame({'lat':[37.0]*10,'lon':[-122.0]*10,'ele':[10.0]*10,'dist':[50.0*i for i in range(10)]}); original_cols = set(df.columns); sanitize_dataframe(df); assert set(df.columns) == original_cols, f'columns mutated: {set(df.columns) - original_cols}'; print('OK: no mutation')" — must print OK
- **Depends on:** —

### C30 — `tools/sanitize_gps.py:217-265`
- **Closes:** F-sanitize-3
- **Change:** In the main() function, after resolving input_path and output_path at lines 217-218, add a guard: 'if output_path.resolve() == input_path.resolve(): sys.exit("Error: output path must differ from input path; refusing to overwrite source data")'. Place this check before any file-reading or writing begins.
- **Verify:** python tools/sanitize_gps.py data/ data/ --recursive 2>&1 | grep 'Error.*overwrite' — must print the error message and exit without modifying any files.
- **Depends on:** —

### C31 — `src/biosystems/physics/gap.py:224`
- **Closes:** F-gap-ele-zero-sea-level-7
- **Change:** In check_elevation_quality() at line 224, change 'ele_series = df[ele_col].replace(0, np.nan).dropna()' to 'ele_series = df[ele_col].dropna()' — remove the replace(0, np.nan) that falsely treats sea-level 0m readings as missing data. Update the corresponding pattern in metrics.py at the check_elevation_quality call site (~line 317) if it also filters ele==0. Add a comment: '# 0 m is valid elevation for coastal/sea-level activities; only true NaN indicates missing'.
- **Verify:** pytest tests/test_physics_gap.py -v — all existing tests pass. Add a new test in test_physics_gap.py: test_sea_level_elevation — construct a df with all ele=0 and verify check_elevation_quality returns (True, ...) rather than (False, 'insufficient elevation data points').
- **Depends on:** —

### C32 — `src/biosystems/physics/metrics.py:310`
- **Closes:** F-cadence-int-truncation-10
- **Change:** At line 310, change 'avg_cadence = int(cadence_series.mean())' to 'avg_cadence = round(cadence_series.mean())' (round() returns an int in Python 3 when given 0 ndigits). This makes cadence consistent with all other metric fields in run_metrics() which use round() rather than int() for numeric rounding.
- **Verify:** python -c "import pandas as pd; import numpy as np; from biosystems.physics.metrics import run_metrics; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); df = pd.read_csv('data/sample/sample_run.csv', parse_dates=['time']); df['cadence'] = [179.9]*len(df); m = run_metrics(df, z); assert m.avg_cadence == 180, f'got {m.avg_cadence}'; print('OK: rounded to 180')" — must print OK (int(179.9) would give 179; round(179.9) gives 180)
- **Depends on:** —

### C33 — `src/biosystems/physics/metrics.py:301-303`
- **Closes:** F-new-metrics-pace-keyerror-06
- **Change:** Before the compute_training_zones() call at line 301 that accesses df['pace_sec_km'] directly, add a guard: 'if "pace_sec_km" not in df.columns: raise KeyError("pace_sec_km column not found; call add_derived_metrics() on FIT DataFrames before run_metrics()")'. This mirrors the existing guards for 'cadence' (line 307) and 'ele' (line 315) and produces a clear error message instead of an opaque KeyError.
- **Verify:** python -c "import pandas as pd; from biosystems.physics.metrics import run_metrics; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); df = pd.DataFrame({'hr':[160.0]*10,'dist':[50.0]*10,'dt':[5.0]*10,'cadence':[170]*10}); run_metrics(df, z)" 2>&1 | grep 'pace_sec_km.*add_derived' — must show the helpful KeyError message
- **Depends on:** —

### C34 — `src/biosystems/cli.py:415, src/biosystems/cli.py:526, src/biosystems/ingestion/strava.py:345, src/biosystems/wellness/analytics.py:74`
- **Closes:** F-cli-dead-1
- **Change:** Remove four dead bare-expression statements: 1) cli.py:415 — delete '[bb for bb in report.block_bests if bb.is_new_best and bb.prev_best_s is None]' (the entire line). 2) cli.py:526 — delete 'summary.get("moving_time", 0)' (the entire line). 3) strava.py:345 — delete 'len(streams["time"])' (the entire line). 4) analytics.py:74 — delete '(df.index.max() - df.index.min()).days + 1' (the entire line).
- **Verify:** grep -n 'prev_best_s is None\]$' src/biosystems/cli.py — must return nothing. grep -n 'moving_time", 0)$' src/biosystems/cli.py — must return nothing. grep -n 'len(streams\[.time.\])' src/biosystems/ingestion/strava.py — must return nothing. pytest -q — all existing tests still pass.
- **Depends on:** —

### C35 — `daily_running_brief/daily_running_brief.py:26-27,1157-1158`
- **Closes:** F-brief-1
- **Change:** 1) Update the module-level docstring at lines 26-27 to list all three providers in priority order: 'Required env vars (one of): OPENROUTER_API_KEY (tried first), OPENAI_API_KEY (second), ANTHROPIC_API_KEY (fallback)'. 2) Update the RuntimeError message at line 1157-1158 to include OPENROUTER_API_KEY: 'No API key found. Set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY.'
- **Verify:** grep 'OPENROUTER' daily_running_brief/daily_running_brief.py | grep -E 'docstring|env var|No API' — must match at least two lines (docstring and error message). grep -c 'OPENROUTER_API_KEY' daily_running_brief/daily_running_brief.py — must be >= 3 (existing call sites plus the two new references).
- **Depends on:** —

### C36 — `tools/ingest_new_runs.py:281-284`
- **Closes:** F-iso-week-no-year-4
- **Change:** At line 284, change 'iso_week = dt.isocalendar().week' to 'iso_week = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"'. Update all downstream dict operations that used iso_week as an integer key (lines 304, 311) — they now use the string key and the weekly JSON records will carry YYYY-WNN keys instead of bare integers.
- **Verify:** python -c "from tools.ingest_new_runs import regenerate_weekly_json; print('import OK')" (no crash). After running the tool on any fixture, verify 'grep -E "W[0-9]{2}" data/real_weekly_data.json' matches 'YYYY-W' prefixed week keys rather than bare integers.
- **Depends on:** —

### C37 — `tools/reproduce_study_analysis.py:85`
- **Closes:** F-new-repro-week-no-year-02
- **Change:** In parse_week() at line 85, change 'return dt.isocalendar()[1]' to 'return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"'. This makes the week key format (YYYY-WNN) consistent with C36 and prevents year-collision when running the reproduction script on a dataset spanning multiple years.
- **Verify:** python -c "from tools.reproduce_study_analysis import parse_week; from datetime import date; k = parse_week(date(2025, 5, 1)); assert k == '2025-W18', f'got {k}'; print('OK:', k)" — must print OK: 2025-W18
- **Depends on:** —

### C38 — `README.md:238,311`
- **Closes:** F-doc-08
- **Change:** Update both occurrences of the test count in README.md. 1) Line 238: change '161 tests' to the current count (run 'pytest --collect-only -q | tail -1' to get the current number, currently 185 from Stage 3 execution). 2) Line 311: change '161 tests' to the same current count. Add a note: 'count subject to change as tests are added'.
- **Verify:** CURRENT=$(python -m pytest --collect-only -q 2>/dev/null | grep 'selected' | grep -oE '[0-9]+' | head -1); grep "$CURRENT tests" README.md | wc -l — must return 2 (both occurrences updated to current count)
- **Depends on:** C26, C27, C42, C43

### C39 — `src/biosystems/physics/metrics.py:306-310`
- **Closes:** F-intent-01
- **Change:** In run_metrics() at lines 306-310, change avg_cadence to compute from the walk-filtered set rather than the full df. Replace 'if "cadence" in df.columns: cadence_series = df["cadence"].replace(0, np.nan); avg_cadence = round(cadence_series.mean())' with 'if "cadence" in df.columns and "is_walk" in df.columns: cadence_series = df.loc[~df["is_walk"].astype(bool), "cadence"].replace(0, np.nan); avg_cadence = round(cadence_series.mean()) \nelif "cadence" in df.columns: cadence_series = df["cadence"].replace(0, np.nan); avg_cadence = round(cadence_series.mean())'. This makes avg_cadence consistent with the report's stated 'Run-Only Filter' methodology.
- **Verify:** python -c "import pandas as pd; from biosystems.physics.metrics import run_metrics; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); df = pd.read_csv('data/sample/sample_run.csv', parse_dates=['time']); df['is_walk'] = False; df.loc[:10, 'is_walk'] = True; df.loc[:10, 'cadence'] = 60; m = run_metrics(df, z); print('cadence excludes walk:', m.avg_cadence)" — reported cadence must exclude the 60 spm walk rows
- **Depends on:** C32

### C40 — `src/biosystems/environment/weather.py:234`
- **Closes:** F-weather-2
- **Change:** At line 234, change 'now = datetime.utcnow()' to 'now = datetime.now(timezone.utc)'. The timezone import is already present at line 12 ('from datetime import datetime, timedelta, timezone'), making this a one-token change.
- **Verify:** python -W error::DeprecationWarning -c "from biosystems.environment.weather import WeatherCache; print('no DeprecationWarning')" — must not raise DeprecationWarning. pytest tests/test_environment.py -q — all tests pass.
- **Depends on:** —

### C41 — `tests/test_cli_integration.py:17-22`
- **Closes:** F-testcov-2
- **Change:** C26 already performs this fix as part of its full rewrite of tests/test_cli_integration.py. Verify that the rewritten file produced by C26 includes 'env={**os.environ, "PYTHONPATH": "src"}' in the subprocess.run call and 'import os' in the imports section. No additional code change is required beyond C26; this item tracks verification that F-testcov-2 (discarded inherited environment) is resolved by the C26 rewrite.
- **Verify:** grep 'os.environ' tests/test_cli_integration.py — must match. pytest tests/test_cli_integration.py -v — the test must PASS (after C26 creates the synthetic GPX fixture).
- **Depends on:** C26

### C42 — `tests/test_physics_metrics.py`
- **Closes:** F-testcov-3
- **Change:** Add a new test class TestCalculateDecouplingEdgeCases (or extend the existing TestCalculateDecoupling) with: (1) test_decoupling_one_row_df — call calculate_decoupling with a 1-row DataFrame ({'hr':[160.0],'dist':[50.0],'dt':[5.0]}) and assert the result is None (after C01 fix); (2) test_decoupling_zero_ef1 — call with first_half that has all dist=0 and assert None or a handled return rather than ZeroDivisionError.
- **Verify:** pytest tests/test_physics_metrics.py::TestCalculateDecouplingEdgeCases -v — both new tests must PASS. pytest tests/test_physics_metrics.py -q — all existing tests still pass.
- **Depends on:** C01

### C43 — `tests/test_physics_metrics.py`
- **Closes:** F-testcov-4
- **Change:** In the existing test_with_cadence test (around line 265), replace the fixture's uniform cadence=170 with values that produce a non-integer mean, e.g. cadence values of [179, 180, 180, 180, 180, ...] so the mean is 179.8. Assert avg_cadence == 180 (round) rather than 179 (int truncation). This test directly detects the truncation-vs-rounding bug (C32 fix).
- **Verify:** pytest tests/test_physics_metrics.py -k 'test_with_cadence' -v — must PASS after C32 is applied (round gives 180); would FAIL if int() truncation were re-introduced.
- **Depends on:** C32

### C44 — `src/biosystems/signal/walk_detection.py:251-255`
- **Closes:** F-walk-debug-print-3
- **Change:** Remove the '[SANITY DEBUG]' print statement at lines 251-255. Replace the bare print call with a structured log call: import logging at the top of walk_detection.py if not already present; change 'print(f"[SANITY DEBUG] SKIPPING BAD SEGMENT...", file=sys.stderr)' to 'log.debug("Skipping walk segment: seg_id=%s dur_s=%.1f dist_km=%s (zero or missing distance)", seg_id, dur_s, dist_km)'. The 'continue' after the print is still valid — keep it.
- **Verify:** python -c "import sys; sys.stderr = open('/dev/null','w'); from biosystems.signal import walk_block_segments; print('no debug output on import')" — no '[SANITY DEBUG]' text. grep 'SANITY DEBUG' src/biosystems/signal/walk_detection.py — must return nothing.
- **Depends on:** —

### C45 — `src/biosystems/signal/walk_detection.py:37-240, src/biosystems/models.py:377`
- **Closes:** F-new-walk-segment-unused-model-15
- **Change:** In walk_block_segments(), change the segment dict construction at the end of each block to instantiate WalkSegment instead of a plain dict. Add 'from biosystems.models import WalkSegment' to the imports. Return List[WalkSegment] from the function. Update models.py line 377: change 'walk_segments: list[dict]' to 'walk_segments: list[WalkSegment]'. This enforces the Pydantic constraints (non-negative duration, valid tag) in production as well as in tests.
- **Verify:** python -c "from biosystems.signal.walk_detection import walk_block_segments; from biosystems.models import WalkSegment; print('import OK')" — no ImportError. After running walk_block_segments on a synthetic fixture, assert all returned items are isinstance(item, WalkSegment) (or dict with valid WalkSegment fields after model_validate).
- **Depends on:** —

### C46 — `tests/test_habitdash.py (new file)`
- **Closes:** F-test-2
- **Change:** Create tests/test_habitdash.py with mock-based unit tests: (1) test_retry_logic — mock requests.get to return 429 with x-ratelimit-remaining: '0' and x-ratelimit-reset: '30', assert _get() retries and eventually raises or returns []; (2) test_non_numeric_remaining — mock x-ratelimit-remaining: 'bad' header, assert no ValueError (tests C11 fix); (3) test_exhausted_retries_silent_return — mock 3 consecutive failures, assert fetch_all_metrics() returns [] without raising; (4) test_15s_delay — mock time.sleep and verify it is called with >= 15 between non-rate-limited requests.
- **Verify:** pytest tests/test_habitdash.py -v — all 4 tests pass. Coverage: pytest --cov=biosystems.wellness.habitdash tests/test_habitdash.py — coverage must be > 0% (currently 0).
- **Depends on:** C11

### C47 — `src/biosystems/analytics/history.py:11-19,211`
- **Closes:** F-bug-01
- **Change:** Add 'from biosystems.models import ZoneConfig' to the imports in history.py (lines 11-19). Remove the '# type: ignore[name-defined]  # noqa: F821' suppression comment from line 211. This makes the annotation resolvable by get_type_hints() and mypy without relying on PEP 563 deferral to silently hide the broken reference.
- **Verify:** python -c "import typing; from biosystems.analytics.history import backfill_from_strava; hints = typing.get_type_hints(backfill_from_strava); print('ZoneConfig resolved:', hints['zone_config'])" — must print ZoneConfig class without NameError
- **Depends on:** —

### C48 — `src/biosystems/ingestion/fit.py:207-208`
- **Closes:** F-fit-indoor-gps-11
- **Change:** In add_derived_metrics(), before the ValueError at line 207-208 that rejects DataFrames without latitude/longitude, add a fallback path for indoor activities: 'if "latitude" not in df.columns or "longitude" not in df.columns: if "distance" in df.columns and "speed" in df.columns: df["dist"] = df["distance"].diff().fillna(0); df["speed_mps"] = df["speed"]; return df  # indoor/treadmill: use native FIT distance and speed; else: raise ValueError(...)'. This makes indoor FIT files usable via the library API.
- **Verify:** python -c "import pandas as pd; from biosystems.ingestion.fit import add_derived_metrics; df = pd.DataFrame({'time':pd.date_range('2025-01-01',periods=10,freq='s'),'hr':[155]*10,'cadence':[170]*10,'distance':[i*3.0 for i in range(10)],'speed':[3.0]*10}).set_index('time'); result = add_derived_metrics(df); print('indoor FIT OK, speed_mps:', result['speed_mps'].iloc[0])" — must not raise ValueError
- **Depends on:** —

### C62 — `src/biosystems/physics/metrics.py:217`
- **Closes:** F-decoupling-ef1-small-12
- **Change:** This bug is partially handled by C01 (which adds a guard for ef_1=0 at the division site). Verify that the guard added in C01 covers this path: when first_half is non-empty but all dist=0, ef_1 = 0.0. The conditional in C01 'decouple_pct = abs(ef_2 - ef_1) / ef_1 * 100 if ef_1 != 0.0 else None' must return None for this case. Add a regression test to tests/test_physics_metrics.py: test_decoupling_zero_ef1 — call calculate_decoupling with a DataFrame where first_half has dist=0 throughout and assert None is returned.
- **Verify:** pytest tests/test_physics_metrics.py -k 'test_decoupling_zero_ef1' -v — must PASS. python -c "import pandas as pd; from biosystems.physics.metrics import calculate_decoupling; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); n=100; df = pd.DataFrame({'hr':[160.0]*n,'dist':[0.0]*(n//2)+[50.0]*(n//2),'dt':[5.0]*n}); r = calculate_decoupling(df, z); print('zero_ef1 result:', r)" — must print None, not ZeroDivisionError
- **Depends on:** C01

### C64 — `tools/ingest_new_runs.py:101`
- **Closes:** F-new-ingest-nan-cadence-study-14
- **Change:** In _add_walk_flag() at line 101, change 'df["is_walk"] = (df["pace_min_per_km"] > 9.5) | (df["cadence"] < 140)' to 'df["is_walk"] = (df["pace_min_per_km"] > 9.5) | (df["cadence"].fillna(0) < 140)'. This aligns the study ingestion tool's cadence handling with C19 (cli.py fillna(0) change) and prevents sensor-dropout rows from being silently classified as running in the study data pipeline.
- **Verify:** python -c "import inspect; from tools.ingest_new_runs import _add_walk_flag; src = inspect.getsource(_add_walk_flag); assert 'fillna(0)' in src, 'fillna not applied'; print('fillna(0) present in _add_walk_flag')" — must print confirmation
- **Depends on:** C19

### C65 — `src/biosystems/physics/metrics.py:285-293, src/biosystems/physics/report.py:464-469`
- **Closes:** F-run-only-walks-leak-3
- **Change:** In run_metrics(), when is_walk column is present, compute distance_km, duration_min, avg_pace_min_per_km, and avg_hr from the non-walk subset as well. Add: 'base_df = df[~df["is_walk"].astype(bool)] if "is_walk" in df.columns else df; total_dist_m = float(base_df["dist"].sum()); secs = float(base_df["dt"].sum()); avg_hr = float(base_df["hr"].mean())'. This makes run_only_metrics genuinely different from session_metrics for these fields, not just for EF and decoupling.
- **Verify:** python -c "import pandas as pd; from biosystems.physics.metrics import run_metrics; from biosystems.models import ZoneConfig, HeartRateZone; z = ZoneConfig(resting_hr=50, threshold_hr=186, zones={'Z2': HeartRateZone(name='Z2', bpm=(145,165), pace_min_per_km=(4.5,6.0))}); df = pd.read_csv('data/sample/sample_run.csv', parse_dates=['time']); df['is_walk'] = False; df.loc[:50, 'is_walk'] = True; m_full = run_metrics(df.drop(columns=['is_walk']), z); m_filtered = run_metrics(df, z); assert m_filtered.distance_km < m_full.distance_km, 'walk filter did not reduce distance'; print('run_only distance:', m_filtered.distance_km, 'session:', m_full.distance_km)"
- **Depends on:** —

### C66 — `src/biosystems/physics/report.py:350-354`
- **Closes:** F-report-kmsplit-zero-pace
- **Change:** In _parse_km_splits(), change the else branch for absent or zero average_speed from storing 0.0 to skipping the split. Replace 'else: pace_min_per_km = 0.0' (lines 352-354) with 'else: continue  # skip splits with no speed data (paused auto-laps)'. This matches the sibling _parse_laps() behavior which already skips zero-speed laps.
- **Verify:** python -c "from biosystems.physics.report import _parse_km_splits; splits = [{'distance': 1000, 'average_speed': None, 'moving_time': 360}]; result = _parse_km_splits(splits); assert all(s.pace_min_per_km > 0 for s in result if hasattr(s,'pace_min_per_km')), 'zero-pace split present'; print('zero-speed splits skipped, count:', len(result))" — must show 0 results (the zero-speed split was skipped)
- **Depends on:** —
## P3

### C49 — `daily_running_brief/daily_running_brief.py:57,1086,1116`
- **Closes:** F-new-brief-reasoning-flag-05
- **Change:** Remove 'gpt-5' from the _REASONING_PREFIXES tuple at lines 1086 and 1116. The prefix 'gpt-5' is too broad and incorrectly matches 'gpt-5-mini' (a standard autoregressive model). Keep ('o1', 'o3', 'o4') as reasoning prefixes. If future GPT-5 reasoning models need to be handled, use their exact model IDs. This ensures temperature=0 is passed for gpt-5-mini, making the daily brief deterministic.
- **Verify:** python -c "from daily_running_brief.daily_running_brief import _OPENAI_MODEL; prefixes = ('o1','o3','o4'); assert not _OPENAI_MODEL.startswith(tuple(prefixes)), f'{_OPENAI_MODEL} mistakenly in reasoning set'; print('gpt-5-mini not in reasoning set')" — must print confirmation
- **Depends on:** —

### C50 — `src/biosystems/physics/report.py:195`
- **Closes:** F-new-aev-keyerror-03
- **Change:** At the start of _compute_aev(), add a column existence guard matching the sibling functions: 'if "pace_min_per_km" not in run_df.columns or "hr" not in run_df.columns: return None'. This prevents a KeyError when build_run_report() is called from contexts that have not added pace_min_per_km (e.g., library consumers or future test fixtures).
- **Verify:** pytest tests/test_report.py::test_compute_aev_missing_column -v — must PASS (test created in C27). grep -n 'if.*pace_min_per_km.*not in' src/biosystems/physics/report.py — must show at least two occurrences (the sibling guard and this new one).
- **Depends on:** C27

### C51 — `src/biosystems/analytics/trending.py:48`
- **Closes:** F-tsb-docstring-typo-5
- **Change:** At line 48, fix the docstring typo: change '- `tsb` (float): CTB = CTL - ATL' to '- `tsb` (float): TSB = CTL - ATL'. One character change (C → T).
- **Verify:** grep 'CTB' src/biosystems/analytics/trending.py — must return nothing.
- **Depends on:** —

### C52 — `src/biosystems/analytics/trending.py:153-167`
- **Closes:** F-new-trending-roll-closure-loop-16
- **Change:** Move the 'def _roll(buf: list[float]) -> float | None:' helper (currently defined inside the 'for e in run_entries:' loop at line 165) above the loop start at line 153. Since _roll only closes over 'window' (a parameter of compute_rolling_metrics(), not a loop variable), moving it above the loop produces identical semantics with a single function allocation instead of N.
- **Verify:** pytest tests/test_trending.py -q — all tests pass. python -c "import inspect; from biosystems.analytics.trending import compute_rolling_metrics; src = inspect.getsource(compute_rolling_metrics); loop_pos = src.index('for e in'); roll_pos = src.index('def _roll'); assert roll_pos < loop_pos, 'closure still inside loop'; print('closure moved above loop')" — must print confirmation
- **Depends on:** —

### C53 — `src/biosystems/cli.py:886,919-920`
- **Closes:** F-new-cli-efforts-mislabel-02
- **Change:** At line 886, separate the two None cases: 'improvement_s = first_t - best_t if first_date != best_date or first_t != best_t else None'. At lines 919-920, consult recording_count: change 'if row["improvement_s"] is None:' display branch to 'if row["improvement_s"] is None and row.get("recording_count", 1) <= 1: typer.echo(f"    First: {fm}:{fs:02d}  on {row["first_date"]}  (only recording)") \nelif row["improvement_s"] is None: typer.echo(f"    Best: {bm}:{bs:02d}  (no improvement across {row["recording_count"]} recordings)")'. This distinguishes single-recording entries from multi-recording plateaus.
- **Verify:** Construct a test history with two identical-time entries for the same distance; run 'biosystems efforts' and verify the output says 'no improvement across 2 recordings' rather than '(only recording)'.
- **Depends on:** —

### C54 — `src/biosystems/cli.py:82-91`
- **Closes:** F-cli-zone-silent-drop
- **Change:** In load_zone_config() at lines 82-91, when a zone entry is skipped due to missing 'bpm' or 'pace_min_per_km' keys, replace the silent 'continue' with 'import logging; log = logging.getLogger(__name__); log.warning("Zone config entry '%s' skipped: missing required keys (bpm and pace_min_per_km both required), found keys: %s", zone_name, list(data.keys())); continue'. This surfaces misconfiguration to the user.
- **Verify:** python -c "import logging; logging.basicConfig(level=logging.WARNING); from biosystems.cli import load_zone_config; import yaml, io, tempfile, os; cfg = yaml.dump({'Z2': {'bpm': [145,165]}}); t = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False); t.write(cfg); t.close(); load_zone_config(t.name); os.unlink(t.name)" 2>&1 | grep 'skipped.*pace_min_per_km' — must print the warning
- **Depends on:** —

### C55 — `src/biosystems/physics/gap.py:171-185`
- **Closes:** F-gap-loop-perf-8
- **Change:** Vectorize the GAP computation loop. Replace the two for-loops at lines 171-185 (computing grade and gap_pace per row via .iloc[i]) with vectorized numpy operations: compute grade as np.diff on the elevation rolling-mean series (with prepend of first value), compute gap_factor via np.vectorize or np.where over the grade array using the Minetti polynomial coefficients. This eliminates ~3600 Python-level .iloc calls per 60-minute activity.
- **Verify:** pytest tests/test_physics_gap.py -q — all tests pass (correctness unchanged). python -c "import timeit, pandas as pd, numpy as np; from biosystems.physics.gap import compute_grade_adjusted_pace; df = pd.DataFrame({'ele': np.random.randn(3600).cumsum() + 100, 'dist': [3.0]*3600, 'dt': [1.0]*3600, 'speed_mps': [3.0]*3600}); t = timeit.timeit(lambda: compute_grade_adjusted_pace(df), number=5); print(f'vectorized: {t/5:.3f}s per call')" — report timing improvement vs baseline
- **Depends on:** —

### C56 — `tools/sanitize_gps.py:1-16`
- **Closes:** F-sanitize-2
- **Change:** Add a 'Re-identification Risks' subsection to the module-level 'Security Guarantees' docstring at lines 11-15. Insert after the existing guarantees: 'Residual re-identification risk: The preserved elevation (ele) column can fingerprint a route via its terrain profile. Unique elevation signatures (hills, bridges, tunnels) allow route identification without lat/lon. If route anonymity beyond endpoint truncation is required, consider also removing or smoothing the elevation column before publication.'
- **Verify:** grep 'terrain\|fingerprint\|elevation.*re-identification' tools/sanitize_gps.py — must match the new warning text.
- **Depends on:** —

### C57 — `src/biosystems/cli.py:748-751`
- **Closes:** F-cli-date-5
- **Change:** In the summary/efforts/top/backfill-streams commands that accept a --since or --after option, parse the date string to datetime.date before lexicographic comparison. Add a helper: 'def _parse_since(since_str: str | None) -> str | None: if since_str is None: return None; try: datetime.date.fromisoformat(since_str); return since_str; except ValueError: raise typer.BadParameter(f"Invalid date format: {since_str!r}. Expected YYYY-MM-DD.")'. Call _parse_since() on the raw option value before line 751.
- **Verify:** biosystems summary --since 2025-1-1 2>&1 | grep 'Invalid date format\|YYYY-MM-DD' — must print an error message rather than silently filtering incorrectly.
- **Depends on:** —

### C58 — `src/biosystems/signal/walk_detection.py:137`
- **Closes:** F-walk-pace-unweighted-6
- **Change:** At line 137, replace the unweighted 'avg_pace = np.mean(paces) if paces else np.nan' with a duration-weighted mean: 'avg_pace = (sum(s["avg_pace_min_km"] * s["dur_s"] for s in valid_segments if s.get("avg_pace_min_km") and s.get("dur_s")) / total_walk_time) if total_walk_time > 0 else np.nan'. This is methodologically correct for aggregating per-segment average pace values.
- **Verify:** pytest tests/test_signal.py -q — all tests pass. python -c "from biosystems.signal.walk_detection import summarize_walk_segments; segs = [{'dur_s':60,'avg_pace_min_km':10.0,'avg_hr':130,'avg_cad':100,'tag':'warm-up','note':None,'hr_recovery_rate_bpm_per_min':None,'dist_km':0.1}, {'dur_s':300,'avg_pace_min_km':8.0,'avg_hr':120,'avg_cad':105,'tag':'mid-session','note':None,'hr_recovery_rate_bpm_per_min':None,'dist_km':0.5}]; s = summarize_walk_segments(segs); expected = (60*10.0+300*8.0)/360; assert abs(s.avg_pace - expected) < 0.01, f'got {s.avg_pace}, expected {expected}'; print('OK: weighted mean')" — must print OK
- **Depends on:** —

### C59 — `src/biosystems/signal/walk_detection.py:268-277`
- **Closes:** F-intent-02
- **Change:** Either (a) emit tag='pause' for short mid-session segments (dur_s < 30 and dist_km < 0.05) by changing the assignment at line 276-278 from 'tag = "mid-session"' + 'note = "pause?"' to 'tag = "pause"'; or (b) remove 'pause' from the WalkSegment.tag field regex pattern in models.py:294 and update the pattern to '^(warm-up|mid-session|cool-down)$'. Option (a) makes the code and model consistent; option (b) removes the dead option. Recommend option (a) since it matches the documented intent of the 'pause?' note.
- **Verify:** python -c "from biosystems.models import WalkSegment; ws = WalkSegment(seg_id=1, dur_s=25, dist_km=0.04, avg_hr=120.0, avg_cad=0.0, tag='pause', note=None, hr_recovery_rate_bpm_per_min=None, avg_pace_min_km=None); print('pause tag valid:', ws.tag)" — must print 'pause tag valid: pause' without ValidationError
- **Depends on:** —

### C60 — `src/biosystems/environment/weather.py:184-218`
- **Closes:** F-new-weather-cache-nodup-11
- **Change:** In WeatherCache.set() at line 200, before the pd.concat call at line 214, add a dedup check: 'existing = self.cache[(self.cache["lat"] == lat_r) & (self.cache["lon"] == lon_r) & (self.cache["date"] == date_str)]; if not existing.empty: return  # already cached, no-op'. This prevents duplicate rows accumulating in both the in-memory cache and the on-disk parquet file.
- **Verify:** python -c "from biosystems.environment.weather import WeatherCache; import tempfile, os; wc = WeatherCache(tempfile.mktemp(suffix='.parquet')); wc.set(37.0, -122.0, '2025-01-01', {'temperature_2m': [15.0]}); wc.set(37.0, -122.0, '2025-01-01', {'temperature_2m': [15.0]}); assert len(wc.cache) == 1, f'expected 1 row, got {len(wc.cache)}'; print('OK: no duplicate')" — must print OK
- **Depends on:** —

### C67 — `src/biosystems/ingestion/strava.py:489-502`
- **Closes:** F-new-strava-name-lost-02
- **Change:** In fetch_activity_streams(), add the activity name to activity_meta. After the existing dict construction at lines 489-502, add: 'activity_meta["name"] = activity.get("name")'. Also update cli.py:330 to use this value: change 'activity_name_str = summary.get("name") if activity_id is None else None' to 'activity_name_str = summary.get("name") or meta.get("name")' (where meta is the returned activity_meta dict from fetch_activity_streams).
- **Verify:** python -c "import inspect; from biosystems.ingestion.strava import StravaClient; src = inspect.getsource(StravaClient.fetch_activity_streams); assert '"name"' in src or 'name' in src, 'name not in activity_meta'; print('name extraction added')" — must print confirmation
- **Depends on:** —

### C68 — `pyproject.toml:17`
- **Closes:** F-doc-09
- **Change:** Change the Development Status classifier from 'Development Status :: 4 - Beta' to 'Development Status :: 5 - Production/Stable'. This is bundled with the version bump in C25 (both changes reflect the v1.1.0 stable release).
- **Verify:** grep 'Development Status' pyproject.toml — must show '5 - Production/Stable'.
- **Depends on:** C25

### C69 — `daily_running_brief/daily_running_brief.py:148-153`
- **Closes:** F-new-brief-dead-pct-rank-03
- **Change:** Remove the dead nested function _pct_rank (lines 148-153) inside _compute_history_stats(). It is created on every invocation but never called; the module-level _pct_rank_inner at line 179 is the active implementation. No caller or test references the nested function.
- **Verify:** grep -n 'def _pct_rank' daily_running_brief/daily_running_brief.py — must show only the module-level definition at line ~179, not the nested one inside _compute_history_stats.
- **Depends on:** —

### C70 — `src/biosystems/cli.py:1109-1110`
- **Closes:** F-cli-types-3
- **Change:** Change the type annotations for date_start and date_end in wellness_sync from 'str' to 'Optional[str]' (or 'str | None'). Lines 1109-1110: 'date_start: str | None = typer.Option(None, ...)' and 'date_end: str | None = typer.Option(None, ...)'.
- **Verify:** python -c "import inspect; from biosystems.cli import wellness_sync; hints = {k:str(v) for k,v in wellness_sync.__annotations__.items()}; assert 'None' in hints.get('date_start','') or 'Optional' in hints.get('date_start',''), 'annotation wrong'; print('type annotation correct:', hints.get('date_start'))"
- **Depends on:** —

### C71 — `README.md:182-198`
- **Closes:** F-doc-05
- **Change:** Update the README 'Run-Only Filter' code snippet (lines 182-188) to show all four steps of the actual implementation: (1) is_walk pre-filter, (2) HR dropna, (3) Z2 HR threshold filter, (4) fallback when fewer than 120 qualifying rows exist. Replace the simplified 3-line pseudocode with a 10-line code block that matches the actual function at metrics.py:133-153.
- **Verify:** grep 'is_walk' README.md — must match the updated snippet. The README snippet must contain at least 'is_walk', 'work_df', 'lz2', and 'fallback' or '120' to reflect all four steps.
- **Depends on:** —

### C72 — `src/biosystems/wellness/habitdash.py:105-108`
- **Closes:** F-habitdash-1
- **Change:** Add epoch-vs-seconds detection for the x-ratelimit-reset header. If the parsed value exceeds 7200 (2 hours in seconds, which no rate-limit window should exceed), treat it as a Unix timestamp and compute 'wait = max(0, reset_secs_epoch - int(time.time()) + 1)' clamped to 3600. Add a comment documenting the ambiguity. The current code's min(..., 3600) cap is retained as a hard upper bound regardless of interpretation.
- **Verify:** python -c "import inspect; from biosystems.wellness.habitdash import HabitDashClient; src = inspect.getsource(HabitDashClient._get); assert 'epoch' in src.lower() or '7200' in src, 'epoch detection missing'; print('epoch detection present')" — must print confirmation
- **Depends on:** C11


_Generated 2026-06-17T21:19:16.035Z · branch claude/epic-goldberg-hebvrp_
