"""Source-bound public entrypoint for Post-Final-Delta validation.

Public callers provide original Final-Delta source packages, never serialized
Final-Delta results. Each package is re-executed through the governed public
Final-Delta compiler before the private structural cohort projection runs.

This module owns no evidence, maturity, regression, generation, artifact, or
write authority. Its job is to preserve upstream trust boundaries downstream.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .final_delta import FinalDeltaEvidenceError, compile_final_delta_learning_evidence
from .post_final_delta import PostFinalDeltaValidationError
from ._post_final_delta_core_v3 import assess_post_final_delta_validation as _assess_internal_projection

_ALLOWED_ROOT_KEYS = {"assessment_id", "hypothesis_id", "final_delta_inputs", "requested_maturity"}


def _assert_no_downstream_attribution_restoration(delta: Mapping[str, Any], *, index: int) -> None:
    """Fail closed if an upstream NOT_COMPARABLE result carries attributed repair state.

    Diagnostic ``unattributed_transition_candidates`` are intentionally ignored.
    They are allowed to describe what the canonical evaluator observed, but they
    must never be copied into formal ``field_transitions`` or eligibility fields.
    """

    status = str(delta.get("comparison_status") or "").strip().upper()
    if status != "NOT_COMPARABLE":
        return

    if delta.get("field_transitions"):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA",
            f"final_delta_inputs[{index}] NOT_COMPARABLE result contains attributed field_transitions",
        )
    outcome = delta.get("repair_outcome") or {}
    for key in ("resolved_fields", "persistent_failure_fields", "regressed_fields"):
        if outcome.get(key):
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_FINAL_DELTA",
                f"final_delta_inputs[{index}] NOT_COMPARABLE result contains attributed {key}",
            )
    regression = delta.get("regression_candidate_handoff") or {}
    if regression.get("eligible") is True:
        raise PostFinalDeltaValidationError(
            "POST_FD_AUTHORITY_VIOLATION",
            f"final_delta_inputs[{index}] NOT_COMPARABLE result cannot be regression eligible",
        )


def assess_source_bound_post_final_delta(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PostFinalDeltaValidationError("POST_FD_INVALID_SHAPE", "assessment root must be a mapping")
    package = dict(raw)
    unknown = set(package) - _ALLOWED_ROOT_KEYS
    if unknown:
        raise PostFinalDeltaValidationError(
            "POST_FD_UNKNOWN_FIELD", f"unknown source-bound assessment fields: {sorted(unknown)}"
        )
    inputs = package.get("final_delta_inputs")
    if not isinstance(inputs, list) or not inputs:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_SHAPE", "final_delta_inputs must be a non-empty list"
        )

    compiled: list[dict[str, Any]] = []
    for index, source in enumerate(inputs):
        if not isinstance(source, Mapping):
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_SHAPE", f"final_delta_inputs[{index}] must be a mapping"
            )
        try:
            delta = compile_final_delta_learning_evidence(source, project_root=project_root)
        except FinalDeltaEvidenceError as exc:
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_FINAL_DELTA",
                f"final_delta_inputs[{index}] canonical re-execution rejected: {exc.code}",
            ) from exc
        _assert_no_downstream_attribution_restoration(delta, index=index)
        compiled.append(delta)

    internal = {
        "assessment_id": package.get("assessment_id"),
        "hypothesis_id": package.get("hypothesis_id"),
        "final_deltas": compiled,
    }
    if "requested_maturity" in package:
        internal["requested_maturity"] = package["requested_maturity"]
    result = _assess_internal_projection(internal, project_root=project_root)
    result["source_binding"] = {
        "mode": "canonical_final_delta_reexecution",
        "serialized_final_deltas_accepted": False,
        "compiled_source_count": len(compiled),
        "structural_projection_visibility": "private_internal_only",
        "upstream_attribution_gate_preserved": True,
        "unattributed_transition_candidates_consumed_as_attributed": False,
    }
    return result
