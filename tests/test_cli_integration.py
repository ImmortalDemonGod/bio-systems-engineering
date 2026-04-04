import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_analyze_gpx():
    """Verify that biosystems.cli analyze works on a real GPX file."""
    # Use one of the real GPX files in data/raw
    gpx_file = Path("data/raw/20250503_174110_baseox_wk1_sat_day6_proglong_30_40min_145_160bpm_11-14minmi_Z2_durability_rpe_4_anklepain_2.gpx")

    if not gpx_file.exists():
        pytest.skip(f"Test file {gpx_file} not found")

    result = subprocess.run(
        [sys.executable, "-m", "biosystems.cli", "analyze", str(gpx_file)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"}
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert "distance_km" in data
    assert "efficiency_factor" in data
    assert data["distance_km"] > 0
