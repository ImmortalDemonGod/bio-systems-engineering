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

from biosystems.physics.gap import (
    calculate_average_gap,
    calculate_gap_from_dataframe,
    calculate_gap_segment,
    calculate_grade_percent,
    minetti_energy_cost,
)
from biosystems.physics.metrics import (
    calculate_decoupling,
    calculate_efficiency_factor,
    calculate_hr_tss,
    compute_training_zones,
    lower_z2_bpm,
    run_metrics,
)

__all__ = [
    "run_metrics",
    "calculate_efficiency_factor",
    "calculate_decoupling",
    "calculate_hr_tss",
    "compute_training_zones",
    "lower_z2_bpm",
    "calculate_gap_segment",
    "calculate_gap_from_dataframe",
    "calculate_average_gap",
    "minetti_energy_cost",
    "calculate_grade_percent",
]
