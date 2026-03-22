# Wellness Integration

## Overview

Wellness telemetry flows from Whoop + Garmin → HabitDash API → local parquet cache → biosystems CLI / daily brief.

```
[Whoop + Garmin]
      ↓
[HabitDash API]  (api.habitdash.com/v1)
      ↓  (cron 6:43am daily)
biosystems wellness-sync --days 3
      ↓
~/.biosystems/wellness.parquet   ← local cache, date-indexed
      ↓                                        ↓
biosystems strava {id}          daily_running_brief.py
(enriches RunContext)           (wellness block in brief)
```

## Data Sources

| Source | Metrics |
|--------|---------|
| Whoop | HRV RMSSD, Resting HR, Recovery Score, Sleep Score, Sleep Duration, Strain Score, Respiratory Rate, Skin Temp, Sleep Disturbances/hr, Sleep Consistency |
| Garmin | Resting HR, Body Battery, VO2max, Steps, Active Time, Avg Stress, Respiratory Rate |

## Signal Timing — Critical for Readiness Interpretation

Not all signals are measured at the same time of day. This matters when using them
to make pre-run decisions.

| Signal | Source | Timing | Pre-run valid? |
|--------|--------|--------|----------------|
| Resting HR | Garmin (overnight) | Overnight | ✅ Yes |
| Sleep duration / score | Garmin / Whoop (overnight) | Overnight | ✅ Yes |
| Sleep respiratory rate | Garmin / Whoop (overnight) | Overnight | ✅ Yes |
| HRV RMSSD | Whoop only | Overnight | ✅ Yes (Whoop era only) |
| Recovery Score | Whoop only | Morning | ✅ Yes (Whoop era only) |
| **Body Battery** | **Garmin (intraday avg)** | **Full-day average** | **❌ No** |
| **Avg Stress** | **Garmin (intraday avg)** | **Full-day average** | **❌ No** |

**Body Battery limitation**: HabitDash exports Garmin's Body Battery as a daily average
of intraday readings. This value includes the run's suppressive effect. A low end-of-day
BB does not tell you what your BB was at 7am. The morning peak is not accessible through
the HabitDash API. Do not use Body Battery as a pre-activity gate.

**Without Whoop**: The only pre-run signals available are RHR and sleep metrics.
The `gar_overnight` field in `compute_wellness_context()` classifies readiness using
only these overnight signals and is the correct signal to use for pre-activity decisions.

## G/A/R Readiness Signal

Two classifications are computed and returned by `compute_wellness_context()`:

### `gar` — Full day (reflects how the day went)
Uses all signals including Body Battery and Avg Stress. Appropriate for recovery
accounting after the fact, but **NOT** for pre-activity gating.

### `gar_overnight` — Overnight only (pre-run valid)
Uses only signals measured during sleep: RHR, sleep metrics, HRV (when available),
respiratory rate. This is the only signal that validly reflects pre-run readiness
in the current Garmin-only era.

| Signal | RED | AMBER | Timing |
|--------|-----|-------|--------|
| HRV (7d drop) | > 20% drop from 7d mean | > 10% drop from 7d mean | Overnight ✅ |
| RHR (7d spike) | > +8 bpm above 7d mean | > +5 bpm above 7d mean | Overnight ✅ |
| Recovery Score | < 34% | 34–67% | Overnight ✅ (Whoop only) |
| Sleep Score | < 60% | 60–80% | Overnight ✅ (Whoop only) |
| Resp Rate | > calibrated +2.5σ above personal mean | > calibrated +1.5σ | Overnight ✅ |
| Body Battery | < 30 (fallback) / < personal p20 (calibrated) | < 45 / < personal p40 | Daily avg ❌ |
| Avg Stress | > 55 (fallback) / > personal p90 (calibrated) | > 40 / > personal p75 | Daily avg ❌ |

Priority: any RED → 🔴 RED. No RED but any AMBER → 🟡 AMBER. All clear → 🟢 GREEN.

### Calibration
Thresholds are derived from personal data distribution via `calibrate_thresholds()` in
`analytics.py` once ≥ 30 days of Garmin data exist. **Before calibration**, the system
falls back to absolute constants defined in `cache.py`:
- HRV: −20% / −10% drop from 7-day mean
- RHR: +8 bpm / +5 bpm above 7-day mean
- Body Battery: < 30 / < 45 (absolute)
- Avg Stress: > 55 / > 40 (absolute)
- Resp Rate: σ-based thresholds from `calibrate_thresholds()` (no absolute fallback)

## Cache

- **Location**: `~/.biosystems/wellness.parquet` (respects `BIOSYSTEMS_HOME` env var)
- **Format**: Date-indexed Parquet, one row per day, one column per metric
- **Canonical column names**: defined in `src/biosystems/wellness/habitdash.py` → `COLUMN_MAP`

## CLI Commands

```bash
# Sync last N days (default 7)
biosystems wellness-sync --days 7

# Sync a specific date range
biosystems wellness-sync --from 2026-01-01 --to 2026-03-18

# Show today's wellness context (G/A/R + deltas)
biosystems wellness-show

# Show a specific date
biosystems wellness-show --date 2026-03-15

# JSON output for scripting
biosystems wellness-show --json

# Full analytics: coverage, era stats, correlations, calibrated thresholds
biosystems wellness-analyze

# Longitudinal fitness arc: RHR + VO2max monthly trends
biosystems wellness-trends
```

## Rate Limiting

HabitDash enforces per-IP rate limits. The client:
- Waits 15s between requests (matching old cultivation sync cadence)
- Reads `x-ratelimit-remaining` / `x-ratelimit-reset` headers and backs off automatically if exhausted
- Retries up to 3× on 429, waiting 60s / 120s / 180s

**Do not run wellness-sync manually in rapid succession** — excess requests trigger a penalty window (up to 1 req/hour).

## Cron Schedule

```cron
# Wellness sync — 6:43am daily
43 6 * * * /bin/bash -c 'set -a; source /Volumes/Totallynotaharddrive/bio-systems-engineering/.env; set +a; /opt/homebrew/bin/biosystems wellness-sync --days 3 >> /Users/tomriddle1/.biosystems/wellness-sync.log 2>&1'
```

Log file: `~/.biosystems/wellness-sync.log`

The brief cron (20:00) runs hours later and reads from the already-warm cache — zero live API calls at brief time.

**Note on preemptive gating**: The 6:43am sync pulls yesterday's data. Even if run
immediately, today's Body Battery doesn't exist yet. A true morning gate would require
RHR + sleep metrics only, which are available. Body Battery cannot be used for morning
gating regardless of sync timing.

## Initial Backfill

When setting up for the first time or after an API key rotation:

```bash
set -a && source /Volumes/Totallynotaharddrive/bio-systems-engineering/.env && set +a
biosystems wellness-sync --days 60
```

With 17 metrics × 15s = ~4.25 minutes. Do not interrupt.

## Source Files

| File | Purpose |
|------|---------|
| `src/biosystems/wellness/habitdash.py` | HabitDash API client, field ID registry, column map |
| `src/biosystems/wellness/cache.py` | Parquet I/O, delta math, dual G/A/R classification |
| `src/biosystems/wellness/analytics.py` | Pure-computation: baselines, coverage, calibration, trends, sleep debt, recovery model |
| `src/biosystems/cli.py` | `wellness-sync`, `wellness-show`, `wellness-analyze`, `wellness-trends` CLI commands |
| `/Volumes/Totallynotaharddrive/bio-systems-engineering/.env` | API keys (not committed to git) |
