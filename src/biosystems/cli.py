"""
Bio-Systems CLI
===============

Command-line interface for analyzing human performance metrics.
Provides a JSON-native output for integration with OpenClaw.
"""

from pathlib import Path

import typer
import yaml
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
    try:
        if activity_id is None:
            summary, df = fetch_latest_run(access_token=token)
            typer.secho(
                f"Using latest run: {summary['name']} ({summary['start_date_local'][:10]})",
                fg=typer.colors.CYAN,
                err=True,
            )
        else:
            df = fetch_activity_streams(activity_id, access_token=token)
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Failed to fetch streams: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Load zone config and run metrics
    try:
        zone_config = load_zone_config(zones_path)
    except Exception as e:
        typer.secho(f"Error loading zones: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    context = RunContext(temperature_c=temp_c) if temp_c is not None else None

    try:
        metrics = run_metrics(df, zone_config, context=context)
    except Exception as e:
        typer.secho(f"Metrics calculation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

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


if __name__ == "__main__":
    app()
