"""Source-bound orchestration for the evidence-driven continual-learning runtime.

Every trust-bearing stage re-executes from original source payloads. Serialized
Expected-vs-Observed results, repair plans, Final-Delta results, and prior
Final-Delta records are not accepted as public upstream truth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from .expected_observed import ExpectedObservedEvalError, evaluate_expected_vs_observed
from .final_delta import FinalDeltaEvidenceError, compile_final_delta_learning_evidence
from .post_final_delta import PostFinalDeltaValidationError
from .post_final_delta_source_bound import assess_source_bound_post_final_delta
from .targeted_repair import TargetedRepairPlanError, plan_targeted_repair


class LearningEvidencePipelineError(ValueError):
    def __init__(self, code: str, message: str, *, stage: str, underlying_code: str | None = None, completed_stages: list[str] | None = None) -> None:
        super().__init__(f"{code}: {stage}: {message}")
        self.code = code
        self.message = message
        self.stage = stage
        self.underlying_code = underlying_code
        self.completed_stages = list(completed_stages or [])

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "STRUCTURAL_REJECT",
            "code": self.code,
            "stage": self.stage,
            "underlying_code": self.underlying_code,
            "message": self.message,
            "completed_stages": list(self.completed_stages),
        }


PIPELINE_STAGE_ORDER = (
    "BEFORE_EXPECTED_OBSERVED",
    "TARGETED_REPAIR",
    "AFTER_EXPECTED_OBSERVED",
    "FINAL_DELTA",
    "POST_FINAL_DELTA",
)

_ALLOWED_ROOT_KEYS = {
    "pipeline_id",
    "hypothesis_id",
    "before_eval_payload",
    "after_eval_payload",
    "change_record",
    "learning_context",
    "requested_maturity",
    "prior_final_delta_inputs",
}

_STAGE_ERRORS = (
    ExpectedObservedEvalError,
    TargetedRepairPlanError,
    FinalDeltaEvidenceError,
    PostFinalDeltaValidationError,
)


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LearningEvidencePipelineError("LEARNING_PIPELINE_INVALID_SHAPE", f"{field} must be a mapping", stage="ORCHESTRATOR_INPUT")
    return dict(value)


def _nonempty(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LearningEvidencePipelineError("LEARNING_PIPELINE_INVALID_SHAPE", f"{field} must be a non-empty string", stage="ORCHESTRATOR_INPUT")
    return value.strip()


def _run_stage(stage: str, completed: list[str], operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        result = operation()
    except _STAGE_ERRORS as exc:
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_STAGE_FAILED",
            getattr(exc, "message", str(exc)),
            stage=stage,
            underlying_code=getattr(exc, "code", exc.__class__.__name__),
            completed_stages=completed,
        ) from exc
    completed.append(stage)
    return result


def _validate_root(raw: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(raw, field="pipeline")
    unknown = set(payload) - _ALLOWED_ROOT_KEYS
    if unknown:
        raise LearningEvidencePipelineError("LEARNING_PIPELINE_UNKNOWN_FIELD", f"unknown pipeline fields: {sorted(unknown)}", stage="ORCHESTRATOR_INPUT")
    for required in ("pipeline_id", "hypothesis_id", "before_eval_payload", "after_eval_payload", "change_record"):
        if required not in payload:
            raise LearningEvidencePipelineError("LEARNING_PIPELINE_INVALID_SHAPE", f"missing required field: {required}", stage="ORCHESTRATOR_INPUT")
    _nonempty(payload["pipeline_id"], field="pipeline_id")
    _nonempty(payload["hypothesis_id"], field="hypothesis_id")
    _mapping(payload["before_eval_payload"], field="before_eval_payload")
    _mapping(payload["after_eval_payload"], field="after_eval_payload")
    _mapping(payload["change_record"], field="change_record")
    if payload.get("learning_context") is not None:
        _mapping(payload["learning_context"], field="learning_context")
    prior = payload.get("prior_final_delta_inputs") or []
    if not isinstance(prior, list) or not all(isinstance(item, Mapping) for item in prior):
        raise LearningEvidencePipelineError("LEARNING_PIPELINE_INVALID_SHAPE", "prior_final_delta_inputs must be a list of source mappings", stage="ORCHESTRATOR_INPUT")
    if "requested_maturity" in payload and payload["requested_maturity"] is not None:
        _nonempty(payload["requested_maturity"], field="requested_maturity")
    return payload


def run_learning_evidence_pipeline(raw: Mapping[str, Any], *, project_root: str | Path) -> dict[str, Any]:
    payload = _validate_root(raw)
    root = Path(project_root)
    completed: list[str] = []

    before_source = dict(payload["before_eval_payload"])
    after_source = dict(payload["after_eval_payload"])
    change_record = dict(payload["change_record"])
    learning_context = dict(payload.get("learning_context") or {})

    before = _run_stage(
        "BEFORE_EXPECTED_OBSERVED", completed,
        lambda: evaluate_expected_vs_observed(before_source, project_root=root),
    )

    repair_plan = _run_stage(
        "TARGETED_REPAIR", completed,
        lambda: plan_targeted_repair(before_source, project_root=root),
    )
    if repair_plan.get("repair_required") is not True or not repair_plan.get("repair_items"):
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_NO_REPAIR_TARGET",
            "before evaluation contains no FAIL/UNKNOWN target for a repair trajectory",
            stage="TARGETED_REPAIR_PRECONDITION",
            completed_stages=completed,
        )

    after = _run_stage(
        "AFTER_EXPECTED_OBSERVED", completed,
        lambda: evaluate_expected_vs_observed(after_source, project_root=root),
    )
    if not str(before.get("eval_id") or "").strip() or not str(after.get("eval_id") or "").strip() or before["eval_id"] == after["eval_id"]:
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_EVAL_ID_COLLISION",
            "before and after evaluations must have distinct non-empty eval_id values",
            stage="AFTER_EXPECTED_OBSERVED_PRECONDITION",
            completed_stages=completed,
        )

    current_final_delta_input = {
        "before_eval_input": before_source,
        "after_eval_input": after_source,
        "change_record": change_record,
        "learning_context": learning_context,
    }
    final_delta = _run_stage(
        "FINAL_DELTA", completed,
        lambda: compile_final_delta_learning_evidence(current_final_delta_input, project_root=root),
    )

    source_inputs = [dict(item) for item in (payload.get("prior_final_delta_inputs") or [])]
    source_inputs.append(current_final_delta_input)
    post_payload: dict[str, Any] = {
        "assessment_id": f"POST_FD::{payload['pipeline_id']}",
        "hypothesis_id": payload["hypothesis_id"],
        "final_delta_inputs": source_inputs,
    }
    if payload.get("requested_maturity") is not None:
        post_payload["requested_maturity"] = payload["requested_maturity"]
    post = _run_stage(
        "POST_FINAL_DELTA", completed,
        lambda: assess_source_bound_post_final_delta(post_payload, project_root=root),
    )

    stages = {
        "before_expected_observed": {
            "eval_id": before["eval_id"],
            "status": before["status"],
            "control_status": before["control_status"],
            "repair_target_count": len(before["targeted_repair_handoff"]["items"]),
        },
        "targeted_repair": {
            "plan_id": repair_plan["plan_id"],
            "repair_required": repair_plan["repair_required"],
            "repair_item_count": len(repair_plan["repair_items"]),
            "preserved_pass_fields": list(repair_plan["preserved_pass_fields"]),
        },
        "after_expected_observed": {
            "eval_id": after["eval_id"],
            "status": after["status"],
            "control_status": after["control_status"],
        },
        "final_delta": {
            "final_delta_id": final_delta["final_delta_id"],
            "comparison_status": final_delta["comparison_status"],
            "resolved_fields": list(final_delta["repair_outcome"]["resolved_fields"]),
            "regressed_fields": list(final_delta["repair_outcome"]["regressed_fields"]),
            "causal_evidence_status": final_delta["causal_evidence"]["status"],
        },
        "post_final_delta": {
            "assessment_id": post["assessment_id"],
            "cohort_count": len(post["cohorts"]),
            "conflict_present": post["conflict_present"],
            "regression_proposal_count": len(post["regression_proposals"]),
            "maturity_route": post["maturity_assessment"]["route"],
            "source_binding": dict(post["source_binding"]),
        },
    }

    return {
        "schema": "LEARNING_EVIDENCE_PIPELINE_RESULT/v2",
        "status": "PASS",
        "pipeline_id": payload["pipeline_id"],
        "hypothesis_id": payload["hypothesis_id"],
        "stage_order": list(PIPELINE_STAGE_ORDER),
        "completed_stages": list(completed),
        "stages": stages,
        "artifacts": {
            "before_eval": before,
            "repair_plan": repair_plan,
            "after_eval": after,
            "final_delta": final_delta,
            "post_final_delta": post,
        },
        "source_binding": {
            "expected_observed_inputs_reexecuted": True,
            "targeted_repair_source_reexecuted": True,
            "final_delta_source_reexecuted": True,
            "post_final_delta_source_reexecuted": True,
            "serialized_prior_final_deltas_accepted": False,
        },
        "candidate_learning_evidence": final_delta["candidate_learning_evidence"],
        "regression_proposals": list(post["regression_proposals"]),
        "maturity_assessment": dict(post["maturity_assessment"]),
        "prompt_mutation_authorized": False,
        "generation_authorized": False,
        "camera_authority_mutation_authorized": False,
        "canonical_mutation_authorized": False,
        "learning_writeback_authorized": False,
        "regression_write_authorized": False,
        "maturity_promotion_authorized": False,
        "causal_claim_authorized": False,
        "authority_boundary": "orchestration_only_source_bound_stage_authorities_unchanged",
    }
