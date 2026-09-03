"""Source-bound Final-Delta public runtime with measurement-contract identity gating.

The heavy structural/evidence compiler lives in ``_final_delta_core``. This
public module adds one fail-closed trust boundary before its output may be
interpreted as a repair trajectory: before/after observations must have been
measured with the same semantic ruler.

A changed comparison mode, expectation provenance, inspection mode, or temporal
coverage contract cannot become ``FAIL -> PASS = RESOLVED``. The underlying
sources are still canonically re-executed by the core compiler; this wrapper
only removes attribution when the measurement contract drifts.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ._final_delta_core import (
    STRUCTURAL_GATE_CODES,
    FinalDeltaEvidenceError,
    compile_final_delta_learning_evidence as _compile_source_bound_core,
)

__all__ = [
    "STRUCTURAL_GATE_CODES",
    "FinalDeltaEvidenceError",
    "compile_final_delta_learning_evidence",
]


def _stable_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _measurement_contract_projection(raw_eval_input: Mapping[str, Any]) -> dict[str, Any]:
    """Project only semantics capable of changing how PASS/FAIL is measured.

    Output-specific evidence references, media IDs, confidence and observed
    values are deliberately excluded. They are evidence/results, not the ruler.
    """

    expectations_raw = raw_eval_input.get("expectations")
    expectations: list[dict[str, Any]] = []
    expectation_fields: list[str] = []
    if isinstance(expectations_raw, list):
        for item in expectations_raw:
            if not isinstance(item, Mapping):
                continue
            field = str(item.get("field") or "").strip()
            expectation_fields.append(field)
            expectations.append(
                {
                    "field": field,
                    "declared_value": deepcopy(item.get("declared_value")),
                    "provenance": deepcopy(item.get("provenance")),
                }
            )
    expectations.sort(key=lambda item: item["field"])

    reverse = raw_eval_input.get("reverse_observation")
    reverse = dict(reverse) if isinstance(reverse, Mapping) else {}
    observations_raw = reverse.get("expectation_observations")
    observations = dict(observations_raw) if isinstance(observations_raw, Mapping) else {}
    comparison_modes: list[dict[str, str]] = []
    for field in sorted(expectation_fields):
        observation = observations.get(field)
        if observation is None:
            mode = "MISSING_OBSERVATION"
        elif isinstance(observation, Mapping):
            mode = str(observation.get("comparison_mode") or "explicit_observation_judgment").strip()
        else:
            mode = "INVALID_OBSERVATION_SHAPE"
        comparison_modes.append({"field": field, "comparison_mode": mode})

    provenance_raw = reverse.get("provenance")
    provenance = dict(provenance_raw) if isinstance(provenance_raw, Mapping) else {}
    observation_method = {
        "inspection_mode": provenance.get("inspection_mode"),
        "temporal_coverage": deepcopy(provenance.get("temporal_coverage")),
        "claimed_frame_by_frame_review": provenance.get("claimed_frame_by_frame_review", False),
    }

    return {
        "expectation_contract": expectations,
        "comparison_modes": comparison_modes,
        "observation_method": observation_method,
    }


def _measurement_contract_reasons(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> list[str]:
    reasons: list[str] = []
    if before.get("expectation_contract") != after.get("expectation_contract"):
        reasons.append("EXPECTATION_CONTRACT_MISMATCH")
    if before.get("comparison_modes") != after.get("comparison_modes"):
        reasons.append("COMPARISON_MODE_MISMATCH")
    if before.get("observation_method") != after.get("observation_method"):
        reasons.append("OBSERVATION_METHOD_MISMATCH")
    return reasons


def _remove_repair_attribution(result: dict[str, Any], reasons: list[str]) -> None:
    comparison_reasons = list(result.get("comparison_reasons") or [])
    for reason in ["MEASUREMENT_CONTRACT_MISMATCH", *reasons]:
        if reason not in comparison_reasons:
            comparison_reasons.append(reason)
    result["comparison_status"] = "NOT_COMPARABLE"
    result["comparison_reasons"] = comparison_reasons
    result["field_transitions"] = []

    outcome = result.get("repair_outcome")
    if isinstance(outcome, dict):
        for key in (
            "resolved_fields",
            "persistent_failure_fields",
            "unresolved_evidence_fields",
            "preserved_pass_fields",
            "regressed_fields",
        ):
            outcome[key] = []

    causal = result.get("causal_evidence")
    if isinstance(causal, dict):
        causal["status"] = "NOT_ELIGIBLE_NOT_COMPARABLE"
        causal["eligible_for_causal_analysis"] = False
        causal["causal_claim_authorized"] = False

    candidate = result.get("candidate_learning_evidence")
    if isinstance(candidate, dict):
        candidate["observed_transitions"] = []
        candidate["causal_evidence_status"] = "NOT_ELIGIBLE_NOT_COMPARABLE"
        candidate["generalization_authorized"] = False
        candidate["promotion_authorized"] = False
        candidate["writeback_authorized"] = False
        candidate["targeted_eval_required"] = True

    regression = result.get("regression_candidate_handoff")
    if isinstance(regression, dict):
        regression["eligible"] = False
        regression["write_authorized"] = False
        regression["promotion_authorized"] = False
        regression["reason"] = "measurement_contract_mismatch"


def compile_final_delta_learning_evidence(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Compile Final-Delta evidence and fail closed on semantic ruler drift."""

    # The core remains the authority for validating and canonically re-executing
    # both evaluator sources and the Targeted Repair source.
    result = _compile_source_bound_core(raw, project_root=project_root)

    if not isinstance(raw, Mapping):
        return result
    before_raw = raw.get("before_eval_input")
    after_raw = raw.get("after_eval_input")
    if not isinstance(before_raw, Mapping) or not isinstance(after_raw, Mapping):
        # The core already rejects this shape. This branch is only defensive.
        return result

    before_contract = _measurement_contract_projection(before_raw)
    after_contract = _measurement_contract_projection(after_raw)
    mismatch_reasons = _measurement_contract_reasons(before_contract, after_contract)
    matched = not mismatch_reasons
    result["measurement_contract_binding"] = {
        "matched": matched,
        "before_digest": _stable_digest(before_contract),
        "after_digest": _stable_digest(after_contract),
        "comparison_mode_bound": True,
        "expectation_provenance_bound": True,
        "observation_method_bound": True,
        "mismatch_reasons": mismatch_reasons,
    }
    if not matched:
        _remove_repair_attribution(result, mismatch_reasons)
    return result
