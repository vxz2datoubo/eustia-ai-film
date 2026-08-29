"""Deterministic Targeted Repair routing for Expected-vs-Observed results.

This module does not direct a shot, rewrite prompts, trigger generation, mutate
upstream camera authority, or promote learning maturity. It verifies the
evaluator handoff, preserves passing dimensions, and routes failed/unknown
dimensions to existing canonical authority surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


class TargetedRepairPlanError(ValueError):
    """Fail-closed structural or authority error for targeted repair planning."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


_ALLOWED_CONTROL_STATUS = {
    "CLEAN",
    "CONFOUNDED",
    "UNVERIFIED_CONTROL",
    "UNCONTROLLED",
}
_ALLOWED_OUTCOMES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}
_REQUIRED_RESULT_KEYS = {
    "field",
    "outcome",
    "expected_value",
    "observed_value",
    "failure_category",
    "evidence_refs",
}
_REQUIRED_HANDOFF_KEYS = {
    "items",
    "prompt_mutation_authorized",
    "requires_director_or_targeted_repair_step",
}

STRUCTURAL_GATE_CODES = {
    "REPAIR_INVALID_SHAPE",
    "REPAIR_UNKNOWN_FAILURE_CATEGORY",
    "REPAIR_POLICY_INCOMPLETE",
    "REPAIR_HANDOFF_MISMATCH",
    "REPAIR_AUTHORITY_VIOLATION",
    "REPAIR_STATUS_MISMATCH",
}


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TargetedRepairPlanError("REPAIR_INVALID_SHAPE", f"{field} must be a mapping")
    return dict(value)


def _load_policy(project_root: str | Path) -> tuple[dict[str, Any], set[str]]:
    root = Path(project_root)
    policy_path = root / "10_运行时/targeted_repair_policy.yaml"
    schema_path = root / "10_运行时/screen_observable_audible_ir_schema.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))

    routes = dict(policy.get("failure_category_routes") or {})
    surfaces = set((policy.get("repair_surfaces") or {}).keys())
    failure_categories = {
        str(item) for item in ((schema.get("reverse_compiler") or {}).get("failure_categories") or [])
    }
    if not failure_categories:
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE", "canonical reverse-compiler failure vocabulary is empty"
        )
    if set(routes) != failure_categories:
        missing = sorted(failure_categories - set(routes))
        extra = sorted(set(routes) - failure_categories)
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE",
            f"repair routing must cover canonical failure vocabulary exactly; missing={missing}, extra={extra}",
        )
    invalid_surfaces = sorted(set(routes.values()) - surfaces)
    if invalid_surfaces:
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE",
            f"failure routes reference undeclared repair surfaces: {invalid_surfaces}",
        )
    unknown_route = str(policy.get("unknown_outcome_route") or "")
    if not unknown_route or unknown_route not in surfaces:
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE", "unknown outcome route is missing or undeclared"
        )
    return policy, failure_categories


def _normalize_repair_item(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "field": result["field"],
        "outcome": result["outcome"],
        "expected_value": result.get("expected_value"),
        "observed_value": result.get("observed_value"),
        "failure_category": result.get("failure_category"),
        "evidence_refs": list(result.get("evidence_refs") or []),
    }


def _validate_results(raw_results: Any, *, failure_categories: set[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_results, list) or not raw_results:
        raise TargetedRepairPlanError(
            "REPAIR_INVALID_SHAPE", "Expected-vs-Observed results must be a non-empty list"
        )
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_results):
        result = _mapping(raw, field=f"results[{index}]")
        missing = _REQUIRED_RESULT_KEYS - set(result)
        if missing:
            raise TargetedRepairPlanError(
                "REPAIR_INVALID_SHAPE", f"results[{index}] missing fields: {sorted(missing)}"
            )
        field = str(result.get("field") or "").strip()
        outcome = str(result.get("outcome") or "").strip().upper()
        if not field or field in seen:
            raise TargetedRepairPlanError(
                "REPAIR_INVALID_SHAPE", f"result field is empty or duplicated: {field!r}"
            )
        if outcome not in _ALLOWED_OUTCOMES:
            raise TargetedRepairPlanError(
                "REPAIR_INVALID_SHAPE", f"invalid result outcome {outcome!r} for {field!r}"
            )
        evidence_refs = result.get("evidence_refs") or []
        if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
            raise TargetedRepairPlanError(
                "REPAIR_INVALID_SHAPE", f"evidence_refs for {field!r} must be a list of strings"
            )
        category = result.get("failure_category")
        if outcome == "FAIL":
            if not isinstance(category, str) or category not in failure_categories:
                raise TargetedRepairPlanError(
                    "REPAIR_UNKNOWN_FAILURE_CATEGORY",
                    f"failed field {field!r} requires a canonical failure category",
                )
        elif category not in (None, ""):
            raise TargetedRepairPlanError(
                "REPAIR_UNKNOWN_FAILURE_CATEGORY",
                f"non-FAIL field {field!r} cannot carry failure category {category!r}",
            )
        result["field"] = field
        result["outcome"] = outcome
        seen.add(field)
        results.append(result)
    return results


def _validate_eval_status(status: str, results: list[dict[str, Any]]) -> None:
    has_fail = any(item["outcome"] == "FAIL" for item in results)
    has_unknown = any(item["outcome"] == "UNKNOWN" for item in results)
    derived = "FAIL" if has_fail else "INCOMPLETE" if has_unknown else "PASS"
    if status != derived:
        raise TargetedRepairPlanError(
            "REPAIR_STATUS_MISMATCH", f"source eval status {status!r} does not match results-derived {derived!r}"
        )


def plan_targeted_repair(raw_eval_result: Mapping[str, Any], *, project_root: str | Path) -> dict[str, Any]:
    """Validate evaluator output and emit a non-mutating repair-routing plan."""

    if not isinstance(raw_eval_result, Mapping):
        raise TargetedRepairPlanError("REPAIR_INVALID_SHAPE", "evaluation result root must be a mapping")
    raw = dict(raw_eval_result)
    policy, failure_categories = _load_policy(project_root)

    required_root = {
        "status",
        "eval_id",
        "results",
        "observation_provenance",
        "control_status",
        "controlled_eval",
        "targeted_repair_handoff",
    }
    missing_root = required_root - set(raw)
    if missing_root:
        raise TargetedRepairPlanError(
            "REPAIR_INVALID_SHAPE", f"evaluation result missing fields: {sorted(missing_root)}"
        )

    status = str(raw.get("status") or "").strip().upper()
    results = _validate_results(raw.get("results"), failure_categories=failure_categories)
    _validate_eval_status(status, results)

    control_status = str(raw.get("control_status") or "").strip().upper()
    if control_status not in _ALLOWED_CONTROL_STATUS:
        raise TargetedRepairPlanError(
            "REPAIR_INVALID_SHAPE", f"invalid control_status {control_status!r}"
        )
    controlled_eval = _mapping(raw.get("controlled_eval"), field="controlled_eval")
    provenance = _mapping(raw.get("observation_provenance"), field="observation_provenance")

    handoff = _mapping(raw.get("targeted_repair_handoff"), field="targeted_repair_handoff")
    missing_handoff = _REQUIRED_HANDOFF_KEYS - set(handoff)
    if missing_handoff:
        raise TargetedRepairPlanError(
            "REPAIR_INVALID_SHAPE", f"targeted_repair_handoff missing fields: {sorted(missing_handoff)}"
        )
    if handoff.get("prompt_mutation_authorized") is not False:
        raise TargetedRepairPlanError(
            "REPAIR_AUTHORITY_VIOLATION", "Expected-vs-Observed handoff must not authorize prompt mutation"
        )

    derived_handoff_items = [
        _normalize_repair_item(item)
        for item in results
        if item["outcome"] in {"FAIL", "UNKNOWN"}
    ]
    supplied_handoff_items = handoff.get("items")
    if not isinstance(supplied_handoff_items, list):
        raise TargetedRepairPlanError(
            "REPAIR_INVALID_SHAPE", "targeted_repair_handoff.items must be a list"
        )
    if supplied_handoff_items != derived_handoff_items:
        raise TargetedRepairPlanError(
            "REPAIR_HANDOFF_MISMATCH",
            "targeted_repair_handoff does not exactly match FAIL/UNKNOWN source results",
        )
    expected_requires = bool(derived_handoff_items)
    if handoff.get("requires_director_or_targeted_repair_step") is not expected_requires:
        raise TargetedRepairPlanError(
            "REPAIR_HANDOFF_MISMATCH", "repair-required flag does not match source results"
        )

    routes = dict(policy["failure_category_routes"])
    unknown_route = str(policy["unknown_outcome_route"])
    repair_items: list[dict[str, Any]] = []
    for item in results:
        if item["outcome"] == "FAIL":
            surface = routes[item["failure_category"]]
            priority = 1
        elif item["outcome"] == "UNKNOWN":
            surface = unknown_route
            priority = 2
        else:
            continue
        repair_items.append(
            {
                "priority": priority,
                "field": item["field"],
                "outcome": item["outcome"],
                "failure_category": item.get("failure_category"),
                "repair_surface": surface,
                "expected_value": item.get("expected_value"),
                "observed_value": item.get("observed_value"),
                "evidence_refs": list(item.get("evidence_refs") or []),
                "creative_mutation_authorized": False,
            }
        )
    repair_items.sort(key=lambda item: (item["priority"], item["field"]))

    preserved_pass_fields = sorted(
        item["field"] for item in results if item["outcome"] == "PASS"
    )
    not_applicable_fields = sorted(
        item["field"] for item in results if item["outcome"] == "NOT_APPLICABLE"
    )

    causal_status_map = dict(policy.get("control_evidence_status") or {})
    if set(causal_status_map) != _ALLOWED_CONTROL_STATUS:
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE", "control evidence policy must cover all control statuses exactly"
        )

    return {
        "plan_id": f"TARGETED_REPAIR::{raw.get('eval_id')}",
        "source_eval_id": raw.get("eval_id"),
        "source_eval_status": status,
        "repair_required": bool(repair_items),
        "repair_items": repair_items,
        "preserved_pass_fields": preserved_pass_fields,
        "not_applicable_fields": not_applicable_fields,
        "observation_provenance": provenance,
        "control_status": control_status,
        "controlled_eval": controlled_eval,
        "causal_evidence_status": causal_status_map[control_status],
        "causal_claim_authorized": False,
        "prompt_mutation_authorized": False,
        "generation_authorized": False,
        "camera_authority_mutation_authorized": False,
        "canonical_mutation_authorized": False,
        "learning_writeback_authorized": False,
        "maturity_promotion_authorized": False,
        "director_method_authority": policy["canonical_authority"]["director_method"],
        "routing_policy_id": policy["policy_id"],
    }