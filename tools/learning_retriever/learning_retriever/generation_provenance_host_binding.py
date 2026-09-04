"""Fail-closed generation provenance host-binding seam.

This candidate deliberately has no positive verification path in repo-only mode.
It composes the accepted immutable-byte identity primitive and records what is
known about before/after content while refusing to infer source-artifact or model
generation-event provenance from caller metadata.

A future host/tool integration may add a separately reviewed positive verifier,
but ordinary Python callers cannot supply an attestation to this module today.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .immutable_byte_identity import (
    ImmutableBytePairEvidence,
    compare_immutable_byte_pair,
)


class GenerationProvenanceError(ValueError):
    """Fail-closed provenance eligibility error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class RepoOnlyGenerationProvenanceAssessment:
    """Negative-capability receipt for one before/after byte pair.

    The receipt is diagnostic only. It cannot be replayed as provenance input,
    and its existence never means that either byte value has been bound to a
    source artifact, provider job, generation event, formal asset, or reference
    input.
    """

    byte_pair: ImmutableBytePairEvidence
    status: str = "UNVERIFIED_HOST_ATTESTATION_REQUIRED"
    byte_content_identity_verified: bool = True
    source_artifact_binding_verified: bool = False
    generation_event_binding_verified: bool = False
    distinct_generation_events_verified: bool = False
    formal_asset_binding_verified: bool = False
    generation_reference_binding_verified: bool = False
    causal_attribution_authorized: bool = False
    regression_support_authorized: bool = False
    maturity_support_authorized: bool = False
    writeback_authorized: bool = False
    host_attestation_input_supported: bool = False
    serialized_receipt_reusable_as_authority: bool = False

    def diagnostic_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "byte_pair": self.byte_pair.diagnostic_dict(),
            "byte_content_identity_verified": self.byte_content_identity_verified,
            "source_artifact_binding_verified": self.source_artifact_binding_verified,
            "generation_event_binding_verified": self.generation_event_binding_verified,
            "distinct_generation_events_verified": self.distinct_generation_events_verified,
            "formal_asset_binding_verified": self.formal_asset_binding_verified,
            "generation_reference_binding_verified": self.generation_reference_binding_verified,
            "causal_attribution_authorized": self.causal_attribution_authorized,
            "regression_support_authorized": self.regression_support_authorized,
            "maturity_support_authorized": self.maturity_support_authorized,
            "writeback_authorized": self.writeback_authorized,
            "host_attestation_input_supported": self.host_attestation_input_supported,
            "serialized_receipt_reusable_as_authority": self.serialized_receipt_reusable_as_authority,
            "required_future_authority": "trusted_host_or_generation_tool_attestation_verifier",
        }


def assess_repo_only_generation_provenance(
    before: bytes,
    after: bytes,
) -> RepoOnlyGenerationProvenanceAssessment:
    """Assess only byte-content identity; provenance always remains unverified.

    No generation_id, media_ref, digest, boolean, receipt, host object, path, or
    provider metadata parameter exists. Exact built-in ``bytes`` enforcement is
    inherited from ``compare_immutable_byte_pair``.
    """

    pair = compare_immutable_byte_pair(before, after)
    return RepoOnlyGenerationProvenanceAssessment(byte_pair=pair)


def future_host_attestation_requirements() -> dict[str, Any]:
    """Return descriptive requirements for a future separately governed adapter.

    This is documentation data, not an accepted attestation schema. Passing a
    mapping with these fields to the public verifier is impossible because the
    current public verifier has no attestation parameter.
    """

    return {
        "status": "DESCRIPTIVE_ONLY_NOT_ACCEPTED_AS_INPUT",
        "must_be_host_originated": True,
        "must_not_be_caller_mintable": True,
        "must_bind_exact_output_bytes_or_content_identity": True,
        "must_bind_provider_or_tool_generation_event_identity": True,
        "must_bind_model_and_version_when_available": True,
        "must_bind_generation_mode_and_reference_inputs_when_relevant": True,
        "must_distinguish_output_artifact_binding_from_reference_input_binding": True,
        "must_be_fresh_or_revalidated_for_invocation": True,
        "serialized_mapping_alone_is_insufficient": True,
        "repo_embedded_secret_is_forbidden": True,
        "python_private_token_is_not_a_security_boundary": True,
        "positive_verifier_requires_fresh_independent_trust_review": True,
    }
