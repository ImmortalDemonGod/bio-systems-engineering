"""
Signal Processing Module
========================

Algorithms for cleaning and classifying activity signals.

Features:
- Walk vs. Run detection based on cadence and pace
- GPS jitter filtering
- Segment identification and classification
"""

from biosystems.signal.walk_detection import (
    walk_block_segments,
    summarize_walk_segments,
    filter_gps_jitter,
)

__all__ = [
    "walk_block_segments",
    "summarize_walk_segments",
    "filter_gps_jitter",
]
