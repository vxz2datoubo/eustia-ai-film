"""Candidate Production Intelligence Capability Atlas runtime.

Structured coordination only.  The package does not own natural-language directing,
project canonical facts, evaluation verdicts, targeted repair, or learning maturity.
Serialized Signal Envelopes are transport metadata, not routing authority.
"""

from .runtime import (
    CapabilityAtlas,
    CapabilityResolution,
    ProductionIntelligenceError,
    resolve_expected_observed,
    validate_handoff_packet,
    validate_handoff_transition,
    validate_project,
)
from .trusted_adapter import (
    TrustedEvalCoordinationReceipt,
    TrustedRepairItem,
    compile_expected_observed_coordination,
    require_trusted_eval_receipt,
    validate_trusted_adapter_policy,
)

__all__ = [
    "CapabilityAtlas",
    "CapabilityResolution",
    "ProductionIntelligenceError",
    "TrustedEvalCoordinationReceipt",
    "TrustedRepairItem",
    "compile_expected_observed_coordination",
    "require_trusted_eval_receipt",
    "resolve_expected_observed",
    "validate_handoff_packet",
    "validate_handoff_transition",
    "validate_project",
    "validate_trusted_adapter_policy",
]
