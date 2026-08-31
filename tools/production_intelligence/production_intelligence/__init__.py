"""Candidate Production Intelligence Capability Atlas runtime.

This package is a structured coordination/routing helper only. It does not own
natural-language directing, project canonical facts, evaluation verdicts,
targeted repair, or learning maturity.
"""

from .runtime import (
    CapabilityAtlas,
    ProductionIntelligenceError,
    validate_handoff_packet,
)

__all__ = [
    "CapabilityAtlas",
    "ProductionIntelligenceError",
    "validate_handoff_packet",
]
