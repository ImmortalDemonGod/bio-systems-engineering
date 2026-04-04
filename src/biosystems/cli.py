"""
Bio-Systems CLI
===============

Command-line interface for analyzing human performance metrics.
Provides a JSON-native output for integration with OpenClaw.
"""

import os
from pathlib import Path

import dotenv
import typer
import yaml
from pydantic import ValidationError

from biosystems.ingestion.fit import add_derived_metrics, parse_fit
from biosystems.ingestion.gpx import parse_gpx
from biosystems.models import HeartRateZone, RunContext, ZoneConfig
from biosystems.physics.metrics import run_metrics

# Load .env using python-dotenv's upward search (CWD → parents).
# This works for both editable installs (repo root .env) and bare
# environment injection (OpenClaw / CI), where load_dotenv() is a safe no-op.
dotenv.load_dotenv()

# _PKG_ROOT is the editable-install repo root, used only as a last-resort
# fallback for zones_path when neither BIOSYSTEMS_ZONES_PATH nor the
# XDG config path exists. Under a regular pip install this resolves to
# site-packages/../../.. (not useful), so _default_zones_path() always
# tries env var and XDG first.
_PKG_ROOT = Path(__file__).resolve().parents[2]


def _default_zones_path() -> Path:
    """
    Resolve the default zones configuration file in priority order:

    1. ``BIOSYSTEMS_ZONES_PATH`` environment variable (explicit override)
    2. ``~/.config/biosystems/zones.yml`` (XDG standard user config)
    3. ``<repo-root>/data/zones_personal.yml`` (editable-install fallback)
    """
    env_override = os.environ.get("BIOSYSTEMS_ZONES_PATH")
    if env_override:
        return Path(env_override)

    xdg_path = Path.home() / ".config" / "biosystems" / "zones.yml"
    if xdg_path.exists():
        return xdg_path

    return _PKG_ROOT / "data" / "zones_personal.yml"

app = typer.Typer(
    help=(
        "Running performance analytics pipeline.\n\n"
        "[bold]Quick start — answer common questions:[/bold]\n\n"
        "  How have I been trending?     [cyan]biosystems summary[/cyan]\n"
        "  What are my best runs?        [cyan]biosystems top --by ef[/cyan]\n"
        "  Process today's Strava run?   [cyan]biosystems strava[/cyan]\n"
        "  Catch up on missed runs?      [cyan]biosystems backfill-streams[/cyan]\n"
        "  PMC / fatigue curve?          [cyan]biosystems trend[/cyan]"
    ),
    rich_markup_mode="rich",
)


def load_zone_config(yaml_path: Path) -> ZoneConfig:
    """Load zones from YAML and return a validated ZoneConfig."""
    if not yaml_path.exists():
        raise FileNotFoundError(f"Zone configuration not found at {yaml_path}")

    with yaml_path.open() as f:
        raw = yaml.safe_load(f)

    # Clean up metadata
    raw.pop("model", None)

    zones: dict[str, HeartRateZone] = {}
    for name, data in raw.items():
        if not isinstance(data, dict) or "bpm" not in data or "pace_min_per_km" not in data:
            continue

        zones[name] = HeartRateZone(
            name=name,
            bpm=tuple(data["bpm"]),
            pace_min_per_km=tuple(data["pace_min_per_km"]),
        )

    # Use defaults for physiological markers if not in YAML
    return ZoneConfig(
        resting_hr=raw.get("resting_hr", 50),
        threshold_hr=raw.get("threshold_hr", 186),
        max_hr=raw.get("max_hr", 201),
        zones=zones
    )


@app.command(rich_help_panel="Data Ingestion")
def analyze(
    file_path: Path = typer.Argument(..., help="Path to activity file (.fit or .gpx)"),
    zones_path: Path = typer.Option(
        _default_zones_path(),
        "--zones", "-z",
        help="Path to zones configuration YAML"
    ),
    temp_c: float | None = typer.Option(None, "--temp", help="Ambient temperature in Celsius"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output results as JSON"),
):
    """
    Analyze an activity file and output physiological metrics.
    """
    try:
        # 1. Load configuration
        try:
            zone_config = load_zone_config(zones_path)
        except Exception as e:
            typer.secho(f"Error loading zones: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        # 2. Parse activity
        suffix = file_path.suffix.lower()
        if suffix == ".fit":
            df = parse_fit(file_path)
            df = add_derived_metrics(df)
        elif suffix == ".gpx":
            df = parse_gpx(file_path)
            # GPX parser already adds derived metrics (dist, dt, etc.)
            # But we might need to rename columns for consistency with metrics.py
            if "time" in df.columns:
                df = df.rename(columns={"time": "timestamp"}).set_index("timestamp")
        else:
            typer.secho(f"Unsupported file format: {suffix}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        # 3. Create context
        context = RunContext(temperature_c=temp_c) if temp_c is not None else None

        # 4. Calculate metrics
        metrics = run_metrics(df, zone_config, context=context)

        # 5. Output
        if json_output:
            typer.echo(metrics.model_dump_json(indent=2))
        else:
            typer.secho("\n--- Physiological Metrics ---", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"Distance:     {metrics.distance_km:.2f} km")
            typer.echo(f"Duration:     {metrics.duration_min:.1f} min")
            typer.echo(f"Avg Pace:     {metrics.avg_pace_min_per_km:.2f} min/km")
            typer.echo(f"Avg HR:       {metrics.avg_hr:.1f} bpm")
            typer.echo(f"EF:           {metrics.efficiency_factor:.5f}")
            typer.echo(f"Decoupling:   {metrics.decoupling_pct:.1f}%")
            typer.echo(f"hrTSS:        {metrics.hr_tss:.1f}")

    except ValidationError as e:
        typer.secho(f"Validation Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Analysis Failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Data Ingestion")
def strava(
    activity_id: int | None = typer.Argument(
        None, help="Strava activity ID. Omit to use the most recent run."
    ),
    zones_path: Path = typer.Option(
        _default_zones_path(),
        "--zones", "-z",
        help="Path to zones configuration YAML",
    ),
    temp_c: float | None = typer.Option(None, "--temp", help="Ambient temperature in Celsius"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output results as JSON"),
    list_runs: bool = typer.Option(False, "--list", "-l", help="List recent runs and exit"),
    n: int = typer.Option(5, "--count", "-n", help="Number of runs to list (with --list)"),
):
    """
    Fetch a Strava activity and output physiological metrics.

    Requires STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN
    to be set in the environment.
    """
    from biosystems.ingestion.strava import (
        _refresh_access_token,
        fetch_activity_streams,
        fetch_latest_run,
        fetch_recent_runs,
    )

    try:
        token = _refresh_access_token()
    except OSError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Auth failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # --list mode: print recent runs and exit
    if list_runs:
        try:
            runs = fetch_recent_runs(n=n, access_token=token)
        except Exception as e:
            typer.secho(f"Failed to fetch activities: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        if not runs:
            if json_output:
                typer.echo("[]")
            else:
                typer.echo("No recent runs found.")
            raise typer.Exit()

        if json_output:
            import json as _json
            payload = [
                {
                    "id": r["id"],
                    "date": r.get("start_date_local", "")[:10],
                    "name": r.get("name", ""),
                    "distance_km": round(r.get("distance", 0) / 1000, 2),
                    "moving_time_min": round(r.get("moving_time", 0) / 60, 1),
                    "sport_type": r.get("sport_type", ""),
                }
                for r in runs
            ]
            typer.echo(_json.dumps(payload, indent=2))
        else:
            for r in runs:
                dist_km = r.get("distance", 0) / 1000
                moving_min = r.get("moving_time", 0) / 60
                typer.echo(
                    f"  {r['id']}  {r['start_date_local'][:10]}  "
                    f"{r['name']:<30}  {dist_km:.1f}km  {moving_min:.0f}min"
                )
        raise typer.Exit()

    # Fetch streams
    activity_meta: dict = {}
    try:
        if activity_id is None:
            summary, df, activity_meta = fetch_latest_run(access_token=token)
            typer.secho(
                f"Using latest run: {summary['name']} ({summary['start_date_local'][:10]})",
                fg=typer.colors.CYAN,
                err=True,
            )
        else:
            df, activity_meta = fetch_activity_streams(activity_id, access_token=token)
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Failed to fetch streams: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Load zone config
    try:
        zone_config = load_zone_config(zones_path)
    except Exception as e:
        typer.secho(f"Error loading zones: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # --- Walk detection: pace OR cadence below running threshold ---
    df["pace_min_per_km"] = df["pace_sec_km"] / 60
    df["is_walk"] = (df["pace_min_per_km"] > 9.5) | (df["cadence"].fillna(0) < 140)
    if "moving" in df.columns:
        df["is_walk"] = df["is_walk"] | (~df["moving"].fillna(True).astype(bool))

    # --- Auto weather context from GPS ---
    if temp_c is not None:
        context = RunContext(temperature_c=temp_c)
    else:
        context = None
        lat_col = df["latitude"].dropna()
        lon_col = df["longitude"].dropna()
        if not lat_col.empty and not lon_col.empty:
            from biosystems.environment.weather import WMO_WEATHER_CODES, fetch_weather_open_meteo
            lat = float(lat_col.median())
            lon = float(lon_col.median())
            start_dt = df.index[0].to_pydatetime()
            typer.secho("Fetching weather context...", fg=typer.colors.CYAN, err=True)
            try:
                weather, _ = fetch_weather_open_meteo(lat, lon, start_dt)
                if weather and "hourly" in weather:
                    hourly = weather["hourly"]
                    code = hourly["weathercode"][0] if hourly.get("weathercode") else None
                    context = RunContext(
                        temperature_c=hourly["temperature_2m"][0] if hourly.get("temperature_2m") else None,
                        weather_code=code,
                        weather_description=WMO_WEATHER_CODES.get(int(code), "Unknown") if code is not None else None,
                    )
            except Exception:
                pass

    # --- Enrich context with wellness data (HRV, RHR, sleep from local cache) ---
    try:
        from biosystems.wellness.cache import enrich_run_context
        run_date_str = str(df.index[0].date()) if len(df) > 0 else None
        if run_date_str:
            context = enrich_run_context(run_date_str, context)
    except Exception:
        pass  # wellness cache absent or unreadable — degrade gracefully

    # --- Build full run report ---
    from biosystems.physics.report import build_run_report

    # Determine activity name from summary (only available when activity_id is None)
    activity_name_str: str | None = summary.get("name") if activity_id is None else None

    try:
        report = build_run_report(
            df,
            zone_config,
            context=context,
            activity_name=activity_name_str,
            activity_meta=activity_meta,
        )
    except Exception as e:
        typer.secho(f"Report generation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # --- Persist to local run history ---
    from biosystems.analytics.history import append_run
    run_date = str(df.index[0].date()) if len(df) > 0 else None
    if run_date:
        history_entry: dict = {
            "date": run_date,
            "hrTSS": round(report.run_only.hr_tss, 1),
            "distance_km": round(report.run_only.distance_km, 2),
            "avg_hr": round(report.run_only.avg_hr, 1),
            "avg_pace_min_per_km": round(report.run_only.avg_pace_min_per_km, 2),
            "ef": round(report.run_only.efficiency_factor, 5),
            "ef_gap": report.ef_grade_adjusted,
            "decoupling_pct": round(report.run_only.decoupling_pct, 2),
            "avg_cadence": round(report.run_only.avg_cadence, 1) if report.run_only.avg_cadence else None,
            "activity_name": activity_name_str,
            "source": "biosystems_strava",
        }
        if activity_id is not None:
            history_entry["strava_activity_id"] = activity_id
        strava_efforts_store: dict[str, int] = {
            e["name"]: e["elapsed_time_s"]
            for e in activity_meta.get("best_efforts", [])
            if e.get("name") and e.get("elapsed_time_s")
        }
        try:
            append_run(history_entry, strava_efforts=strava_efforts_store or None)
        except Exception as exc:
            typer.secho(f"WARNING: history write failed — {exc}", fg=typer.colors.YELLOW, err=True)
            if not json_output:
                raise typer.Exit(code=1)
            # In JSON mode: emit the report (stdout is clean) but signal failure via exit code
            typer.echo(report.model_dump_json(indent=2))
            raise typer.Exit(code=2)  # 2 = analysis OK, persistence failed

    if json_output:
        typer.echo(report.model_dump_json(indent=2))
    else:
        m = report.run_only
        typer.secho("\n--- Run Only ---", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"Distance:      {m.distance_km:.2f} km")
        typer.echo(f"Duration:      {m.duration_min:.1f} min")
        typer.echo(f"Avg Pace:      {m.avg_pace_min_per_km:.2f} min/km")
        typer.echo(f"Avg HR:        {m.avg_hr:.1f} bpm")
        if report.max_hr is not None:
            typer.echo(f"Max HR:        {report.max_hr:.0f} bpm")
        if report.max_speed_mps is not None:
            max_pace = (1000.0 / 60.0) / report.max_speed_mps
            typer.echo(f"Max Speed:     {report.max_speed_mps:.2f} m/s  ({max_pace:.2f} min/km)")
        if report.elevation_gain_m is not None:
            typer.echo(f"Elevation:     +{report.elevation_gain_m:.0f}m gain")
        if report.calories is not None:
            typer.echo(f"Calories:      {report.calories:.0f} kcal")
        if report.device_name:
            typer.echo(f"Device:        {report.device_name}")
        typer.echo(f"EF (raw):      {m.efficiency_factor:.5f}")
        typer.echo(f"EF (GAP):      {report.ef_grade_adjusted or 'N/A'}")
        typer.echo(f"EF CV:         {report.ef_reliability_cv or 'N/A'}")
        typer.echo(f"Decoupling:    {m.decoupling_pct:.1f}%")
        typer.echo(f"hrTSS:         {m.hr_tss:.1f}")
        typer.echo(f"AeV @ {report.aev_ref_hr} bpm:  {report.aev_pace_min_per_km or 'N/A'} min/km")
        if report.walk_summary:
            ws = report.walk_summary
            typer.secho("\n--- Walks ---", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"Segments: {ws.segment_count}  |  {ws.total_time_s/60:.1f} min ({ws.total_time_pct:.1f}%)")
        if report.dynamics:
            d = report.dynamics
            typer.secho("\n--- Dynamics ---", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"HR drift:   {d.first_half_hr:.0f} → {d.second_half_hr:.0f} bpm ({d.hr_drift_pct:+.1f}%)")
            typer.echo(f"Pace split: {d.first_half_pace_min_km:.2f} → {d.second_half_pace_min_km:.2f} ({d.pace_strategy})")
        if report.block_bests:
            new_bests = [bb for bb in report.block_bests if bb.is_new_best and bb.prev_best_s is not None]
            [bb for bb in report.block_bests if bb.is_new_best and bb.prev_best_s is None]
            if new_bests:
                typer.secho("\n--- Personal Records (recorded history) ---", fg=typer.colors.GREEN, bold=True)
            else:
                typer.secho("\n--- Best Efforts ---", fg=typer.colors.CYAN, bold=True)
            for bb in report.block_bests:
                mins, secs = divmod(bb.elapsed_time_s, 60)
                time_str = f"{mins}:{secs:02d}"
                if bb.is_new_best and bb.prev_best_s is not None:
                    imp_mins, imp_secs = divmod(abs(bb.improvement_s or 0), 60)
                    detail = f" PR  -{imp_mins}:{imp_secs:02d}"
                    typer.secho(f"  {bb.name:<12} {time_str}{detail}", fg=typer.colors.GREEN, bold=True)
                elif bb.is_new_best:
                    detail = "  (first recorded)"
                    typer.echo(f"  {bb.name:<12} {time_str}{detail}")
                else:
                    if bb.prev_best_s is not None:
                        pb_mins, pb_secs = divmod(bb.prev_best_s, 60)
                        detail = f"  best: {pb_mins}:{pb_secs:02d}"
                    else:
                        detail = ""
                    typer.echo(f"  {bb.name:<12} {time_str}{detail}")
        elif report.best_efforts:
            prs = [effort for effort in report.best_efforts if effort.pr_rank == 1]
            if prs:
                typer.secho("\n--- Personal Records! ---", fg=typer.colors.GREEN, bold=True)
            else:
                typer.secho("\n--- Best Efforts ---", fg=typer.colors.CYAN, bold=True)
            for effort in report.best_efforts:
                mins, secs = divmod(effort.elapsed_time_s, 60)
                if effort.pr_rank == 1:
                    rank_str = " PR"
                    typer.secho(f"  {effort.name:<12} {mins}:{secs:02d}{rank_str}", fg=typer.colors.GREEN, bold=True)
                elif effort.pr_rank and effort.pr_rank <= 3:
                    rank_str = f" #{effort.pr_rank}"
                    typer.secho(f"  {effort.name:<12} {mins}:{secs:02d}{rank_str}", fg=typer.colors.YELLOW)
                else:
                    typer.echo(f"  {effort.name:<12} {mins}:{secs:02d}")
        if report.splits_km:
            typer.secho("\n--- Km Splits ---", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"  {'km':<4}  {'pace':>8}  {'GAP':>8}  {'avg HR':>7}  {'elev':>6}")
            for sp in report.splits_km:
                pace_str = f"{sp.pace_min_per_km:.2f}/km"
                gap_str = f"{sp.gap_pace_min_per_km:.2f}/km" if sp.gap_pace_min_per_km else "  —  "
                hr_str = f"{sp.avg_hr:.0f}" if sp.avg_hr else " — "
                ele_str = f"{sp.elevation_diff_m:+.1f}m" if sp.elevation_diff_m is not None else ""
                typer.echo(f"  km{sp.km:<3}  {pace_str:>8}  {gap_str:>8}  {hr_str:>6}  {ele_str:>6}")
        if report.laps and len(report.laps) > 1:
            typer.secho("\n--- Laps ---", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"  {'lap':<5}  {'dist':>7}  {'pace':>8}  {'avg HR':>7}  {'max HR':>7}  {'cad':>5}  {'elev':>6}")
            for lap in report.laps:
                dist_str = f"{lap.distance_m/1000:.2f}km"
                pace_str = f"{lap.pace_min_per_km:.2f}/km"
                hr_str = f"{lap.avg_hr:.0f}" if lap.avg_hr else " — "
                max_hr_str = f"{lap.max_hr:.0f}" if lap.max_hr else " — "
                cad_str = f"{lap.avg_cadence:.0f}" if lap.avg_cadence else " — "
                ele_str = f"+{lap.elevation_gain_m:.0f}m" if lap.elevation_gain_m else ""
                typer.echo(f"  lap{lap.lap_index:<3}  {dist_str:>7}  {pace_str:>8}  {hr_str:>6}  {max_hr_str:>6}  {cad_str:>5}  {ele_str:>6}")


@app.command(name="backfill-efforts", rich_help_panel="Data Ingestion")
def backfill_efforts(
    n: int = typer.Argument(50, help="Number of recent runs to backfill efforts for"),
):
    """
    Backfill best effort times from past Strava activities into local history.

    Fetches activity details (no full stream data) for the last N runs and stores
    the Strava-detected best effort times (400m, 1K, 1mi, 5K, etc.) so the
    own-history PR comparison has data to work with.

    Much faster than re-running 'biosystems strava' for each activity — only
    one API call per activity, no GPS stream processing.
    """
    from biosystems.analytics.history import append_run, load_history
    from biosystems.ingestion.strava import (
        _refresh_access_token,
        fetch_activity_efforts,
        fetch_recent_runs,
    )

    try:
        token = _refresh_access_token()
    except Exception as e:
        typer.secho(f"Auth failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"Fetching last {n} run summaries...", fg=typer.colors.CYAN, err=True)
    try:
        runs = fetch_recent_runs(n=n, access_token=token)
    except Exception as e:
        typer.secho(f"Failed to list activities: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    existing = {e["date"]: e for e in load_history()}
    updated = 0

    for summary in runs:
        activity_id = summary["id"]
        try:
            run_date, efforts = fetch_activity_efforts(activity_id, access_token=token)
        except Exception as e:
            typer.secho(f"  Skipped {activity_id}: {e}", fg=typer.colors.YELLOW, err=True)
            continue

        if not efforts:
            continue

        efforts_dict = {e["name"]: e["elapsed_time_s"] for e in efforts if e.get("name") and e.get("elapsed_time_s")}
        if not efforts_dict:
            continue

        # Merge into existing history entry or create a minimal one
        entry = dict(existing.get(run_date, {}))
        if not entry:
            dist_km = round(summary.get("distance", 0) / 1000, 2)
            summary.get("moving_time", 0)
            avg_hr = float(summary.get("average_heartrate") or 0)
            entry = {
                "date": run_date,
                "hrTSS": 0,  # unknown without zone config
                "distance_km": dist_km,
                "avg_hr": round(avg_hr, 1) if avg_hr else None,
                "activity_name": summary.get("name"),
                "source": "strava_efforts_only",
            }

        append_run(entry, strava_efforts=efforts_dict)
        updated += 1
        typer.echo(f"  {run_date}  {summary.get('name', ''):<30}  {len(efforts_dict)} efforts")

    typer.secho(f"\nUpdated {updated}/{len(runs)} entries with effort data.", fg=typer.colors.GREEN)


@app.command(name="backfill-streams", rich_help_panel="Data Ingestion")
def backfill_streams(
    after: str = typer.Option(
        "2025-09-08",
        "--after",
        help="Fetch all runs on or after this date (YYYY-MM-DD). Default: day after study end.",
    ),
    zones_path: Path = typer.Option(
        _default_zones_path(),
        "--zones", "-z",
        help="Path to zones configuration YAML",
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--reprocess",
        help="Skip dates already in history with source=biosystems_strava.",
    ),
    delay: float = typer.Option(
        18.0,
        "--delay",
        # Each run needs 2 API calls (activity detail + streams).
        # Strava enforces 100 req / 15 min = 6.67 req/min.
        # Safe minimum per run: 2 × (900 s / 100 req) = 18 s.
        # 1.5 s was ~12× too fast and would hit 429 after ~7 runs.
        help="Seconds to sleep between runs (default 18 s respects Strava 100 req/15 min limit).",
    ),
):
    """
    Backfill full stream metrics for all runs since a given date.

    Fetches GPS/HR streams for every run, computes EF, decoupling, hrTSS, and
    saves each to local history as a biosystems_strava entry. Much slower than
    backfill-efforts but produces complete physiological metrics.
    """
    import time

    from biosystems.analytics.history import append_run, load_history
    from biosystems.ingestion.strava import (
        _refresh_access_token,
        fetch_activity_streams,
        fetch_runs_since,
    )
    from biosystems.physics.report import build_run_report

    try:
        token = _refresh_access_token()
    except Exception as e:
        typer.secho(f"Auth failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    try:
        zone_config = load_zone_config(zones_path)
    except Exception as e:
        typer.secho(f"Error loading zones: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"Fetching all runs since {after}...", fg=typer.colors.CYAN, err=True)
    try:
        runs = fetch_runs_since(after_date=after, access_token=token)
    except Exception as e:
        typer.secho(f"Failed to list activities: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if not runs:
        typer.echo("No runs found since that date.")
        raise typer.Exit()

    typer.secho(f"Found {len(runs)} runs to process.\n", fg=typer.colors.CYAN, err=True)

    # Build set of already-processed activity IDs (and dates as fallback)
    existing_stream_ids: set[int] = set()
    existing_stream_dates: set[str] = set()
    if skip_existing:
        for entry in load_history():
            if entry.get("source") == "biosystems_strava":
                aid = entry.get("strava_activity_id")
                if aid:
                    existing_stream_ids.add(int(aid))
                else:
                    existing_stream_dates.add(entry["date"])

    processed = 0
    skipped = 0
    failed = 0

    # Strava returns newest-first; reverse to process chronologically
    for summary in reversed(runs):
        activity_id = summary["id"]
        run_date = summary.get("start_date_local", "")[:10]
        activity_name = summary.get("name", "")
        dist_km = summary.get("distance", 0) / 1000
        moving_min = summary.get("moving_time", 0) / 60

        label = f"{run_date}  {activity_name:<28}  {dist_km:.1f}km  {moving_min:.0f}min"

        if skip_existing and (
            activity_id in existing_stream_ids
            or (not existing_stream_ids and run_date in existing_stream_dates)
        ):
            typer.echo(f"  [skip]  {label}")
            skipped += 1
            continue

        try:
            df, activity_meta = fetch_activity_streams(activity_id, access_token=token)
        except Exception as e:
            typer.secho(f"  [fail]  {label}  — {e}", fg=typer.colors.RED, err=True)
            failed += 1
            time.sleep(delay)
            continue

        # Walk detection: pace OR cadence below running threshold
        df["pace_min_per_km"] = df["pace_sec_km"] / 60
        df["is_walk"] = (df["pace_min_per_km"] > 9.5) | (df["cadence"].fillna(0) < 140)
        if "moving" in df.columns:
            df["is_walk"] = df["is_walk"] | (~df["moving"].fillna(True).astype(bool))

        # Enrich context with wellness data for this run's date
        backfill_context = None
        try:
            from biosystems.wellness.cache import enrich_run_context
            backfill_context = enrich_run_context(run_date, None)
        except Exception:
            pass

        try:
            report = build_run_report(
                df,
                zone_config,
                context=backfill_context,
                activity_name=activity_name,
                activity_meta=activity_meta,
            )
        except Exception as e:
            typer.secho(f"  [fail]  {label}  — report: {e}", fg=typer.colors.RED, err=True)
            failed += 1
            time.sleep(delay)
            continue

        m = report.run_only
        history_entry: dict = {
            "date": run_date,
            "strava_activity_id": activity_id,
            "hrTSS": round(m.hr_tss, 1),
            "distance_km": round(m.distance_km, 2),
            "avg_hr": round(m.avg_hr, 1),
            "avg_pace_min_per_km": round(m.avg_pace_min_per_km, 2),
            "ef": round(m.efficiency_factor, 5),
            "ef_gap": report.ef_grade_adjusted,
            "decoupling_pct": round(m.decoupling_pct, 2),
            "avg_cadence": round(m.avg_cadence, 1) if m.avg_cadence else None,
            "activity_name": activity_name,
            "source": "biosystems_strava",
        }
        strava_efforts_store: dict[str, int] = {
            e["name"]: e["elapsed_time_s"]
            for e in activity_meta.get("best_efforts", [])
            if e.get("name") and e.get("elapsed_time_s")
        }
        try:
            append_run(history_entry, strava_efforts=strava_efforts_store or None)
        except Exception as exc:
            typer.secho(f"  [warn]  {label}  — history write failed: {exc}", fg=typer.colors.YELLOW, err=True)
            failed += 1
            time.sleep(delay)
            continue

        ef_str = f"EF={m.efficiency_factor:.5f}"
        dec_str = f"Dec={m.decoupling_pct:+.1f}%"
        typer.secho(f"  [ok]    {label}  {ef_str}  {dec_str}", fg=typer.colors.GREEN)
        processed += 1
        time.sleep(delay)

    typer.secho(
        f"\nDone: {processed} processed, {skipped} skipped, {failed} failed.",
        fg=typer.colors.CYAN,
    )


@app.command(rich_help_panel="Analytics")
def summary(
    since: str | None = typer.Option(None, "--since", help="Start date YYYY-MM-DD (default: all history)"),
    group: str = typer.Option("month", "--group", "-g", help="Group by: month | week | all"),
    min_dist: float = typer.Option(3.0, "--min-dist", help="Minimum run distance in km to include"),
    source: str | None = typer.Option(None, "--source", help="Filter by source (e.g. biosystems_strava)"),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Output as JSON array"),
):
    """
    How have I been improving? EF / decoupling / HR / pace by period.

    Groups all recorded runs and prints aggregate stats per month (default),
    week, or overall. Use --since to scope to post-study data only.

    Examples:

      biosystems summary                          # all time, by month
      biosystems summary --since 2025-09-08       # post-study only
      biosystems summary --group week --since 2026-01-01
    """
    from collections import defaultdict

    from biosystems.analytics.history import load_history

    entries = load_history()

    # Filters
    if since:
        entries = [e for e in entries if e.get("date", "") >= since]
    if source:
        entries = [e for e in entries if e.get("source") == source]
    entries = [e for e in entries if e.get("distance_km", 0) >= min_dist]

    if not entries:
        typer.echo("No entries match the given filters.")
        raise typer.Exit()

    def _group_key(date_str: str) -> str:
        if group == "week":
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        elif group == "all":
            return "all"
        else:  # month
            return date_str[:7]

    by_group: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_group[_group_key(e["date"])].append(e)

    # Build period rows
    period_rows = []
    for period in sorted(by_group):
        runs = by_group[period]
        efs = [e["ef"] for e in runs if e.get("ef")]
        decs = [e["decoupling_pct"] for e in runs if e.get("decoupling_pct") is not None]
        hrs = [e["avg_hr"] for e in runs if e.get("avg_hr")]
        paces = [e["avg_pace_min_per_km"] for e in runs if e.get("avg_pace_min_per_km")]
        tss_total = sum(e.get("hrTSS", 0) for e in runs)
        period_rows.append({
            "period": period,
            "run_count": len(runs),
            "ef_mean": round(sum(efs) / len(efs), 5) if efs else None,
            "ef_best": round(max(efs), 5) if efs else None,
            "decoupling_mean": round(sum(decs) / len(decs), 2) if decs else None,
            "avg_hr": round(sum(hrs) / len(hrs), 1) if hrs else None,
            "avg_pace_min_per_km": round(sum(paces) / len(paces), 2) if paces else None,
            "total_tss": round(tss_total, 1),
        })

    if json_output:
        import json as _json
        typer.echo(_json.dumps(period_rows, indent=2))
        return

    typer.secho(f"\n{'Period':<12}  {'Runs':>4}  {'EF mean':>8}  {'EF best':>8}  {'Decoup':>8}  {'avg HR':>7}  {'avg pace':>10}  {'TSS':>6}", bold=True)
    typer.echo("-" * 78)

    for row in period_rows:
        ef_mean_str = f"{row['ef_mean']:.5f}" if row["ef_mean"] is not None else "  —    "
        ef_best_str = f"{row['ef_best']:.5f}" if row["ef_best"] is not None else "  —    "
        dec_str = f"{row['decoupling_mean']:+.1f}%" if row["decoupling_mean"] is not None else "  —   "
        hr_str = f"{row['avg_hr']:.0f}" if row["avg_hr"] is not None else " — "
        pace_str = f"{row['avg_pace_min_per_km']:.2f}/km" if row["avg_pace_min_per_km"] is not None else "  —    "
        typer.echo(f"{row['period']:<12}  {row['run_count']:>4}  {ef_mean_str:>8}  {ef_best_str:>8}  {dec_str:>8}  {hr_str:>7}  {pace_str:>10}  {row['total_tss']:>6.0f}")

    typer.echo()
    all_efs = [e["ef"] for e in entries if e.get("ef")]
    all_decs = [e["decoupling_pct"] for e in entries if e.get("decoupling_pct") is not None]
    if all_efs:
        typer.secho(
            f"Overall  {len(entries):>4} runs  EF {sum(all_efs)/len(all_efs):.5f} mean / {max(all_efs):.5f} best  "
            f"Decoupling {sum(all_decs)/len(all_decs):.1f}% avg",
            fg=typer.colors.CYAN,
        )


@app.command(rich_help_panel="Analytics")
def efforts(
    since: str | None = typer.Option(None, "--since", help="Only include runs on or after this date (YYYY-MM-DD)"),
    distances: str = typer.Option(
        "400m,1K,1 mile,5K,10K,Half-Marathon",
        "--distances", "-d",
        help="Comma-separated distances to report",
    ),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Output as JSON array"),
):
    """
    How have my race times progressed? First recorded → current best per distance.

    Shows each standard effort distance with the first recorded time, the current
    best, the improvement, and the dates of both. Reads from own recorded history
    (not Strava all-time PRs).

    Examples:

      biosystems efforts                          # all time, all standard distances
      biosystems efforts --since 2025-09-08       # post-study only
      biosystems efforts --distances 5K,10K       # specific distances
    """
    from biosystems.analytics.history import load_history

    dist_km_map = {
        "400m": 0.4,
        "1/2 mile": 0.805,
        "1K": 1.0,
        "1 mile": 1.609,
        "2 mile": 3.219,
        "5K": 5.0,
        "10K": 10.0,
        "15K": 15.0,
        "10 mile": 16.093,
        "20K": 20.0,
        "Half-Marathon": 21.098,
        "Marathon": 42.195,
    }

    target_distances = [d.strip() for d in distances.split(",")]

    entries = load_history()
    if since:
        entries = [e for e in entries if e.get("date", "") >= since]

    # Collect all recorded times per distance, sorted by date
    from collections import defaultdict
    by_distance: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for e in entries:
        for dist, t in (e.get("strava_efforts") or {}).items():
            if isinstance(t, int) and t > 0:
                by_distance[dist].append((e["date"], t))

    effort_rows = []
    for dist in target_distances:
        times = sorted(by_distance.get(dist, []))  # sort by date
        if not times:
            continue

        best_date, best_t = min(times, key=lambda x: x[1])
        first_date, first_t = times[0]
        dk = dist_km_map.get(dist, 0)
        best_pace = round(best_t / 60 / dk, 2) if dk else None
        improvement_s = first_t - best_t if first_date != best_date or first_t != best_t else None
        recent = [{"date": d, "elapsed_time_s": t} for d, t in times[-3:]] if len(times) >= 4 else []

        effort_rows.append({
            "distance": dist,
            "best_elapsed_s": best_t,
            "best_date": best_date,
            "best_pace_min_per_km": best_pace,
            "first_elapsed_s": first_t,
            "first_date": first_date,
            "improvement_s": improvement_s,
            "recording_count": len(times),
            "recent": recent,
        })

    if json_output:
        import json as _json
        typer.echo(_json.dumps(effort_rows, indent=2))
        return

    typer.secho("\nBest Effort Progression (own recorded history)\n", bold=True)

    if not effort_rows:
        typer.echo("No effort data found for the requested distances.")
        return

    for row in effort_rows:
        dist = row["distance"]
        bm, bs = row["best_elapsed_s"] // 60, row["best_elapsed_s"] % 60
        fm, fs = row["first_elapsed_s"] // 60, row["first_elapsed_s"] % 60
        typer.secho(f"  {dist}", bold=True)
        typer.echo(f"    Best:  {bm}:{bs:02d}  ({row['best_pace_min_per_km']:.2f} min/km)  on {row['best_date']}")

        if row["improvement_s"] is None:
            typer.echo(f"    First: {fm}:{fs:02d}  on {row['first_date']}  (only recording)")
        elif row["improvement_s"] > 0:
            dm, ds = row["improvement_s"] // 60, row["improvement_s"] % 60
            typer.secho(
                f"    First: {fm}:{fs:02d}  on {row['first_date']}  →  improved {dm}:{ds:02d}",
                fg=typer.colors.GREEN,
            )
        else:
            typer.echo(f"    First: {fm}:{fs:02d}  on {row['first_date']}  (no improvement yet)")

        if row["recent"]:
            progression = "  ".join(
                f"{r['elapsed_time_s']//60}:{r['elapsed_time_s']%60:02d} ({r['date']})"
                for r in row["recent"]
            )
            typer.echo(f"    Recent: {progression}")
        typer.echo()


@app.command(rich_help_panel="Analytics")
def top(
    by: str = typer.Option("ef", "--by", "-b", help="Sort metric: ef | decoupling | pace | tss | distance"),
    n: int = typer.Option(15, "--count", "-n", help="Number of results to show"),
    min_dist: float = typer.Option(3.0, "--min-dist", help="Minimum run distance in km"),
    since: str | None = typer.Option(None, "--since", help="Start date YYYY-MM-DD"),
    asc: bool = typer.Option(False, "--asc", help="Sort ascending instead of descending"),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Output as JSON array"),
):
    """
    What are my best runs? Rank by EF, pace, decoupling, TSS, or distance.

    Examples:
      biosystems top                            # top 15 runs by EF
      biosystems top --by ef           # best Efficiency Factor runs
      biosystems top --by decoupling --asc   # most aerobically stable runs
      biosystems top --by pace         # fastest average paces
      biosystems top --by distance     # longest runs
    """
    from biosystems.analytics.history import load_history

    entries = load_history()
    if since:
        entries = [e for e in entries if e.get("date", "") >= since]
    entries = [e for e in entries if e.get("distance_km", 0) >= min_dist]

    metric_map = {
        "ef": "ef",
        "decoupling": "decoupling_pct",
        "pace": "avg_pace_min_per_km",
        "tss": "hrTSS",
        "distance": "distance_km",
    }
    field = metric_map.get(by, "ef")

    # Filter to entries that have the metric
    entries = [e for e in entries if e.get(field) is not None]
    if not entries:
        typer.echo(f"No entries with metric '{by}' found.")
        raise typer.Exit()

    # Default sort: descending for ef/tss/distance, ascending for pace/decoupling
    default_asc = by in ("pace", "decoupling")
    sort_asc = asc if asc else default_asc
    entries = sorted(entries, key=lambda e: e[field], reverse=not sort_asc)[:n]

    if json_output:
        import json as _json
        typer.echo(_json.dumps(entries, indent=2))
        return

    typer.secho(f"\nTop {n} runs by {by} (min {min_dist}km{', since ' + since if since else ''}):\n", bold=True)
    typer.secho(
        f"  {'#':<3}  {'Date':<12}  {'Activity':<28}  {by.upper():>9}  {'EF':>8}  {'HR':>5}  {'Pace':>9}  {'km':>6}  {'Dec':>8}",
        fg=typer.colors.CYAN,
    )
    typer.echo("  " + "-" * 96)

    for i, e in enumerate(entries, 1):
        name = (e.get("activity_name") or "")[:26]
        ef_str = f"{e['ef']:.5f}" if e.get("ef") else "  —    "
        hr_str = f"{e['avg_hr']:.0f}" if e.get("avg_hr") else " — "
        pace_str = f"{e['avg_pace_min_per_km']:.2f}/km" if e.get("avg_pace_min_per_km") else "  —    "
        dist_str = f"{e.get('distance_km', 0):.1f}"
        dec_str = f"{e['decoupling_pct']:+.1f}%" if e.get("decoupling_pct") is not None else "  — "
        val = e[field]
        val_str = (
            f"{val:.5f}" if by == "ef" else
            f"{val:+.1f}%" if by == "decoupling" else
            f"{val:.2f}/km" if by == "pace" else
            f"{val:.1f}"
        )
        typer.echo(f"  {i:<3}  {e['date']:<12}  {name:<28}  {val_str:>9}  {ef_str:>8}  {hr_str:>5}  {pace_str:>9}  {dist_str:>6}  {dec_str:>8}")


@app.command(rich_help_panel="Analytics")
def trend(
    zones_path: Path = typer.Option(
        _default_zones_path(),
        "--zones", "-z",
        help="Path to zones configuration YAML",
    ),
    backfill: int = typer.Option(
        0, "--backfill", "-b",
        help="Backfill N recent Strava runs from summary data (no stream fetch)",
    ),
    pmc: bool = typer.Option(True, "--pmc/--no-pmc", help="Include full PMC day-by-day table"),
    rolling_window: int = typer.Option(10, "--window", "-w", help="Rolling average window (runs)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
):
    """
    Show longitudinal fitness trends: ATL, CTL, TSB (Performance Management Chart)
    and rolling EF / decoupling across all recorded runs.

    Run history is stored in ~/.biosystems/history.jsonl and updated
    automatically each time 'biosystems strava' is executed.

    Use --backfill N to seed history from the last N Strava activity summaries
    without fetching full streams (uses hrTSS approximation).
    """
    from biosystems.analytics.history import backfill_from_strava, load_history
    from biosystems.analytics.trending import compute_pmc, compute_rolling_stats, summarize_trend

    # Optional backfill from Strava summaries
    if backfill > 0:
        try:
            zone_config = load_zone_config(zones_path)
        except Exception as e:
            typer.secho(f"Error loading zones: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        from biosystems.ingestion.strava import _refresh_access_token
        try:
            token = _refresh_access_token()
        except Exception as e:
            typer.secho(f"Auth failed: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        try:
            new_entries = backfill_from_strava(backfill, zone_config, access_token=token)
            typer.secho(
                f"Backfilled {len(new_entries)} new entries from Strava.",
                fg=typer.colors.CYAN, err=True,
            )
        except Exception as e:
            typer.secho(f"Backfill failed: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

    entries = load_history()
    if not entries:
        typer.secho(
            "No run history found. Run 'biosystems strava' first, or use --backfill N to seed from Strava.",
            fg=typer.colors.YELLOW, err=True,
        )
        raise typer.Exit(code=1)

    pmc_data = compute_pmc(entries)
    rolling_data = compute_rolling_stats(entries, window=rolling_window)
    summary = summarize_trend(pmc_data, rolling_data)

    if json_output:
        import json
        output: dict = {"summary": summary, "rolling": rolling_data}
        if pmc:
            output["pmc"] = pmc_data
        typer.echo(json.dumps(output, indent=2))
    else:
        typer.secho("\n--- Performance Management ---", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"CTL (fitness):  {summary.get('ctl', 0):.1f}  [{summary.get('ctl_trend', 'unknown')}]")
        typer.echo(f"ATL (fatigue):  {summary.get('atl', 0):.1f}")
        typer.echo(f"TSB (form):     {summary.get('tsb', 0):+.1f}")
        typer.echo(f"EF trend:       {summary.get('ef_trend', 'unknown')}")
        typer.echo(f"History runs:   {summary.get('history_runs', 0)}")
        if rolling_data:
            typer.secho("\n--- Recent Runs ---", fg=typer.colors.CYAN, bold=True)
            for r in rolling_data[-10:]:
                ef_str = f"{r['ef']:.5f}" if r.get("ef") else "  —  "
                dec_str = f"{r['decoupling_pct']:.1f}%" if r.get("decoupling_pct") is not None else " — "
                tss_str = f"{r['hrTSS']:.0f}" if r.get("hrTSS") else " — "
                typer.echo(
                    f"  {r['date']}  TSS={tss_str:>5}  EF={ef_str}  Dec={dec_str:>6}"
                    f"  {r.get('activity_name') or ''}"
                )


@app.command(name="wellness-sync", rich_help_panel="Wellness")
def wellness_sync(
    days: int = typer.Option(7, "--days", "-d", help="Days to sync back from today"),
    date_start: str = typer.Option(None, "--from", help="Start date YYYY-MM-DD (overrides --days)"),
    date_end: str = typer.Option(None, "--to", help="End date YYYY-MM-DD (default: today)"),
    api_key: str = typer.Option(None, "--api-key", envvar="HABITDASH_API_KEY", help="HabitDash API key"),
) -> None:
    """
    Sync wellness metrics from HabitDash (Whoop + Garmin) into the local cache.

    Cache location: ~/.biosystems/wellness.parquet

    Fetches: HRV RMSSD, Resting HR, Recovery Score, Sleep Score, Sleep Duration,
    Body Battery, Strain Score, VO2max, and more.

    Run nightly after 'biosystems strava' or schedule via cron:
        0 21 * * * biosystems wellness-sync >> ~/.biosystems/wellness.log 2>&1
    """
    from biosystems.wellness.cache import sync_wellness

    try:
        n = sync_wellness(
            days=days,
            date_start=date_start,
            date_end=date_end,
            api_key=api_key or None,
        )
        typer.secho(f"[wellness-sync] {n} date rows updated → ~/.biosystems/wellness.parquet",
                    fg=typer.colors.GREEN, err=True)
    except ValueError as exc:
        typer.secho(f"[wellness-sync] {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.secho(f"[wellness-sync] Failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command(name="wellness-show", rich_help_panel="Wellness")
def wellness_show(
    date_str: str = typer.Option(None, "--date", "-d", help="Date YYYY-MM-DD (default: today)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """
    Show wellness readiness for a date: G/A/R signal, raw values, and 1d/7d deltas.

    Requires at least 1 day of data from 'biosystems wellness-sync'.
    """
    import json as _json
    from datetime import date as _date

    from biosystems.wellness.cache import compute_wellness_context

    target = date_str or _date.today().isoformat()
    ctx = compute_wellness_context(target)

    if not ctx:
        typer.secho(
            f"No wellness data for {target}. Run 'biosystems wellness-sync' first.",
            fg=typer.colors.YELLOW, err=True,
        )
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(_json.dumps(ctx, indent=2))
        return

    gar = ctx.get("gar", "—")
    detail = ctx.get("gar_detail", "")
    typer.secho(f"\nWellness Readiness — {target}", fg=typer.colors.CYAN, bold=True)
    typer.secho(f"  {gar}  {detail}", bold=True)

    if ctx.get("stale"):
        typer.secho(
            f"  ⚠ WARNING: most recent data is {ctx['staleness_days']} day(s) old",
            fg=typer.colors.YELLOW,
        )

    typer.echo()
    typer.secho("  Raw values:", fg=typer.colors.CYAN)
    def _row(label, val, unit=""):
        return typer.echo(f"    {label:<28} {val if val is not None else 'n/a'} {unit}".rstrip())
    _row("HRV RMSSD",           ctx.get("hrv_rmssd"),      "ms")
    _row("Resting HR",          ctx.get("resting_hr"),     "bpm")
    _row("Recovery Score",      ctx.get("recovery_score"), "%")
    _row("Sleep Score",         ctx.get("sleep_score"),    "%")
    if ctx.get("sleep_duration_s") is not None:
        hours = ctx["sleep_duration_s"] / 3600
        typer.echo(f"    {'Sleep Duration':<28} {hours:.1f} h")
    _row("Body Battery",        ctx.get("body_battery"),   "%")
    _row("Strain Score",        ctx.get("strain_score"))

    typer.echo()
    typer.secho("  Deltas:", fg=typer.colors.CYAN)
    def _delta(label, val, unit=""):
        return typer.echo(
            f"    {label:<28} {(f'{val:+.1f}' if val is not None else 'n/a')} {unit}".rstrip()
        )
    _delta("HRV 1d Δ",             ctx.get("hrv_1d_delta"),  "ms")
    _delta("HRV 7d Δ (% of mean)", ctx.get("hrv_7d_pct"),   "%")
    _delta("RHR 1d Δ",             ctx.get("rhr_1d_delta"),  "bpm")
    _delta("RHR 7d Δ",             ctx.get("rhr_7d_delta"),  "bpm vs 7d mean")
    _delta("Body Battery 7d Δ",    ctx.get("bb_7d_delta"),   "%")
    if ctx.get("avg_stress") is not None:
        typer.echo(f"    {'Avg Stress':<28} {ctx['avg_stress']:.0f}")
    if ctx.get("vo2max") is not None:
        typer.echo(f"    {'VO2max':<28} {ctx['vo2max']:.1f} ml/kg/min")
    if ctx.get("sleep_hours") is not None:
        typer.echo(f"    {'Sleep':<28} {ctx['sleep_hours']:.1f} h")
    if ctx.get("sleep_debt_7d") is not None:
        debt = ctx["sleep_debt_7d"]
        sign = "+" if debt > 0 else ""
        label = "debt" if debt > 0 else "surplus"
        typer.echo(f"    {'7-day Sleep Debt':<28} {sign}{debt:.1f} h ({label})")
    if ctx.get("respiratory_rate") is not None:
        rr_str = f"{ctx['respiratory_rate']:.1f} brpm"
        if ctx.get("rr_sigma") is not None:
            rr_str += f"  ({ctx['rr_sigma']:+.1f}σ vs personal mean)"
        typer.echo(f"    {'Respiratory Rate':<28} {rr_str}")

    norms = ctx.get("norms") or {}
    if any(v is not None for v in norms.values()):
        typer.echo()
        typer.secho("  Personal norms:", fg=typer.colors.CYAN)
        if norms.get("rhr_garmin_mean"):
            typer.echo(f"    {'RHR mean (Garmin era)':<28} {norms['rhr_garmin_mean']:.1f} bpm")
        if norms.get("hrv_mean"):
            typer.echo(f"    {'HRV mean (Whoop era)':<28} {norms['hrv_mean']:.1f} ms")
        if norms.get("bb_mean"):
            typer.echo(f"    {'Body Battery mean':<28} {norms['bb_mean']:.1f} %")
        if norms.get("stress_mean"):
            typer.echo(f"    {'Avg Stress mean':<28} {norms['stress_mean']:.1f}")
        if norms.get("vo2max_mean"):
            typer.echo(f"    {'VO2max mean':<28} {norms['vo2max_mean']:.1f} ml/kg/min")
        src = "calibrated" if ctx.get("thresholds_calibrated") else "clinical fallback"
        typer.secho(f"  G/A/R thresholds: {src}", fg=typer.colors.CYAN)
    typer.echo()


@app.command(name="wellness-analyze", rich_help_panel="Wellness")
def wellness_analyze(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """
    Analyze personal wellness baselines, coverage, correlations, and calibrated thresholds.

    Surfaces the analytics methodology used to understand and calibrate the G/A/R system.
    """
    import json as _json

    from biosystems.wellness.analytics import (
        calibrate_thresholds,
        compute_correlations,
        compute_coverage,
        compute_era_stats,
    )
    from biosystems.wellness.cache import load_wellness_df, wellness_path

    df = load_wellness_df()
    if df.empty:
        typer.secho(
            "No wellness data found. Run 'biosystems wellness-sync' or import a CSV first.",
            fg=typer.colors.YELLOW, err=True,
        )
        raise typer.Exit(code=1)

    coverage    = compute_coverage(df)
    era_stats   = compute_era_stats(df)
    thresholds  = calibrate_thresholds(df)

    # Correlations on the metrics that have overlapping data
    corr_cols = [c for c in [
        "hrv_rmssd", "resting_hr_whoop", "resting_hr_garmin",
        "recovery_score", "sleep_score", "body_battery",
        "avg_stress", "strain_score",
    ] if c in df.columns]
    correlations = compute_correlations(df, cols=corr_cols)

    if json_output:
        out: dict = {
            "coverage":     coverage.reset_index().to_dict(orient="records"),
            "era_stats":    era_stats,
            "thresholds":   thresholds,
            "correlations": {
                c: {c2: round(v, 3) for c2, v in row.items()}
                for c, row in correlations.to_dict().items()
            },
        }
        typer.echo(_json.dumps(out, indent=2, default=str))
        return

    # ── Human-readable output ────────────────────────────────────────────────
    typer.secho(f"\nWellness Analytics — {wellness_path()}", fg=typer.colors.CYAN, bold=True)
    typer.secho(f"  {len(df)} date rows  |  {df.index.min().date()} → {df.index.max().date()}\n",
                fg=typer.colors.CYAN)

    typer.secho("── Coverage ──", fg=typer.colors.YELLOW, bold=True)
    typer.echo(coverage[["n_rows", "date_start", "date_end", "pct_coverage"]].to_string())

    typer.secho("\n── Era Stats ──", fg=typer.colors.YELLOW, bold=True)
    for era_name in ("whoop_era", "garmin_era"):
        era = era_stats.get(era_name, {})
        if not era.get("days"):
            continue
        typer.secho(f"\n  {era_name.replace('_', ' ').title()} "
                    f"({era['start']} → {era['end']}, {era['days']} days)",
                    fg=typer.colors.CYAN)
        for metric, stats in era.get("baselines", {}).items():
            typer.echo(
                f"    {metric:<30}  mean={stats['mean']:>7.1f}  "
                f"std={stats['std']:>6.1f}  "
                f"p25={stats['p25']:>7.1f}  p75={stats['p75']:>7.1f}  "
                f"n={stats['n']}"
            )

    typer.secho("\n── Key Correlations (Whoop era) ──", fg=typer.colors.YELLOW, bold=True)
    if not correlations.empty:
        typer.echo(correlations.round(2).to_string())

    typer.secho("\n── Calibrated G/A/R Thresholds ──", fg=typer.colors.YELLOW, bold=True)
    src = "personal data" if thresholds.get("calibrated") else "clinical fallback"
    typer.secho(f"  Source: {src}  |  Garmin days: {thresholds.get('garmin_days', 0)}\n",
                fg=typer.colors.CYAN)
    typer.echo(f"  HRV drop RED:      > {thresholds['hrv_pct_drop_red']:.1f}% below 7d mean")
    typer.echo(f"  HRV drop AMBER:    > {thresholds['hrv_pct_drop_amber']:.1f}% below 7d mean")
    typer.echo(f"  RHR spike RED:     > +{thresholds['rhr_spike_red']:.1f} bpm above 7d mean")
    typer.echo(f"  RHR spike AMBER:   > +{thresholds['rhr_spike_amber']:.1f} bpm above 7d mean")
    bb = thresholds.get("body_battery", {})
    if bb:
        typer.echo(f"  Body Battery RED:  < {bb['red']:.0f}%  (personal p20, n={bb.get('n','?')})")
        typer.echo(f"  Body Battery AMBER:< {bb['amber']:.0f}%  (personal p40)")
    stress = thresholds.get("avg_stress", {})
    if stress:
        typer.echo(f"  Stress RED:        > {stress['red']:.0f}  (personal p90)")
        typer.echo(f"  Stress AMBER:      > {stress['amber']:.0f}  (personal p75)")
    rr = thresholds.get("respiratory_rate", {})
    if rr:
        typer.echo(f"  Resp Rate RED:     > {rr['red']:.1f} brpm  (+2.5σ, mean={rr['mean']:.1f}, n={rr.get('n','?')})")
        typer.echo(f"  Resp Rate AMBER:   > {rr['amber']:.1f} brpm  (+1.5σ)")

    norms = thresholds.get("norms", {})
    if norms:
        typer.secho("\n── Personal Norms ──", fg=typer.colors.YELLOW, bold=True)
        pairs = [
            ("RHR Garmin mean", norms.get("rhr_garmin_mean"), "bpm"),
            ("HRV mean (Whoop era)", norms.get("hrv_mean"), "ms"),
            ("Body Battery mean", norms.get("bb_mean"), "%"),
            ("Avg Stress mean", norms.get("stress_mean"), ""),
            ("VO2max mean", norms.get("vo2max_mean"), "ml/kg/min"),
            ("Sleep mean", norms.get("sleep_h_mean"), "h"),
        ]
        for label, val, unit in pairs:
            if val is not None:
                typer.echo(f"  {label:<28}  {val:.1f} {unit}".rstrip())
    typer.echo()


@app.command(name="wellness-trends", rich_help_panel="Wellness")
def wellness_trends(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """
    Show longitudinal fitness arc: RHR and VO2max monthly trends since tracking began.

    Highlights: RHR improvement over time, VO2max trajectory, training adaptation.
    """
    import json as _json

    from biosystems.wellness.analytics import compute_longitudinal_fitness
    from biosystems.wellness.cache import load_wellness_df

    df = load_wellness_df()
    if df.empty:
        typer.secho(
            "No wellness data found. Run 'biosystems wellness-sync' first.",
            fg=typer.colors.YELLOW, err=True,
        )
        raise typer.Exit(code=1)

    trends = compute_longitudinal_fitness(df)
    if not trends:
        typer.secho("Insufficient data for trend analysis (need ≥2 months).",
                    fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    if json_output:
        typer.echo(_json.dumps(trends, indent=2, default=str))
        return

    typer.secho("\nLongitudinal Fitness Arc", fg=typer.colors.CYAN, bold=True)
    typer.secho(f"  {trends.get('era_summary', '')}\n", fg=typer.colors.CYAN)

    for metric_key, metric_label, unit in [
        ("rhr",    "Resting Heart Rate",  "bpm"),
        ("vo2max", "VO2max",              "ml/kg/min"),
    ]:
        data = trends.get(metric_key)
        if not data:
            continue
        typer.secho(f"── {metric_label} ──", fg=typer.colors.YELLOW, bold=True)
        typer.secho(f"  {data['trend_label']}\n", fg=typer.colors.GREEN)
        typer.echo(f"  {'Month':<10} {'Mean':>8} {'N':>5}")
        typer.echo(f"  {'-'*10} {'-'*8} {'-'*5}")
        for row in data["monthly_means"]:
            typer.echo(f"  {row['month']:<10} {row['mean']:>8.1f} {unit:<12} n={row['n']}")
        typer.echo()


if __name__ == "__main__":
    app()
