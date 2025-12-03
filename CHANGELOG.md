# Changelog

All notable changes to the bio-systems-engineering library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-02

### Added
- Initial release of bio-systems-engineering library
- **Ingestion Module**: Parsers for GPX and FIT files with GPS/HR/cadence support
- **Physics Module**: 
  - Efficiency Factor (EF) calculation with metabolic filtering
  - Aerobic Decoupling analysis
  - Grade Adjusted Pace (GAP) using Minetti's equation
  - Training Stress Score (TSS) calculation
- **Signal Module**: 
  - Walk detection with dual-criterion classifier (pace + cadence)
  - GPS jitter filtering
  - Walk segment analysis
- **Models Module**: Pydantic models for type-safe data validation
  - `ActivityData`: Validated GPS/HR time-series
  - `ZoneConfiguration`: Heart rate and pace zone definitions
  - `PhysiologicalMetrics`: Calculated summary metrics
- **Environment Module**: Weather data integration via OpenWeatherMap API
- **Tools**:
  - `sanitize_gps.py`: Privacy-preserving GPS data sanitization
  - `verify_installation.py`: Installation verification script
- Comprehensive test suite with 85% code coverage
- Docker support for reproducible environments
- Complete API documentation

### Features
- Type-safe data processing with Pydantic validation
- Stateless, pure functional design for reproducibility
- Privacy-first architecture (no data storage in library)
- Configurable zone thresholds
- Graceful degradation for incomplete data (e.g., HR-only files)
- Support for single-leg cadence auto-detection and doubling

### Documentation
- README with quick start guide
- DATA_PREPARATION guide for users
- Citation file (CITATION.cff) for academic use
- Comprehensive inline code documentation
- Example usage in tests

### Testing
- Unit tests for all modules
- Integration tests for full pipeline
- Edge case coverage (GPS-only, HR-only, corrupt files)
- Pytest-based test suite

### Performance
- Efficient pandas-based data processing
- Minimal dependencies (numpy, pandas, pydantic, requests)
- Fast parsing (~7 seconds per activity file)

### Known Limitations
- GAP calculation requires elevation data
- Weather data requires API key (gracefully skips if unavailable)
- Metabolic filtering assumes Zone 2 lower bound at 130 bpm (configurable)

## [Unreleased]

### Planned Features
- Support for cycling power data
- Swimming pace analysis
- Multi-sport transition handling
- Advanced sleep/recovery metrics
- Integration with Strava API
