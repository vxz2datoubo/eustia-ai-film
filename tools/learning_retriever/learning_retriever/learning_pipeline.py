"""Bounded orchestration for the evidence-driven continual-learning runtime.

This module composes existing executable stages only:

Expected-vs-Observed(before) -> Targeted Repair -> Expected-vs-Observed(after)
-> Final-Delta -> Post-Final-Delta validation.

It owns no film method, evaluation vocabulary, repair routing, learning truth,
maturity decision, prompt mutation, generation, camera authority or persistence.
Every stage is executed by its existing canonical runtime and every failure is
surfaced with the exact source stage and underlying error code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from .expected_observed import ExpectedObservedEvalError, evaluate_expected_vs_observed
from .final_delta import FinalDeltaEvidenceError, compile_final_delta_learning_evidence
from .post_final_delta import PostFinalDeltaValidationError, assess_post_final_delta_validation
from .targeted_repair import TargetedRepairPlanError, plan_targeted_repair


class LearningEvidencePipelineError(ValueError):
    """Fail-closed orchestration error with stage provenance."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        underlying_code: str | None = None,
        completed_stages: list[str] | None = None,
    ) -> None:
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
    "prior_final_deltas",
}

_STAGE_ERRORS = (
    ExpectedObservedEvalError,
    TargetedRepairPlanError,
    FinalDeltaEvidenceError,
    PostFinalDeltaValidationError,
)


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_INVALID_SHAPE",
            f"{field} must be a mapping",
            stage="ORCHESTRATOR_INPUT",
        )
    return dict(value)


def _nonempty(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_INVALID_SHAPE",
            f"{field} must be a non-empty string",
            stage="ORCHESTRATOR_INPUT",
        )
    return value.strip()


def _run_stage(
    stage: str,
    completed: list[str],
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
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
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_UNKNOWN_FIELD",
            f"unknown pipeline fields: {sorted(unknown)}",
            stage="ORCHESTRATOR_INPUT",
        )
    for required in (
        "pipeline_id",
        "hypothesis_id",
        "before_eval_payload",
        "after_eval_payload",
        "change_record",
    ):
        if required not in payload:
            raise LearningEvidencePipelineError(
                "LEARNING_PIPELINE_INVALID_SHAPE",
                f"missing required field: {required}",
                stage="ORCHESTRATOR_INPUT",
            )
    _nonempty(payload["pipeline_id"], field="pipeline_id")
    _nonempty(payload["hypothesis_id"], field="hypothesis_id")
    _mapping(payload["before_eval_payload"], field="before_eval_payload")
    _mapping(payload["after_eval_payload"], field="after_eval_payload")
    _mapping(payload["change_record"], field="change_record")
    if payload.get("learning_context") is not None:
        _mapping(payload["learning_context"], field="learning_context")
    prior = payload.get("prior_final_deltas") or []
    if not isinstance(prior, list) or not all(isinstance(item, Mapping) for item in prior):
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_INVALID_SHAPE",
            "prior_final_deltas must be a list of mappings",
            stage="ORCHESTRATOR_INPUT",
        )
    if "requested_maturity" in payload and payload["requested_maturity"] is not None:
        _nonempty(payload["requested_maturity"], field="requested_maturity")
    return payload


def run_learning_evidence_pipeline(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Execute the existing evidence-learning stages in canonical order.

    A successful result is still non-writing and non-promoting. The pipeline is
    an execution envelope, not a new authority or a shortcut around any stage.
    """

    payload = _validate_root(raw)
    root = Path(project_root)
    completed: list[str] = []

    before = _run_stage(
        "BEFORE_EXPECTED_OBSERVED",
        completed,
        lambda: evaluate_expected_vs_observed(
            payload["before_eval_payload"], project_root=root
        ),
    )

    repair_plan = _run_stage(
        "TARGETED_REPAIR",
        completed,
        lambda: plan_targeted_repair(before, project_root=root),
    )
    if repair_plan.get("repair_required") is not True or not repair_plan.get("repair_items"):
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_NO_REPAIR_TARGET",
            "before evaluation contains no FAIL/UNKNOWN target for a repair trajectory",
            stage="TARGETED_REPAIR_PRECONDITION",
            completed_stages=completed,
        )

    after = _run_stage(
        "AFTER_EXPECTED_OBSERVED",
        completed,
        lambda: evaluate_expected_vs_observed(
            payload["after_eval_payload"], project_root=root
        ),
    )
    before_eval_id = str(before.get("eval_id") or "").strip()
    after_eval_id = str(after.get("eval_id") or "").strip()
    if not before_eval_id or not after_eval_id or before_eval_id == after_eval_id:
        raise LearningEvidencePipelineError(
            "LEARNING_PIPELINE_EVAL_ID_COLLISION",
            "before and after evaluations must have distinct non-empty eval_id values",
            stage="AFTER_EXPECTED_OBSERVED_PRECONDITION",
            completed_stages=completed,
        )

    final_delta = _run_stage(
        "FINAL_DELTA",
        completed,
        lambda: compile_final_delta_learning_evidence(
            {
                "before_eval": before,
                "after_eval": after,
                "repair_plan": repair_plan,
                "change_record": payload["change_record"],
                "learning_context": payload.get("learning_context") or {},
            },
            project_root=root,
        ),
    )

    all_deltas = [dict(item) for item in (payload.get("prior_final_deltas") or [])]
    all_deltas.append(final_delta)
    post_payload: dict[str, Any] = {
        "assessment_id": f"POST_FD::{payload['pipeline_id']}",
        "hypothesis_id": payload["hypothesis_id"],
        "final_deltas": all_deltas,
    }
    if payload.get("requested_maturity") is not None:
        post_payload["requested_maturity"] = payload["requested_maturity"]

    post = _run_stage(
        "POST_FINAL_DELTA",
        completed,
        lambda: assess_post_final_delta_validation(post_payload, project_root=root),
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
        },
    }

    return {
        "schema": "LEARNING_EVIDENCE_PIPELINE_RESULT/v1",
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
        "authority_boundary": "orchestration_only_existing_stage_authorities_unchanged",
    }
