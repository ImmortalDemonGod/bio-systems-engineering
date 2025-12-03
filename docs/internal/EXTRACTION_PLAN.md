# Bio-Systems-Engineering Repository Extraction Plan

**Document ID:** `BIO-SYS-EXTRACT-V1.0`  
**Date:** 2025-12-02  
**Status:** Phase A Complete, Phase B In Progress

---

## Executive Summary

This document provides the systematic plan for extracting the Running System from the Cultivation monorepo into a standalone, publication-grade `bio-systems-engineering` repository.

### Key Findings from Code Analysis

**Extractable Core Logic (→ Library):**
1. ✅ `metrics.py` (365 lines) - Pure physics/algorithms
2. ✅ `walk_utils.py` (173 lines) - Signal processing
3. ✅ `weather_utils.py` (145 lines) - Weather API integration

**Cultivation-Dependent Orchestration (→ Stays in Cultivation):**
1. ❌ `process_all_runs.py` - Main orchestrator with hardcoded paths
2. ❌ `parse_run_files.py` - File parsing + subprocess calls
3. ❌ `run_performance_analysis.py` - Report generation with Cultivation imports
4. ❌ `analyze_hr_pace_distribution.py` - Visualization scripts
5. ❌ `aggregate_weekly_runs.py` - Time-series aggregation

---

## Critical Dependencies to Decouple

### 1. Zone Configuration Coupling
**Location:** `metrics.py:198`
```python
_ZONES_FILE = Path(__file__).parents[2] / "data" / "zones_personal.yml"
```

**Problem:** Hardcoded Cultivation-specific path

**Solution:** 
- Create `ZoneConfig` Pydantic model
- Accept zones as function parameter
- Provide `load_zones_from_yaml()` helper function
- No default file path in library

### 2. Wellness Data Coupling
**Location:** `process_all_runs.py:19-41`
```python
SYNC_SCRIPT = UTILITIES_DIR / 'sync_habitdash.py'
```

**Problem:** Direct dependency on HabitDash API sync

**Solution:**
- Make wellness data optional
- Accept pre-generated `wellness_context.csv`
- Graceful degradation when unavailable

### 3. Import Path Hacks
**Location:** Multiple files
```python
sys.path.insert(0, str(Path(__file__).parents[3]))
```

**Problem:** Fragile path manipulation

**Solution:**
- Proper package structure with `pyproject.toml`
- Editable install: `pip install -e .`
- Clean imports: `from biosystems.physics import calculate_ef`

---

## Target Repository Architecture

```
bio-systems-engineering/
├── src/
│   └── biosystems/
│       ├── __init__.py
│       ├── models.py           # Pydantic data contracts
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── gpx.py          # GPX parser (from metrics.py)
│       │   └── fit.py          # FIT parser (from parse_run_files.py)
│       ├── physics/
│       │   ├── __init__.py
│       │   ├── metrics.py      # EF, Decoupling, TSS
│       │   └── gap.py          # Grade Adjusted Pace (NEW)
│       ├── signal/
│       │   ├── __init__.py
│       │   └── walk_detection.py  # From walk_utils.py
│       └── environment/
│           ├── __init__.py
│           └── weather.py      # From weather_utils.py
├── data/
│   ├── processed/              # Weekly aggregates (SAFE TO COMMIT)
│   │   └── weekly_metrics.parquet
│   └── raw/                    # .gitignore (DO NOT COMMIT)
├── reports/
│   ├── figures/                # Publication charts
│   └── 01_longitudinal_study.md
├── notebooks/                  # Analysis Jupyter notebooks
│   └── 01_generate_figures.ipynb
├── tests/                      # Public unit tests
│   ├── test_physics.py
│   ├── test_signal.py
│   └── test_models.py
├── tools/                      # Utility scripts
│   └── sanitize_gps.py
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── CITATION.cff
└── README.md
```

---

## Data Contracts (Pydantic Models)

### ZoneConfig
```python
from pydantic import BaseModel, Field
from typing import Tuple

class HeartRateZone(BaseModel):
    name: str
    bpm: Tuple[int, int] = Field(..., description="(lower, upper) HR bounds")
    pace_min_per_km: Tuple[float, float]

class ZoneConfig(BaseModel):
    zones: dict[str, HeartRateZone]
    resting_hr: int = Field(..., gt=0)
    threshold_hr: int = Field(..., gt=0)
```

### RunContext
```python
class RunContext(BaseModel):
    temperature_c: Optional[float] = None
    weather_code: Optional[int] = None
    rest_hr: Optional[int] = None
    sleep_score: Optional[float] = None
    hrv_rmssd: Optional[float] = None
```

### PhysiologicalMetrics
```python
class PhysiologicalMetrics(BaseModel):
    distance_km: float
    duration_min: float
    avg_pace_min_per_km: float
    avg_hr: float
    efficiency_factor: float
    decoupling_pct: float
    hr_tss: float
    avg_cadence: Optional[int] = None
```

---

## Phased Extraction Plan

### ✅ Phase A: Dependency Analysis (Complete)
**Duration:** 1 hour  
**Deliverables:**
- [x] Map all file dependencies
- [x] Identify core logic vs. orchestration
- [x] Design data contracts
- [x] Document critical coupling points

### 🔄 Phase B: Repository Initialization (In Progress)
**Duration:** 2-3 hours  
**Tasks:**
1. Create directory structure
2. Write `pyproject.toml` with metadata
3. Create `.gitignore` (protect raw GPS data)
4. Initialize git repository
5. Write minimal `README.md`

**Deliverables:**
- Empty but properly structured repository
- Valid Python package installable via `pip install -e .`

### 📋 Phase C: Core Logic Extraction
**Duration:** 4-5 hours  
**Tasks:**
1. **Extract `metrics.py` → `biosystems/physics/metrics.py`**
   - Remove `_ZONES_FILE` hardcoding
   - Accept `zones: ZoneConfig` as parameter
   - Keep `load_personal_zones()` as optional helper
   
2. **Extract `walk_utils.py` → `biosystems/signal/walk_detection.py`**
   - No changes needed (already pure logic)
   
3. **Extract `weather_utils.py` → `biosystems/environment/weather.py`**
   - Remove hardcoded `DATA_DIR` path
   - Accept `cache_path: Optional[Path]` as parameter

4. **Extract GPX parsing → `biosystems/ingestion/gpx.py`**
   - Move `parse_gpx()` from `metrics.py`
   - Keep as standalone parser

**Verification:**
- All tests pass in isolation
- No Cultivation imports
- Type hints present

### 📋 Phase D: Data Contracts Implementation
**Duration:** 2 hours  
**Tasks:**
1. Create `models.py` with Pydantic models
2. Refactor core functions to accept/return models
3. Add validation tests

### 📋 Phase E: Grade Adjusted Pace (GAP)
**Duration:** 2-3 hours  
**Tasks:**
1. Research Minetti's equation
2. Implement `calculate_gap()` in `physics/gap.py`
3. Add unit tests with known values
4. Update `PhysiologicalMetrics` to include GAP

### 📋 Phase F: Privacy Sanitization
**Duration:** 2 hours  
**Tasks:**
1. Create `tools/sanitize_gps.py`:
   - Truncate first/last 500m of GPS traces
   - Remove absolute coordinates
   - Keep relative distance/elevation
2. Process Cultivation data through sanitizer
3. Copy safe artifacts to `data/processed/`

### 📋 Phase G: Documentation
**Duration:** 4-5 hours  
**Tasks:**
1. Write comprehensive `README.md`
2. Write `reports/01_longitudinal_study.md`
3. Create `CITATION.cff`
4. Write `Dockerfile`
5. Create Jupyter notebook for figure generation

### 📋 Phase H: Integration Testing
**Duration:** 3-4 hours  
**Tasks:**
1. Install library in Cultivation: `pip install -e ../bio-systems-engineering`
2. Refactor `process_all_runs.py` to use library
3. Run full pipeline
4. Verify output is identical to previous version

---

## Privacy & Security Checklist

**Before First Public Push:**
- [ ] No raw `.fit` or `.gpx` files committed
- [ ] No API keys in code
- [ ] No absolute GPS coordinates in data files
- [ ] `data/raw/` in `.gitignore`
- [ ] Wellness data anonymized (if included)
- [ ] Manual audit of all committed files

---

## Risk Mitigation Matrix

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| GPS Privacy Exposure | CRITICAL | `.gitignore` + sanitization script | Planned |
| API Key Leakage | CRITICAL | Environment variable documentation | Planned |
| Dependency Coupling | HIGH | Pydantic models + optional params | Designed |
| Import Path Fragility | MEDIUM | Proper package structure | Designed |
| Technical Debt Migration | MEDIUM | Fix during extraction | Planned |

---

## Success Criteria

**For Library:**
- ✅ Clean separation of logic (public) from data/secrets (private)
- ✅ Reproducible environment (Docker + requirements.txt)
- ✅ Professional structure (src/, tests/, docs/)
- ✅ Privacy-safe data artifacts
- ✅ Standalone functionality (no Cultivation dependencies)
- ✅ Proper semantic versioning (v1.0.0 release)

**For Integration:**
- ✅ Cultivation successfully imports library
- ✅ Output files are byte-identical to previous version
- ✅ All existing tests still pass
- ✅ Pipeline runs without errors

**For Publication:**
- ✅ README compelling and professional
- ✅ Technical report complete with narrative arc
- ✅ Figures publication-quality
- ✅ CITATION.cff valid
- ✅ Dockerfile builds successfully

---

## Next Immediate Actions

1. ✅ Create this extraction plan document
2. 🔄 Initialize repository structure (Phase B)
3. 📋 Begin core logic extraction (Phase C)

**Estimated Timeline:** 7-8 days to full completion with quality standards maintained.
