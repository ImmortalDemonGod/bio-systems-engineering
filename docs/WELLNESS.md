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
```

## G/A/R Readiness Signal

Delta-first classification (7-day rolling mean as baseline):

| Signal | RED | AMBER |
|--------|-----|-------|
| HRV (7d drop) | > 20% | 10–20% |
| RHR (7d spike) | > 8 bpm | 5–8 bpm |
| Recovery Score | < 34% | 34–67% |
| Sleep Score | < 60% | 60–80% |

Priority: any RED signal → 🔴 RED. No RED but any AMBER → 🟡 AMBER. All clear → 🟢 GREEN.

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
| `src/biosystems/wellness/cache.py` | Parquet I/O, delta math, G/A/R classification |
| `src/biosystems/cli.py` | `wellness-sync` and `wellness-show` CLI commands |
| `/Volumes/Totallynotaharddrive/bio-systems-engineering/.env` | API keys (not committed to git) |
