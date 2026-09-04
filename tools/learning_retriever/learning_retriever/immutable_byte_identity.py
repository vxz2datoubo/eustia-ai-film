"""Pure immutable-byte identity primitive for the EUSTIA AI-film runtime.

This candidate deliberately proves less than an artifact verifier.
It accepts only already-materialized exact built-in Python ``bytes`` and computes
stable content identity from that exact value. It performs no filesystem,
locator, network, generation, asset, media, or semantic resolution.

The separation is intentional:

    governed artifact resolver (future) -> exact built-in bytes -> this primitive
        -> generation provenance binding (future)

A caller may supply arbitrary bytes, so the resulting identity is evidence only
about the byte value supplied to this invocation. It is never evidence that the
bytes came from a named file, File Library object, formal asset, model job, or
specific generation event. ``bytes`` subclasses are rejected before any caller-
defined special method can run inside the primitive.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any


class ByteIdentityError(ValueError):
    """Fail-closed immutable-byte identity error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ImmutableByteObservation:
    """Invocation-local identity of one exact built-in byte value."""

    content_sha256: str
    byte_length: int
    observation_state: str = "IMMUTABLE_BYTES_OBSERVED"
    input_contract: str = "PYTHON_BYTES_ONLY"
    source_artifact_binding_state: str = "UNVERIFIED"
    generation_binding_state: str = "UNVERIFIED"
    formal_asset_binding_state: str = "UNVERIFIED"
    semantic_verification_state: str = "NOT_PERFORMED"

    @property
    def content_identity(self) -> str:
        return f"sha256:{self.content_sha256}:{self.byte_length}"

    def diagnostic_dict(self) -> dict[str, Any]:
        """Serialize diagnostics only; serialized output is never identity input."""
        return {
            "content_sha256": self.content_sha256,
            "byte_length": self.byte_length,
            "content_identity": self.content_identity,
            "observation_state": self.observation_state,
            "input_contract": self.input_contract,
            "source_artifact_binding_state": self.source_artifact_binding_state,
            "generation_binding_state": self.generation_binding_state,
            "formal_asset_binding_state": self.formal_asset_binding_state,
            "semantic_verification_state": self.semantic_verification_state,
            "source_artifact_verified": False,
            "generation_event_verified": False,
            "formal_asset_verified": False,
            "serialized_receipt_reusable_as_authority": False,
        }


@dataclass(frozen=True, slots=True)
class ImmutableBytePairEvidence:
    """Comparison of two invocation-local exact built-in byte values."""

    before: ImmutableByteObservation
    after: ImmutableByteObservation
    same_content: bool
    distinct_content_observed: bool
    pair_digest: str
    claim_scope: str = "IN_MEMORY_BYTE_CONTENT_IDENTITY_ONLY"
    source_artifact_binding_state: str = "UNVERIFIED"
    generation_binding_state: str = "UNVERIFIED"
    formal_asset_binding_state: str = "UNVERIFIED"

    def diagnostic_dict(self) -> dict[str, Any]:
        return {
            "before": self.before.diagnostic_dict(),
            "after": self.after.diagnostic_dict(),
            "same_content": self.same_content,
            "distinct_content_observed": self.distinct_content_observed,
            "pair_digest": self.pair_digest,
            "claim_scope": self.claim_scope,
            "source_artifact_binding_state": self.source_artifact_binding_state,
            "generation_binding_state": self.generation_binding_state,
            "formal_asset_binding_state": self.formal_asset_binding_state,
            "source_artifacts_verified": False,
            "distinct_generation_events_verified": False,
            "formal_assets_verified": False,
            "serialized_receipt_reusable_as_authority": False,
        }


def _require_immutable_bytes(value: Any, *, label: str) -> bytes:
    """Accept exact built-in bytes only; invoke no caller-defined bytes hooks."""
    if type(value) is not bytes:
        raise ByteIdentityError(
            "BYTE_INPUT_NOT_IMMUTABLE_BYTES",
            f"{label} must be an exact built-in Python bytes value",
        )
    return value


def observe_immutable_bytes(payload: bytes) -> ImmutableByteObservation:
    """Compute identity for exactly the built-in byte value supplied by the caller."""
    value = _require_immutable_bytes(payload, label="payload")
    return ImmutableByteObservation(
        content_sha256=hashlib.sha256(value).hexdigest(),
        byte_length=len(value),
    )


def compare_immutable_byte_pair(before: bytes, after: bytes) -> ImmutableBytePairEvidence:
    """Compare two exact built-in byte values without asserting their provenance."""
    before_value = _require_immutable_bytes(before, label="before")
    after_value = _require_immutable_bytes(after, label="after")
    before_observation = observe_immutable_bytes(before_value)
    after_observation = observe_immutable_bytes(after_value)
    same_content = before_observation.content_identity == after_observation.content_identity
    pair_payload = (
        f"{before_observation.content_identity}\n{after_observation.content_identity}"
    ).encode("utf-8")
    return ImmutableBytePairEvidence(
        before=before_observation,
        after=after_observation,
        same_content=same_content,
        distinct_content_observed=not same_content,
        pair_digest=hashlib.sha256(pair_payload).hexdigest(),
    )
