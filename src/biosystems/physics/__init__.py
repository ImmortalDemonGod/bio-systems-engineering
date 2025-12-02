"""
Physics Module
==============

Algorithms for calculating physiological and biomechanical metrics.

Core Metrics:
- Efficiency Factor (EF): Speed / Heart Rate
- Aerobic Decoupling: HR drift over time (Pa:HR)
- Training Stress Score (TSS): Quantified training load
- Grade Adjusted Pace (GAP): Normalized pace accounting for elevation
"""

from biosystems.physics.metrics import (
    run_metrics,
    calculate_efficiency_factor,
    calculate_decoupling,
    calculate_hr_tss,
    compute_training_zones,
    lower_z2_bpm,
)

__all__ = [
    "run_metrics",
    "calculate_efficiency_factor",
    "calculate_decoupling",
    "calculate_hr_tss",
    "compute_training_zones",
    "lower_z2_bpm",
]
