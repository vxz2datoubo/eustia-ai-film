"""Evidence-preserving Repair Outcome and Final-Delta compiler.

This module is intentionally non-generative and non-authoritative. It compares
already evaluated before/after outputs, validates the Targeted Repair handoff,
and emits candidate learning evidence without claiming causality, mutating
prompts/canonical state, or promoting maturity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


class FinalDeltaEvidenceError(ValueError):
    """Fail-closed structural or authority error for Final-Delta compilation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


_ALLOWED_EVAL_STATUS = {"PASS", "FAIL", "INCOMPLETE"}
_ALLOWED_OUTCOMES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}
_ALLOWED_CONTROL_STATUS = {"CLEAN", "CONFOUNDED", "UNVERIFIED_CONTROL", "UNCONTROLLED"}
_ALLOWED_SCOPE = {
    "EPISODIC_WORK_ITEM",
    "SCENE_LOCAL",
    "CHARACTER_OR_RELATION",
    "PROJECT_CANONICAL",
    "MODEL_VERSION_BOUND",
    "TRANSFERABLE_METHOD",
}
_ALLOWED_CONFIRMATION = {
    "NOT_CONFIRMED",
    "CONFIRMED_BETTER",
    "CONFIRMED_USE",
    "REJECTED",
    "UNKNOWN",
}
_ALLOWED_PACKAGE_KEYS = {
    "before_eval",
    "after_eval",
    "repair_plan",
    "change_record",
    "learning_context",
}
_ALLOWED_CHANGE_KEYS = {
    "change_id",
    "changed_variables",
    "preserved_variables",
    "revoked_variables",
    "experimental_variables",
    "scope",
    "evidence_refs",
    "user_confirmation_state",
    "rationale",
}
_ALLOWED_LEARNING_CONTEXT_KEYS = {
    "candidate_lesson",
    "inferred_intent",
    "real_goal",
    "value_priority",
    "alternative_explanations",
    "counterfactuals",
    "applicable_context",
    "non_applicable_context",
    "boundaries",
    "failure_conditions",
    "model_or_tool_dependency",
    "user_feedback_refs",
}

STRUCTURAL_GATE_CODES = {
    "FINAL_DELTA_INVALID_SHAPE",
    "FINAL_DELTA_UNKNOWN_FIELD",
    "FINAL_DELTA_SOURCE_EVAL_MISMATCH",
    "FINAL_DELTA_REPAIR_PLAN_MISMATCH",
    "FINAL_DELTA_AUTHORITY_VIOLATION",
    "FINAL_DELTA_CHANGE_RECORD_REQUIRED",
    "FINAL_DELTA_POLICY_INCOMPLETE",
}

_AUTHORITY_FALSE_KEYS = (
    "causal_claim_authorized",
    "prompt_mutation_authorized",
    "generation_authorized",
    "camera_authority_mutation_authorized",
    "canonical_mutation_authorized",
    "learning_writeback_authorized",
    "maturity_promotion_authorized",
)


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{field} must be a mapping"
        )
    return dict(value)


def _string_list(value: Any, *, field: str, required_nonempty: bool = False) -> list[str]:
    if value is None:
        items: list[str] = []
    elif isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        items = [item.strip() for item in value]
    else:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{field} must be a list of non-empty strings"
        )
    if required_nonempty and not items:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_CHANGE_RECORD_REQUIRED", f"{field} cannot be empty"
        )
    if len(items) != len(set(items)):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{field} contains duplicate values"
        )
    return items


def _load_policy(project_root: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(project_root)
    policy_path = root / "10_运行时/final_delta_learning_policy.yaml"
    maturity_path = root / "10_运行时/maturity_model.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    maturity = yaml.safe_load(maturity_path.read_text(encoding="utf-8"))
    if not isinstance(policy, Mapping) or not isinstance(maturity, Mapping):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_POLICY_INCOMPLETE", "policy or maturity model is not a mapping"
        )
    states = set((maturity.get("states") or {}).keys())
    if "candidate" not in states:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_POLICY_INCOMPLETE", "maturity model has no candidate state"
        )
    principles = policy.get("principles") or {}
    required_true = {
        "observation_is_not_causality",
        "single_success_cannot_universalize",
        "explicit_change_record_required",
        "model_version_mismatch_not_aggregated",
        "automatic_maturity_promotion_forbidden",
        "automatic_canonical_writeback_forbidden",
        "automatic_prompt_mutation_forbidden",
    }
    if not all(principles.get(key) is True for key in required_true):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_POLICY_INCOMPLETE", "required safety principles are missing"
        )
    return dict(policy), dict(maturity)


def _validate_eval_result(raw: Any, *, label: str) -> dict[str, Any]:
    value = _mapping(raw, field=label)
    required = {
        "status",
        "eval_id",
        "results",
        "observation_provenance",
        "control_status",
        "controlled_eval",
        "learning_evidence_handoff",
    }
    missing = required - set(value)
    if missing:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{label} missing fields: {sorted(missing)}"
        )
    status = str(value.get("status") or "").strip().upper()
    if status not in _ALLOWED_EVAL_STATUS:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{label}.status is invalid: {status!r}"
        )
    eval_id = str(value.get("eval_id") or "").strip()
    if not eval_id:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{label}.eval_id is empty"
        )
    raw_results = value.get("results")
    if not isinstance(raw_results, list) or not raw_results:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", f"{label}.results must be a non-empty list"
        )
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for index, raw_result in enumerate(raw_results):
        result = _mapping(raw_result, field=f"{label}.results[{index}]")
        field = str(result.get("field") or "").strip()
        outcome = str(result.get("outcome") or "").strip().upper()
        if not field or field in seen:
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_INVALID_SHAPE",
                f"{label} result field is empty or duplicated: {field!r}",
            )
        if outcome not in _ALLOWED_OUTCOMES:
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_INVALID_SHAPE",
                f"{label} result outcome is invalid for {field!r}: {outcome!r}",
            )
        if "expected_value" not in result:
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_INVALID_SHAPE",
                f"{label} result {field!r} has no expected_value",
            )
        result["field"] = field
        result["outcome"] = outcome
        results.append(result)
        seen.add(field)

    control_status = str(value.get("control_status") or "").strip().upper()
    if control_status not in _ALLOWED_CONTROL_STATUS:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE",
            f"{label}.control_status is invalid: {control_status!r}",
        )
    controlled_eval = _mapping(value.get("controlled_eval"), field=f"{label}.controlled_eval")
    provenance = _mapping(
        value.get("observation_provenance"), field=f"{label}.observation_provenance"
    )
    handoff = _mapping(
        value.get("learning_evidence_handoff"), field=f"{label}.learning_evidence_handoff"
    )
    if str(handoff.get("eval_id") or "") != eval_id:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_SOURCE_EVAL_MISMATCH",
            f"{label}.learning_evidence_handoff.eval_id does not match eval_id",
        )
    if handoff.get("maturity_effect") != "none":
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_AUTHORITY_VIOLATION",
            f"{label} learning handoff attempts a maturity effect",
        )
    if handoff.get("promotion_authorized") is not False or handoff.get("writeback_authorized") is not False:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_AUTHORITY_VIOLATION",
            f"{label} learning handoff must not authorize promotion/writeback",
        )
    handoff_control = str(handoff.get("control_status") or "").strip().upper()
    if handoff_control != control_status:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_SOURCE_EVAL_MISMATCH",
            f"{label} learning handoff control status does not match eval result",
        )

    normalized = dict(value)
    normalized["status"] = status
    normalized["eval_id"] = eval_id
    normalized["results"] = results
    normalized["control_status"] = control_status
    normalized["controlled_eval"] = controlled_eval
    normalized["observation_provenance"] = provenance
    normalized["learning_evidence_handoff"] = handoff
    return normalized


def _validate_repair_plan(raw: Any, *, before: Mapping[str, Any]) -> dict[str, Any]:
    plan = _mapping(raw, field="repair_plan")
    if str(plan.get("source_eval_id") or "") != before["eval_id"]:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_REPAIR_PLAN_MISMATCH",
            "repair_plan.source_eval_id must match before_eval.eval_id",
        )
    for key in _AUTHORITY_FALSE_KEYS:
        if plan.get(key) is not False:
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_AUTHORITY_VIOLATION",
                f"repair plan must keep {key}=false",
            )
    raw_items = plan.get("repair_items")
    if not isinstance(raw_items, list):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", "repair_plan.repair_items must be a list"
        )
    actual_fields: list[str] = []
    for index, raw_item in enumerate(raw_items):
        item = _mapping(raw_item, field=f"repair_plan.repair_items[{index}]")
        field = str(item.get("field") or "").strip()
        if not field:
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_INVALID_SHAPE", "repair plan contains an empty field"
            )
        if item.get("creative_mutation_authorized") is not False:
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_AUTHORITY_VIOLATION",
                f"repair item {field!r} authorizes creative mutation",
            )
        actual_fields.append(field)
    if len(actual_fields) != len(set(actual_fields)):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", "repair plan contains duplicate repair fields"
        )

    expected_fields = sorted(
        item["field"] for item in before["results"] if item["outcome"] in {"FAIL", "UNKNOWN"}
    )
    if sorted(actual_fields) != expected_fields:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_REPAIR_PLAN_MISMATCH",
            f"repair fields must exactly match before FAIL/UNKNOWN fields; expected={expected_fields}, actual={sorted(actual_fields)}",
        )
    expected_pass = sorted(
        item["field"] for item in before["results"] if item["outcome"] == "PASS"
    )
    if sorted(plan.get("preserved_pass_fields") or []) != expected_pass:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_REPAIR_PLAN_MISMATCH",
            "repair plan preserved_pass_fields do not match before PASS fields",
        )
    if bool(plan.get("repair_required")) is not bool(expected_fields):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_REPAIR_PLAN_MISMATCH",
            "repair_required does not match before FAIL/UNKNOWN fields",
        )
    if str(plan.get("control_status") or "").strip().upper() != before["control_status"]:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_REPAIR_PLAN_MISMATCH",
            "repair plan control status does not match before evaluation",
        )
    return plan


def _validate_change_record(raw: Any) -> dict[str, Any]:
    change = _mapping(raw, field="change_record")
    unknown = set(change) - _ALLOWED_CHANGE_KEYS
    if unknown:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_UNKNOWN_FIELD", f"unknown change_record fields: {sorted(unknown)}"
        )
    change_id = str(change.get("change_id") or "").strip()
    if not change_id:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_CHANGE_RECORD_REQUIRED", "change_record.change_id is required"
        )
    changed = _string_list(
        change.get("changed_variables"),
        field="change_record.changed_variables",
        required_nonempty=True,
    )
    preserved = _string_list(change.get("preserved_variables"), field="change_record.preserved_variables")
    revoked = _string_list(change.get("revoked_variables"), field="change_record.revoked_variables")
    experimental = _string_list(
        change.get("experimental_variables"), field="change_record.experimental_variables"
    )
    evidence_refs = _string_list(
        change.get("evidence_refs"),
        field="change_record.evidence_refs",
        required_nonempty=True,
    )
    scope = str(change.get("scope") or "").strip().upper()
    if scope not in _ALLOWED_SCOPE:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_CHANGE_RECORD_REQUIRED", f"invalid or missing change scope: {scope!r}"
        )
    confirmation = str(change.get("user_confirmation_state") or "UNKNOWN").strip().upper()
    if confirmation not in _ALLOWED_CONFIRMATION:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE",
            f"invalid user_confirmation_state: {confirmation!r}",
        )
    overlap = (set(changed) & set(preserved)) | (set(changed) & set(revoked)) | (set(preserved) & set(revoked))
    if overlap:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE",
            f"changed/preserved/revoked variables overlap: {sorted(overlap)}",
        )
    normalized = dict(change)
    normalized.update(
        {
            "change_id": change_id,
            "changed_variables": changed,
            "preserved_variables": preserved,
            "revoked_variables": revoked,
            "experimental_variables": experimental,
            "scope": scope,
            "evidence_refs": evidence_refs,
            "user_confirmation_state": confirmation,
        }
    )
    return normalized


def _validate_learning_context(raw: Any) -> dict[str, Any]:
    context = _mapping(raw, field="learning_context")
    unknown = set(context) - _ALLOWED_LEARNING_CONTEXT_KEYS
    if unknown:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_UNKNOWN_FIELD",
            f"unknown learning_context fields: {sorted(unknown)}",
        )
    list_fields = {
        "value_priority",
        "alternative_explanations",
        "counterfactuals",
        "applicable_context",
        "non_applicable_context",
        "boundaries",
        "failure_conditions",
        "user_feedback_refs",
    }
    normalized = dict(context)
    for field in list_fields:
        normalized[field] = _string_list(context.get(field), field=f"learning_context.{field}")
    for field in {
        "candidate_lesson",
        "inferred_intent",
        "real_goal",
        "model_or_tool_dependency",
    }:
        value = context.get(field)
        if value is not None and not isinstance(value, str):
            raise FinalDeltaEvidenceError(
                "FINAL_DELTA_INVALID_SHAPE", f"learning_context.{field} must be a string or null"
            )
        normalized[field] = value.strip() if isinstance(value, str) and value.strip() else None
    return normalized


def _result_map(eval_result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["field"]: dict(item) for item in eval_result["results"]}


def _context_identity(eval_result: Mapping[str, Any]) -> dict[str, Any]:
    handoff = eval_result["learning_evidence_handoff"]
    return {
        "work_item_id": handoff.get("work_item_id"),
        "model": handoff.get("model"),
        "model_version": handoff.get("model_version"),
    }


def _comparability(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    gaps: list[str] = []
    before_identity = _context_identity(before)
    after_identity = _context_identity(after)

    for key in ("work_item_id", "model", "model_version"):
        old = before_identity.get(key)
        new = after_identity.get(key)
        if old and new and old != new:
            reasons.append(f"{key.upper()}_MISMATCH")
        elif not old or not new:
            gaps.append(f"{key.upper()}_MISSING")

    before_map = _result_map(before)
    after_map = _result_map(after)
    if set(before_map) != set(after_map):
        reasons.append("EXPECTATION_FIELD_SET_MISMATCH")
    else:
        changed_expectations = sorted(
            field
            for field in before_map
            if before_map[field].get("expected_value") != after_map[field].get("expected_value")
        )
        if changed_expectations:
            reasons.append(
                "EXPECTED_VALUE_CHANGED:" + ",".join(changed_expectations)
            )

    if reasons:
        return "NOT_COMPARABLE", reasons + gaps
    if gaps:
        return "COMPARABLE_WITH_GAPS", gaps
    return "COMPARABLE", []


def _transition(before_outcome: str, after_outcome: str) -> str:
    table = {
        ("PASS", "PASS"): "PRESERVED",
        ("PASS", "FAIL"): "REGRESSED",
        ("PASS", "UNKNOWN"): "EVIDENCE_LOST",
        ("FAIL", "PASS"): "RESOLVED",
        ("FAIL", "FAIL"): "PERSISTED",
        ("FAIL", "UNKNOWN"): "EVIDENCE_LOST",
        ("UNKNOWN", "PASS"): "EVIDENCE_GAINED_PASS",
        ("UNKNOWN", "FAIL"): "EVIDENCE_GAINED_FAIL",
        ("UNKNOWN", "UNKNOWN"): "UNKNOWN",
        ("NOT_APPLICABLE", "NOT_APPLICABLE"): "NOT_APPLICABLE",
    }
    return table.get((before_outcome, after_outcome), "SCOPE_CHANGED")


def _causal_evidence_status(
    *, before: Mapping[str, Any], after: Mapping[str, Any], change: Mapping[str, Any], comparison_status: str,
    target_transitions: list[dict[str, Any]], regressed_fields: list[str],
) -> tuple[str, bool]:
    if comparison_status == "NOT_COMPARABLE":
        return "NOT_ELIGIBLE_NOT_COMPARABLE", False
    statuses = {before["control_status"], after["control_status"]}
    if "CONFOUNDED" in statuses:
        return "HYPOTHESIS_ONLY_CONFOUNDED", False
    if "UNVERIFIED_CONTROL" in statuses:
        return "CONTROL_NOT_VERIFIED", False
    if "UNCONTROLLED" in statuses:
        return "OBSERVATIONAL_ONLY", False

    before_target = str(before["controlled_eval"].get("target_variable") or "").strip()
    after_target = str(after["controlled_eval"].get("target_variable") or "").strip()
    resolved = any(item["transition"] == "RESOLVED" for item in target_transitions)
    if before_target != after_target or not before_target:
        return "CONTROL_TARGET_MISMATCH", False
    if len(change["changed_variables"]) != 1 or change["changed_variables"][0] != before_target:
        return "CHANGE_RECORD_NOT_SINGLE_TARGET", False
    if regressed_fields:
        return "TARGET_IMPROVED_WITH_REGRESSION", False
    if not resolved:
        return "CONTROLLED_BUT_NO_TARGET_RESOLUTION", False
    return "CONTROLLED_SINGLE_VARIABLE_CANDIDATE", True


def compile_final_delta_learning_evidence(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Compile before/after repair evidence into a non-promoting Final-Delta artifact."""

    if not isinstance(raw, Mapping):
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_INVALID_SHAPE", "Final-Delta package root must be a mapping"
        )
    package = dict(raw)
    unknown = set(package) - _ALLOWED_PACKAGE_KEYS
    if unknown:
        raise FinalDeltaEvidenceError(
            "FINAL_DELTA_UNKNOWN_FIELD", f"unknown Final-Delta package fields: {sorted(unknown)}"
        )
    policy, _ = _load_policy(project_root)
    before = _validate_eval_result(package.get("before_eval"), label="before_eval")
    after = _validate_eval_result(package.get("after_eval"), label="after_eval")
    repair_plan = _validate_repair_plan(package.get("repair_plan"), before=before)
    change = _validate_change_record(package.get("change_record"))
    learning_context = _validate_learning_context(package.get("learning_context"))

    comparison_status, comparison_reasons = _comparability(before, after)
    before_map = _result_map(before)
    after_map = _result_map(after)

    transitions: list[dict[str, Any]] = []
    if comparison_status != "NOT_COMPARABLE":
        for field in sorted(before_map):
            old = before_map[field]
            new = after_map[field]
            transitions.append(
                {
                    "field": field,
                    "before_outcome": old["outcome"],
                    "after_outcome": new["outcome"],
                    "transition": _transition(old["outcome"], new["outcome"]),
                    "before_observed_value": old.get("observed_value"),
                    "after_observed_value": new.get("observed_value"),
                    "before_evidence_refs": list(old.get("evidence_refs") or []),
                    "after_evidence_refs": list(new.get("evidence_refs") or []),
                }
            )

    repair_fields = {item["field"] for item in repair_plan.get("repair_items") or []}
    target_transitions = [item for item in transitions if item["field"] in repair_fields]
    preserved_pass_fields = sorted(
        item["field"] for item in transitions if item["transition"] == "PRESERVED"
    )
    regressed_fields = sorted(
        item["field"] for item in transitions if item["transition"] == "REGRESSED"
    )
    resolved_fields = sorted(
        item["field"] for item in target_transitions if item["transition"] == "RESOLVED"
    )
    persistent_failure_fields = sorted(
        item["field"] for item in target_transitions if item["transition"] in {"PERSISTED", "EVIDENCE_GAINED_FAIL"}
    )
    unresolved_evidence_fields = sorted(
        item["field"] for item in target_transitions if item["transition"] in {"UNKNOWN", "EVIDENCE_LOST"}
    )

    causal_evidence_status, causal_analysis_eligible = _causal_evidence_status(
        before=before,
        after=after,
        change=change,
        comparison_status=comparison_status,
        target_transitions=target_transitions,
        regressed_fields=regressed_fields,
    )

    alternatives = learning_context["alternative_explanations"] or ["UNKNOWN_NOT_SUPPLIED"]
    counterfactuals = learning_context["counterfactuals"] or ["UNKNOWN_NOT_SUPPLIED"]
    candidate_lesson = learning_context.get("candidate_lesson")
    regression_candidate_eligible = bool(
        comparison_status != "NOT_COMPARABLE"
        and resolved_fields
        and not regressed_fields
        and after["status"] in {"PASS", "INCOMPLETE"}
    )

    identity = _context_identity(after)
    return {
        "final_delta_id": f"FINAL_DELTA::{change['change_id']}",
        "source_before_eval_id": before["eval_id"],
        "source_after_eval_id": after["eval_id"],
        "source_repair_plan_id": repair_plan.get("plan_id"),
        "comparison_status": comparison_status,
        "comparison_reasons": comparison_reasons,
        "work_item_id": identity.get("work_item_id") or _context_identity(before).get("work_item_id"),
        "model": identity.get("model") or _context_identity(before).get("model"),
        "model_version": identity.get("model_version") or _context_identity(before).get("model_version"),
        "change_record": change,
        "field_transitions": transitions,
        "repair_outcome": {
            "resolved_fields": resolved_fields,
            "persistent_failure_fields": persistent_failure_fields,
            "unresolved_evidence_fields": unresolved_evidence_fields,
            "preserved_pass_fields": preserved_pass_fields,
            "regressed_fields": regressed_fields,
            "before_observation_provenance": before["observation_provenance"],
            "after_observation_provenance": after["observation_provenance"],
        },
        "causal_evidence": {
            "status": causal_evidence_status,
            "eligible_for_causal_analysis": causal_analysis_eligible,
            "causal_claim_authorized": False,
            "before_control_status": before["control_status"],
            "after_control_status": after["control_status"],
            "before_controlled_eval": before["controlled_eval"],
            "after_controlled_eval": after["controlled_eval"],
            "alternative_explanations": alternatives,
            "counterfactuals": counterfactuals,
        },
        "candidate_learning_evidence": {
            "evidence_id": f"CANDIDATE_LEARNING::{change['change_id']}",
            "maturity": "candidate",
            "maturity_effect": "none",
            "scope": change["scope"],
            "user_confirmation_state": change["user_confirmation_state"],
            "candidate_lesson": candidate_lesson,
            "inferred_intent": learning_context.get("inferred_intent"),
            "real_goal": learning_context.get("real_goal"),
            "value_priority": learning_context["value_priority"],
            "observed_transitions": transitions,
            "changed_variables": change["changed_variables"],
            "preserved_variables": change["preserved_variables"],
            "revoked_variables": change["revoked_variables"],
            "experimental_variables": change["experimental_variables"],
            "evidence_refs": change["evidence_refs"],
            "user_feedback_refs": learning_context["user_feedback_refs"],
            "applicable_context": learning_context["applicable_context"],
            "non_applicable_context": learning_context["non_applicable_context"],
            "boundaries": learning_context["boundaries"],
            "failure_conditions": learning_context["failure_conditions"],
            "model_or_tool_dependency": learning_context.get("model_or_tool_dependency"),
            "alternative_explanations": alternatives,
            "counterfactuals": counterfactuals,
            "causal_evidence_status": causal_evidence_status,
            "generalization_authorized": False,
            "promotion_authorized": False,
            "writeback_authorized": False,
            "targeted_eval_required": True,
        },
        "regression_candidate_handoff": {
            "eligible": regression_candidate_eligible,
            "write_authorized": False,
            "promotion_authorized": False,
            "source_final_delta_id": f"FINAL_DELTA::{change['change_id']}",
            "reason": (
                "resolved_target_without_pass_regression"
                if regression_candidate_eligible
                else "not_yet_eligible"
            ),
        },
        "prompt_mutation_authorized": False,
        "generation_authorized": False,
        "camera_authority_mutation_authorized": False,
        "canonical_mutation_authorized": False,
        "learning_writeback_authorized": False,
        "maturity_promotion_authorized": False,
        "director_method_authority": policy["canonical_authority"]["feedback_learning"],
        "runtime_policy_id": policy["policy_id"],
    }
