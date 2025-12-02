"""
Ingestion Module
================

Parsers and readers for various activity file formats.

Available parsers:
- GPX: XML-based GPS exchange format
- FIT: Garmin binary format (Flexible and Interoperable Data Transfer)
"""

from biosystems.ingestion.gpx import parse_gpx

__all__ = ["parse_gpx"]
