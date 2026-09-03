"""Source-bound Final-Delta public runtime with comparison trust gates.

The heavy structural/evidence compiler lives in ``_final_delta_core``. This
facade may diagnose a before/after pair, but it may attribute a repair only when
measurement identity, semantic source identity, and real artifact identity are
all trustworthy. The current canonical project has no artifact-to-generation
verifier, so artifact attribution intentionally fails closed rather than turning
caller-provided generation labels into truth.
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

__all__ = ["STRUCTURAL_GATE_CODES", "FinalDeltaEvidenceError", "compile_final_delta_learning_evidence"]

_REQUIRED_PAIR_IDENTITY = ("work_item_id", "model", "model_version", "generation_id")


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _measurement_contract_projection(raw_eval_input: Mapping[str, Any]) -> dict[str, Any]:
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
        # Reviewer/evaluator source is part of the ruler for explicit judgment;
        # changing it can change MATCH/CONTRADICTS even when the other method
        # fields are identical.
        "evidence_source": provenance.get("evidence_source"),
        "inspection_mode": provenance.get("inspection_mode"),
        "temporal_coverage": deepcopy(provenance.get("temporal_coverage")),
        "claimed_frame_by_frame_review": provenance.get("claimed_frame_by_frame_review", False),
    }
    return {
        "expectation_contract": expectations,
        "comparison_modes": comparison_modes,
        "observation_method": observation_method,
    }


def _measurement_contract_reasons(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
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


def _source_pair_identity_reasons(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
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
    result: dict[str, Any], reasons: list[str], *, umbrella_reason: str, handoff_reason: str
) -> None:
    original_transitions = result.get("field_transitions")
    if isinstance(original_transitions, list) and original_transitions:
        result.setdefault("unattributed_transition_candidates", deepcopy(original_transitions))

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
            "resolved_fields", "persistent_failure_fields", "unresolved_evidence_fields",
            "preserved_pass_fields", "regressed_fields",
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
        regression["reason"] = handoff_reason


def _apply_preserved_pass_gate(result: dict[str, Any]) -> None:
    transitions = result.get("field_transitions")
    transition_list = transitions if isinstance(transitions, list) else []
    violated = sorted(
        str(item.get("field"))
        for item in transition_list
        if isinstance(item, Mapping)
        and item.get("before_outcome") == "PASS"
        and item.get("transition") != "PRESERVED"
        and str(item.get("field") or "").strip()
    )
    result["preserved_pass_gate"] = {
        "passed": not violated,
        "violated_prior_pass_fields": violated,
        "rule": "every_prior_PASS_must_remain_PRESERVED",
    }
    outcome = result.get("repair_outcome")
    if isinstance(outcome, dict):
        outcome["violated_prior_pass_fields"] = violated
    if not violated:
        return

    causal = result.get("causal_evidence")
    if isinstance(causal, dict):
        causal["status"] = "TARGET_IMPROVED_WITH_PRIOR_PASS_LOSS"
        causal["eligible_for_causal_analysis"] = False
        causal["causal_claim_authorized"] = False
    candidate = result.get("candidate_learning_evidence")
    if isinstance(candidate, dict):
        candidate["causal_evidence_status"] = "TARGET_IMPROVED_WITH_PRIOR_PASS_LOSS"
        candidate["generalization_authorized"] = False
        candidate["promotion_authorized"] = False
        candidate["writeback_authorized"] = False
        candidate["targeted_eval_required"] = True
    regression = result.get("regression_candidate_handoff")
    if isinstance(regression, dict):
        regression["eligible"] = False
        regression["write_authorized"] = False
        regression["promotion_authorized"] = False
        regression["reason"] = "prior_pass_not_preserved"


def _bind_collision_resistant_ids(
    result: dict[str, Any],
    *,
    before_identity: Mapping[str, Any],
    after_identity: Mapping[str, Any],
) -> None:
    change = result.get("change_record")
    change_id = str((change or {}).get("change_id") or "UNSPECIFIED_CHANGE") if isinstance(change, Mapping) else "UNSPECIFIED_CHANGE"
    source_key = {
        "change_id": change_id,
        "work_item_id": before_identity.get("work_item_id") or after_identity.get("work_item_id"),
        "before_eval_id": result.get("source_before_eval_id"),
        "after_eval_id": result.get("source_after_eval_id"),
        "before_generation_id": before_identity.get("generation_id"),
        "after_generation_id": after_identity.get("generation_id"),
    }
    suffix = _stable_digest(source_key)[:20]
    final_delta_id = f"FINAL_DELTA::{change_id}::{suffix}"
    result["final_delta_id"] = final_delta_id
    candidate = result.get("candidate_learning_evidence")
    if isinstance(candidate, dict):
        candidate["evidence_id"] = f"CANDIDATE_LEARNING::{change_id}::{suffix}"
    regression = result.get("regression_candidate_handoff")
    if isinstance(regression, dict):
        regression["source_final_delta_id"] = final_delta_id
    result["identity_binding"] = {
        "source_pair_included": True,
        "change_id_alone_is_not_identity": True,
        "source_pair_digest": suffix,
    }


def compile_final_delta_learning_evidence(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
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
    result["measurement_contract_binding"] = {
        "matched": not measurement_reasons,
        "before_digest": _stable_digest(before_contract),
        "after_digest": _stable_digest(after_contract),
        "comparison_mode_bound": True,
        "expectation_provenance_bound": True,
        "evidence_source_bound": True,
        "observation_method_bound": True,
        "mismatch_reasons": measurement_reasons,
    }

    before_identity = _source_identity_projection(before_raw)
    after_identity = _source_identity_projection(after_raw)
    identity_reasons = _source_pair_identity_reasons(before_identity, after_identity)
    result["source_pair_identity_binding"] = {
        "matched": not identity_reasons,
        "required_fields": list(_REQUIRED_PAIR_IDENTITY),
        "before": before_identity,
        "after": after_identity,
        "same_work_item_required": True,
        "same_model_required": True,
        "same_model_version_required": True,
        "distinct_generation_label_required": True,
        "generation_label_is_not_artifact_proof": True,
        "mismatch_reasons": identity_reasons,
    }
    _bind_collision_resistant_ids(result, before_identity=before_identity, after_identity=after_identity)

    # Evaluate this before attribution is cleared so diagnostics remember whether
    # any previously passing guarantee was lost, including PASS->NOT_APPLICABLE.
    _apply_preserved_pass_gate(result)

    # Current canonical has no trusted generation-manifest/media-byte verifier.
    # Caller generation_id/media_refs are therefore descriptive metadata only.
    artifact_reasons = ["ARTIFACT_PROVENANCE_UNVERIFIED"]
    result["artifact_provenance_binding"] = {
        "verified": False,
        "status": "UNVERIFIED_NO_CANONICAL_ARTIFACT_VERIFIER",
        "caller_generation_id_authoritative": False,
        "caller_media_refs_authoritative": False,
        "distinct_artifact_attribution_allowed": False,
        "required_future_authority": "canonical_artifact_to_generation_verifier",
    }

    if measurement_reasons:
        _remove_repair_attribution(
            result,
            measurement_reasons,
            umbrella_reason="MEASUREMENT_CONTRACT_MISMATCH",
            handoff_reason="measurement_contract_mismatch",
        )
    elif identity_reasons:
        _remove_repair_attribution(
            result,
            identity_reasons,
            umbrella_reason="SOURCE_PAIR_IDENTITY_MISMATCH",
            handoff_reason="source_pair_identity_mismatch",
        )
    else:
        _remove_repair_attribution(
            result,
            artifact_reasons,
            umbrella_reason="ARTIFACT_PROVENANCE_REQUIRED",
            handoff_reason="artifact_provenance_unverified",
        )
    return result
