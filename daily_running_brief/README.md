# Daily Running Brief

Post-run analysis engine that uses the `biosystems` CLI as its data source and Claude
(OpenAI primary, Anthropic fallback) to synthesize physiological assessments.

## Deployment

Drop `daily_running_brief.py` into the OpenClaw scripts directory:

```
cp daily_running_brief.py ~/.openclaw/workspace/scripts/
```

Output writes to:

```
~/.openclaw/workspace/memory/intelligence/YYYY-MM-DD_running_brief.md
```

Seen-runs ledger at:

```
~/.openclaw/workspace/memory/intelligence/seen_runs.json
```

## Requirements

```bash
pip install openai anthropic         # LLM providers
pip install -e /path/to/bio-systems-engineering   # biosystems CLI
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | preferred | gpt-5-mini reasoning model |
| `ANTHROPIC_API_KEY` | fallback | claude-sonnet-4-6 |
| `STRAVA_CLIENT_ID` | yes | Strava OAuth |
| `STRAVA_CLIENT_SECRET` | yes | Strava OAuth |
| `STRAVA_REFRESH_TOKEN` | yes | Strava OAuth |
| `HABITDASH_API_KEY` | optional | Wellness telemetry (Whoop + Garmin via HabitDash) |
| `BIOSYSTEMS_ZONES_PATH` | optional | Override default zones.yml location |

All env vars are read from `/Volumes/Totallynotaharddrive/bio-systems-engineering/.env`.

## Usage

```bash
# Standard: analyze any new runs from the last 7 days
python daily_running_brief.py

# Look back further (e.g. after a vacation)
python daily_running_brief.py --days 14

# Re-analyze runs already in the seen ledger
python daily_running_brief.py --force

# See what would be analyzed without calling Claude
python daily_running_brief.py --dry-run
```

## cron

Two cron jobs are required — one for wellness sync, one for the brief itself.

```cron
# 1. Wellness sync — runs at 6:43am daily, populates ~/.biosystems/wellness.parquet
#    Fetches last 3 days of Whoop + Garmin data from HabitDash.
#    Rate limit: ~4 req/min, 17 metrics → ~4 min runtime.
43 6 * * * /bin/bash -c 'set -a; source /Volumes/Totallynotaharddrive/bio-systems-engineering/.env; set +a; /opt/homebrew/bin/biosystems wellness-sync --days 3 >> /Users/tomriddle1/.biosystems/wellness-sync.log 2>&1'

# 2. Brief — runs at 20:00, picks up any runs completed that day
#    Reads wellness from cache (no live API calls).
0 20 * * * cd ~/.openclaw/workspace && /usr/bin/env python3 scripts/daily_running_brief.py >> logs/running_brief.log 2>&1
```

The two jobs are deliberately separated: wellness data arrives via HabitDash hours before the brief runs at 20:00, so the cache is always warm.

## Pipeline

```
biosystems strava --list --json --count 30
    ↓  client-side date filter (--days)
    ↓  seen_runs.json dedup (Strava activity ID)
biosystems strava {id} --json   ← FullRunReport per new run
    ↓
_get_operator_context()         ← USER.md + MEMORY.md + trend + efforts + top
    ↓
_chat(analyze_run)              ← per-run: EF / decoupling / PMC timing / next-session
    ↓  (if ≥2 runs)
_chat(synthesize_brief)         ← weekly pattern + adaptation hypothesis
    ↓
YYYY-MM-DD_running_brief.md
```

## Architecture notes

- `WORKSPACE = Path(__file__).parent.parent` — identical to `nightly_synthesis_engine.py`
- OpenAI primary / Anthropic fallback — identical `_chat()` to SIF engine
- `_TOKEN_LOG` + usage table — identical format to SIF engine
- Exit code 2 from `biosystems strava` = analysis OK, history persistence failed — output is valid JSON, treated as success
- FullRunReport JSON truncated to 12k chars if extremely large (marathon with full splits)
