"""Post-Final-Delta evidence validation and non-writing proposal compilation.

This runtime does not discover hypotheses, resolve semantic equivalence, promote
maturity, write regressions, or mutate creative/canonical state. It preserves
model/version splits and contradictions so a later governed process can decide.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import yaml


class PostFinalDeltaValidationError(ValueError):
    """Fail-closed validation error for post-Final-Delta evidence processing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


STRUCTURAL_GATE_CODES = {
    "POST_FD_INVALID_SHAPE",
    "POST_FD_UNKNOWN_FIELD",
    "POST_FD_AUTHORITY_VIOLATION",
    "POST_FD_INVALID_FINAL_DELTA",
    "POST_FD_POLICY_INCOMPLETE",
    "POST_FD_UNKNOWN_MATURITY",
}

_ALLOWED_ROOT_KEYS = {"assessment_id", "hypothesis_id", "final_deltas", "requested_maturity"}
_AUTHORITY_FALSE_KEYS = (
    "prompt_mutation_authorized",
    "generation_authorized",
    "camera_authority_mutation_authorized",
    "canonical_mutation_authorized",
    "learning_writeback_authorized",
    "maturity_promotion_authorized",
)


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PostFinalDeltaValidationError("POST_FD_INVALID_SHAPE", f"{field} must be a mapping")
    return dict(value)


def _nonempty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PostFinalDeltaValidationError("POST_FD_INVALID_SHAPE", f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_SHAPE", f"{field} must be a list of non-empty strings"
        )
    items = [item.strip() for item in value]
    if len(items) != len(set(items)):
        raise PostFinalDeltaValidationError("POST_FD_INVALID_SHAPE", f"{field} contains duplicates")
    return items


def _load_policy(project_root: str | Path) -> tuple[dict[str, Any], set[str]]:
    root = Path(project_root)
    policy = yaml.safe_load((root / "10_运行时/post_final_delta_validation_policy.yaml").read_text(encoding="utf-8"))
    maturity = yaml.safe_load((root / "10_运行时/maturity_model.yaml").read_text(encoding="utf-8"))
    if not isinstance(policy, Mapping) or not isinstance(maturity, Mapping):
        raise PostFinalDeltaValidationError("POST_FD_POLICY_INCOMPLETE", "policy or maturity model is invalid")
    principles = policy.get("principles") or {}
    required_true = {
        "explicit_hypothesis_id_required",
        "semantic_auto_clustering_forbidden",
        "exact_candidate_lesson_payload_partitioning",
        "model_version_evidence_partitioning_required",
        "latest_wins_conflict_resolution_forbidden",
        "contradictions_must_remain_visible",
        "regression_proposal_is_not_regression_write",
        "maturity_assessment_is_not_maturity_promotion",
        "maturity_promotion_forbidden",
    }
    if not all(principles.get(key) is True for key in required_true):
        raise PostFinalDeltaValidationError(
            "POST_FD_POLICY_INCOMPLETE", "required safety principles are missing"
        )
    states = set((maturity.get("states") or {}).keys())
    routes = set((policy.get("maturity_routes") or {}).keys())
    if states != routes:
        raise PostFinalDeltaValidationError(
            "POST_FD_POLICY_INCOMPLETE",
            f"maturity routes must cover canonical states exactly; missing={sorted(states-routes)}, extra={sorted(routes-states)}",
        )
    return dict(policy), states


def _validate_final_delta(raw: Any, *, index: int) -> dict[str, Any]:
    delta = _mapping(raw, field=f"final_deltas[{index}]")
    required = {
        "final_delta_id",
        "comparison_status",
        "work_item_id",
        "model",
        "model_version",
        "change_record",
        "field_transitions",
        "repair_outcome",
        "causal_evidence",
        "candidate_learning_evidence",
        "regression_candidate_handoff",
        "runtime_policy_id",
    } | set(_AUTHORITY_FALSE_KEYS)
    missing = required - set(delta)
    if missing:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", f"final_deltas[{index}] missing fields: {sorted(missing)}"
        )
    for key in _AUTHORITY_FALSE_KEYS:
        if delta.get(key) is not False:
            raise PostFinalDeltaValidationError(
                "POST_FD_AUTHORITY_VIOLATION", f"final_deltas[{index}] must keep {key}=false"
            )

    final_delta_id = _nonempty_string(delta.get("final_delta_id"), field=f"final_deltas[{index}].final_delta_id")
    comparison_status = str(delta.get("comparison_status") or "").strip().upper()
    if comparison_status not in {"COMPARABLE", "COMPARABLE_WITH_GAPS", "NOT_COMPARABLE"}:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", f"invalid comparison_status {comparison_status!r}"
        )

    change = _mapping(delta.get("change_record"), field=f"final_deltas[{index}].change_record")
    evidence_refs = _string_list(change.get("evidence_refs"), field=f"final_deltas[{index}].change_record.evidence_refs")
    if not evidence_refs:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", "Final-Delta change_record must retain evidence_refs"
        )

    transitions_raw = delta.get("field_transitions")
    if not isinstance(transitions_raw, list):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", "field_transitions must be a list"
        )
    transitions: list[dict[str, Any]] = []
    seen_fields: set[str] = set()
    for pos, raw_transition in enumerate(transitions_raw):
        transition = _mapping(raw_transition, field=f"final_deltas[{index}].field_transitions[{pos}]")
        field = _nonempty_string(transition.get("field"), field="field transition field")
        if field in seen_fields:
            raise PostFinalDeltaValidationError(
                "POST_FD_INVALID_FINAL_DELTA", f"duplicate transition field {field!r}"
            )
        state = _nonempty_string(transition.get("transition"), field=f"transition state for {field}")
        transition["field"] = field
        transition["transition"] = state
        transitions.append(transition)
        seen_fields.add(field)

    outcome = _mapping(delta.get("repair_outcome"), field=f"final_deltas[{index}].repair_outcome")
    resolved = _string_list(outcome.get("resolved_fields"), field="repair_outcome.resolved_fields")
    persistent = _string_list(outcome.get("persistent_failure_fields"), field="repair_outcome.persistent_failure_fields")
    unresolved = _string_list(outcome.get("unresolved_evidence_fields"), field="repair_outcome.unresolved_evidence_fields")
    preserved = _string_list(outcome.get("preserved_pass_fields"), field="repair_outcome.preserved_pass_fields")
    regressed = _string_list(outcome.get("regressed_fields"), field="repair_outcome.regressed_fields")

    candidate = _mapping(
        delta.get("candidate_learning_evidence"), field=f"final_deltas[{index}].candidate_learning_evidence"
    )
    if candidate.get("maturity") != "candidate" or candidate.get("maturity_effect") != "none":
        raise PostFinalDeltaValidationError(
            "POST_FD_AUTHORITY_VIOLATION", "post-Final-Delta input must remain candidate with no maturity effect"
        )
    for key in ("generalization_authorized", "promotion_authorized", "writeback_authorized"):
        if candidate.get(key) is not False:
            raise PostFinalDeltaValidationError(
                "POST_FD_AUTHORITY_VIOLATION", f"candidate learning evidence must keep {key}=false"
            )
    if candidate.get("targeted_eval_required") is not True:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", "candidate learning evidence must retain targeted_eval_required=true"
        )
    _nonempty_string(candidate.get("evidence_id"), field="candidate_learning_evidence.evidence_id")
    lesson = candidate.get("candidate_lesson")
    if lesson is not None and (not isinstance(lesson, str) or not lesson.strip()):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", "candidate_lesson must be a non-empty string or null"
        )
    if isinstance(lesson, str):
        lesson = lesson.strip()
        candidate["candidate_lesson"] = lesson

    causal = _mapping(delta.get("causal_evidence"), field=f"final_deltas[{index}].causal_evidence")
    if causal.get("causal_claim_authorized") is not False:
        raise PostFinalDeltaValidationError(
            "POST_FD_AUTHORITY_VIOLATION", "causal claim authority cannot enter post-Final-Delta validation"
        )
    causal_status = _nonempty_string(causal.get("status"), field="causal_evidence.status")
    if candidate.get("causal_evidence_status") != causal_status:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", "candidate learning causal status must match Final-Delta causal status"
        )

    regression = _mapping(
        delta.get("regression_candidate_handoff"), field=f"final_deltas[{index}].regression_candidate_handoff"
    )
    if regression.get("write_authorized") is not False or regression.get("promotion_authorized") is not False:
        raise PostFinalDeltaValidationError(
            "POST_FD_AUTHORITY_VIOLATION", "regression candidate handoff must not authorize write/promotion"
        )
    if str(regression.get("source_final_delta_id") or "") != final_delta_id:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_FINAL_DELTA", "regression candidate source_final_delta_id mismatch"
        )

    normalized = dict(delta)
    normalized["final_delta_id"] = final_delta_id
    normalized["comparison_status"] = comparison_status
    normalized["change_record"] = change
    normalized["field_transitions"] = transitions
    normalized["repair_outcome"] = {
        **outcome,
        "resolved_fields": resolved,
        "persistent_failure_fields": persistent,
        "unresolved_evidence_fields": unresolved,
        "preserved_pass_fields": preserved,
        "regressed_fields": regressed,
    }
    normalized["candidate_learning_evidence"] = candidate
    normalized["causal_evidence"] = causal
    normalized["regression_candidate_handoff"] = regression
    return normalized


def _classification(delta: Mapping[str, Any]) -> str:
    outcome = delta["repair_outcome"]
    if delta["comparison_status"] == "NOT_COMPARABLE":
        return "INCONCLUSIVE"
    if outcome["regressed_fields"] or outcome["persistent_failure_fields"]:
        return "CONTRADICTORY"
    if outcome["resolved_fields"]:
        return "SUPPORTING"
    return "INCONCLUSIVE"


def _cohort_key(delta: Mapping[str, Any]) -> tuple[str, str, str]:
    model = str(delta.get("model") or "UNKNOWN_MODEL")
    version = str(delta.get("model_version") or "UNKNOWN_VERSION")
    lesson = delta["candidate_learning_evidence"].get("candidate_lesson") or "UNKNOWN_LESSON_PAYLOAD"
    return model, version, lesson


def _evidence_refs(delta: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    refs.extend(delta["change_record"].get("evidence_refs") or [])
    for transition in delta["field_transitions"]:
        refs.extend(transition.get("before_evidence_refs") or [])
        refs.extend(transition.get("after_evidence_refs") or [])
    return sorted(set(str(item) for item in refs if isinstance(item, str) and item.strip()))


def _regression_proposal(delta: Mapping[str, Any], classification: str) -> dict[str, Any] | None:
    handoff = delta["regression_candidate_handoff"]
    if handoff.get("eligible") is not True or classification != "SUPPORTING":
        return None
    resolved = set(delta["repair_outcome"]["resolved_fields"])
    target_transitions = [
        transition for transition in delta["field_transitions"] if transition["field"] in resolved
    ]
    if not target_transitions:
        return None
    return {
        "proposal_id": f"REGRESSION_PROPOSAL::{delta['final_delta_id']}",
        "status": "candidate",
        "source_final_delta_id": delta["final_delta_id"],
        "work_item_id": delta.get("work_item_id"),
        "model": delta.get("model"),
        "model_version": delta.get("model_version"),
        "scope": delta["candidate_learning_evidence"].get("scope"),
        "candidate_lesson": delta["candidate_learning_evidence"].get("candidate_lesson"),
        "resolved_target_transitions": target_transitions,
        "protected_pass_fields": list(delta["repair_outcome"]["preserved_pass_fields"]),
        "evidence_refs": _evidence_refs(delta),
        "canonical_write_target": None,
        "write_authorized": False,
        "promotion_authorized": False,
        "human_or_governed_review_required": True,
    }


def _maturity_assessment(
    *, requested_maturity: str | None, states: set[str], policy: Mapping[str, Any],
    evidence_rows: list[dict[str, Any]], conflict_present: bool,
) -> dict[str, Any]:
    if requested_maturity is None:
        return {
            "requested_maturity": None,
            "route": "NO_PROMOTION_REQUESTED",
            "promotion_authorized": False,
            "trusted_confirmation_binding_present": False,
        }
    if requested_maturity not in states:
        raise PostFinalDeltaValidationError(
            "POST_FD_UNKNOWN_MATURITY", f"requested maturity is not canonical: {requested_maturity!r}"
        )
    supporting = [row for row in evidence_rows if row["classification"] == "SUPPORTING"]
    if conflict_present and requested_maturity in {"scene_verified", "project_verified", "general_stable"}:
        route = "CONFLICT_REQUIRES_ADJUDICATION"
    elif requested_maturity == "scene_verified" and not supporting:
        route = "INSUFFICIENT_SUPPORT_FOR_SCENE_VERIFICATION"
    else:
        route = policy["maturity_routes"][requested_maturity]
    return {
        "requested_maturity": requested_maturity,
        "route": route,
        "supporting_evidence_present": bool(supporting),
        "trusted_confirmation_binding_present": False,
        "promotion_authorized": False,
        "automatic_writeback_authorized": False,
        "note": (
            "caller-supplied confirmation claims are evidence only; this runtime cannot mint trusted user/canonical confirmation"
            if requested_maturity == "scene_verified"
            else "high-impact or special-state transitions remain governed outside this runtime"
        ),
    }


def assess_post_final_delta_validation(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Partition Final-Delta evidence and emit non-writing validation proposals."""

    if not isinstance(raw, Mapping):
        raise PostFinalDeltaValidationError("POST_FD_INVALID_SHAPE", "assessment root must be a mapping")
    payload = dict(raw)
    unknown = set(payload) - _ALLOWED_ROOT_KEYS
    if unknown:
        raise PostFinalDeltaValidationError(
            "POST_FD_UNKNOWN_FIELD", f"unknown assessment fields: {sorted(unknown)}"
        )
    policy, states = _load_policy(project_root)
    assessment_id = _nonempty_string(payload.get("assessment_id"), field="assessment_id")
    hypothesis_id = _nonempty_string(payload.get("hypothesis_id"), field="hypothesis_id")
    requested_raw = payload.get("requested_maturity")
    requested_maturity = None if requested_raw in (None, "") else str(requested_raw).strip()

    raw_deltas = payload.get("final_deltas")
    if not isinstance(raw_deltas, list) or not raw_deltas:
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_SHAPE", "final_deltas must be a non-empty list"
        )
    deltas = [_validate_final_delta(item, index=index) for index, item in enumerate(raw_deltas)]
    ids = [item["final_delta_id"] for item in deltas]
    if len(ids) != len(set(ids)):
        raise PostFinalDeltaValidationError(
            "POST_FD_INVALID_SHAPE", "final_deltas contains duplicate final_delta_id values"
        )

    evidence_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    proposals: list[dict[str, Any]] = []
    for delta in deltas:
        classification = _classification(delta)
        key = _cohort_key(delta)
        row = {
            "final_delta_id": delta["final_delta_id"],
            "classification": classification,
            "cohort_model": key[0],
            "cohort_model_version": key[1],
            "exact_candidate_lesson_payload": key[2],
            "work_item_id": delta.get("work_item_id"),
            "causal_evidence_status": delta["causal_evidence"].get("status"),
            "user_confirmation_state": delta["candidate_learning_evidence"].get("user_confirmation_state"),
            "resolved_fields": list(delta["repair_outcome"]["resolved_fields"]),
            "persistent_failure_fields": list(delta["repair_outcome"]["persistent_failure_fields"]),
            "regressed_fields": list(delta["repair_outcome"]["regressed_fields"]),
            "evidence_refs": _evidence_refs(delta),
        }
        evidence_rows.append(row)
        grouped[key].append(row)
        proposal = _regression_proposal(delta, classification)
        if proposal is not None:
            proposals.append(proposal)

    cohorts: list[dict[str, Any]] = []
    conflict_present = False
    for key in sorted(grouped):
        rows = grouped[key]
        classes = {row["classification"] for row in rows}
        cohort_conflict = "SUPPORTING" in classes and "CONTRADICTORY" in classes
        conflict_present = conflict_present or cohort_conflict
        cohorts.append(
            {
                "model": key[0],
                "model_version": key[1],
                "exact_candidate_lesson_payload": key[2],
                "evidence_count": len(rows),
                "supporting_count": sum(row["classification"] == "SUPPORTING" for row in rows),
                "contradictory_count": sum(row["classification"] == "CONTRADICTORY" for row in rows),
                "inconclusive_count": sum(row["classification"] == "INCONCLUSIVE" for row in rows),
                "distinct_work_items": sorted(
                    {str(row["work_item_id"]) for row in rows if row.get("work_item_id")}
                ),
                "conflict_present": cohort_conflict,
                "source_final_delta_ids": [row["final_delta_id"] for row in rows],
            }
        )

    maturity = _maturity_assessment(
        requested_maturity=requested_maturity,
        states=states,
        policy=policy,
        evidence_rows=evidence_rows,
        conflict_present=conflict_present,
    )
    model_version_pairs = sorted({(row["cohort_model"], row["cohort_model_version"]) for row in evidence_rows})
    exact_lessons = sorted({row["exact_candidate_lesson_payload"] for row in evidence_rows})

    return {
        "assessment_id": assessment_id,
        "hypothesis_id": hypothesis_id,
        "evidence_rows": evidence_rows,
        "cohorts": cohorts,
        "model_version_partition_count": len(model_version_pairs),
        "cross_model_or_version_split_present": len(model_version_pairs) > 1,
        "exact_lesson_payload_count": len(exact_lessons),
        "semantic_auto_clustering_performed": False,
        "conflict_present": conflict_present,
        "latest_wins_resolution_performed": False,
        "regression_proposals": proposals,
        "maturity_assessment": maturity,
        "prompt_mutation_authorized": False,
        "generation_authorized": False,
        "camera_authority_mutation_authorized": False,
        "canonical_mutation_authorized": False,
        "learning_writeback_authorized": False,
        "regression_write_authorized": False,
        "maturity_promotion_authorized": False,
        "causal_claim_authorized": False,
        "policy_id": policy["policy_id"],
        "feedback_learning_authority": policy["canonical_authority"]["feedback_learning"],
        "maturity_authority": policy["canonical_authority"]["maturity_model"],
    }
