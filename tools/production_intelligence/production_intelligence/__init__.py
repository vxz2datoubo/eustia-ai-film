"""Candidate Production Intelligence Capability Atlas runtime.

Structured coordination only. The package does not own natural-language directing,
project canonical facts, evaluation verdicts, targeted repair, or learning maturity.
"""

from .runtime import (
    CapabilityAtlas,
    ProductionIntelligenceError,
    validate_handoff_packet,
    validate_handoff_transition,
    validate_project,
)

__all__ = [
    "CapabilityAtlas",
    "ProductionIntelligenceError",
    "validate_handoff_packet",
    "validate_handoff_transition",
    "validate_project",
]
