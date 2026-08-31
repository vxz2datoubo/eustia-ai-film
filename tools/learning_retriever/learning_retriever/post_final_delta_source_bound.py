"""Source-bound public entrypoint for Post-Final-Delta validation.

Public callers provide original Final-Delta source packages, never serialized
Final-Delta results. Each package is re-executed through the canonical
source-bound Final-Delta compiler before the existing structural cohort
validator runs. This module owns no evidence, maturity, regression, or write
authority; it only closes the source-authenticity boundary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .final_delta import FinalDeltaEvidenceError, compile_final_delta_learning_evidence
from .post_final_delta import PostFinalDeltaValidationError, assess_post_final_delta_validation

_ALLOWED_ROOT_KEYS = {"assessment_id", "hypothesis_id", "final_delta_inputs", "requested_maturity"}


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
            compiled.append(compile_final_delta_learning_evidence(source, project_root=project_root))
        except FinalDeltaEvidenceError as exc:
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_FINAL_DELTA",
                f"final_delta_inputs[{index}] canonical re-execution rejected: {exc.code}",
            ) from exc

    internal = {
        "assessment_id": package.get("assessment_id"),
        "hypothesis_id": package.get("hypothesis_id"),
        "final_deltas": compiled,
    }
    if "requested_maturity" in package:
        internal["requested_maturity"] = package["requested_maturity"]
    result = assess_post_final_delta_validation(internal, project_root=project_root)
    result["source_binding"] = {
        "mode": "canonical_final_delta_reexecution",
        "serialized_final_deltas_accepted": False,
        "compiled_source_count": len(compiled),
    }
    return result
