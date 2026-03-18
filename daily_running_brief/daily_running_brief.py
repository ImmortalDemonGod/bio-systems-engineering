#!/usr/bin/env python3
"""
Daily Running Brief
===================
cron: after each run (or nightly at 20:00)

Pipeline:
  Collect   (biosystems strava --list + per-run fetch)
  → Stats   (pre-compute all baselines in Python — Claude never does arithmetic)
  → Cards   (build structured run card per activity — replaces raw JSON dumps)
  → Preamble (Claude writes plain-English fitness state — one call, no metrics)
  → Analyze (Claude writes narrative interpretation of pre-computed run cards)
  → Synthesize (Claude identifies cross-run structural pattern if ≥2 runs)
  → Write   memory/intelligence/YYYY-MM-DD_running_brief.md

Place this file at:  ~/.openclaw/workspace/scripts/daily_running_brief.py
Output writes to:    ~/.openclaw/workspace/memory/intelligence/
Seen-runs ledger:    ~/.openclaw/workspace/memory/intelligence/seen_runs.json

Design principle: Claude is the narrator, not the calculator.
All numeric comparisons (EF vs baseline, decoupling classification, load context,
anomaly detection) are computed in Python and injected as authoritative facts.
Claude only interprets pre-computed structured cards.

Requires:
  ANTHROPIC_API_KEY  (or OPENAI_API_KEY — OpenAI is primary, Anthropic is fallback)
  STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN  (for biosystems strava)
  biosystems CLI installed and on PATH  (pip install -e /path/to/bio-systems-engineering)
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any

# ─── Paths — mirror nightly_synthesis_engine.py exactly ──────────────────────

WORKSPACE   = Path(__file__).parent.parent          # ~/.openclaw/workspace
OUTPUT_DIR  = WORKSPACE / "memory" / "intelligence"
SEEN_LEDGER = OUTPUT_DIR / "seen_runs.json"

_CONTEXT_FILES = [
    ("USER.md",   "OPERATOR PROFILE"),
    ("MEMORY.md", "CURATED LONG-TERM MEMORY"),
]

# ─── LLM config ───────────────────────────────────────────────────────────────

_OPENAI_MODEL    = "gpt-5-mini"
_ANTHROPIC_MODEL = "claude-sonnet-4-6"

# ─── Types ────────────────────────────────────────────────────────────────────

RunEntry    = dict[str, Any]
RunReport   = dict[str, Any]
HistStats   = dict[str, Any]


# ─── biosystems CLI helper ────────────────────────────────────────────────────


def _run_cli(*args: str, timeout: int = 60) -> str | None:
    """
    Run a biosystems CLI command and return stdout, or None on failure.
    Exit code 2 = analysis OK / persistence failed — stdout is still valid JSON.
    """
    try:
        result = subprocess.run(
            ["biosystems", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode not in (0, 2):
            print(
                f"[cli] biosystems {' '.join(args[:4])} "
                f"exit {result.returncode}: {result.stderr[:200]}",
                file=sys.stderr,
            )
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"[cli] biosystems {' '.join(args[:4])} timed out after {timeout}s", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(
            "[cli] 'biosystems' not found — install with: pip install -e /path/to/bio-systems-engineering",
            file=sys.stderr,
        )
        return None
    except Exception as exc:
        print(f"[cli] {exc}", file=sys.stderr)
        return None


# ─── History stats (pre-computed in Python) ───────────────────────────────────


def _load_all_history() -> list[dict]:
    """
    Fetch all history entries via biosystems top (sorted by EF, all distances).
    Using count=500 captures full history for an athlete with years of data.
    """
    raw = _run_cli("top", "--by", "ef", "--count", "500", "--min-dist", "1.0", "--json", timeout=45)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _compute_history_stats(entries: list[dict]) -> HistStats:
    """
    Pre-compute all athlete baselines in Python.
    These numbers are authoritative — injected into prompts, never re-derived by LLM.
    """
    if not entries:
        return {}

    # Filter junk entries: HR sensor dropout produces impossibly high EF
    # A legitimate running avg HR is always > 100 bpm; < 100 = GPS glitch or sensor failure
    entries = [
        e for e in entries
        if e.get("avg_hr") is None or e["avg_hr"] >= 100
    ]
    if not entries:
        return {}

    efs  = sorted([e["ef"] for e in entries if e.get("ef")])
    decs = [e["decoupling_pct"] for e in entries if e.get("decoupling_pct") is not None]
    tss  = [e["hrTSS"] for e in entries if e.get("hrTSS")]

    # 30-day window
    cutoff_30d = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent = [e for e in entries if e.get("date", "") >= cutoff_30d]
    recent_efs  = [e["ef"]          for e in recent if e.get("ef")]
    recent_tss  = [e["hrTSS"]       for e in recent if e.get("hrTSS")]
    recent_decs = [e["decoupling_pct"] for e in recent if e.get("decoupling_pct") is not None]

    def _pct_rank(value: float, sorted_list: list[float]) -> int:
        """Percentile rank of value in a sorted list (0-100)."""
        if not sorted_list:
            return 50
        below = sum(1 for x in sorted_list if x < value)
        return round(below / len(sorted_list) * 100)

    ef_mean     = mean(efs)         if efs else None
    ef_std      = stdev(efs)        if len(efs) > 1 else None
    ef_best     = max(efs)          if efs else None
    ef_30d_mean = mean(recent_efs)  if recent_efs else ef_mean

    return {
        "ef_mean":       round(ef_mean, 5)      if ef_mean     else None,
        "ef_std":        round(ef_std, 5)        if ef_std      else None,
        "ef_best":       round(ef_best, 5)       if ef_best     else None,
        "ef_30d_mean":   round(ef_30d_mean, 5)   if ef_30d_mean else None,
        "ef_30d_n":      len(recent_efs),
        "dec_mean":      round(mean(decs), 2)    if decs        else None,
        "dec_30d_mean":  round(mean(recent_decs), 2) if recent_decs else None,
        "tss_30d_mean":  round(mean(recent_tss), 1)  if recent_tss  else None,
        "total_runs":    len(entries),
        # Percentile function (closure over sorted efs)
        "_efs_sorted":   efs,
    }


def _ef_percentile(ef: float, stats: HistStats) -> int:
    return _pct_rank_inner(ef, stats.get("_efs_sorted", []))


def _pct_rank_inner(value: float, sorted_list: list[float]) -> int:
    if not sorted_list:
        return 50
    below = sum(1 for x in sorted_list if x < value)
    return round(below / len(sorted_list) * 100)


# ─── Run card builders (all numeric classification done here, not in LLM) ─────


def _classify_decoupling(pct: float) -> tuple[str, str]:
    """
    Return (label, plain-English meaning).
    Decoupling = cardiac drift over the run. Lower = better aerobic stability.
    """
    if pct < 2.0:
        return "EXCELLENT", "near-zero cardiac drift — strong aerobic base"
    elif pct < 5.0:
        return "GOOD", "low cardiac drift — solid aerobic base"
    elif pct < 10.0:
        return "BORDERLINE", "moderate drift — aerobic base still developing"
    else:
        return "CONCERNING", "significant cardiac drift — durability concern, aerobic base needs work"


def _classify_ef(ef: float, ef_30d_mean: float | None) -> tuple[str, float | None]:
    """Return (status_label, delta_pct vs 30-day mean)."""
    if ef_30d_mean is None or ef_30d_mean == 0:
        return "baseline", None
    delta = (ef - ef_30d_mean) / ef_30d_mean * 100
    if delta > 5:
        return "ABOVE MEAN", round(delta, 1)
    elif delta < -5:
        return "BELOW MEAN", round(delta, 1)
    else:
        return "AT MEAN", round(delta, 1)


def _classify_load(hr_tss: float, tss_30d_mean: float | None) -> str:
    if tss_30d_mean is None or tss_30d_mean == 0:
        if hr_tss < 40:
            return "easy"
        elif hr_tss < 80:
            return "moderate"
        else:
            return "hard"
    ratio = hr_tss / tss_30d_mean
    if ratio < 0.6:
        return f"easy ({ratio:.0%} of 30-day mean {tss_30d_mean:.0f})"
    elif ratio < 1.3:
        return f"moderate ({ratio:.0%} of 30-day mean {tss_30d_mean:.0f})"
    elif ratio < 1.8:
        return f"hard ({ratio:.0%} of 30-day mean {tss_30d_mean:.0f})"
    else:
        return f"very hard ({ratio:.0%} of 30-day mean {tss_30d_mean:.0f})"


def _run_type(distance_km: float) -> str:
    if distance_km >= 18:
        return "long run"
    elif distance_km >= 12:
        return "medium-long run"
    elif distance_km >= 7:
        return "standard run"
    else:
        return "short run"


def _detect_ef_gap_anomaly(ef_raw: float | None, ef_gap: float | None) -> str | None:
    """
    Flag if EF_GAP is implausibly different from EF_raw.
    A ratio outside 0.5–1.5 means terrain accounted for >50% of EF — GPS artifact likely.
    """
    if ef_raw is None or ef_gap is None or ef_raw == 0:
        return None
    ratio = ef_gap / ef_raw
    if ratio < 0.5:
        return (
            f"⚠ DATA ANOMALY: EF_GAP ({ef_gap}) is {ratio:.0%} of EF_raw ({ef_raw}). "
            f"This implies extreme terrain effect unlikely on this route. "
            f"Probable cause: GPS altitude error (tunnel, bridge, barometric spike). "
            f"Disregard EF_GAP for this run."
        )
    if ratio > 1.5:
        return (
            f"⚠ DATA ANOMALY: EF_GAP ({ef_gap}) exceeds EF_raw ({ef_raw}) by {ratio:.0%}. "
            f"Check elevation data quality for this run."
        )
    return None


def _classify_cadence(spm: float | None) -> tuple[str, str]:
    """Return (label, plain-English meaning) for running cadence."""
    if spm is None:
        return "—", "not recorded"
    if spm >= 170:
        return "EXCELLENT", "optimal stride rate — minimal energy wasted on braking"
    elif spm >= 165:
        return "GOOD", "efficient stride rate — solid running economy"
    elif spm >= 160:
        return "MODERATE", "developing — 5–10 spm below optimal; economy gains available"
    else:
        return "LOW", f"mechanical limiter — {170 - spm:.0f} spm below target; direct contributor to lower EF"


def _classify_heat(temp_c: float | None) -> tuple[str, str]:
    """Return (label, impact note) for ambient temperature."""
    if temp_c is None:
        return "—", ""
    if temp_c >= 32:
        return "EXTREME HEAT", (
            f"⚠ {temp_c:.1f}°C — major physiological limiter. HR elevated by 5-15 bpm "
            f"vs cool conditions. EF and pace suppressed by thermoregulation demands. "
            f"Treat this run's metrics as heat-adjusted — actual fitness is higher than metrics show."
        )
    elif temp_c >= 27:
        return "HOT", (
            f"⚠ {temp_c:.1f}°C — significant heat load. HR elevated ~3-8 bpm vs cool baseline. "
            f"EF modestly suppressed. Performance underestimates true aerobic capacity."
        )
    elif temp_c >= 22:
        return "WARM", f"{temp_c:.1f}°C — mild heat effect; minor HR elevation expected."
    else:
        return "COOL", f"{temp_c:.1f}°C — optimal conditions; metrics represent true capacity."


def _load_wellness_context(date_str: str) -> dict:
    """
    Load full wellness context for a run date from the biosystems wellness cache.
    Returns {} if cache absent or date not found — always degrades gracefully.
    """
    try:
        # biosystems may not be on the path depending on how the brief is invoked
        import sys
        import importlib.util
        spec = importlib.util.find_spec("biosystems")
        if spec is None:
            return {}
        from biosystems.wellness.cache import compute_wellness_context
        return compute_wellness_context(date_str) or {}
    except Exception:
        return {}


def _classify_wellness(sleep_score: float | None, hrv: float | None, rest_hr: float | None) -> str:
    """
    Return G/A/R readiness signal from RunContext wellness fields.
    Used when full wellness context is unavailable (fallback path).
    Raw-value-only classification — deltas preferred when available.
    """
    signals = []
    if sleep_score is not None:
        if sleep_score >= 80:
            signals.append(f"Sleep {sleep_score:.0f}%")
        elif sleep_score >= 60:
            signals.append(f"Sleep {sleep_score:.0f}% ⚠")
        else:
            signals.append(f"Sleep {sleep_score:.0f}% ❌")
    if hrv is not None:
        signals.append(f"HRV {hrv:.0f} ms")
    if rest_hr is not None:
        signals.append(f"RHR {rest_hr:.0f} bpm")

    if not signals:
        return "not available"

    if sleep_score is not None and sleep_score < 60:
        readiness = "🔴 RED"
    elif sleep_score is not None and sleep_score < 80:
        readiness = "🟡 AMBER"
    else:
        readiness = "🟢 GREEN"

    return f"{readiness}  ({' · '.join(signals)})"


def _format_wellness_block(wellness_ctx: dict) -> str:
    """
    Format full wellness context (from biosystems cache) into a run card block.
    Includes raw values, 1d/7d deltas, and G/A/R with reasons.
    Falls back gracefully when data is partial.
    """
    if not wellness_ctx:
        return "not available"

    gar     = wellness_ctx.get("gar", "—")
    detail  = wellness_ctx.get("gar_detail", "")
    stale   = wellness_ctx.get("stale", False)
    stale_d = wellness_ctx.get("staleness_days", 0)

    parts = [f"{gar}  —  {detail}"]
    if stale:
        parts.append(f"  ⚠ DATA IS {stale_d}d OLD — treat with caution")

    metrics = []
    hrv = wellness_ctx.get("hrv_rmssd")
    hrv_1d = wellness_ctx.get("hrv_1d_delta")
    hrv_7d = wellness_ctx.get("hrv_7d_pct")
    if hrv is not None:
        hrv_str = f"HRV {hrv:.0f} ms"
        if hrv_1d is not None:
            hrv_str += f"  (1d: {hrv_1d:+.0f} ms"
            if hrv_7d is not None:
                hrv_str += f", 7d: {hrv_7d:+.0f}% vs mean"
            hrv_str += ")"
        metrics.append(hrv_str)

    rhr = wellness_ctx.get("resting_hr")
    rhr_1d = wellness_ctx.get("rhr_1d_delta")
    rhr_7d = wellness_ctx.get("rhr_7d_delta")
    if rhr is not None:
        rhr_str = f"RHR {rhr:.0f} bpm"
        if rhr_1d is not None:
            rhr_str += f"  (1d: {rhr_1d:+.0f}"
            if rhr_7d is not None:
                rhr_str += f", 7d: {rhr_7d:+.0f} vs mean"
            rhr_str += ")"
        metrics.append(rhr_str)

    rec = wellness_ctx.get("recovery_score")
    if rec is not None:
        metrics.append(f"Recovery {rec:.0f}%")

    slp = wellness_ctx.get("sleep_score")
    slp_dur = wellness_ctx.get("sleep_duration_s")
    if slp is not None:
        slp_str = f"Sleep {slp:.0f}%"
        if slp_dur is not None:
            slp_str += f" ({slp_dur/3600:.1f}h)"
        metrics.append(slp_str)

    bb = wellness_ctx.get("body_battery")
    if bb is not None:
        metrics.append(f"Body Battery {bb:.0f}%")

    if metrics:
        parts.append("  " + " · ".join(metrics))

    return "\n".join(parts)


def _build_wellness_section(date_str: str) -> str:
    """
    Build a printed ## Wellness Readiness section for the brief.
    Shows G/A/R signal, 7-day trend table with all available columns,
    personal-baseline deltas, and calibrated threshold source note.
    Returns empty string if no wellness data available.
    """
    try:
        import importlib.util, math as _math
        if importlib.util.find_spec("biosystems") is None:
            return ""
        from biosystems.wellness.cache import compute_wellness_context, get_wellness_window
        from biosystems.wellness.analytics import calibrate_thresholds
        from biosystems.wellness.cache import load_wellness_df
    except Exception:
        return ""

    ctx = compute_wellness_context(date_str)
    if not ctx:
        return ""

    gar     = ctx.get("gar", "—")
    detail  = ctx.get("gar_detail", "")
    stale   = ctx.get("stale", False)
    stale_d = ctx.get("staleness_days", 0)

    # Personal norms from calibration
    try:
        full_df    = load_wellness_df()
        thresholds = calibrate_thresholds(full_df)
        norms      = thresholds.get("norms", {})
        calibrated = thresholds.get("calibrated", False)
    except Exception:
        norms      = {}
        calibrated = False

    lines = ["## Wellness Readiness\n", f"{gar} — {detail}"]
    if stale:
        lines.append(f"\n⚠ Data is {stale_d}d old — sync when API key is available.")

    # 7-day trend table
    window = get_wellness_window(date_str, days=8)
    if not window.empty:
        import pandas as pd
        end_ts = pd.Timestamp(date_str).normalize()
        rows   = window[window.index <= end_ts].tail(7)

        def _v(row, col, fmt="{:.0f}", suffix=""):
            v = row.get(col)
            if v is None or (hasattr(v, "__float__") and _math.isnan(float(v))):
                return "—"
            try:
                return fmt.format(float(v)) + suffix
            except Exception:
                return "—"

        has_hrv      = "hrv_rmssd"        in rows.columns and rows["hrv_rmssd"].notna().any()
        has_recovery = "recovery_score"   in rows.columns and rows["recovery_score"].notna().any()
        has_sleep_sc = "sleep_score"      in rows.columns and rows["sleep_score"].notna().any()
        has_bb       = "body_battery"     in rows.columns and rows["body_battery"].notna().any()
        has_stress   = "avg_stress"       in rows.columns and rows["avg_stress"].notna().any()
        has_sleep_h  = any(
            c in rows.columns and rows[c].notna().any()
            for c in ["sleep_duration_s", "sleep_duration_s_garmin"]
        )

        cols = ["Date", "RHR"]
        if has_bb:       cols.append("Body Batt")
        if has_stress:   cols.append("Stress")
        if has_sleep_h:  cols.append("Sleep h")
        if has_sleep_sc: cols.append("Sleep %")
        if has_recovery: cols.append("Recovery")
        if has_hrv:      cols.append("HRV ms")

        header = "| " + " | ".join(cols) + " |"
        sep    = "| " + " | ".join(["---"] * len(cols)) + " |"

        table_rows = []
        for ts, row in rows.sort_index(ascending=False).iterrows():
            r    = row.to_dict()
            rhr  = r.get("resting_hr_whoop") or r.get("resting_hr_garmin")
            rhr_str = f"{float(rhr):.0f}" if rhr and not _math.isnan(float(rhr)) else "—"
            cells = [ts.strftime("%b %-d"), rhr_str]
            if has_bb:       cells.append(_v(r, "body_battery", "{:.0f}"))
            if has_stress:   cells.append(_v(r, "avg_stress", "{:.0f}"))
            if has_sleep_h:
                s = r.get("sleep_duration_s") or r.get("sleep_duration_s_garmin")
                cells.append(f"{float(s)/3600:.1f}h" if s and not _math.isnan(float(s)) else "—")
            if has_sleep_sc: cells.append(_v(r, "sleep_score", "{:.0f}"))
            if has_recovery: cells.append(_v(r, "recovery_score", "{:.0f}"))
            if has_hrv:      cells.append(_v(r, "hrv_rmssd", "{:.0f}"))
            table_rows.append("| " + " | ".join(cells) + " |")

        lines.append("\n" + header)
        lines.append(sep)
        lines.extend(table_rows)

    # Key signals vs personal baselines
    rhr     = ctx.get("resting_hr")
    rhr_7d  = ctx.get("rhr_7d_delta")
    hrv     = ctx.get("hrv_rmssd")
    hrv_7d  = ctx.get("hrv_7d_pct")
    bb      = ctx.get("body_battery")
    bb_7d   = ctx.get("bb_7d_delta")
    stress  = ctx.get("avg_stress")
    slp_h   = ctx.get("sleep_hours")
    vo2max  = ctx.get("vo2max")

    delta_parts = []
    if rhr is not None:
        s = f"RHR {rhr:.0f} bpm"
        norm_rhr = norms.get("rhr_garmin_mean")
        if norm_rhr:
            diff = rhr - norm_rhr
            s += f" ({diff:+.1f} vs your mean {norm_rhr:.0f})"
        elif rhr_7d is not None:
            s += f" ({rhr_7d:+.1f} vs 7d mean)"
        delta_parts.append(s)

    if hrv is not None:
        s = f"HRV {hrv:.0f} ms"
        norm_hrv = norms.get("hrv_mean")
        if norm_hrv:
            diff = hrv - norm_hrv
            s += f" ({diff:+.0f} vs your mean {norm_hrv:.0f})"
        elif hrv_7d is not None:
            s += f" ({hrv_7d:+.1f}% vs 7d mean)"
        delta_parts.append(s)

    if bb is not None:
        s = f"Body Battery {bb:.0f}%"
        norm_bb = norms.get("bb_mean")
        if norm_bb:
            diff = bb - norm_bb
            s += f" ({diff:+.0f} vs your mean {norm_bb:.0f})"
        elif bb_7d is not None:
            s += f" ({bb_7d:+.0f} vs 7d mean)"
        delta_parts.append(s)

    if stress is not None:
        norm_str = norms.get("stress_mean")
        s = f"Stress {stress:.0f}"
        if norm_str:
            s += f" (mean {norm_str:.0f})"
        delta_parts.append(s)

    if slp_h is not None:
        norm_slp = norms.get("sleep_h_mean")
        s = f"Sleep {slp_h:.1f}h"
        if norm_slp:
            s += f" (mean {norm_slp:.1f}h)"
        delta_parts.append(s)

    if vo2max is not None:
        norm_v = norms.get("vo2max_mean")
        s = f"VO2max {vo2max:.0f}"
        if norm_v:
            s += f" (mean {norm_v:.0f})"
        delta_parts.append(s)

    sleep_debt = ctx.get("sleep_debt_7d")
    if sleep_debt is not None and abs(sleep_debt) >= 0.5:
        sign = "+" if sleep_debt > 0 else ""
        label = "debt" if sleep_debt > 0 else "surplus"
        delta_parts.append(f"7d sleep {label} {sign}{sleep_debt:.1f}h")

    resp_rate = ctx.get("respiratory_rate")
    rr_sigma  = ctx.get("rr_sigma")
    if resp_rate is not None and rr_sigma is not None and rr_sigma >= 1.5:
        emoji = "🔴" if rr_sigma >= 2.5 else "🟡"
        delta_parts.append(f"Resp rate {resp_rate:.1f} brpm {emoji} (+{rr_sigma:.1f}σ — illness/OTS watch)")

    if delta_parts:
        lines.append("\n_" + " · ".join(delta_parts) + "_")

    # Longitudinal fitness arc (one-line summary)
    try:
        from biosystems.wellness.analytics import compute_longitudinal_fitness
        fitness_trends = compute_longitudinal_fitness(full_df)
        era_summary = fitness_trends.get("era_summary")
        if era_summary and "Insufficient" not in era_summary:
            lines.append(f"\n_Fitness arc: {era_summary}_")
    except Exception:
        pass

    thresh_src = "calibrated from your data" if calibrated else "clinical defaults"
    lines.append(f"\n_Thresholds: {thresh_src}_")

    return "\n".join(lines)


def _format_zone_distribution(zone_hr: list[dict]) -> str:
    """Format zone_hr list into a compact readable string."""
    if not zone_hr:
        return "not available"
    parts = []
    aerobic_pct = 0.0
    for z in zone_hr:
        pct = z.get("percent", 0)
        name = z.get("zone", "?")
        if pct >= 1.0:
            parts.append(f"{name}: {pct:.0f}%")
        if "Z1" in name or "Z2" in name or "Recovery" in name or "Aerobic" in name:
            aerobic_pct += pct
    summary = " · ".join(parts) if parts else "no data"
    if aerobic_pct > 0:
        summary += f"  (aerobic Z1+Z2: {aerobic_pct:.0f}%)"
    return summary


def _format_dynamics(dynamics: dict | None) -> str:
    """Format RunDynamics into a readable summary."""
    if not dynamics:
        return "not available"
    fh_hr    = dynamics.get("first_half_hr")
    sh_hr    = dynamics.get("second_half_hr")
    fh_pace  = dynamics.get("first_half_pace_min_km")
    sh_pace  = dynamics.get("second_half_pace_min_km")
    strategy = dynamics.get("pace_strategy", "unknown")
    drift    = dynamics.get("hr_drift_pct")

    hr_str   = f"{fh_hr:.0f} → {sh_hr:.0f} bpm" if fh_hr and sh_hr else "—"
    pace_str = f"{fh_pace:.2f} → {sh_pace:.2f} min/km" if fh_pace and sh_pace else "—"
    drift_str = f"HR drift: {drift:+.1f}%" if drift is not None else ""
    return f"HR: {hr_str} | Pace: {pace_str} ({strategy} split) {drift_str}".strip()


def _format_walk_detail(walk_summary: dict | None, walk_segments: list[dict]) -> str:
    """Summarise walk segments: total %, count, distribution, and walk HR recovery quality."""
    if not walk_summary:
        return "none detected"
    pct    = walk_summary.get("total_time_pct", 0)
    count  = walk_summary.get("segment_count", 0)
    mins   = walk_summary.get("total_time_s", 0) / 60
    avg_walk_hr = walk_summary.get("avg_hr")

    tags   = [s.get("tag", "?") for s in walk_segments]
    tag_counts: dict[str, int] = {}
    for t in tags:
        tag_counts[t] = tag_counts.get(t, 0) + 1
    tag_str = ", ".join(f"{v}× {k}" for k, v in tag_counts.items()) if tag_counts else ""

    detail = f"{pct:.1f}% of session ({mins:.1f} min across {count} segment{'s' if count != 1 else ''})"
    if tag_str:
        detail += f" — pattern: {tag_str}"

    # Walk HR recovery quality — key insight from old Cultivation system
    if avg_walk_hr is not None:
        if avg_walk_hr < 130:
            walk_hr_note = f"avg walk HR {avg_walk_hr:.0f} bpm → RECOVERING (true Z1 rest)"
        elif avg_walk_hr < 145:
            walk_hr_note = f"avg walk HR {avg_walk_hr:.0f} bpm → PARTIAL recovery (low Z2)"
        else:
            walk_hr_note = (
                f"avg walk HR {avg_walk_hr:.0f} bpm → STILL-LOADED (Z2+): "
                f"walks are not providing cardiovascular recovery — adds to session load"
            )
        detail += f"\n  Walk HR: {walk_hr_note}"

    return detail


def _format_prs(block_bests: list[dict], best_efforts: list[dict]) -> str:
    """Summarise personal records detected in this run."""
    prs = [b for b in block_bests if b.get("is_new_best")]
    if prs:
        lines = []
        for b in prs:
            name = b.get("name", "?")
            t    = b.get("elapsed_time_s", 0)
            pace = b.get("pace_min_per_km")
            imp  = b.get("improvement_s")
            ts   = f"{t//60}:{t%60:02d}"
            pace_str = f" ({pace:.2f}/km)" if pace else ""
            imp_str  = f" — NEW PR by {imp}s" if imp and imp > 0 else " — first recorded"
            lines.append(f"  {name}: {ts}{pace_str}{imp_str}")
        return "\n".join(lines)

    # Fall back to Strava top-10 efforts
    strava_prs = [e for e in best_efforts if e.get("pr_rank") == 1]
    if strava_prs:
        return ", ".join(
            f"{e['name']} {e['elapsed_time_s']//60}:{e['elapsed_time_s']%60:02d} (Strava PR)"
            for e in strava_prs
        )
    return "none detected"


def _build_run_card(entry: RunEntry, report: RunReport, stats: HistStats) -> str:
    """
    Build a structured, pre-computed text card for a single run.
    This replaces raw JSON. Claude receives only these authoritative facts.
    """
    run_only  = report.get("run_only") or {}
    session   = report.get("session") or {}

    ef_raw    = run_only.get("efficiency_factor")
    ef_gap    = report.get("ef_grade_adjusted")
    decouple  = run_only.get("decoupling_pct")
    hr_tss    = run_only.get("hr_tss")
    dist_km   = run_only.get("distance_km") or entry.get("distance_km", 0)
    dur_min   = run_only.get("duration_min", 0)
    avg_hr    = run_only.get("avg_hr")
    avg_pace  = run_only.get("avg_pace_min_per_km")
    max_hr    = report.get("max_hr")
    elevation = report.get("elevation_gain_m")
    calories  = report.get("calories")
    device    = report.get("device_name")
    cadence   = run_only.get("avg_cadence")

    # EF comparisons (authoritative — computed here, not by LLM)
    ef_30d_mean  = stats.get("ef_30d_mean")
    ef_best      = stats.get("ef_best")
    ef_status, ef_delta = _classify_ef(ef_raw, ef_30d_mean) if ef_raw else ("unknown", None)
    ef_pct       = _ef_percentile(ef_raw, stats) if ef_raw else None
    ef_vs_best   = f"{ef_raw / ef_best * 100:.1f}% of best" if ef_raw and ef_best else "—"
    ef_gap_note  = ""
    if ef_raw and ef_gap and ef_30d_mean:
        gap_delta = (ef_gap - ef_30d_mean) / ef_30d_mean * 100
        ef_gap_note = f" (vs 30d mean: {gap_delta:+.1f}%)"

    # Terrain effect (EF_GAP vs EF_raw)
    terrain_note = "—"
    if ef_raw and ef_gap:
        terrain_effect = (ef_gap - ef_raw) / ef_raw * 100
        if abs(terrain_effect) < 3:
            terrain_note = f"flat-equivalent (terrain effect: {terrain_effect:+.1f}%)"
        elif terrain_effect < 0:
            terrain_note = (
                f"net uphill — EF_GAP ({ef_gap}) is {abs(terrain_effect):.1f}% below EF_raw ({ef_raw}). "
                f"Uphill terrain inflates raw pace; EF_raw overstates efficiency on this route. "
                f"EF_GAP is the terrain-corrected signal and the more conservative efficiency estimate."
            )
        else:
            terrain_note = (
                f"net downhill — EF_GAP ({ef_gap}) is {terrain_effect:.1f}% above EF_raw ({ef_raw}). "
                f"Gravity assisted pace; EF_raw understates effort. EF_GAP is the terrain-corrected signal."
            )

    # Anomaly detection
    gap_anomaly = _detect_ef_gap_anomaly(ef_raw, ef_gap)

    # Decoupling (authoritative classification)
    dec_label, dec_meaning = _classify_decoupling(decouple) if decouple is not None else ("—", "—")
    dec_30d_mean = stats.get("dec_30d_mean")
    dec_vs_mean  = ""
    if decouple is not None and dec_30d_mean:
        dec_diff = decouple - dec_30d_mean
        dec_vs_mean = f" (vs 30d mean {dec_30d_mean:.1f}%: {dec_diff:+.1f}%)"

    # Load
    load_str = _classify_load(hr_tss, stats.get("tss_30d_mean")) if hr_tss else "—"

    # Context — temperature, wellness signals (biosystems injects these from Strava + wearable)
    ctx         = report.get("context") or {}
    run_ctx     = (run_only.get("context") or {})   # per run_only block may have wellness
    temp        = ctx.get("temperature_c")
    weather     = ctx.get("weather_description", "")
    temp_str    = f"{temp:.1f}°C{' · ' + weather if weather else ''}" if temp is not None else "not recorded"
    heat_label, heat_note = _classify_heat(temp)

    # Wellness — try full cache context first (has deltas + G/A/R), fall back to RunContext fields
    run_date_str = entry.get("date", "")
    wellness_ctx = _load_wellness_context(run_date_str) if run_date_str else {}
    if wellness_ctx:
        wellness_str = _format_wellness_block(wellness_ctx)
    else:
        sleep_score = ctx.get("sleep_score") or run_ctx.get("sleep_score")
        hrv         = ctx.get("hrv_rmssd")   or run_ctx.get("hrv_rmssd")
        rest_hr     = ctx.get("rest_hr")     or run_ctx.get("rest_hr")
        wellness_str = _classify_wellness(sleep_score, hrv, rest_hr)

    # Run type + session walk fraction
    sess_walk   = session.get("duration_min", 0)
    walk_sum    = report.get("walk_summary") or {}
    walk_detail = _format_walk_detail(walk_sum, report.get("walk_segments") or [])
    walk_pct    = walk_sum.get("total_time_pct", 0)

    # Zones, dynamics, PRs
    zone_str = _format_zone_distribution(report.get("zone_hr") or [])
    dyn_str  = _format_dynamics(report.get("dynamics"))
    pr_str   = _format_prs(report.get("block_bests") or [], report.get("best_efforts") or [])

    # AeV (Aerobic Efficiency Velocity)
    aev_pace  = report.get("aev_pace_min_per_km")
    aev_hr    = report.get("aev_ref_hr")
    aev_str   = f"{aev_pace:.2f} min/km @ {aev_hr} bpm" if aev_pace and aev_hr else "not computed"

    # Next-session direction (conditional on load AND aerobic state — Python decides, Claude elaborates)
    # Very-hard load overrides decoupling — recovery is mandatory regardless of aerobic efficiency
    tss_30d_mean = stats.get("tss_30d_mean")
    is_very_hard = hr_tss and tss_30d_mean and tss_30d_mean > 0 and hr_tss > tss_30d_mean * 1.8
    if is_very_hard:
        next_direction = (
            f"very hard session (hrTSS {hr_tss:.0f} = {hr_tss/tss_30d_mean:.0%} of 30d mean {tss_30d_mean:.0f}) — "
            f"BACK OFF: do not extend or repeat. Next session must be easy Z1–Z2 aerobic, "
            f"≤{max(45, round(dur_min * 0.65)):.0f} min, to allow recovery."
        )
    elif decouple is None:
        next_direction = "maintain current approach (insufficient data)"
    elif decouple < 2.0:
        next_direction = (
            f"aerobic base is strong — safe to EXTEND next Z2 session "
            f"by 5-10% or increase frequency"
        )
    elif decouple < 5.0:
        next_direction = (
            f"aerobic base is solid — MAINTAIN current duration and intensity"
        )
    elif decouple < 10.0:
        next_direction = (
            f"borderline drift — REDUCE next Z2 session to ~{max(30, round(dur_min * 0.85)):.0f} min "
            f"until decoupling returns below 5%"
        )
    else:
        next_direction = (
            f"significant drift — prioritize RECOVERY; cap next effort at "
            f"{max(20, round(dur_min * 0.70)):.0f} min easy Z1 until decoupling returns below 5%"
        )

    # Cadence classification
    cad_label, cad_meaning = _classify_cadence(cadence)

    lines = [
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"RUN CARD — {entry.get('date', '?')} · {entry.get('name', '?')}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"TYPE:          {_run_type(dist_km)} · {dist_km} km · {dur_min:.0f} min",
        f"AVG HR:        {avg_hr:.0f} bpm" + (f"  |  MAX HR: {max_hr:.0f} bpm" if max_hr else ""),
        f"AVG PACE:      {avg_pace:.2f} min/km",
        "",
        "PRE-RUN WELLNESS (G/A/R readiness):",
        f"  {wellness_str}",
        "",
        "CONDITIONS:",
        f"  Temperature: {temp_str}",
        f"  Heat status: {heat_label}" + (f" — {heat_note}" if heat_note else ""),
        f"  Device:      {device or 'not recorded'}",
        "",
        "EFFICIENCY (authoritative — pre-computed):",
        f"  EF raw:      {ef_raw}",
        f"  EF GAP:      {ef_gap}{ef_gap_note}",
        f"  Terrain:     {terrain_note}",
        f"  vs 30d mean ({ef_30d_mean}):  {ef_delta:+.1f}% → STATUS: {ef_status}" if ef_delta is not None else f"  vs 30d mean: {ef_30d_mean} (no delta — baseline run)",
        f"  vs all-time best ({ef_best}): {ef_vs_best}",
        f"  Percentile:  {ef_pct}th in {stats.get('total_runs', '?')}-run history" if ef_pct is not None else "",
        "",
        "AEROBIC STABILITY (authoritative — pre-computed):",
        f"  Decoupling:  {decouple}%{dec_vs_mean}",
        f"  Status:      {dec_label} — {dec_meaning}",
        "",
        "TRAINING LOAD (authoritative — pre-computed):",
        f"  hrTSS:       {hr_tss}",
        f"  Load class:  {load_str}",
        f"  Elevation:   {elevation:.0f}m gain" if elevation else "  Elevation:   not recorded",
        f"  Calories:    {calories:.0f} kcal" if calories else "",
        "",
        "HEART RATE DYNAMICS:",
        f"  {dyn_str}",
        "",
        "INTENSITY DISTRIBUTION (% time in each HR zone):",
        f"  {zone_str}",
        "",
        "WALK SEGMENTS:",
        f"  {walk_detail}",
        "",
        "PERSONAL RECORDS / BEST EFFORTS:",
        f"  {pr_str}",
        "",
        "AEROBIC EFFICIENCY VELOCITY (AeV):",
        f"  {aev_str}",
        "",
        "RUNNING CADENCE (authoritative — pre-computed):",
        f"  {cadence} spm — {cad_label}: {cad_meaning}" if cadence else "  not recorded",
        "",
        "NEXT SESSION DIRECTION (pre-computed from aerobic state):",
        f"  {next_direction}",
    ]

    if gap_anomaly:
        lines += ["", gap_anomaly]

    return "\n".join(l for l in lines if l is not None)


# ─── Operator context (compact bullets, not JSON dumps) ───────────────────────


_OPERATOR_CONTEXT: str | None = None


def _get_operator_context(stats: HistStats, trend_summary: dict, rolling: list[dict]) -> str:
    """
    Build compact operator context.
    Injects pre-computed stats and recent run history as bullet points — not raw JSON.
    Raw JSON dumps waste context window and invite LLM hallucination of baselines.
    """
    global _OPERATOR_CONTEXT
    if _OPERATOR_CONTEXT is not None:
        return _OPERATOR_CONTEXT

    parts: list[str] = []

    # ── OpenClaw workspace docs ───────────────────────────────────────────────
    for fname, label in _CONTEXT_FILES:
        p = WORKSPACE / fname
        if p.exists():
            parts.append(
                f"{'='*60}\n{label}  ({fname})\n{'='*60}\n{p.read_text().strip()}"
            )

    # ── Athlete baselines (pre-computed — authoritative) ─────────────────────
    baseline_lines = [
        "=" * 60,
        "ATHLETE BASELINES (pre-computed — do not re-derive)",
        "=" * 60,
        f"  History:        {stats.get('total_runs', '?')} runs recorded",
        f"  EF all-time best: {stats.get('ef_best', '?')}",
        f"  EF 30-day mean:   {stats.get('ef_30d_mean', '?')} (n={stats.get('ef_30d_n', '?')})",
        f"  EF overall mean:  {stats.get('ef_mean', '?')}",
        f"  EF 1-sigma:       ±{stats.get('ef_std', '?')}",
        f"  Decoupling 30d:   {stats.get('dec_30d_mean', '?')}% mean",
        f"  hrTSS 30d mean:   {stats.get('tss_30d_mean', '?')}",
    ]
    parts.append("\n".join(baseline_lines))

    # ── PMC state (pre-computed) ──────────────────────────────────────────────
    ctl = trend_summary.get("ctl", "?")
    atl = trend_summary.get("atl", "?")
    tsb = trend_summary.get("tsb", "?")
    ef_trend = trend_summary.get("ef_trend", "?")
    ctl_trend = trend_summary.get("ctl_trend", "?")
    pmc_lines = [
        "=" * 60,
        "CURRENT TRAINING STATE (Performance Management Chart)",
        "=" * 60,
        f"  CTL (42-day fitness load):  {ctl}",
        f"  ATL (7-day fatigue load):   {atl}",
        f"  TSB (form = CTL - ATL):     {tsb}",
        f"  EF trend direction:         {ef_trend}",
        f"  CTL trend:                  {ctl_trend}",
        "",
        "  Interpretation guide:",
        "  TSB +5 to +15 = fresh / race-ready",
        "  TSB 0 to -10  = normal training load",
        "  TSB -10 to -20 = fatigue accumulation (building phase)",
        "  TSB < -20      = overreaching risk",
    ]
    parts.append("\n".join(pmc_lines))

    # ── Recent runs (last 10, formatted as table not JSON) ────────────────────
    if rolling:
        table_lines = [
            "=" * 60,
            "RECENT RUNS (newest first, last 10)",
            "=" * 60,
            f"  {'Date':<12} {'EF':>8} {'EF_GAP':>8} {'Dec%':>6} {'TSS':>6}  Activity",
        ]
        for r in reversed(rolling[-10:]):
            ef_r   = f"{r['ef']:.5f}"       if r.get("ef")             else "  —  "
            efg_r  = f"{r['ef_gap']:.5f}"   if r.get("ef_gap")         else "  —  "
            dec_r  = f"{r['decoupling_pct']:.1f}%" if r.get("decoupling_pct") is not None else "  —  "
            tss_r  = f"{r['hrTSS']:.0f}"    if r.get("hrTSS")          else "  — "
            name_r = (r.get("activity_name") or "")[:28]
            table_lines.append(f"  {r['date']:<12} {ef_r:>8} {efg_r:>8} {dec_r:>6} {tss_r:>6}  {name_r}")
        parts.append("\n".join(table_lines))

    _OPERATOR_CONTEXT = "\n\n".join(parts)
    return _OPERATOR_CONTEXT


# ─── Seen-runs ledger ─────────────────────────────────────────────────────────


def _load_seen_runs() -> set[str]:
    if not SEEN_LEDGER.exists():
        return set()
    try:
        return set(json.loads(SEEN_LEDGER.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen_runs(existing: set[str], new_ids: list[str]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_LEDGER.write_text(json.dumps(list(existing | set(new_ids)), indent=2))


# ─── Data collectors ──────────────────────────────────────────────────────────


def collect_recent_runs(days: int = 7) -> list[RunEntry]:
    raw = _run_cli("strava", "--list", "--json", "--count", "30", timeout=90)
    if not raw:
        return []
    try:
        all_runs: list[RunEntry] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[collect] JSON parse error: {exc}", file=sys.stderr)
        return []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [r for r in all_runs if r.get("date", "") >= cutoff]


def fetch_run_report(strava_id: int | str) -> RunReport | None:
    raw = _run_cli("strava", str(strava_id), "--json", timeout=120)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[fetch:{strava_id}] JSON parse error: {exc}", file=sys.stderr)
        return None


# ─── LLM provider — OpenAI primary, Anthropic fallback ───────────────────────

_TOKEN_LOG: list[dict] = []


def _chat(messages: list[dict], system: str, label: str = "call") -> str:
    """Call OpenAI (primary) or Anthropic (fallback). Mirrors SIF engine."""
    openai_key    = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if openai_key:
        try:
            from openai import OpenAI
        except ImportError:
            openai_key = None
    if openai_key:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        _REASONING_PREFIXES = ("o1", "o3", "o4", "gpt-5")
        is_reasoning = any(_OPENAI_MODEL.startswith(p) for p in _REASONING_PREFIXES)
        kwargs: dict = dict(
            model=_OPENAI_MODEL,
            messages=[{"role": "system", "content": system}] + messages,
        )
        if not is_reasoning:
            kwargs["temperature"] = 0
        resp = client.chat.completions.create(**kwargs)
        u = resp.usage
        # gpt-5-mini pricing: $0.30/1M input, $1.20/1M output (mirrors SIF engine)
        _TOKEN_LOG.append({
            "label":  label,
            "model":  _OPENAI_MODEL,
            "input":  u.prompt_tokens,
            "output": u.completion_tokens,
            "total":  u.total_tokens,
            "cost":   round(u.prompt_tokens * 0.00000030 + u.completion_tokens * 0.00000120, 6),
        })
        return resp.choices[0].message.content or ""

    if anthropic_key:
        from anthropic import Anthropic
        client = Anthropic(api_key=anthropic_key)
        resp = client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        u = resp.usage
        _TOKEN_LOG.append({
            "label":  label,
            "model":  _ANTHROPIC_MODEL,
            "input":  u.input_tokens,
            "output": u.output_tokens,
            "total":  u.input_tokens + u.output_tokens,
            "cost":   round(u.input_tokens * 0.000003 + u.output_tokens * 0.000015, 6),
        })
        return resp.content[0].text

    raise RuntimeError(
        "No API key found. Set OPENAI_API_KEY (preferred, cheaper) or ANTHROPIC_API_KEY."
    )


# ─── Prompt templates ─────────────────────────────────────────────────────────

# All numeric comparisons are pre-computed in the run card.
# Claude's sole job: write clear, grounded narrative interpretation.
# DO NOT ask Claude to compute or derive any numbers.

_ANALYZE_SYSTEM = """\
You are writing a section of a daily running brief for an endurance athlete.

The brief will be read by someone who may have NO prior running knowledge.
Write clearly enough that a non-runner can understand what happened, why it matters,
and what to do about it. Define any technical term you use on first mention.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPERATOR CONTEXT
(athlete profile, training history, PMC state, recent run table)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{operator_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METRIC DEFINITIONS (use these exact interpretations):

DECOUPLING SCALE (cardiac drift — lower = better):
  EXCELLENT (<2%):   near-zero drift, strong aerobic base — recommend extending duration
  GOOD (2–5%):       low drift, solid aerobic base — maintain current approach
  BORDERLINE (5–10%): moderate drift, base developing — reduce duration until it improves
  CONCERNING (>10%): significant drift, durability concern — prioritize recovery

EF (Efficiency Factor) = avg speed (m/s) ÷ avg HR (bpm).
  Higher = more aerobic output per heartbeat.
  Improvement over months = aerobic base growing.

EF_GAP = EF calculated using Grade Adjusted Pace (terrain-normalized via Minetti 2002).
  Use for hilly runs. Anomaly flagged if GAP differs >50% from raw EF.

hrTSS (Training Stress Score) = 100 ≈ 1 hour at lactate threshold.
  Accumulates acute fatigue. Compare to athlete's 30-day mean for context.

Z1–Z5 (Heart Rate Zones): Z1=very easy, Z2=aerobic base, Z3=tempo, Z4=threshold, Z5=max.
  Time in Z1+Z2 = aerobic base building. Time in Z4+Z5 = intensity.

CADENCE (steps per minute — stride rate):
  EXCELLENT (≥170 spm): optimal, minimal energy wasted on braking
  GOOD (165–169 spm): efficient, solid running economy
  MODERATE (160–164 spm): developing — 5-10 spm below optimal; economy gains available
  LOW (<160 spm): mechanical limiter — direct contributor to lower EF; most accessible fix

WALK HR QUALITY (are the walk breaks actually recovering?):
  RECOVERING (<130 bpm): true Z1 rest — cardiovascular recovery occurring
  PARTIAL (130–145 bpm): low Z2 — some recovery benefit
  STILL-LOADED (>145 bpm): Z2+ — walks add to session load, not subtracting from it

HEAT IMPACT (how ambient temperature suppresses performance metrics):
  COOL (<22°C): metrics represent true capacity
  WARM (22–27°C): minor HR elevation; minimal metric distortion
  HOT (27–32°C): HR elevated ~3-8 bpm over cool baseline; EF modestly suppressed
  EXTREME HEAT (>32°C): major physiological limiter; actual fitness is higher than metrics show\
"""

_ANALYZE_USER = """\
Write the run assessment for this specific run. Use ONLY the pre-computed facts in the \
run card below — do not re-derive or re-calculate any numbers.

Structure your response EXACTLY as (use #### for all sub-headings inside this run section):

#### What Happened
1-2 sentences. Plain English. What kind of run was this, and was it a good one?
(Example: "This was a 9.7 km easy-to-moderate aerobic run. Your heart stayed efficient \
throughout — a genuinely strong training day.")

#### Efficiency (EF)
1-2 sentences. Reference the pre-computed status and delta. Explain what it means for \
this athlete's trend. If ABOVE MEAN, explain why that's significant. If BELOW MEAN, \
explain whether it's a concern or expected (e.g., after hard day).
If EF_GAP differs significantly from EF_raw, note which is the more reliable signal \
based on the terrain note in the run card. For net uphill: EF_GAP is the conservative \
terrain-corrected estimate; EF_raw overstates efficiency. For flat: both are equivalent.

#### Cardiac Stability (Decoupling)
1 sentence. Use the pre-computed STATUS label and meaning. Never say "strong drift" \
for low decoupling — low decoupling means low/no drift.

#### Intensity & Effort
1-2 sentences covering: load classification + zone distribution. Was this aerobic-focused \
(Z1+Z2 dominant) or did it push into higher zones?

#### Heart Rate Pattern
1 sentence. What did the first-half → second-half dynamics show? Stable = aerobic control. \
Rising HR with stable pace = drift. Improving pace with stable HR = fitness signal.

{cadence_section}

{heat_section}

{walk_section}

{pr_section}

{anomaly_section}

#### Key Signal
1 sentence only. The single most physiologically significant finding as a mechanism.
Use specific pre-computed numbers. Do not be vague.
BAD: "EF was above average."
GOOD: "EF 0.02118 — 3.3% above your 30-day mean — held with only 0.58% cardiac drift, \
suggesting your aerobic base has measurably strengthened in recent weeks."

#### Next Session
1 sentence. Use the pre-computed NEXT SESSION DIRECTION from the run card as your basis.
Make it specific and actionable. Include a number (duration, distance, or zone).

Run Card (authoritative — all numbers pre-computed):
{run_card}
"""

_PREAMBLE_SYSTEM = """\
You write the opening section of a daily running brief.
The reader may have zero background in endurance training or exercise physiology.
Write in plain English. Define every technical term on first use.
Be direct and specific. No filler. No motivational language.\
"""

_PREAMBLE_USER = """\
Write a "Fitness State" section — 3-4 sentences — that answers three questions for \
someone with no training background:

1. Where is this athlete in their fitness journey right now? (near peak / improving / \
   plateauing / declining — relative to their personal history)
2. How tired/fresh are they right now? (in plain English)
3. Is now a good time to push harder, maintain, or back off?

CRITICAL INSTRUCTIONS:
- EF (Efficiency Factor) is the performance signal — it measures actual aerobic fitness.
  CTL measures training VOLUME, not fitness quality.
- When EF is near the all-time best, the athlete is near PEAK PERFORMANCE regardless \
  of whether CTL is growing. Do not call fitness "plateauing" if EF is high.
- EF momentum is the strongest fitness direction signal. ACCELERATING UPWARD or IMPROVING \
  means the athlete is getting fitter. Only say "plateauing" if EF momentum is STABLE or DECLINING.
- Lead with the EF momentum and peak proximity as the primary fitness characterization.
  Use CTL/ATL/TSB only for the fatigue/freshness question (#2), not for fitness level (#1).

Use only the pre-computed data below. Do not invent or assume anything.
Define technical terms on first use.

Performance signals (PRIMARY — use these for fitness level):
  EF momentum (rolling 7-run trend): {ef_momentum}
  Peak proximity: {peak_proximity}
  EF 30-day mean: {ef_30d_mean}
  EF all-time best: {ef_best}

Training load signals (use ONLY for fatigue/freshness question):
  CTL (42-day training volume average — higher = more habitual volume): {ctl}
  CTL trend: {ctl_trend}
  ATL (7-day training stress — higher = more recently tired): {atl}
  TSB (form = CTL minus ATL — positive = fresh, negative = carrying fatigue): {tsb}

{wellness_block}

Recent run summary (last 7 days):
{recent_summary}

History: {total_runs} runs recorded
"""

_SYNTHESIS_SYSTEM = """\
You write the weekly training synthesis for a running brief.
The reader may have no background in endurance training.
Be clinically direct. No filler. No generic advice.
Ground every claim in specific numbers from the data provided.\
"""

_SYNTHESIS_USER = """\
Date: {date}
Runs analyzed this session ({n} runs):

{run_summaries}

Write ONLY these two sections. No other text.

## Weekly Pattern
2-3 sentences. Identify the structural trend across these runs.
Cite specific numbers (EF values, decoupling percentages, dates).
Name the mechanism: aerobic base building, fatigue accumulation, fat oxidation shift, etc.
End with exactly: "Priority signal: [the single most important metric to watch next week \
and the specific threshold to watch for]."

## Adaptation Hypothesis
- **Observed:** <one sentence — the measurable trend, with numbers>
- **Mechanism:** <one sentence — the physiological explanation, specific>
- **Falsification test:** <one test for next week — must include a specific number or threshold>
"""

# ─── Glossary (included in every brief) ───────────────────────────────────────

_GLOSSARY = """
---

## How to Read This Brief

| Metric | What it measures | What's good |
|--------|-----------------|-------------|
| **EF (Efficiency Factor)** | How fast you run per heartbeat: speed (m/s) ÷ heart rate (bpm). Higher = more output per beat. | Improving over months means your aerobic engine is growing. |
| **EF_GAP** | EF recalculated using terrain-adjusted pace (Minetti 2002). Comparable across hilly and flat runs. | Same direction as EF. Use when your route had significant elevation. |
| **Decoupling** | How much your heart rate drifted upward while you held the same pace. 0% = perfectly stable. | < 2% excellent · 2–5% good · 5–10% borderline · > 10% needs work |
| **hrTSS** | How hard this session stressed your body. 100 = 1 hour at your maximum sustainable pace. | Accumulate steadily. A spike without recovery = debt. |
| **ATL (Acute Load)** | Your average daily training stress over the last 7 days. Reflects current fatigue. | Lower = fresher. |
| **CTL (Chronic Load)** | Your average daily training stress over the last 42 days. Reflects fitness built. | Higher = more capacity. |
| **TSB (Form)** | CTL minus ATL. Positive = fresh. Negative = carrying fatigue. | +5 to +15: race-ready · 0 to -10: normal training · -10 to -20: building phase · < -20: overreaching risk |
| **Z1–Z5** | Heart rate intensity zones. Z1 = easy walk/jog, Z2 = aerobic base, Z3 = tempo, Z4 = threshold, Z5 = all-out. | Z1+Z2 time builds the aerobic engine. Z4+Z5 time builds speed. |
| **AeV** | Aerobic Efficiency Velocity — the pace at which your aerobic system operates optimally. | Higher AeV at the same HR = improved fat oxidation and running economy. |
| **Cadence** | Steps per minute. How fast your feet turn over. Low cadence = longer stride = more braking force. | ≥170 spm optimal · 165–169 good · 160–164 developing · <160 mechanical limiter |
| **Walk HR** | Average heart rate during walk breaks. Reveals whether walks are actually recovering you. | <130 bpm = true recovery · 130–145 = partial · >145 bpm = still-loaded (walks adding stress, not subtracting) |
| **Heat** | Ambient temperature during the run. Hot conditions force the heart to work harder for cooling. | >27°C suppresses EF and pace; >32°C is a major limiter — actual fitness is higher than hot-run metrics show |
| **Wellness (G/A/R)** | Pre-run readiness from sleep score and HRV. Green = ready · Amber = caution · Red = rest or easy only. | 🟢 GREEN = full effort safe · 🟡 AMBER = reduce intensity · 🔴 RED = rest; hard training on Red = high injury/overreach risk |
"""


# ─── Analysis + synthesis passes ──────────────────────────────────────────────


def analyze_run(
    entry: RunEntry,
    report: RunReport,
    run_card: str,
    operator_context: str,
) -> dict:
    """Call Claude to write narrative interpretation of a pre-computed run card."""
    walk_sum = report.get("walk_summary") or {}
    walk_pct = walk_sum.get("total_time_pct", 0)
    run_only = report.get("run_only") or {}
    ctx      = report.get("context") or {}
    cadence  = run_only.get("avg_cadence")
    temp     = ctx.get("temperature_c")

    # Conditional sections (only rendered if relevant)
    walk_section = (
        "\n#### Walk Segments\n"
        "1-2 sentences. Interpret the walk pattern — warm-up, mid-session, or cool-down? "
        "Planned or fatigue-driven? Comment on the walk HR quality (recovering vs still-loaded). "
        "Effect on the overall session quality."
        if walk_pct > 5 else ""
    )

    cad_label, _ = _classify_cadence(cadence)
    cadence_section = (
        "\n#### Running Cadence\n"
        "1 sentence. Use the pre-computed cadence label and meaning from the run card. "
        "If LOW or MODERATE, name it as a specific, actionable lever for economy improvement. "
        "If GOOD or EXCELLENT, note it as a positive mechanical signal."
        if cadence is not None else ""
    )

    heat_label, _ = _classify_heat(temp)
    heat_section = (
        "\n#### Heat Adjustment\n"
        "1 sentence. State the temperature and that metrics (EF, HR, pace) are suppressed "
        "by thermoregulation. Clarify that actual fitness is higher than the numbers show."
        if heat_label in ("HOT", "EXTREME HEAT") else ""
    )
    prs = report.get("block_bests") or []
    strava_prs = [e for e in (report.get("best_efforts") or []) if e.get("pr_rank") == 1]
    pr_section = (
        "\n#### Personal Records\n"
        "1-2 sentences. Acknowledge and contextualize the PR(s). "
        "Does a PR during a low-decoupling run suggest a new fitness ceiling? "
        "Or was it a maximal effort that inflated the session metrics?"
        if (any(b.get("is_new_best") for b in prs) or strava_prs) else ""
    )
    has_anomaly = "⚠ DATA ANOMALY" in run_card
    anomaly_section = (
        "\n#### Data Note\n"
        "Acknowledge the flagged anomaly in the run card in one sentence. "
        "Explain why EF_GAP should be disregarded for this run."
        if has_anomaly else ""
    )

    analysis = _chat(
        messages=[{"role": "user", "content": _ANALYZE_USER.format(
            cadence_section=cadence_section,
            heat_section=heat_section,
            walk_section=walk_section,
            pr_section=pr_section,
            anomaly_section=anomaly_section,
            run_card=run_card,
        )}],
        system=_ANALYZE_SYSTEM.format(operator_context=operator_context),
        label=f"analyze-{str(entry.get('id', ''))[:12]}",
    )

    run_only = report.get("run_only") or {}
    return {
        "id":          entry.get("id", ""),
        "date":        entry.get("date", ""),
        "name":        entry.get("name", ""),
        "distance_km": run_only.get("distance_km") or entry.get("distance_km"),
        "ef":          run_only.get("efficiency_factor"),
        "ef_gap":      report.get("ef_grade_adjusted"),
        "decoupling":  run_only.get("decoupling_pct"),
        "hr_tss":      run_only.get("hr_tss"),
        "avg_hr":      run_only.get("avg_hr"),
        "duration_min": run_only.get("duration_min"),
        "analysis":    analysis,
        "run_card":    run_card,
    }


def _compute_ef_momentum(rolling: list[dict]) -> dict:
    """
    Compute EF momentum from rolling trend data — more accurate than biosystems ef_trend label.
    Returns: current ef_roll, ef_roll 7 days ago, pct change, and direction label.
    """
    if not rolling:
        return {}

    # Get last entry's ef_roll (current)
    current_ef_roll = None
    for entry in reversed(rolling):
        if entry.get("ef_roll"):
            current_ef_roll = entry["ef_roll"]
            break

    # Get ef_roll from ~7 entries back (approx 1 week)
    week_ago_ef_roll = None
    # Find entries from ~7 days ago
    if len(rolling) >= 5:
        week_back = rolling[-8] if len(rolling) >= 8 else rolling[0]
        week_ago_ef_roll = week_back.get("ef_roll")

    if current_ef_roll and week_ago_ef_roll and week_ago_ef_roll > 0:
        pct_change = (current_ef_roll - week_ago_ef_roll) / week_ago_ef_roll * 100
        if pct_change > 3:
            direction = "ACCELERATING UPWARD"
        elif pct_change > 1:
            direction = "IMPROVING"
        elif pct_change > -1:
            direction = "STABLE"
        elif pct_change > -3:
            direction = "SLIGHTLY DECLINING"
        else:
            direction = "DECLINING"
    else:
        pct_change = None
        direction = "insufficient data"

    return {
        "ef_roll_current": round(current_ef_roll, 5) if current_ef_roll else None,
        "ef_roll_week_ago": round(week_ago_ef_roll, 5) if week_ago_ef_roll else None,
        "ef_roll_pct_change": round(pct_change, 1) if pct_change is not None else None,
        "ef_momentum": direction,
    }


def generate_fitness_preamble(
    trend_summary: dict,
    stats: HistStats,
    analyzed_runs: list[dict],
    operator_context: str,
    rolling: list[dict] | None = None,
) -> str:
    """
    Generate plain-English fitness state section — one Claude call, no metrics jargon.
    Written for a reader with zero running background.
    """
    recent_lines = "\n".join(
        f"  {r['date']}  {r['distance_km']}km  EF={r['ef']}  Decouple={r['decoupling']}%  TSS={r['hr_tss']}"
        for r in analyzed_runs
    )

    # Compute EF momentum independently — more accurate than biosystems ef_trend label
    momentum = _compute_ef_momentum(rolling or [])
    ef_roll_current  = momentum.get("ef_roll_current", "?")
    ef_roll_week_ago = momentum.get("ef_roll_week_ago", "?")
    ef_roll_change   = momentum.get("ef_roll_pct_change")
    ef_momentum_label = momentum.get("ef_momentum", "?")
    ef_momentum_str = (
        f"{ef_momentum_label} ({ef_roll_change:+.1f}% over last 7 runs: "
        f"{ef_roll_week_ago} → {ef_roll_current})"
        if ef_roll_change is not None
        else ef_momentum_label
    )

    # Peak proximity: how close is the most recent run EF to all-time best?
    ef_best = stats.get("ef_best")
    latest_ef = analyzed_runs[-1]["ef"] if analyzed_runs else None
    # Use the highest EF from the analyzed window for peak proximity
    best_recent_ef = max((r["ef"] for r in analyzed_runs if r.get("ef")), default=None)
    peak_proximity = ""
    if ef_best and best_recent_ef:
        pct_of_best = best_recent_ef / ef_best * 100
        peak_proximity = (
            f"{pct_of_best:.1f}% of all-time best EF "
            f"(recent best {best_recent_ef} vs all-time {ef_best})"
        )

    # Wellness context — use today's date; fall back to most recent run if no today data
    from datetime import date as _today_date
    today_str = _today_date.today().isoformat()
    wellness_ctx = _load_wellness_context(today_str) if today_str else {}

    # Personal norms for baseline context
    try:
        import importlib.util as _ilu
        if _ilu.find_spec("biosystems") is not None:
            from biosystems.wellness.analytics import calibrate_thresholds
            from biosystems.wellness.cache import load_wellness_df
            _norms = calibrate_thresholds(load_wellness_df()).get("norms", {})
        else:
            _norms = {}
    except Exception:
        _norms = {}

    if wellness_ctx:
        gar          = wellness_ctx.get("gar", "—")
        detail       = wellness_ctx.get("gar_detail", "")
        hrv          = wellness_ctx.get("hrv_rmssd")
        hrv_7d       = wellness_ctx.get("hrv_7d_pct")
        rhr          = wellness_ctx.get("resting_hr")
        rhr_7d       = wellness_ctx.get("rhr_7d_delta")
        rec          = wellness_ctx.get("recovery_score")
        slp          = wellness_ctx.get("sleep_score")
        bb           = wellness_ctx.get("body_battery")
        bb_7d        = wellness_ctx.get("bb_7d_delta")
        stress       = wellness_ctx.get("avg_stress")
        slp_h        = wellness_ctx.get("sleep_hours")
        vo2max       = wellness_ctx.get("vo2max")
        sleep_debt   = wellness_ctx.get("sleep_debt_7d")
        resp_rate    = wellness_ctx.get("respiratory_rate")
        rr_sigma     = wellness_ctx.get("rr_sigma")

        # Build personal-context strings
        def _norm_line(label, val, norm_key, unit="", fmt=".0f"):
            if val is None:
                return ""
            s = f"  {label}: {val:{fmt}} {unit}".rstrip()
            norm = _norms.get(norm_key)
            if norm is not None:
                diff = val - norm
                s += f"  (personal mean {norm:{fmt}} {unit}, Δ {diff:+{fmt}} {unit})".rstrip()
            return s + "\n"

        rhr_line = _norm_line("Resting HR",    rhr,    "rhr_garmin_mean", "bpm")
        hrv_line = _norm_line("HRV RMSSD",     hrv,    "hrv_mean",        "ms")
        bb_line  = _norm_line("Body Battery",  bb,     "bb_mean",         "%")
        slp_line = (_norm_line("Sleep",        slp_h,  "sleep_h_mean",    "h", ".1f")
                    if slp_h is not None
                    else (f"  Sleep Score: {slp:.0f}%\n" if slp else ""))
        vo2_line = _norm_line("VO2max",        vo2max, "vo2max_mean",     "ml/kg/min", ".0f")

        # Delta context for HRV and RHR
        if hrv and hrv_7d:
            hrv_line = hrv_line.rstrip("\n") + f"  (7d Δ: {hrv_7d:+.0f}%)\n"
        if rhr and rhr_7d:
            rhr_line = rhr_line.rstrip("\n") + f"  (7d Δ: {rhr_7d:+.0f} bpm)\n"

        # Sleep debt
        sleep_debt_line = ""
        if sleep_debt is not None and abs(sleep_debt) >= 0.5:
            label = "debt" if sleep_debt > 0 else "surplus"
            sleep_debt_line = f"  7-day sleep {label}: {sleep_debt:+.1f}h cumulative\n"

        # Respiratory rate (only show when elevated)
        rr_line = ""
        if resp_rate is not None and rr_sigma is not None and rr_sigma >= 1.5:
            flag = "⚠ illness/OTS watch" if rr_sigma >= 2.5 else "early warning"
            rr_line = f"  Resp Rate: {resp_rate:.1f} brpm (+{rr_sigma:.1f}σ — {flag})\n"

        # Longitudinal fitness arc
        fitness_arc_line = ""
        try:
            import importlib.util as _ilu2
            if _ilu2.find_spec("biosystems") is not None:
                from biosystems.wellness.analytics import compute_longitudinal_fitness
                from biosystems.wellness.cache import load_wellness_df as _lwdf
                _ft = compute_longitudinal_fitness(_lwdf())
                _era = _ft.get("era_summary", "")
                if _era and "Insufficient" not in _era:
                    fitness_arc_line = f"  Fitness arc (longitudinal): {_era}\n"
        except Exception:
            pass

        wellness_block = (
            "Pre-run wellness signals (authoritative — use for fatigue/readiness answer):\n"
            f"  Readiness: {gar} — {detail}\n"
            + hrv_line
            + rhr_line
            + (f"  Recovery Score: {rec:.0f}%\n" if rec else "")
            + slp_line
            + sleep_debt_line
            + bb_line
            + (f"  Avg Stress: {stress:.0f}"
               + (f"  (mean {_norms['stress_mean']:.0f})" if _norms.get("stress_mean") else "")
               + "\n" if stress else "")
            + vo2_line
            + rr_line
            + fitness_arc_line
            + "  NOTE: BB→EF correlation r≈0.00 — readiness doesn't predict performance "
              "but predicts adaptation capacity and injury risk.\n"
            + "  CRITICAL: If readiness is RED, explicitly note athlete should not push hard "
              "regardless of EF performance signals."
        )
    else:
        wellness_block = "Pre-run wellness signals: not available (run 'biosystems wellness-sync' to enable)"

    return _chat(
        messages=[{"role": "user", "content": _PREAMBLE_USER.format(
            ctl=trend_summary.get("ctl", "?"),
            atl=trend_summary.get("atl", "?"),
            tsb=trend_summary.get("tsb", "?"),
            ctl_trend=trend_summary.get("ctl_trend", "?"),
            ef_momentum=ef_momentum_str,
            peak_proximity=peak_proximity,
            wellness_block=wellness_block,
            recent_summary=recent_lines,
            ef_30d_mean=stats.get("ef_30d_mean", "?"),
            ef_best=stats.get("ef_best", "?"),
            total_runs=stats.get("total_runs", "?"),
        )}],
        system=_PREAMBLE_SYSTEM,
        label="preamble",
    )


def synthesize_brief(analyzed_runs: list[dict], operator_context: str, today: str) -> str:
    """Identify structural patterns across ≥ 2 runs."""
    import re
    run_summaries = "\n\n".join(
        f"[{r['date']}] {r['name']} | {r['distance_km']} km | "
        f"EF={r['ef']} | EF_GAP={r['ef_gap']} | "
        f"Decouple={r['decoupling']}% | hrTSS={r['hr_tss']}\n"
        + r["analysis"]
        for r in analyzed_runs
    )
    result = _chat(
        messages=[{"role": "user", "content": _SYNTHESIS_USER.format(
            date=today,
            n=len(analyzed_runs),
            run_summaries=run_summaries,
        )}],
        system=_SYNTHESIS_SYSTEM,
        label="synthesis",
    )
    # Ensure ## headers are present — some models omit the markdown prefix
    result = re.sub(r'^(?:##\s+)?(Weekly Pattern)\b', r'## \1', result, flags=re.MULTILINE)
    result = re.sub(r'^(?:##\s+)?(Adaptation Hypothesis)\b', r'## \1', result, flags=re.MULTILINE)
    return result


# ─── Brief assembly ───────────────────────────────────────────────────────────


def _build_summary_table(analyzed_runs: list[dict], stats: HistStats) -> str:
    """Compact cross-run comparison table at the top of the brief."""
    ef_mean = stats.get("ef_30d_mean")
    rows = ["| Date | Activity | Dist | EF | vs 30d Mean | Decouple | hrTSS | Load |",
            "|------|----------|------|----|-------------|----------|-------|------|"]
    for r in analyzed_runs:
        ef = r.get("ef")
        dec = r.get("decoupling")
        dec_label, _ = _classify_decoupling(dec) if dec is not None else ("—", "")
        ef_delta_str = ""
        if ef and ef_mean:
            delta = (ef - ef_mean) / ef_mean * 100
            ef_delta_str = f"{delta:+.1f}%"
        load_str = _classify_load(r.get("hr_tss"), stats.get("tss_30d_mean"))
        load_short = load_str.split("(")[0].strip()
        rows.append(
            f"| {r['date']} | {r['name']} | {r['distance_km']} km | "
            f"`{ef}` | {ef_delta_str} | `{dec}%` {dec_label.lower()} | "
            f"`{r['hr_tss']}` | {load_short} |"
        )
    return "\n".join(rows)


def assemble_brief(
    analyzed_runs: list[dict],
    fitness_preamble: str,
    synthesis: str,
    today: str,
    raw_count: int,
    new_count: int,
    stats: HistStats,
) -> str:
    summary_table = _build_summary_table(analyzed_runs, stats)

    run_sections = "\n\n---\n\n".join(
        f"### {r['date']} — {r['name']}\n"
        f"**{r['distance_km']} km** | "
        f"EF `{r['ef']}` | "
        f"EF_GAP `{r['ef_gap']}` | "
        f"Decoupling `{r['decoupling']}%` | "
        f"hrTSS `{r['hr_tss']}`\n\n"
        + r["analysis"]
        for r in analyzed_runs
    )

    synthesis_block = f"\n\n---\n\n{synthesis}" if synthesis else ""

    wellness_section = _build_wellness_section(today)

    return (
        f"# Daily Running Brief — {today}\n"
        f"_Generated {datetime.now().strftime('%H:%M')} | "
        f"{raw_count} runs collected → {new_count} analyzed_\n\n"
        "## Fitness State\n\n"
        + fitness_preamble
        + "\n\n---\n\n"
        + (wellness_section + "\n\n---\n\n" if wellness_section else "")
        + "## This Week at a Glance\n\n"
        + summary_table
        + "\n\n---\n\n"
        "## Run Analyses\n\n"
        + (run_sections or "_No new runs._")
        + synthesis_block
        + "\n"
        + _GLOSSARY
    )


# ─── Token report ─────────────────────────────────────────────────────────────


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
            f"{e['total']:>7,}  ${e['cost']:>8.6f}"
        )
    print(f"  {'─'*35} {'─'*7} {'─'*7} {'─'*7}  {'─'*9}")
    print(f"  {'TOTAL':<35} {total_in:>7,} {total_out:>7,} {total_tok:>7,}  ${total_usd:>8.6f}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "Error: no API key found.\n"
            "  Set OPENAI_API_KEY (preferred, cheaper) or ANTHROPIC_API_KEY."
        )

    parser = argparse.ArgumentParser(
        description="Generate a daily running brief via Claude.",
        epilog="Place at ~/.openclaw/workspace/scripts/ — writes to memory/intelligence/",
    )
    parser.add_argument("--days",  type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--force", action="store_true", help="Re-analyze already-briefed runs")
    parser.add_argument("--dry-run", action="store_true", help="Collect runs without calling Claude")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today       = datetime.now().strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{today}_running_brief.md"

    print(f"[running-brief] Daily running brief — {today}")

    # ── Pre-compute history stats (all baselines in Python) ───────────────────
    print("  → Loading history stats...", end=" ", flush=True)
    history_entries = _load_all_history()
    stats = _compute_history_stats(history_entries)
    print(f"{stats.get('total_runs', 0)} runs · EF mean {stats.get('ef_30d_mean', '?')} (30d)")

    # ── Load trend data ───────────────────────────────────────────────────────
    print("  → Loading PMC / trend data...", end=" ", flush=True)
    trend_summary: dict = {}
    rolling: list[dict] = []
    raw = _run_cli("trend", "--json", "--no-pmc", timeout=45)
    if raw:
        try:
            td = json.loads(raw)
            trend_summary = td.get("summary", {})
            rolling       = td.get("rolling", [])
        except json.JSONDecodeError:
            pass
    print(f"CTL={trend_summary.get('ctl', '?')} ATL={trend_summary.get('atl', '?')} TSB={trend_summary.get('tsb', '?')}")

    # ── Build operator context (compact bullets, not JSON dumps) ──────────────
    print("  → Building operator context...", end=" ", flush=True)
    operator_context = _get_operator_context(stats, trend_summary, rolling)
    print("done")

    # ── Collect runs ──────────────────────────────────────────────────────────
    print(f"  → Collecting runs (last {args.days} days)...", end=" ", flush=True)
    recent_runs = collect_recent_runs(days=args.days)
    print(f"{len(recent_runs)} found")

    if not recent_runs:
        output_path.write_text(
            f"# Daily Running Brief — {today}\n\n"
            "_No runs retrieved. Check Strava credentials._\n"
        )
        print(f"[running-brief] Wrote empty brief → {output_path}")
        return

    # ── Seen-ledger filter ────────────────────────────────────────────────────
    seen_ledger = _load_seen_runs()
    new_runs = recent_runs if args.force else [
        r for r in recent_runs if str(r.get("id", "")) not in seen_ledger
    ]
    stale = len(recent_runs) - len(new_runs)
    if stale:
        print(f"  → {len(new_runs)} new ({stale} already briefed)")
    if not new_runs:
        print("[running-brief] No new runs. Use --force to re-analyze.")
        return

    if args.dry_run:
        print("[running-brief] --dry-run: would analyze:")
        for r in new_runs:
            print(f"  {r['date']}  {r['name']:<35}  {r['distance_km']}km  id={r['id']}")
        return

    # ── Fetch reports, build run cards, analyze ───────────────────────────────
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

        run_card = _build_run_card(entry, report, stats)
        result   = analyze_run(entry, report, run_card, operator_context)
        analyzed.append(result)
        print("done")

    if not analyzed:
        print("[running-brief] All fetches failed. Check Strava credentials.")
        return

    # ── Fitness preamble (one Claude call, plain English) ─────────────────────
    print("  → Generating fitness preamble...", end=" ", flush=True)
    fitness_preamble = generate_fitness_preamble(trend_summary, stats, analyzed, operator_context, rolling)
    print("done")

    # ── Synthesize (≥2 runs) ──────────────────────────────────────────────────
    synthesis = ""
    if len(analyzed) >= 2:
        print(f"  → Synthesizing {len(analyzed)}-run pattern...", end=" ", flush=True)
        synthesis = synthesize_brief(analyzed, operator_context, today)
        print("done")

    # ── Assemble + write ──────────────────────────────────────────────────────
    brief = assemble_brief(
        analyzed, fitness_preamble, synthesis, today,
        raw_count=len(recent_runs), new_count=len(analyzed),
        stats=stats,
    )
    output_path.write_text(brief)
    print(f"[running-brief] Brief → {output_path}")

    _save_seen_runs(seen_ledger, [str(r["id"]) for r in analyzed if r.get("id")])
    _print_token_report()


if __name__ == "__main__":
    main()
