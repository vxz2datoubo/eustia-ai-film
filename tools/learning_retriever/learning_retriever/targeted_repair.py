"""Deterministic Targeted Repair routing from Expected-vs-Observed source input.

This module does not direct a shot, rewrite prompts, trigger generation, mutate
upstream camera authority, or promote learning maturity. Public planning never
accepts a serialized evaluator result as authority. It re-executes the canonical
Expected-vs-Observed evaluator from its source payload, then verifies the
in-memory evaluator handoff, preserves passing dimensions, and routes
failed/unknown dimensions to existing canonical authority surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from .expected_observed import ExpectedObservedEvalError, evaluate_expected_vs_observed


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
    "REPAIR_UPSTREAM_EVAL_REJECTED",
    "REPAIR_UNKNOWN_FAILURE_CATEGORY",
    "REPAIR_POLICY_INCOMPLETE",
    "REPAIR_HANDOFF_MISMATCH",
    "REPAIR_AUTHORITY_VIOLATION",
    "REPAIR_STATUS_MISMATCH",
    "REPAIR_CONTROL_PROJECTION_MISMATCH",
}


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TargetedRepairPlanError("REPAIR_INVALID_SHAPE", f"{field} must be a mapping")
    return dict(value)


def _load_policy(project_root: str | Path) -> tuple[dict[str, Any], set[str], list[str]]:
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
    control_requirements = [
        str(item).strip()
        for item in ((schema.get("validation") or {}).get("controlled_eval_requirements") or [])
        if str(item).strip()
    ]
    if not failure_categories:
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE", "canonical reverse-compiler failure vocabulary is empty"
        )
    if not control_requirements:
        raise TargetedRepairPlanError(
            "REPAIR_POLICY_INCOMPLETE", "canonical SOAC controlled-eval requirements are empty"
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
    return policy, failure_categories, control_requirements


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


def _validate_control_projection(
    control_status: str,
    controlled_eval: Mapping[str, Any],
    *,
    canonical_requirements: list[str],
) -> None:
    """Validate upstream control truth without allowing a serialized trust upgrade.

    Current canonical Expected-vs-Observed has no mechanically trusted control
    verifier. Therefore the evaluator may preserve a caller declaration and
    evidence references, but it cannot legitimately emit CLEAN or
    ``non_target_controls_verified=true``. A future canonical verifier must
    introduce a separately reviewed machine trust binding before this gate can be
    expanded.
    """

    target_variable = str(controlled_eval.get("target_variable") or "").strip()
    confounds = controlled_eval.get("confounds") or []
    if not isinstance(confounds, list) or not all(isinstance(item, str) for item in confounds):
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH", "controlled_eval.confounds is not normalized"
        )
    controls_verified = controlled_eval.get("non_target_controls_verified", False)
    if not isinstance(controls_verified, bool):
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH", "non_target_controls_verified is not boolean"
        )
    caller_claim = controlled_eval.get("caller_claimed_non_target_controls_verified", False)
    if not isinstance(caller_claim, bool):
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH", "caller control-verification claim is not boolean"
        )
    verification_state = str(controlled_eval.get("control_verification_state") or "").strip().upper()
    if verification_state not in {"NOT_VERIFIED", "DECLARED_BY_CALLER"}:
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH",
            "current canonical evaluator exposes no trusted control-verification state",
        )
    if verification_state == "DECLARED_BY_CALLER" and not caller_claim:
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH", "declared-by-caller state requires the caller claim to be preserved"
        )
    if verification_state == "NOT_VERIFIED" and caller_claim:
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH", "caller claim and verification state disagree"
        )

    projected_requirements = controlled_eval.get("canonical_control_requirements")
    if not isinstance(projected_requirements, list) or projected_requirements != canonical_requirements:
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH",
            "controlled_eval canonical requirement projection does not match current SOAC authority",
        )

    provenance_raw = controlled_eval.get("control_provenance")
    provenance = dict(provenance_raw) if isinstance(provenance_raw, Mapping) else None
    if provenance is not None:
        provenance_state = str(provenance.get("verification_state") or "").strip().upper()
        if provenance_state and provenance_state != "DECLARED_BY_CALLER":
            raise TargetedRepairPlanError(
                "REPAIR_CONTROL_PROJECTION_MISMATCH", "control provenance claims an unsupported trusted state"
            )
        covered = provenance.get("canonical_requirements_covered")
        if covered is not None and (
            not isinstance(covered, list) or not set(covered).issubset(set(canonical_requirements))
        ):
            raise TargetedRepairPlanError(
                "REPAIR_CONTROL_PROJECTION_MISMATCH", "control coverage contains non-canonical requirements"
            )

    if controls_verified or control_status == "CLEAN":
        raise TargetedRepairPlanError(
            "REPAIR_CONTROL_PROJECTION_MISMATCH",
            "CLEAN/verified controls are not mintable by the current canonical evaluator contract",
        )

    if control_status == "CONFOUNDED":
        if not confounds:
            raise TargetedRepairPlanError(
                "REPAIR_CONTROL_PROJECTION_MISMATCH", "CONFOUNDED status requires explicit confounds"
            )
    elif control_status == "UNVERIFIED_CONTROL":
        if not target_variable:
            raise TargetedRepairPlanError(
                "REPAIR_CONTROL_PROJECTION_MISMATCH", "UNVERIFIED_CONTROL requires a target variable"
            )
        if confounds:
            raise TargetedRepairPlanError(
                "REPAIR_CONTROL_PROJECTION_MISMATCH", "UNVERIFIED_CONTROL cannot hide explicit confounds"
            )
    elif control_status == "UNCONTROLLED":
        if target_variable or confounds:
            raise TargetedRepairPlanError(
                "REPAIR_CONTROL_PROJECTION_MISMATCH", "UNCONTROLLED projection is inconsistent"
            )


def plan_targeted_repair(raw_eval_input: Mapping[str, Any], *, project_root: str | Path) -> dict[str, Any]:
    """Re-execute canonical Expected-vs-Observed and emit a non-mutating repair plan.

    ``raw_eval_input`` is the source evaluator payload, not a serialized evaluator
    output. This is the planner's source-authentic choke point: caller-provided
    result/handoff/status projections are never accepted as upstream truth.
    """

    if not isinstance(raw_eval_input, Mapping):
        raise TargetedRepairPlanError("REPAIR_INVALID_SHAPE", "evaluation source input root must be a mapping")

    try:
        evaluated = evaluate_expected_vs_observed(raw_eval_input, project_root=project_root)
    except ExpectedObservedEvalError as exc:
        raise TargetedRepairPlanError(
            "REPAIR_UPSTREAM_EVAL_REJECTED",
            f"canonical Expected-vs-Observed rejected source input: {exc.code}: {exc.message}",
        ) from exc

    raw = dict(evaluated)
    policy, failure_categories, canonical_control_requirements = _load_policy(project_root)

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
            "REPAIR_INVALID_SHAPE", f"canonical evaluator result missing fields: {sorted(missing_root)}"
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
    _validate_control_projection(
        control_status,
        controlled_eval,
        canonical_requirements=canonical_control_requirements,
    )
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
            "canonical evaluator handoff does not exactly match FAIL/UNKNOWN source results",
        )
    expected_requires = bool(derived_handoff_items)
    if handoff.get("requires_director_or_targeted_repair_step") is not expected_requires:
        raise TargetedRepairPlanError(
            "REPAIR_HANDOFF_MISMATCH", "repair-required flag does not match canonical evaluator results"
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
        "source_binding": {
            "mode": "canonical_expected_observed_reexecution",
            "evaluator_runtime": "expected_observed.evaluate_expected_vs_observed",
            "serialized_eval_result_accepted": False,
        },
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
