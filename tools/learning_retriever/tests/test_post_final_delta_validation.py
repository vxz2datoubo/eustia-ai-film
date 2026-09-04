from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever._post_final_delta_core_v3 import (
    STRUCTURAL_GATE_CODES,
    PostFinalDeltaValidationError,
    assess_post_final_delta_validation,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = yaml.safe_load(
    (REPO_ROOT / "10_运行时/post_final_delta_validation_policy.yaml").read_text(encoding="utf-8")
)
REGRESSION = yaml.safe_load(
    (REPO_ROOT / "11_验收/post_final_delta_validation_regression_cases.yaml").read_text(encoding="utf-8")
)


def _delta(
    delta_id: str,
    *,
    model: str | None = "C-DANCE",
    model_version: str | None = "2.5",
    lesson: str | None = "stable_lesson_text",
    work_item: str = "SCENE-A-SHOT-01",
    resolved: list[str] | None = None,
    persistent: list[str] | None = None,
    regressed: list[str] | None = None,
    comparison_status: str = "COMPARABLE",
    regression_eligible: bool | None = None,
    confirmation: str = "CONFIRMED_USE",
    causal_status: str = "OBSERVATIONAL_ONLY",
) -> dict:
    resolved = list(resolved if resolved is not None else ["attention_handoff"])
    persistent = list(persistent or [])
    regressed = list(regressed or [])
    if regression_eligible is None:
        regression_eligible = bool(resolved and not persistent and not regressed and comparison_status != "NOT_COMPARABLE")

    fields = []
    for field in resolved:
        fields.append(
            {
                "field": field,
                "before_outcome": "FAIL",
                "after_outcome": "PASS",
                "transition": "RESOLVED",
                "before_observed_value": {"state": "bad"},
                "after_observed_value": {"state": "good"},
                "before_evidence_refs": [f"{delta_id}::before::{field}"],
                "after_evidence_refs": [f"{delta_id}::after::{field}"],
            }
        )
    for field in persistent:
        fields.append(
            {
                "field": field,
                "before_outcome": "FAIL",
                "after_outcome": "FAIL",
                "transition": "PERSISTED",
                "before_observed_value": {"state": "bad"},
                "after_observed_value": {"state": "still_bad"},
                "before_evidence_refs": [f"{delta_id}::before::{field}"],
                "after_evidence_refs": [f"{delta_id}::after::{field}"],
            }
        )
    for field in regressed:
        fields.append(
            {
                "field": field,
                "before_outcome": "PASS",
                "after_outcome": "FAIL",
                "transition": "REGRESSED",
                "before_observed_value": {"state": "good"},
                "after_observed_value": {"state": "bad"},
                "before_evidence_refs": [f"{delta_id}::before::{field}"],
                "after_evidence_refs": [f"{delta_id}::after::{field}"],
            }
        )

    return {
        "final_delta_id": delta_id,
        "source_before_eval_id": f"{delta_id}::before",
        "source_after_eval_id": f"{delta_id}::after",
        "source_repair_plan_id": f"{delta_id}::repair",
        "comparison_status": comparison_status,
        "comparison_reasons": [],
        "work_item_id": work_item,
        "model": model,
        "model_version": model_version,
        "change_record": {
            "change_id": f"change::{delta_id}",
            "changed_variables": ["target_variable"],
            "preserved_variables": [],
            "revoked_variables": [],
            "experimental_variables": [],
            "scope": "SCENE_LOCAL",
            "evidence_refs": [f"evidence::{delta_id}"],
            "user_confirmation_state": confirmation,
        },
        "field_transitions": fields if comparison_status != "NOT_COMPARABLE" else [],
        "repair_outcome": {
            "resolved_fields": resolved if comparison_status != "NOT_COMPARABLE" else [],
            "persistent_failure_fields": persistent if comparison_status != "NOT_COMPARABLE" else [],
            "unresolved_evidence_fields": [],
            "preserved_pass_fields": ["composition"] if not regressed and comparison_status != "NOT_COMPARABLE" else [],
            "regressed_fields": regressed if comparison_status != "NOT_COMPARABLE" else [],
            "before_observation_provenance": {"evidence_source": "fixture_before"},
            "after_observation_provenance": {"evidence_source": "fixture_after"},
        },
        "causal_evidence": {
            "status": causal_status,
            "eligible_for_causal_analysis": causal_status == "CONTROLLED_SINGLE_VARIABLE_CANDIDATE",
            "causal_claim_authorized": False,
            "alternative_explanations": ["UNKNOWN_NOT_SUPPLIED"],
            "counterfactuals": ["UNKNOWN_NOT_SUPPLIED"],
        },
        "candidate_learning_evidence": {
            "evidence_id": f"candidate::{delta_id}",
            "maturity": "candidate",
            "maturity_effect": "none",
            "scope": "SCENE_LOCAL",
            "user_confirmation_state": confirmation,
            "candidate_lesson": lesson,
            "causal_evidence_status": causal_status,
            "generalization_authorized": False,
            "promotion_authorized": False,
            "writeback_authorized": False,
            "targeted_eval_required": True,
        },
        "regression_candidate_handoff": {
            "eligible": regression_eligible,
            "write_authorized": False,
            "promotion_authorized": False,
            "source_final_delta_id": delta_id,
            "reason": "fixture",
        },
        "prompt_mutation_authorized": False,
        "generation_authorized": False,
        "camera_authority_mutation_authorized": False,
        "canonical_mutation_authorized": False,
        "learning_writeback_authorized": False,
        "maturity_promotion_authorized": False,
        "runtime_policy_id": "EUSTIA_FINAL_DELTA_LEARNING_EVIDENCE_V1",
    }


def _assess(deltas: list[dict], requested_maturity: str | None = None) -> dict:
    payload = {
        "assessment_id": "ASSESS-001",
        "hypothesis_id": "HYPOTHESIS-EXPLICIT-001",
        "final_deltas": deltas,
    }
    if requested_maturity is not None:
        payload["requested_maturity"] = requested_maturity
    return assess_post_final_delta_validation(payload, project_root=REPO_ROOT)


class PostFinalDeltaValidationTests(unittest.TestCase):
    def test_policy_forbids_semantic_clustering_latest_wins_and_promotion(self):
        principles = POLICY["principles"]
        self.assertTrue(principles["semantic_auto_clustering_forbidden"])
        self.assertTrue(principles["model_version_evidence_partitioning_required"])
        self.assertTrue(principles["latest_wins_conflict_resolution_forbidden"])
        self.assertTrue(principles["contradictions_must_remain_visible"])
        self.assertTrue(principles["maturity_promotion_forbidden"])
        self.assertTrue(principles["regression_proposal_is_not_regression_write"])

    def test_same_version_same_exact_lesson_forms_one_supporting_cohort(self):
        result = _assess(
            [
                _delta("FD-A", work_item="SCENE-A"),
                _delta("FD-B", work_item="SCENE-B"),
            ]
        )
        self.assertEqual(len(result["cohorts"]), 1)
        cohort = result["cohorts"][0]
        self.assertEqual(cohort["evidence_count"], 2)
        self.assertEqual(cohort["supporting_count"], 2)
        self.assertEqual(cohort["contradictory_count"], 0)
        self.assertEqual(cohort["distinct_work_items"], ["SCENE-A", "SCENE-B"])
        self.assertFalse(cohort["conflict_present"])
        self.assertFalse(result["semantic_auto_clustering_performed"])

    def test_model_versions_are_partitioned_never_silently_pooled(self):
        result = _assess(
            [
                _delta("FD-V25", model_version="2.5"),
                _delta("FD-V26", model_version="2.6"),
            ]
        )
        self.assertEqual(result["model_version_partition_count"], 2)
        self.assertTrue(result["cross_model_or_version_split_present"])
        self.assertEqual(len(result["cohorts"]), 2)

    def test_exact_lesson_payloads_are_partitioned_without_semantic_guessing(self):
        result = _assess(
            [
                _delta("FD-L1", lesson="keep reveal hidden until return"),
                _delta("FD-L2", lesson="delay visible departure until cutaway"),
            ]
        )
        self.assertEqual(result["exact_lesson_payload_count"], 2)
        self.assertEqual(len(result["cohorts"]), 2)
        self.assertFalse(result["semantic_auto_clustering_performed"])

    def test_support_and_contradiction_remain_visible_in_same_cohort(self):
        supporting = _delta("FD-SUPPORT")
        contradictory = _delta(
            "FD-CONTRADICT",
            resolved=[],
            persistent=["attention_handoff"],
            regression_eligible=False,
        )
        result = _assess([supporting, contradictory], requested_maturity="project_verified")
        self.assertTrue(result["conflict_present"])
        self.assertEqual(len(result["cohorts"]), 1)
        cohort = result["cohorts"][0]
        self.assertEqual(cohort["supporting_count"], 1)
        self.assertEqual(cohort["contradictory_count"], 1)
        self.assertTrue(cohort["conflict_present"])
        self.assertFalse(result["latest_wins_resolution_performed"])
        self.assertEqual(
            result["maturity_assessment"]["route"], "CONFLICT_REQUIRES_ADJUDICATION"
        )

    def test_regression_proposal_is_candidate_and_never_writable(self):
        result = _assess([_delta("FD-REG-PROP")])
        self.assertEqual(len(result["regression_proposals"]), 1)
        proposal = result["regression_proposals"][0]
        self.assertEqual(proposal["status"], "candidate")
        self.assertFalse(proposal["write_authorized"])
        self.assertFalse(proposal["promotion_authorized"])
        self.assertTrue(proposal["human_or_governed_review_required"])
        self.assertIsNone(proposal["canonical_write_target"])
        self.assertIn("attention_handoff", [item["field"] for item in proposal["resolved_target_transitions"]])
        self.assertTrue(proposal["evidence_refs"])
        self.assertFalse(result["regression_write_authorized"])

    def test_contradictory_or_inconclusive_evidence_cannot_emit_regression_proposal(self):
        contradictory = _delta(
            "FD-NO-PROP-CONTRA",
            resolved=[],
            persistent=["attention_handoff"],
            regression_eligible=True,
        )
        inconclusive = _delta(
            "FD-NO-PROP-INC",
            comparison_status="NOT_COMPARABLE",
            regression_eligible=True,
        )
        result = _assess([contradictory, inconclusive])
        self.assertEqual(result["regression_proposals"], [])

    def test_scene_verified_never_trusts_caller_confirmation_claim_as_authority(self):
        result = _assess(
            [_delta("FD-SCENE", confirmation="CONFIRMED_USE")],
            requested_maturity="scene_verified",
        )
        assessment = result["maturity_assessment"]
        self.assertEqual(
            assessment["route"], "TRUSTED_USER_OR_CANONICAL_CONFIRMATION_BINDING_REQUIRED"
        )
        self.assertTrue(assessment["supporting_evidence_present"])
        self.assertFalse(assessment["trusted_confirmation_binding_present"])
        self.assertFalse(assessment["promotion_authorized"])
        self.assertFalse(result["maturity_promotion_authorized"])

    def test_scene_verified_without_support_is_insufficient(self):
        result = _assess(
            [
                _delta(
                    "FD-SCENE-NO-SUPPORT",
                    resolved=[],
                    persistent=[],
                    regression_eligible=False,
                )
            ],
            requested_maturity="scene_verified",
        )
        self.assertEqual(
            result["maturity_assessment"]["route"], "INSUFFICIENT_SUPPORT_FOR_SCENE_VERIFICATION"
        )
        self.assertFalse(result["maturity_assessment"]["promotion_authorized"])

    def test_project_and_general_stable_are_high_impact_governed_gates(self):
        for maturity in ("project_verified", "general_stable"):
            with self.subTest(maturity=maturity):
                result = _assess([_delta(f"FD-{maturity}")], requested_maturity=maturity)
                self.assertEqual(
                    result["maturity_assessment"]["route"],
                    "HIGH_IMPACT_GOVERNED_PROMOTION_GATE_REQUIRED",
                )
                self.assertFalse(result["maturity_assessment"]["promotion_authorized"])

    def test_special_maturity_states_require_governed_decision(self):
        for maturity in ("conflicted", "needs_revalidation", "deprecated"):
            with self.subTest(maturity=maturity):
                result = _assess([_delta(f"FD-SPECIAL-{maturity}")], requested_maturity=maturity)
                self.assertEqual(
                    result["maturity_assessment"]["route"],
                    "SPECIAL_STATE_GOVERNED_DECISION_REQUIRED",
                )
                self.assertFalse(result["maturity_assessment"]["promotion_authorized"])

    def test_authority_escalation_fails_closed(self):
        base = _delta("FD-AUTH")
        mutations = [
            ("learning_writeback_authorized", lambda item: item.__setitem__("learning_writeback_authorized", True)),
            ("camera_authority_mutation_authorized", lambda item: item.__setitem__("camera_authority_mutation_authorized", True)),
            ("candidate_maturity", lambda item: item["candidate_learning_evidence"].__setitem__("maturity", "scene_verified")),
            ("candidate_writeback", lambda item: item["candidate_learning_evidence"].__setitem__("writeback_authorized", True)),
            ("regression_write", lambda item: item["regression_candidate_handoff"].__setitem__("write_authorized", True)),
            ("causal_claim", lambda item: item["causal_evidence"].__setitem__("causal_claim_authorized", True)),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                item = deepcopy(base)
                mutate(item)
                with self.assertRaises(PostFinalDeltaValidationError) as ctx:
                    _assess([item])
                self.assertEqual(ctx.exception.code, "POST_FD_AUTHORITY_VIOLATION")
                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_missing_hypothesis_id_and_unknown_maturity_fail_closed(self):
        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            assess_post_final_delta_validation(
                {
                    "assessment_id": "ASSESS-MISSING-HYP",
                    "final_deltas": [_delta("FD-MISSING-HYP")],
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "POST_FD_INVALID_SHAPE")

        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            _assess([_delta("FD-UNKNOWN-MAT")], requested_maturity="magic_verified")
        self.assertEqual(ctx.exception.code, "POST_FD_UNKNOWN_MATURITY")

    def test_duplicate_final_delta_ids_fail_closed(self):
        item = _delta("FD-DUP")
        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            _assess([item, deepcopy(item)])
        self.assertEqual(ctx.exception.code, "POST_FD_INVALID_SHAPE")

    def test_regression_registry_keeps_all_governance_gates(self):
        self.assertEqual(
            REGRESSION["suite_id"],
            "POST_FINAL_DELTA_VALIDATION_REGRESSION_V3_ELIGIBLE_COHORT_GATED",
        )
        gates = REGRESSION["gates"]
        self.assertTrue(gates["public_source_packages_are_reexecuted"])
        self.assertTrue(gates["serialized_final_delta_never_authoritative"])
        self.assertTrue(gates["artifact_verification_checked_independently"])
        self.assertTrue(gates["artifact_unverified_is_inconclusive_or_rejected_on_drift"])
        self.assertTrue(gates["unattributed_diagnostic_resolved_never_supporting"])
        self.assertTrue(gates["unattributed_diagnostic_resolved_never_regression_proposal"])
        self.assertTrue(gates["formal_resolved_transition_required_for_support"])
        self.assertTrue(gates["upstream_regression_eligibility_required_for_support"])
        self.assertTrue(gates["downstream_cannot_mint_support_eligibility"])
        self.assertTrue(gates["maturity_uses_selected_exact_cohort_only"])
        self.assertTrue(gates["multi_cohort_maturity_requires_exact_target"])
        self.assertTrue(gates["no_semantic_auto_clustering"])
        self.assertTrue(gates["no_cross_model_version_pooling"])
        self.assertTrue(gates["conflict_cannot_be_silently_resolved"])
        self.assertTrue(gates["regression_proposal_cannot_write"])
        self.assertTrue(gates["caller_confirmation_claim_cannot_mint_trusted_confirmation"])
        self.assertTrue(gates["project_verified_not_auto_promoted"])
        self.assertTrue(gates["general_stable_not_auto_promoted"])
        self.assertTrue(gates["no_second_learning_authority"])
        self.assertTrue(gates["no_final_delta_authority_restoration"])


if __name__ == "__main__":
    unittest.main()
