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
from biosystems.physics.gap import (
    calculate_gap_segment,
    calculate_gap_from_dataframe,
    calculate_average_gap,
    minetti_energy_cost,
    calculate_grade_percent,
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
