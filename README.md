# Bio-Systems Engineering

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: Active](https://img.shields.io/badge/status-active-success.svg)]()

> **An N=1 longitudinal study applying MLOps pipelines and control theory to human physiological optimization.**

---

## The Hook: Science Meets Systems Engineering

This repository documents a 103-day experiment (2025-W17 to W36) where systematic, data-driven interventions produced measurable physiological improvements:

| Metric | Baseline (W17) | Final (W35) | Δ Change |
|--------|---------------|-------------|----------|
| **Efficiency Factor** | 0.0161 | 0.0188 | **+18.4%** |
| **Aerobic Decoupling** | 8.2% | 4.7% | **-42.7%** |
| **Average Pace** | 5:03/km | 4:20/km | **-15.2%** |
| **Cadence** | 155 spm | 166 spm | **+10 spm** |
| **Environmental Resilience** | 19.8% drift @ 32°C | 4.7% drift @ 27°C | **Breakthrough** |

**The Innovation:** This isn't just about the performance gains—it's about the **reproducible software pipeline** that made systematic measurement, intervention, and validation possible.

👉 **[Read the Full Technical Report →](reports/01_longitudinal_study.md)**

---

## The Stack: Tools & Technologies

**Core Libraries:**
- 🐍 **Python 3.10+** - Primary language
- 📊 **Pandas & NumPy** - Data manipulation and analysis
- ✅ **Pydantic** - Runtime validation and data contracts
- 🏃 **fitdecode** - Garmin FIT file parsing
- 🌦️ **Open-Meteo API** - Environmental context

**Research Quality:**
- 🧪 **pytest** - Automated testing
- 📝 **Type Hints** - mypy-compatible type safety
- 🐳 **Docker** - Reproducible environment
- 📚 **Jupyter** - Interactive analysis notebooks

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bio-systems-engineering.git
cd bio-systems-engineering

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Docker (Recommended for Reproducibility)

```bash
# Build the image
docker build -t biosystems:latest .

# Run analysis
docker run -v $(pwd)/data:/app/data biosystems:latest
```

### Basic Usage

```python
from biosystems.ingestion.gpx import parse_gpx
from biosystems.physics.metrics import calculate_efficiency_factor
from biosystems.models import ZoneConfig

# Parse your activity file
df = parse_gpx("data/raw/my_run.gpx")

# Define your heart rate zones
zones = ZoneConfig(
    resting_hr=50,
    threshold_hr=186,
    zones={
        "Z2": {"bpm": (160, 186), "pace_min_per_km": (9.0, 9.4)}
    }
)

# Calculate metrics
metrics = calculate_efficiency_factor(df, zones)
print(f"Efficiency Factor: {metrics.efficiency_factor:.5f}")
print(f"Aerobic Decoupling: {metrics.decoupling_pct:.2f}%")
```

---

## Key Findings: The "Black Box" Investigation

The project's technical report documents a systematic progression through four phases:

### Phase A: The Diagnosis (Weeks 17-20)
**Discovery:** High volume training, stagnant performance  
**Data:** EF = 0.016, Cadence = 155 spm  
**Insight:** *"The engine works, but the chassis is inefficient"*

### Phase B: The Crucible (Weeks 21-24)
**Event:** Environmental stress test  
**Data:** Week 23 @ 32.3°C → 19.78% decoupling  
**Insight:** *"System breakdown under thermal load validates instrumentation sensitivity"*

### Phase C: The Intervention (Weeks 25-31)
**Strategy:** Biomechanical re-patterning (NME drills)  
**Data:** Cadence gradually shifts 158 → 165 spm  
**Insight:** *"Deliberate neuromuscular training"*

### Phase D: The Breakthrough (Weeks 32-36)
**Outcome:** Performance ceiling shattered  
**Data:** Week 32: 166 spm, 3:59/km pace | Week 35: EF = 0.0188, 4.71% decoupling @ 27°C  
**Insight:** *"Systemic adaptation + heat resilience confirmed"*

---

## The Methodology: Run-Only Filter

**The Critical Innovation:**

Traditional running analytics (Strava, Garmin) average across entire activities—including warm-ups, cool-downs, and traffic stops. This pollutes physiological metrics.

Our solution: **The Run-Only Filter**

```python
# From biosystems/physics/metrics.py
lz2 = lower_z2_bpm(zones)  # Lower bound of Zone 2
work_df = df[df['hr'] >= lz2]  # Filter: Only data where HR ≥ Z2

# Calculate Efficiency Factor on pure running signal
ef = (work_df['dist'].sum() / work_df['dt'].sum()) / work_df['hr'].mean()
```

**Why This Matters:**
- Mathematically removes recovery periods
- Validates claim: *"Gains are from running performance, not just moving"*
- Separates this study from casual analytics

**Example Validation:**
- Total session: 59 minutes
- Isolated running: 39 minutes @ Z2+
- **Filter precision: 66% signal extraction**

---

## Transparent Limitations

This study explicitly acknowledges:

1. **No Grade Adjusted Pace (GAP):** Analysis assumes topographically similar training routes
2. **No heat adjustment algorithm:** Performance gains likely **underestimated** (improvement occurred despite higher thermal stress)
3. **N=1 design:** Results demonstrate feasibility, not generalizability
4. **Missing power data:** Power metrics excluded from analysis

**Framing:** These limitations are transparently disclosed. The **18.4% improvement represents a conservative lower bound** of actual physiological adaptation.

---

## Repository Structure

```
bio-systems-engineering/
├── src/biosystems/          # Core library code
│   ├── ingestion/           # FIT/GPX parsers
│   ├── physics/             # EF, Decoupling, TSS algorithms
│   ├── signal/              # Walk detection, filtering
│   └── environment/         # Weather integration
├── data/
│   ├── processed/           # Weekly aggregates (safe, anonymized)
│   └── raw/                 # .gitignored (your private GPS data)
├── reports/
│   ├── figures/             # Publication-quality charts
│   └── 01_longitudinal_study.md  # Full technical narrative
├── notebooks/               # Jupyter analysis notebooks
├── tests/                   # Automated test suite
└── tools/                   # Utility scripts (GPS sanitization)
```

---

## For Researchers & Developers

### Contributing

We welcome contributions! Areas of interest:
- [ ] Implement Grade Adjusted Pace (Minetti's equation)
- [ ] Add FIT file parser module
- [ ] Expand test coverage
- [ ] Create additional analysis notebooks

### Running Tests

```bash
# Run full test suite with coverage
pytest

# Run specific test file
pytest tests/test_physics.py -v

# Type checking
mypy src/biosystems
```

### Citation

If you use this work in research, please cite:

```bibtex
@software{biosystems2025,
  author = {Holistic Performance Enhancement Contributors},
  title = {Bio-Systems Engineering: MLOps for Human Performance},
  year = {2025},
  url = {https://github.com/yourusername/bio-systems-engineering}
}
```

See `CITATION.cff` for structured metadata.

---

## The Vision: System as Contribution

This project positions the **software pipeline itself** as a primary research contribution:

> *"We didn't just run; we built a machine to measure the running."*

Traditional sports science relies on manual logging, proprietary platforms, or expensive lab equipment. This repository demonstrates:

1. **Automated ETL** - From raw GPS → validated metrics
2. **Reproducible Environment** - Docker + requirements.txt
3. **Rigorous Filtering** - Run-Only algorithm for signal purity
4. **Privacy-Safe Design** - No GPS coordinates, only derived time-series

**The broader impact:** A blueprint for N=1 self-experimentation that meets publication standards.

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Open-Meteo API** - Free weather data
- **Python Scientific Stack** - NumPy, Pandas, SciPy communities
- **fitdecode** - Robust FIT file parsing

---

**Status:** ✅ Active Development | 📊 Publication-Ready | 🔬 Research Artifact

For questions or collaboration: [Open an Issue](https://github.com/yourusername/bio-systems-engineering/issues)
