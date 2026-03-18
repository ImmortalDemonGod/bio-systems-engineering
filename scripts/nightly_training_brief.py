#!/usr/bin/env python3
"""
Nightly Training Brief
======================

Post-run or nightly synthesis engine for the bio-systems-engineering pipeline.

Architecture mirrors OpenClaw's nightly_synthesis_engine.py:

  Collect   → biosystems CLI (strava list, run analysis, trend, efforts)
  Enrich    → inject athlete context (PMC state, zones, PRs, top runs)
  Analyze   → Claude assesses each new run physiologically
  Synthesize → Claude identifies structural patterns across the session
  Write     → dated markdown brief to OUTPUT_DIR

Usage:
  python scripts/nightly_training_brief.py              # last 7 days
  python scripts/nightly_training_brief.py --days 14    # last 14 days
  python scripts/nightly_training_brief.py --force      # re-analyze already-briefed runs

Requires:
  ANTHROPIC_API_KEY  — for Claude analysis
  STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN  — for biosystems strava
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from anthropic import Anthropic

# ─── Paths ────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_PKG_ROOT   = _SCRIPT_DIR.parent  # repo root

# Output directory for briefs (override with BIOSYSTEMS_BRIEFS_DIR)
_OUTPUT_DIR = Path(
    os.environ.get(
        "BIOSYSTEMS_BRIEFS_DIR",
        str(Path.home() / ".config" / "biosystems" / "briefs"),
    )
)

# Seen-runs ledger — prevents re-briefing the same Strava activity ID
_SEEN_LEDGER = _OUTPUT_DIR / "seen_runs.json"

# ─── Types ────────────────────────────────────────────────────────────────────

RunEntry  = dict[str, Any]   # one row from biosystems strava --list --json
RunReport = dict[str, Any]   # FullRunReport JSON from biosystems strava {id} --json

# ─── Seen-runs ledger ─────────────────────────────────────────────────────────


def _load_seen_runs() -> set[str]:
    """Load set of already-briefed Strava activity IDs."""
    if not _SEEN_LEDGER.exists():
        return set()
    try:
        return set(json.loads(_SEEN_LEDGER.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen_runs(existing: set[str], new_ids: list[str]) -> None:
    """Append newly briefed run IDs to the ledger."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined = list(existing | set(new_ids))
    _SEEN_LEDGER.write_text(json.dumps(combined, indent=2))


# ─── Athlete context ──────────────────────────────────────────────────────────

_ATHLETE_CONTEXT: str | None = None  # cached after first load


def _run_cli(*args: str, timeout: int = 60) -> str | None:
    """
    Run a biosystems CLI command and return stdout string, or None on failure.
    stderr is passed through for diagnostic visibility.
    """
    try:
        result = subprocess.run(
            ["biosystems", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode not in (0, 2):
            # exit 2 = analysis OK, persistence failed — output is still valid JSON
            print(
                f"[cli] biosystems {' '.join(args[:3])} exit {result.returncode}: "
                f"{result.stderr[:200]}",
                file=sys.stderr,
            )
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"[cli] biosystems {' '.join(args[:3])} timed out after {timeout}s", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("[cli] 'biosystems' command not found — is the package installed?", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"[cli] {exc}", file=sys.stderr)
        return None


def _get_athlete_context() -> str:
    """
    Build athlete context string from biosystems trend, efforts, and top runs.

    This is injected into every Claude prompt so physiological assessments are
    grounded in the athlete's actual history rather than generic population norms.
    Cached globally after first call.
    """
    global _ATHLETE_CONTEXT
    if _ATHLETE_CONTEXT is not None:
        return _ATHLETE_CONTEXT

    sections: list[str] = []

    # 1. Performance Management Chart — ATL/CTL/TSB + rolling EF trend
    raw = _run_cli("trend", "--json", "--no-pmc", timeout=45)
    if raw:
        try:
            trend = json.loads(raw)
            summary = trend.get("summary", {})
            rolling = trend.get("rolling", [])[-10:]  # last 10 data points
            sections.append(
                "## Performance Management State\n"
                f"```json\n{json.dumps(summary, indent=2)}\n```\n\n"
                "## Recent Rolling Stats (last 10 runs)\n"
                f"```json\n{json.dumps(rolling, indent=2)}\n```"
            )
        except json.JSONDecodeError as exc:
            print(f"[context:trend] JSON parse error: {exc}", file=sys.stderr)

    # 2. EF trend by month — directional signal
    raw = _run_cli("summary", "--json", "--group", "month", timeout=30)
    if raw:
        try:
            trend_by_month = json.loads(raw)
            sections.append(
                "## Monthly EF / Decoupling Trend\n"
                f"```json\n{json.dumps(trend_by_month, indent=2)}\n```"
            )
        except json.JSONDecodeError as exc:
            print(f"[context:summary] JSON parse error: {exc}", file=sys.stderr)

    # 3. Personal records — baseline for PR detection
    raw = _run_cli("efforts", "--json", timeout=30)
    if raw:
        try:
            efforts = json.loads(raw)
            sections.append(
                "## Personal Records (own recorded history)\n"
                f"```json\n{json.dumps(efforts, indent=2)}\n```"
            )
        except json.JSONDecodeError as exc:
            print(f"[context:efforts] JSON parse error: {exc}", file=sys.stderr)

    # 4. Top 10 runs by EF — reference ceiling for comparisons
    raw = _run_cli("top", "--by", "ef", "--count", "10", "--json", timeout=30)
    if raw:
        try:
            top = json.loads(raw)
            sections.append(
                "## Top 10 Runs by Efficiency Factor\n"
                f"```json\n{json.dumps(top, indent=2)}\n```"
            )
        except json.JSONDecodeError as exc:
            print(f"[context:top] JSON parse error: {exc}", file=sys.stderr)

    _ATHLETE_CONTEXT = "\n\n".join(sections) if sections else "(no athlete context available)"
    return _ATHLETE_CONTEXT


# ─── Data collectors ──────────────────────────────────────────────────────────


def collect_recent_runs(days: int = 7) -> list[RunEntry]:
    """
    Fetch list of recent runs from Strava via biosystems CLI.

    Returns list of {id, date, name, distance_km, moving_time_min, sport_type}.
    Uses --count 30 and filters client-side since --list has no --since flag.
    """
    raw = _run_cli("strava", "--list", "--json", "--count", "30", timeout=90)
    if not raw:
        return []
    try:
        all_runs: list[RunEntry] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[collect:strava-list] JSON parse error: {exc}", file=sys.stderr)
        return []

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [r for r in all_runs if r.get("date", "") >= cutoff]


def fetch_run_report(strava_id: int | str) -> RunReport | None:
    """
    Fetch full FullRunReport JSON for a single Strava activity.

    biosystems strava {id} --json returns FullRunReport as JSON.
    Exit code 2 means analysis succeeded but history write failed — report is valid.
    """
    raw = _run_cli("strava", str(strava_id), "--json", timeout=120)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[fetch:{strava_id}] JSON parse error: {exc}", file=sys.stderr)
        return None


# ─── LLM chat helper ──────────────────────────────────────────────────────────

# claude-sonnet-4-6: strong physiological reasoning; large context for full FullRunReport JSON
_MODEL     = "claude-sonnet-4-6"
_TOKEN_LOG: list[dict] = []


def _chat(messages: list[dict], system: str, label: str = "call") -> str:
    """Call Claude. Logs token usage. Raises if ANTHROPIC_API_KEY not set."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=system,
        messages=messages,
    )
    u = resp.usage
    # claude-sonnet-4-6: $3.00/1M input, $15.00/1M output
    _TOKEN_LOG.append({
        "label":  label,
        "model":  _MODEL,
        "input":  u.input_tokens,
        "output": u.output_tokens,
        "total":  u.input_tokens + u.output_tokens,
        "cost":   round(u.input_tokens * 0.000003 + u.output_tokens * 0.000015, 6),
    })
    return resp.content[0].text


# ─── Prompt templates ─────────────────────────────────────────────────────────

_ANALYZE_SYSTEM = """\
You are a sports physiologist analyzing running data for a competitive endurance athlete.

Your assessment must be grounded in the athlete's actual metrics — not generic population norms.
Be clinically direct. No filler. No motivational language.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ATHLETE CONTEXT
(PMC state, monthly EF trend, personal records, top runs by EF)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{athlete_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERPRETATION FRAMEWORK:

- Efficiency Factor (EF) = avg speed (m/s) / avg HR (bpm). Higher = more aerobic output per heartbeat.
  EF_GAP uses grade-adjusted pace (Minetti 2002 polynomial) for terrain-normalized comparison.
- Aerobic Decoupling = |EF_second_half - EF_first_half| / EF_first_half × 100%.
  < 5%: strong aerobic base. 5-10%: borderline. > 10%: significant drift (durability concern).
- hrTSS: 100 ≈ 1 hour at lactate threshold. Tracks acute fatigue load.
- Walk segments: classified by pace > 8.7 min/km or Strava moving=false; excluded from EF/decoupling.
- ATL (acute training load, ~7d): reflects recent fatigue.
  CTL (chronic training load, ~42d): reflects fitness.
  TSB (form) = CTL - ATL: positive = fresh, negative = fatigued.\
"""

_ANALYZE_USER = """\
Analyze this run. Structure your response EXACTLY as shown — no deviations, no extra sections.

## Run Assessment
- **EF (raw):** [value] — [vs athlete context: quantify the gap to mean / ceiling]
- **EF (GAP):** [value or N/A] — [terrain effect: did elevation inflate or deflate the raw EF?]
- **Decoupling:** [value]% — [classification: strong / borderline / significant drift]
- **hrTSS:** [value] — [load classification relative to this athlete's recent TSS distribution]
- **Walk time:** [X% of session / none] — [physiological significance if nonzero]
- **PMC context:** [TSB at run time, ATL vs CTL direction — was this run well-timed relative to form?]

## Key Signal
1-2 sentences. The single most physiologically significant finding, stated as a mechanism.
BAD: "EF was good." GOOD: "EF 0.00318 — 4.2% above the 30-run mean of 0.00305 — on a \
12°C day with 380m gain suggests fat oxidation efficiency has meaningfully shifted upward."

## Next-Session Implication
1 sentence. A specific, falsifiable training recommendation grounded in THIS run's data.
BAD: "Keep running easy." GOOD: "Given 7.8% decoupling on a 75-min run, cap the next Z2 \
session at 60 min until decoupling returns below 5% at that duration."

Run data (FullRunReport JSON):
```json
{run_data}
```
"""

_SYNTHESIS_SYSTEM = """\
You write the weekly training synthesis section of an endurance athlete's training brief.
Be clinically direct. No filler. No generic advice. Ground every claim in the data below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ATHLETE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{athlete_context}\
"""

_SYNTHESIS_USER = """\
Date: {date}
Runs analyzed this session ({n} runs):

{run_summaries}

Write ONLY these two sections. No other text.

## Weekly Pattern
2-3 sentences. Identify the structural trend across these runs — EF direction, \
decoupling pattern, load distribution. Name the specific mechanism: is the athlete \
building aerobic base, accumulating fatigue, improving fat oxidation, drifting toward \
threshold, etc.?
End with exactly: "Priority signal: [the single most important metric to watch next week]."

## Adaptation Hypothesis
- **Observed:** <one sentence — the measurable trend across this session's runs>
- **Mechanism:** <one sentence — the physiological explanation>
- **Falsification test:** <one concrete, measurable check for next week's runs — \
must include a number or threshold>
"""

# ─── Analysis pass ────────────────────────────────────────────────────────────


def analyze_run(entry: RunEntry, report: RunReport, athlete_context: str) -> dict:
    """
    Call Claude to assess a single run physiologically.
    Strips non-serializable / overly large fields before sending.
    """
    # FullRunReport may include Pydantic-serialized nested objects.
    # Exclude stream-level arrays and null-heavy fields to keep context tight.
    SKIP_KEYS = {"stream_df", "raw_data"}
    run_data = {k: v for k, v in report.items() if k not in SKIP_KEYS and v is not None}

    run_json = json.dumps(run_data, indent=2, default=str)
    # Truncate if the activity is enormous (e.g. marathon with full split arrays)
    if len(run_json) > 12_000:
        run_json = run_json[:12_000] + "\n... [truncated]"

    analysis = _chat(
        messages=[{"role": "user", "content": _ANALYZE_USER.format(run_data=run_json)}],
        system=_ANALYZE_SYSTEM.format(athlete_context=athlete_context),
        label=f"analyze-{str(entry.get('id', ''))[:10]}",
    )

    run_only = report.get("run_only") or {}
    return {
        "id":          entry.get("id", ""),
        "date":        entry.get("date", ""),
        "name":        entry.get("name", ""),
        "distance_km": entry.get("distance_km"),
        "ef":          run_only.get("efficiency_factor"),
        "ef_gap":      report.get("ef_grade_adjusted"),
        "decoupling":  run_only.get("decoupling_pct"),
        "hr_tss":      run_only.get("hr_tss"),
        "analysis":    analysis,
    }


# ─── Synthesis pass ───────────────────────────────────────────────────────────


def synthesize_brief(analyzed_runs: list[dict], athlete_context: str, today: str) -> str:
    """
    Call Claude to identify structural training patterns across multiple analyzed runs.
    Only called when ≥ 2 runs were analyzed in this session.
    """
    run_summaries = "\n\n".join(
        f"[{r['date']}] {r['name']} | {r['distance_km']} km | "
        f"EF={r.get('ef')} | EF_GAP={r.get('ef_gap')} | "
        f"Decouple={r.get('decoupling')}% | hrTSS={r.get('hr_tss')}\n"
        + r["analysis"]
        for r in analyzed_runs
    )

    return _chat(
        messages=[{"role": "user", "content": _SYNTHESIS_USER.format(
            date=today,
            n=len(analyzed_runs),
            run_summaries=run_summaries,
        )}],
        system=_SYNTHESIS_SYSTEM.format(athlete_context=athlete_context),
        label="synthesis",
    )


# ─── Brief assembly ───────────────────────────────────────────────────────────


def assemble_brief(
    analyzed_runs: list[dict],
    synthesis: str,
    today: str,
    raw_count: int,
    new_count: int,
) -> str:
    """Build the full markdown brief from per-run analyses + synthesis."""
    run_sections = "\n\n---\n\n".join(
        f"### {r['date']} — {r['name']}\n"
        f"**Distance:** {r['distance_km']} km  |  "
        f"**EF:** {r.get('ef')}  |  "
        f"**EF_GAP:** {r.get('ef_gap') or 'N/A'}  |  "
        f"**Decoupling:** {r.get('decoupling')}%  |  "
        f"**hrTSS:** {r.get('hr_tss')}\n\n"
        + r["analysis"]
        for r in analyzed_runs
    )

    synthesis_section = f"\n\n---\n\n{synthesis}" if synthesis else ""

    return (
        f"# Training Brief — {today}\n"
        f"_Generated {datetime.now().strftime('%H:%M')} | "
        f"{raw_count} runs collected → {new_count} new analyzed_\n\n"
        f"## Run Analyses\n\n"
        + (run_sections or "_No new runs._")
        + synthesis_section
        + "\n"
    )


# ─── Token usage report ───────────────────────────────────────────────────────


def _print_token_report() -> None:
    if not _TOKEN_LOG:
        return
    total_in  = sum(e["input"]  for e in _TOKEN_LOG)
    total_out = sum(e["output"] for e in _TOKEN_LOG)
    total_tok = sum(e["total"]  for e in _TOKEN_LOG)
    total_usd = sum(e["cost"]   for e in _TOKEN_LOG)
    print("\n[brief] Token usage:")
    print(f"  {'Call':<35} {'Input':>7} {'Output':>7} {'Total':>7}  {'Cost':>9}")
    print(f"  {'-'*35} {'-'*7} {'-'*7} {'-'*7}  {'-'*9}")
    for e in _TOKEN_LOG:
        print(
            f"  {e['label']:<35} {e['input']:>7,} {e['output']:>7,} "
            f"{e['total']:>7,}  ${e['cost']:>8.5f}"
        )
    print(f"  {'─'*35} {'─'*7} {'─'*7} {'─'*7}  {'─'*9}")
    print(f"  {'TOTAL':<35} {total_in:>7,} {total_out:>7,} {total_tok:>7,}  ${total_usd:>8.5f}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Error: ANTHROPIC_API_KEY not set.")

    parser = argparse.ArgumentParser(
        description="Generate a nightly training brief via Claude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Look back N days for recent runs (default: 7)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-analyze runs already in seen ledger",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Collect + list runs without calling Claude or writing files",
    )
    args = parser.parse_args()

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today       = datetime.now().strftime("%Y-%m-%d")
    output_path = _OUTPUT_DIR / f"{today}_training_brief.md"

    print(f"[brief] Nightly training brief — {today}")

    # ── Load athlete context (cached) ─────────────────────────────────────────
    print("  → Loading athlete context...", end=" ", flush=True)
    athlete_context = _get_athlete_context()
    print("done")

    # ── Collect recent runs from Strava ───────────────────────────────────────
    print(f"  → Collecting runs from last {args.days} days...", end=" ", flush=True)
    recent_runs = collect_recent_runs(days=args.days)
    print(f"{len(recent_runs)} runs found")

    if not recent_runs:
        output_path.write_text(
            f"# Training Brief — {today}\n\n"
            "_Collection failed — no runs retrieved. Check Strava credentials._\n"
        )
        print(f"[brief] Wrote empty brief to {output_path}")
        return

    # ── Filter against seen ledger ────────────────────────────────────────────
    seen_ledger = _load_seen_runs()
    if args.force:
        new_runs = recent_runs
    else:
        new_runs = [r for r in recent_runs if str(r.get("id", "")) not in seen_ledger]

    stale_count = len(recent_runs) - len(new_runs)
    if stale_count:
        print(f"  → {len(new_runs)} new runs ({stale_count} already briefed)")

    if not new_runs:
        print("[brief] No new runs to analyze. Use --force to re-analyze.")
        return

    if args.dry_run:
        print("[brief] --dry-run: would analyze:")
        for r in new_runs:
            print(f"  {r['date']}  {r['name']:<35}  {r['distance_km']}km  id={r['id']}")
        return

    # ── Fetch full reports and analyze each run ───────────────────────────────
    analyzed: list[dict] = []
    for entry in new_runs:
        run_id   = entry.get("id", "")
        run_date = entry.get("date", "?")
        run_name = entry.get("name", "?")
        run_km   = entry.get("distance_km", 0)

        print(f"  → {run_date} '{run_name}' ({run_km}km)...", end=" ", flush=True)

        report = fetch_run_report(run_id)
        if report is None:
            print("fetch failed — skipping")
            continue

        result = analyze_run(entry, report, athlete_context)
        analyzed.append(result)
        print("done")

    if not analyzed:
        print("[brief] All run fetches failed — check logs.")
        return

    # ── Synthesize weekly pattern (≥ 2 runs) ─────────────────────────────────
    synthesis = ""
    if len(analyzed) >= 2:
        print(f"  → Synthesizing pattern across {len(analyzed)} runs...", end=" ", flush=True)
        synthesis = synthesize_brief(analyzed, athlete_context, today)
        print("done")

    # ── Assemble and write brief ──────────────────────────────────────────────
    brief = assemble_brief(
        analyzed, synthesis, today,
        raw_count=len(recent_runs),
        new_count=len(analyzed),
    )
    output_path.write_text(brief)
    print(f"[brief] Brief → {output_path}")

    # Record briefed run IDs (only successful analyses)
    briefed_ids = [str(r["id"]) for r in analyzed if r.get("id")]
    _save_seen_runs(seen_ledger, briefed_ids)

    _print_token_report()


if __name__ == "__main__":
    main()
