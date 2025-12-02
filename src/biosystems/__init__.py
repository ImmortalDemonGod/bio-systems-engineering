"""
Bio-Systems Engineering
=======================

A Python library for systematic human performance optimization using MLOps principles.

Modules
-------
- ingestion: Parsers for GPS activity files (.fit, .gpx)
- physics: Physiological metrics (Efficiency Factor, Decoupling, TSS)
- signal: Signal processing for activity detection
- environment: Environmental context (weather, altitude)
- models: Pydantic data contracts

Example
-------
>>> from biosystems.ingestion.gpx import parse_gpx
>>> from biosystems.physics.metrics import calculate_efficiency_factor
>>> 
>>> # Parse activity file
>>> df = parse_gpx("my_run.gpx")
>>> 
>>> # Calculate metrics
>>> ef = calculate_efficiency_factor(df, zones)
>>> print(f"Efficiency Factor: {ef:.5f}")

Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Holistic Performance Enhancement Contributors"
__license__ = "MIT"

from biosystems import models

__all__ = ["models", "__version__"]
