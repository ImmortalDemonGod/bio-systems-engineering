"""
Bio-Systems CLI
===============

Command-line interface for analyzing human performance metrics.
Provides a JSON-native output for integration with OpenClaw.
"""

from pathlib import Path

import dotenv
import typer
import yaml

dotenv.load_dotenv()
from pydantic import ValidationError

from biosystems.ingestion.fit import add_derived_metrics, parse_fit
from biosystems.ingestion.gpx import parse_gpx
from biosystems.models import HeartRateZone, RunContext, ZoneConfig
from biosystems.physics.metrics import run_metrics

app = typer.Typer(help="Bio-Systems Engineering CLI")


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


@app.command()
def analyze(
    file_path: Path = typer.Argument(..., help="Path to activity file (.fit or .gpx)"),
    zones_path: Path = typer.Option(
        Path("data/zones_personal.yml"),
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


@app.command()
def strava(
    activity_id: int | None = typer.Argument(
        None, help="Strava activity ID. Omit to use the most recent run."
    ),
    zones_path: Path = typer.Option(
        Path("data/zones_personal.yml"),
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
            typer.echo("No recent runs found.")
            raise typer.Exit()

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

    # --- Walk detection using Strava moving flag (primary) + pace fallback ---
    df["pace_min_per_km"] = df["pace_sec_km"] / 60
    if "moving" in df.columns:
        df["is_walk"] = (~df["moving"].fillna(True).astype(bool)) | (
            df["pace_min_per_km"] > 8.7
        )
    else:
        df["is_walk"] = (df["pace_min_per_km"] > 8.7) | (df["cadence"].fillna(0) < 128)

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
            "activity_name": activity_name_str,
            "source": "biosystems_strava",
        }
        strava_efforts_store: dict[str, int] = {
            e["name"]: e["elapsed_time_s"]
            for e in activity_meta.get("best_efforts", [])
            if e.get("name") and e.get("elapsed_time_s")
        }
        try:
            append_run(history_entry, strava_efforts=strava_efforts_store or None)
        except Exception:
            pass  # never block output due to history write failure

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
            first_ever = [bb for bb in report.block_bests if bb.is_new_best and bb.prev_best_s is None]
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


@app.command(name="backfill-efforts")
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
            moving_s = summary.get("moving_time", 0)
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


@app.command(name="backfill-streams")
def backfill_streams(
    after: str = typer.Option(
        "2025-09-08",
        "--after",
        help="Fetch all runs on or after this date (YYYY-MM-DD). Default: day after study end.",
    ),
    zones_path: Path = typer.Option(
        Path("data/zones_personal.yml"),
        "--zones", "-z",
        help="Path to zones configuration YAML",
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--reprocess",
        help="Skip dates already in history with source=biosystems_strava.",
    ),
    delay: float = typer.Option(
        1.5,
        "--delay",
        help="Seconds to sleep between Strava API calls (rate limit courtesy).",
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
    from biosystems.models import RunContext
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

    # Build set of already-processed dates for fast skip checks
    existing_stream_dates: set[str] = set()
    if skip_existing:
        for entry in load_history():
            if entry.get("source") == "biosystems_strava":
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

        if skip_existing and run_date in existing_stream_dates:
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

        # Walk detection: Strava moving flag (primary) + pace fallback
        df["pace_min_per_km"] = df["pace_sec_km"] / 60
        if "moving" in df.columns:
            df["is_walk"] = (~df["moving"].fillna(True).astype(bool)) | (
                df["pace_min_per_km"] > 8.7
            )
        else:
            df["is_walk"] = (df["pace_min_per_km"] > 8.7) | (df["cadence"].fillna(0) < 128)

        try:
            report = build_run_report(
                df,
                zone_config,
                context=None,
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
            "hrTSS": round(m.hr_tss, 1),
            "distance_km": round(m.distance_km, 2),
            "avg_hr": round(m.avg_hr, 1),
            "avg_pace_min_per_km": round(m.avg_pace_min_per_km, 2),
            "ef": round(m.efficiency_factor, 5),
            "ef_gap": report.ef_grade_adjusted,
            "decoupling_pct": round(m.decoupling_pct, 2),
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
        except Exception:
            pass

        ef_str = f"EF={m.efficiency_factor:.5f}"
        dec_str = f"Dec={m.decoupling_pct:+.1f}%"
        typer.secho(f"  [ok]    {label}  {ef_str}  {dec_str}", fg=typer.colors.GREEN)
        processed += 1
        time.sleep(delay)

    typer.secho(
        f"\nDone: {processed} processed, {skipped} skipped, {failed} failed.",
        fg=typer.colors.CYAN,
    )


@app.command()
def trend(
    zones_path: Path = typer.Option(
        Path("data/zones_personal.yml"),
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
        typer.secho(f"\n--- Performance Management ---", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"CTL (fitness):  {summary.get('ctl', 0):.1f}  [{summary.get('ctl_trend', 'unknown')}]")
        typer.echo(f"ATL (fatigue):  {summary.get('atl', 0):.1f}")
        typer.echo(f"TSB (form):     {summary.get('tsb', 0):+.1f}")
        typer.echo(f"EF trend:       {summary.get('ef_trend', 'unknown')}")
        typer.echo(f"History runs:   {summary.get('history_runs', 0)}")
        if rolling_data:
            typer.secho(f"\n--- Recent Runs ---", fg=typer.colors.CYAN, bold=True)
            for r in rolling_data[-10:]:
                ef_str = f"{r['ef']:.5f}" if r.get("ef") else "  —  "
                dec_str = f"{r['decoupling_pct']:.1f}%" if r.get("decoupling_pct") is not None else " — "
                tss_str = f"{r['hrTSS']:.0f}" if r.get("hrTSS") else " — "
                typer.echo(
                    f"  {r['date']}  TSS={tss_str:>5}  EF={ef_str}  Dec={dec_str:>6}"
                    f"  {r.get('activity_name') or ''}"
                )


if __name__ == "__main__":
    app()
