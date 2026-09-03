"""Source-bound Final-Delta public runtime with comparison trust gates.

The heavy structural/evidence compiler lives in ``_final_delta_core``. This
public module adds fail-closed boundaries before its output may be interpreted
as a repair trajectory:

1. before/after must use the same semantic measurement ruler;
2. comparison identity must be complete for work item, model and model version;
3. before/after must identify two distinct generated artifacts via generation_id;
4. a prior PASS losing evidence blocks regression/Golden eligibility just like a
   direct PASS regression, while preserving the diagnostic transition.

The underlying sources are still canonically re-executed by the core compiler.
This facade does not evaluate media, mint observations, or become a learning
or repair authority.
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

_REQUIRED_PAIR_IDENTITY = ("work_item_id", "model", "model_version", "generation_id")


def _stable_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _measurement_contract_projection(raw_eval_input: Mapping[str, Any]) -> dict[str, Any]:
    """Project only semantics capable of changing how PASS/FAIL is measured."""

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


def _source_identity_projection(raw_eval_input: Mapping[str, Any]) -> dict[str, str | None]:
    context_raw = raw_eval_input.get("context")
    context = dict(context_raw) if isinstance(context_raw, Mapping) else {}
    result: dict[str, str | None] = {}
    for field in _REQUIRED_PAIR_IDENTITY:
        value = context.get(field)
        normalized = str(value).strip() if value is not None else ""
        result[field] = normalized or None
    return result


def _source_pair_identity_reasons(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> list[str]:
    reasons: list[str] = []
    for side, identity in (("BEFORE", before), ("AFTER", after)):
        for field in _REQUIRED_PAIR_IDENTITY:
            if not identity.get(field):
                reasons.append(f"{side}_{field.upper()}_MISSING")

    for field in ("work_item_id", "model", "model_version"):
        old, new = before.get(field), after.get(field)
        if old and new and old != new:
            reasons.append(f"{field.upper()}_MISMATCH")

    before_generation = before.get("generation_id")
    after_generation = after.get("generation_id")
    if before_generation and after_generation and before_generation == after_generation:
        reasons.append("SOURCE_ARTIFACT_IDENTITY_COLLISION")
    return reasons


def _remove_repair_attribution(
    result: dict[str, Any],
    reasons: list[str],
    *,
    umbrella_reason: str,
    handoff_reason: str,
) -> None:
    comparison_reasons = list(result.get("comparison_reasons") or [])
    for reason in [umbrella_reason, *reasons]:
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
        outcome["lost_pass_evidence_fields"] = []

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
        regression["reason"] = handoff_reason


def _apply_preserved_pass_gate(result: dict[str, Any]) -> None:
    transitions = result.get("field_transitions")
    transition_list = transitions if isinstance(transitions, list) else []
    lost_pass = sorted(
        str(item.get("field"))
        for item in transition_list
        if isinstance(item, Mapping)
        and item.get("before_outcome") == "PASS"
        and item.get("transition") == "EVIDENCE_LOST"
        and str(item.get("field") or "").strip()
    )
    result["preserved_pass_gate"] = {
        "passed": not lost_pass,
        "lost_pass_evidence_fields": lost_pass,
        "pass_to_fail_and_pass_to_unknown_both_block_candidates": True,
    }
    outcome = result.get("repair_outcome")
    if isinstance(outcome, dict):
        outcome["lost_pass_evidence_fields"] = lost_pass
    if not lost_pass:
        return

    causal = result.get("causal_evidence")
    if isinstance(causal, dict):
        causal["status"] = "TARGET_IMPROVED_WITH_EVIDENCE_LOSS"
        causal["eligible_for_causal_analysis"] = False
        causal["causal_claim_authorized"] = False

    candidate = result.get("candidate_learning_evidence")
    if isinstance(candidate, dict):
        candidate["causal_evidence_status"] = "TARGET_IMPROVED_WITH_EVIDENCE_LOSS"
        candidate["generalization_authorized"] = False
        candidate["promotion_authorized"] = False
        candidate["writeback_authorized"] = False
        candidate["targeted_eval_required"] = True

    regression = result.get("regression_candidate_handoff")
    if isinstance(regression, dict):
        regression["eligible"] = False
        regression["write_authorized"] = False
        regression["promotion_authorized"] = False
        regression["reason"] = "prior_pass_evidence_lost"


def compile_final_delta_learning_evidence(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Compile Final-Delta evidence and fail closed on comparison trust drift."""

    result = _compile_source_bound_core(raw, project_root=project_root)

    if not isinstance(raw, Mapping):
        return result
    before_raw = raw.get("before_eval_input")
    after_raw = raw.get("after_eval_input")
    if not isinstance(before_raw, Mapping) or not isinstance(after_raw, Mapping):
        return result

    before_contract = _measurement_contract_projection(before_raw)
    after_contract = _measurement_contract_projection(after_raw)
    measurement_reasons = _measurement_contract_reasons(before_contract, after_contract)
    measurement_matched = not measurement_reasons
    result["measurement_contract_binding"] = {
        "matched": measurement_matched,
        "before_digest": _stable_digest(before_contract),
        "after_digest": _stable_digest(after_contract),
        "comparison_mode_bound": True,
        "expectation_provenance_bound": True,
        "observation_method_bound": True,
        "mismatch_reasons": measurement_reasons,
    }

    before_identity = _source_identity_projection(before_raw)
    after_identity = _source_identity_projection(after_raw)
    identity_reasons = _source_pair_identity_reasons(before_identity, after_identity)
    identity_matched = not identity_reasons
    result["source_pair_identity_binding"] = {
        "matched": identity_matched,
        "required_fields": list(_REQUIRED_PAIR_IDENTITY),
        "before": before_identity,
        "after": after_identity,
        "same_work_item_required": True,
        "same_model_required": True,
        "same_model_version_required": True,
        "distinct_generation_id_required": True,
        "mismatch_reasons": identity_reasons,
    }

    if not measurement_matched:
        _remove_repair_attribution(
            result,
            measurement_reasons,
            umbrella_reason="MEASUREMENT_CONTRACT_MISMATCH",
            handoff_reason="measurement_contract_mismatch",
        )
    elif not identity_matched:
        _remove_repair_attribution(
            result,
            identity_reasons,
            umbrella_reason="SOURCE_PAIR_IDENTITY_MISMATCH",
            handoff_reason="source_pair_identity_mismatch",
        )

    _apply_preserved_pass_gate(result)
    return result
