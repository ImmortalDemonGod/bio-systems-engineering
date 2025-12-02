#!/usr/bin/env python3
"""
Installation Verification Script
=================================

Verifies that biosystems package is correctly installed and all core
functions can be imported and are callable.
"""

import sys


def verify_imports():
    """Test that all core functions can be imported."""
    print("=" * 60)
    print("BIOSYSTEMS INSTALLATION VERIFICATION")
    print("=" * 60)
    print()
    
    errors = []
    
    # Test models
    print("✓ Testing models...")
    try:
        from biosystems.models import (
            ZoneConfig,
            RunContext,
            PhysiologicalMetrics,
            HeartRateZone,
        )
        print("  ✓ All models imported successfully")
    except Exception as e:
        errors.append(f"Models import failed: {e}")
        print(f"  ✗ Models import failed: {e}")
    
    # Test ingestion
    print("✓ Testing ingestion...")
    try:
        from biosystems.ingestion import parse_gpx
        print("  ✓ GPX parser imported successfully")
        print(f"    parse_gpx callable: {callable(parse_gpx)}")
    except Exception as e:
        errors.append(f"Ingestion import failed: {e}")
        print(f"  ✗ Ingestion import failed: {e}")
    
    # Test physics
    print("✓ Testing physics...")
    try:
        from biosystems.physics import (
            run_metrics,
            calculate_efficiency_factor,
            calculate_decoupling,
            calculate_hr_tss,
            calculate_average_gap,
            minetti_energy_cost,
        )
        print("  ✓ Physics functions imported successfully")
        print(f"    run_metrics callable: {callable(run_metrics)}")
        print(f"    calculate_efficiency_factor callable: {callable(calculate_efficiency_factor)}")
        print(f"    calculate_decoupling callable: {callable(calculate_decoupling)}")
        print(f"    calculate_hr_tss callable: {callable(calculate_hr_tss)}")
        print(f"    calculate_average_gap callable: {callable(calculate_average_gap)}")
        print(f"    minetti_energy_cost callable: {callable(minetti_energy_cost)}")
        
        # Test GAP calculation with simple example
        print("  ✓ Testing GAP calculation...")
        test_cost_flat = minetti_energy_cost(0.0)
        test_cost_uphill = minetti_energy_cost(5.0)
        print(f"    Minetti cost (flat): {test_cost_flat:.3f}")
        print(f"    Minetti cost (5% uphill): {test_cost_uphill:.3f}")
        if test_cost_uphill > test_cost_flat:
            print("    ✓ GAP calculations working correctly")
        else:
            errors.append("GAP calculation logic error")
            print("    ✗ GAP calculation logic error")
    except Exception as e:
        errors.append(f"Physics import failed: {e}")
        print(f"  ✗ Physics import failed: {e}")
    
    # Test signal
    print("✓ Testing signal...")
    try:
        from biosystems.signal import (
            walk_block_segments,
            summarize_walk_segments,
        )
        print("  ✓ Signal functions imported successfully")
        print(f"    walk_block_segments callable: {callable(walk_block_segments)}")
        print(f"    summarize_walk_segments callable: {callable(summarize_walk_segments)}")
    except Exception as e:
        errors.append(f"Signal import failed: {e}")
        print(f"  ✗ Signal import failed: {e}")
    
    # Test environment
    print("✓ Testing environment...")
    try:
        from biosystems.environment import (
            fetch_weather_open_meteo,
            get_weather_description,
            WeatherCache,
        )
        print("  ✓ Environment functions imported successfully")
        print(f"    fetch_weather_open_meteo callable: {callable(fetch_weather_open_meteo)}")
        print(f"    get_weather_description callable: {callable(get_weather_description)}")
        print(f"    WeatherCache class: {WeatherCache}")
    except Exception as e:
        errors.append(f"Environment import failed: {e}")
        print(f"  ✗ Environment import failed: {e}")
    
    print()
    print("=" * 60)
    if errors:
        print(f"VERIFICATION FAILED: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("✓ ALL TESTS PASSED - Package is correctly installed!")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(verify_imports())
