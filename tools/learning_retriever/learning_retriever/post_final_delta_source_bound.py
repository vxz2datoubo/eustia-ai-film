"""Source-bound public entrypoint for Post-Final-Delta validation.

Public callers provide original Final-Delta source packages, never serialized
Final-Delta results. Each package is re-executed through the governed public
Final-Delta compiler before the private structural cohort projection runs.

This facade owns no evidence, maturity, regression, generation, artifact, or
write authority. It mechanically prevents weaker downstream aggregation from
restoring authority that the upstream Final-Delta did not actually earn.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .final_delta import FinalDeltaEvidenceError, compile_final_delta_learning_evidence
from .post_final_delta import PostFinalDeltaValidationError
from ._post_final_delta_core_v3 import assess_post_final_delta_validation as _assess_internal_projection

_ALLOWED_ROOT_KEYS = {
    "assessment_id",
    "hypothesis_id",
    "final_delta_inputs",
    "requested_maturity",
    "maturity_target",
}
_MATURITY_TARGET_KEYS = {"model", "model_version", "exact_candidate_lesson_payload"}
_COMPARABLE_STATES = {"COMPARABLE", "COMPARABLE_WITH_GAPS"}


def _mapping(value: Any, *, code: str, message: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PostFinalDeltaValidationError(code, message)
    return dict(value)


def _assert_upstream_artifact_and_attribution_gate(
    delta: Mapping[str, Any], *, index: int
) -> None:
    """Fail closed on upstream contract drift before private cohort projection."""

    status = str(delta.get("comparison_status") or "").strip().upper()
    artifact = delta.get("artifact_provenance_binding")
    artifact_verified = isinstance(artifact, Mapping) and artifact.get("verified") is True

    # Artifact provenance is an independent trust axis. A future/regressed
    # upstream cannot regain attribution merely by relabeling comparison_status.
    if status in _COMPARABLE_STATES and not artifact_verified:
        raise PostFinalDeltaValidationError(
            "POST_FD_AUTHORITY_VIOLATION",
            f"final_delta_inputs[{index}] comparable result lacks verified artifact provenance",
        )

    if status != "NOT_COMPARABLE":
        return

    if delta.get("field_transitions"):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA",
            f"final_delta_inputs[{index}] NOT_COMPARABLE result contains attributed field_transitions",
        )
    outcome = delta.get("repair_outcome") or {}
    for key in ("resolved_fields", "persistent_failure_fields", "regressed_fields"):
        if isinstance(outcome, Mapping) and outcome.get(key):
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_FINAL_DELTA",
                f"final_delta_inputs[{index}] NOT_COMPARABLE result contains attributed {key}",
            )
    regression = delta.get("regression_candidate_handoff") or {}
    if isinstance(regression, Mapping) and regression.get("eligible") is True:
        raise PostFinalDeltaValidationError(
            "POST_FD_AUTHORITY_VIOLATION",
            f"final_delta_inputs[{index}] NOT_COMPARABLE result cannot be regression eligible",
        )


def _support_eligible_projection(
    delta: Mapping[str, Any], *, index: int
) -> tuple[dict[str, Any], bool]:
    """Project SUPPORTING only from formally attributed and upstream-eligible repair.

    The private v3 cohort core predates the artifact gate and classifies any
    non-empty ``resolved_fields`` as SUPPORTING. We preserve that core unchanged
    but clear resolved support in the internal projection unless the upstream
    result has a matching formal RESOLVED transition *and* explicitly marks the
    regression handoff eligible.
    """

    projected = deepcopy(dict(delta))
    status = str(projected.get("comparison_status") or "").strip().upper()
    if status not in _COMPARABLE_STATES:
        return projected, False

    outcome = _mapping(
        projected.get("repair_outcome"),
        code="POST_FD_INVALID_FINAL_DELTA",
        message=f"final_delta_inputs[{index}] repair_outcome must be a mapping",
    )
    resolved = {
        str(field).strip()
        for field in (outcome.get("resolved_fields") or [])
        if isinstance(field, str) and field.strip()
    }
    if not resolved:
        return projected, False

    transitions = projected.get("field_transitions")
    if not isinstance(transitions, list):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA",
            f"final_delta_inputs[{index}] field_transitions must be a list",
        )
    formal_resolved: set[str] = set()
    for transition in transitions:
        if not isinstance(transition, Mapping):
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_FINAL_DELTA",
                f"final_delta_inputs[{index}] field transition must be a mapping",
            )
        field = str(transition.get("field") or "").strip()
        state = str(transition.get("transition") or "").strip().upper()
        if field and state == "RESOLVED":
            formal_resolved.add(field)

    if not resolved.issubset(formal_resolved):
        missing = sorted(resolved - formal_resolved)
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA",
            f"final_delta_inputs[{index}] resolved_fields lack formal RESOLVED transitions: {missing}",
        )

    regression = projected.get("regression_candidate_handoff") or {}
    upstream_eligible = isinstance(regression, Mapping) and regression.get("eligible") is True
    if upstream_eligible:
        return projected, False

    # Improvement may remain diagnostic evidence, but it cannot count as
    # SUPPORTING maturity/regression evidence without upstream eligibility.
    outcome["resolved_fields"] = []
    projected["repair_outcome"] = outcome
    regression = dict(regression) if isinstance(regression, Mapping) else {}
    regression["eligible"] = False
    projected["regression_candidate_handoff"] = regression
    return projected, True


def _required_partition_string(value: Any, *, field: str, index: int) -> str:
    """Require an explicit non-empty exact cohort partition value.

    Missing-value sentinels are intentionally forbidden. A literal business value
    such as ``UNKNOWN_MODEL`` remains an ordinary string and can never collide
    with absence because absence fails before cohort construction.
    """

    if not isinstance(value, str) or not value.strip():
        raise PostFinalDeltaValidationError(
            "POST_FD_COHORT_IDENTITY_INCOMPLETE",
            f"final_delta_inputs[{index}] requires explicit non-empty cohort field {field}",
        )
    return value


def _validated_cohort_key(delta: Mapping[str, Any], *, index: int) -> tuple[str, str, str]:
    candidate = delta.get("candidate_learning_evidence")
    if not isinstance(candidate, Mapping):
        raise PostFinalDeltaValidationError(
            "POST_FD_COHORT_IDENTITY_INCOMPLETE",
            f"final_delta_inputs[{index}] requires candidate_learning_evidence mapping",
        )
    return (
        _required_partition_string(delta.get("model"), field="model", index=index),
        _required_partition_string(
            delta.get("model_version"), field="model_version", index=index
        ),
        _required_partition_string(
            candidate.get("candidate_lesson"), field="candidate_lesson", index=index
        ),
    )


def _cohort_key(delta: Mapping[str, Any]) -> tuple[str, str, str]:
    """Return exact already-validated cohort identity without missing sentinels."""

    candidate = delta.get("candidate_learning_evidence")
    if not isinstance(candidate, Mapping):
        raise PostFinalDeltaValidationError(
            "POST_FD_COHORT_IDENTITY_INCOMPLETE",
            "validated evidence lost candidate_learning_evidence before cohort projection",
        )
    model = delta.get("model")
    version = delta.get("model_version")
    lesson = candidate.get("candidate_lesson")
    if not all(isinstance(value, str) and value.strip() for value in (model, version, lesson)):
        raise PostFinalDeltaValidationError(
            "POST_FD_COHORT_IDENTITY_INCOMPLETE",
            "validated evidence lost exact cohort partition identity before projection",
        )
    return model, version, lesson


def _resolve_maturity_target(
    *,
    package: Mapping[str, Any],
    projected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    requested_raw = package.get("requested_maturity")
    requested = None if requested_raw in (None, "") else str(requested_raw).strip()
    if requested is None:
        if package.get("maturity_target") not in (None, {}):
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_SHAPE",
                "maturity_target is allowed only when requested_maturity is present",
            )
        return projected, None

    keys = sorted({_cohort_key(delta) for delta in projected})
    raw_target = package.get("maturity_target")
    if raw_target in (None, {}):
        if len(keys) != 1:
            raise PostFinalDeltaValidationError(
                "POST_FD_MATURITY_TARGET_REQUIRED",
                "requested_maturity over multiple evidence cohorts requires an exact maturity_target",
            )
        selected = keys[0]
    else:
        target = _mapping(
            raw_target,
            code="POST_FD_INVALID_SHAPE",
            message="maturity_target must be a mapping",
        )
        unknown = set(target) - _MATURITY_TARGET_KEYS
        missing = _MATURITY_TARGET_KEYS - set(target)
        if unknown or missing:
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_SHAPE",
                f"maturity_target must contain exactly {sorted(_MATURITY_TARGET_KEYS)}",
            )
        selected_values = tuple(
            target[key]
            for key in ("model", "model_version", "exact_candidate_lesson_payload")
        )
        if not all(isinstance(value, str) and value.strip() for value in selected_values):
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_SHAPE",
                "maturity_target partition values must be explicit non-empty strings",
            )
        selected = selected_values
        if selected not in keys:
            raise PostFinalDeltaValidationError(
                "POST_FD_MATURITY_TARGET_NOT_FOUND",
                "maturity_target does not match any exact evidence cohort",
            )

    selected_rows = [delta for delta in projected if _cohort_key(delta) == selected]
    return selected_rows, {
        "model": selected[0],
        "model_version": selected[1],
        "exact_candidate_lesson_payload": selected[2],
    }


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
    projected: list[dict[str, Any]] = []
    downgraded_support_count = 0
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
        _assert_upstream_artifact_and_attribution_gate(delta, index=index)
        safe_projection, downgraded = _support_eligible_projection(delta, index=index)
        # Every evidence row must own a complete exact partition identity before
        # *any* cohort summary or maturity projection. No UNKNOWN sentinels.
        _validated_cohort_key(safe_projection, index=index)
        compiled.append(delta)
        projected.append(safe_projection)
        downgraded_support_count += int(downgraded)

    # Overall cohort/conflict output is computed across all evidence, but without
    # any maturity request so the private core cannot globally recombine cohorts.
    internal = {
        "assessment_id": package.get("assessment_id"),
        "hypothesis_id": package.get("hypothesis_id"),
        "final_deltas": projected,
    }
    result = _assess_internal_projection(internal, project_root=project_root)

    maturity_rows, maturity_target = _resolve_maturity_target(
        package=package,
        projected=projected,
    )
    if package.get("requested_maturity") not in (None, ""):
        maturity_internal = {
            "assessment_id": f"{package.get('assessment_id')}::MATURITY_TARGET",
            "hypothesis_id": package.get("hypothesis_id"),
            "final_deltas": maturity_rows,
            "requested_maturity": package.get("requested_maturity"),
        }
        maturity_projection = _assess_internal_projection(
            maturity_internal, project_root=project_root
        )
        result["maturity_assessment"] = maturity_projection["maturity_assessment"]
        result["maturity_assessment"]["evidence_cohort"] = maturity_target

    result["source_binding"] = {
        "mode": "canonical_final_delta_reexecution",
        "serialized_final_deltas_accepted": False,
        "compiled_source_count": len(compiled),
        "structural_projection_visibility": "private_internal_only",
        "upstream_artifact_gate_checked_independently": True,
        "upstream_attribution_gate_preserved": True,
        "support_requires_formal_resolved_transition": True,
        "support_requires_upstream_regression_eligibility": True,
        "support_downgraded_to_inconclusive_count": downgraded_support_count,
        "cohort_partition_requires_explicit_nonempty_values": True,
        "missing_value_sentinels_used": False,
        "maturity_is_cohort_scoped": True,
        "maturity_target": maturity_target,
        "unattributed_transition_candidates_consumed_as_attributed": False,
    }
    return result
