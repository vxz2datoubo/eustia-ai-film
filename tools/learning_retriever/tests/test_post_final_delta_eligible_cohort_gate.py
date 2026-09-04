from pathlib import Path
import unittest
from unittest.mock import patch

from learning_retriever.post_final_delta import PostFinalDeltaValidationError
from learning_retriever.post_final_delta_source_bound import assess_source_bound_post_final_delta


REPO_ROOT = Path(__file__).resolve().parents[3]


def _delta(
    delta_id: str,
    *,
    model: str = "C-DANCE",
    model_version: str = "2.5",
    lesson: str = "lesson-A",
    artifact_verified: bool = True,
    comparison_status: str = "COMPARABLE",
    resolved: bool = False,
    formal_resolved: bool = False,
    regression_eligible: bool = False,
) -> dict:
    transitions = []
    resolved_fields = []
    if resolved:
        resolved_fields = ["attention_handoff"]
    if formal_resolved:
        transitions = [
            {
                "field": "attention_handoff",
                "transition": "RESOLVED",
            }
        ]
    return {
        "final_delta_id": delta_id,
        "comparison_status": comparison_status,
        "artifact_provenance_binding": {"verified": artifact_verified},
        "field_transitions": transitions,
        "repair_outcome": {
            "resolved_fields": resolved_fields,
            "persistent_failure_fields": [],
            "regressed_fields": [],
        },
        "regression_candidate_handoff": {"eligible": regression_eligible},
        "candidate_learning_evidence": {"candidate_lesson": lesson},
        "model": model,
        "model_version": model_version,
    }


def _base_projection_result() -> dict:
    return {
        "assessment_id": "A",
        "hypothesis_id": "H",
        "evidence_rows": [],
        "cohorts": [],
        "regression_proposals": [],
        "maturity_assessment": {
            "requested_maturity": None,
            "route": "NO_PROMOTION_REQUESTED",
            "promotion_authorized": False,
        },
    }


class PostFinalDeltaEligibleCohortGateTests(unittest.TestCase):
    def test_comparable_unverified_artifact_is_rejected_before_projection(self):
        forged = _delta(
            "FD-UNVERIFIED-COMPARABLE",
            artifact_verified=False,
            comparison_status="COMPARABLE",
            resolved=True,
            formal_resolved=True,
            regression_eligible=True,
        )
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            return_value=forged,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection"
        ) as projection:
            with self.assertRaises(PostFinalDeltaValidationError) as ctx:
                assess_source_bound_post_final_delta(
                    {
                        "assessment_id": "A",
                        "hypothesis_id": "H",
                        "final_delta_inputs": [{"source": "synthetic"}],
                    },
                    project_root=REPO_ROOT,
                )
        self.assertEqual(ctx.exception.code, "POST_FD_AUTHORITY_VIOLATION")
        projection.assert_not_called()

    def test_resolved_without_upstream_eligibility_is_downgraded_before_projection(self):
        delta = _delta(
            "FD-INELIGIBLE-RESOLVED",
            resolved=True,
            formal_resolved=True,
            regression_eligible=False,
        )
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            return_value=delta,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection",
            return_value=_base_projection_result(),
        ) as projection:
            result = assess_source_bound_post_final_delta(
                {
                    "assessment_id": "A",
                    "hypothesis_id": "H",
                    "final_delta_inputs": [{"source": "synthetic"}],
                },
                project_root=REPO_ROOT,
            )

        internal = projection.call_args.args[0]
        projected = internal["final_deltas"][0]
        self.assertEqual(projected["repair_outcome"]["resolved_fields"], [])
        self.assertFalse(projected["regression_candidate_handoff"]["eligible"])
        self.assertEqual(result["source_binding"]["support_downgraded_to_inconclusive_count"], 1)
        self.assertTrue(result["source_binding"]["support_requires_formal_resolved_transition"])
        self.assertTrue(result["source_binding"]["support_requires_upstream_regression_eligibility"])

    def test_resolved_field_without_matching_formal_transition_is_rejected(self):
        delta = _delta(
            "FD-MISSING-FORMAL-RESOLVED",
            resolved=True,
            formal_resolved=False,
            regression_eligible=True,
        )
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            return_value=delta,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection"
        ) as projection:
            with self.assertRaises(PostFinalDeltaValidationError) as ctx:
                assess_source_bound_post_final_delta(
                    {
                        "assessment_id": "A",
                        "hypothesis_id": "H",
                        "final_delta_inputs": [{"source": "synthetic"}],
                    },
                    project_root=REPO_ROOT,
                )
        self.assertEqual(ctx.exception.code, "POST_FD_INVALID_FINAL_DELTA")
        projection.assert_not_called()

    def test_multi_cohort_maturity_requires_exact_target(self):
        deltas = [
            _delta("FD-25", model_version="2.5", lesson="lesson-A"),
            _delta("FD-26", model_version="2.6", lesson="lesson-A"),
        ]
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            side_effect=deltas,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection",
            return_value=_base_projection_result(),
        ):
            with self.assertRaises(PostFinalDeltaValidationError) as ctx:
                assess_source_bound_post_final_delta(
                    {
                        "assessment_id": "A",
                        "hypothesis_id": "H",
                        "final_delta_inputs": [{"source": "a"}, {"source": "b"}],
                        "requested_maturity": "scene_verified",
                    },
                    project_root=REPO_ROOT,
                )
        self.assertEqual(ctx.exception.code, "POST_FD_MATURITY_TARGET_REQUIRED")

    def test_maturity_projection_uses_only_selected_exact_cohort(self):
        deltas = [
            _delta("FD-25", model_version="2.5", lesson="lesson-A"),
            _delta("FD-26", model_version="2.6", lesson="lesson-A"),
        ]
        overall = _base_projection_result()
        maturity = _base_projection_result()
        maturity["maturity_assessment"] = {
            "requested_maturity": "scene_verified",
            "route": "INSUFFICIENT_SUPPORT_FOR_SCENE_VERIFICATION",
            "promotion_authorized": False,
        }
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            side_effect=deltas,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection",
            side_effect=[overall, maturity],
        ) as projection:
            result = assess_source_bound_post_final_delta(
                {
                    "assessment_id": "A",
                    "hypothesis_id": "H",
                    "final_delta_inputs": [{"source": "a"}, {"source": "b"}],
                    "requested_maturity": "scene_verified",
                    "maturity_target": {
                        "model": "C-DANCE",
                        "model_version": "2.5",
                        "exact_candidate_lesson_payload": "lesson-A",
                    },
                },
                project_root=REPO_ROOT,
            )

        self.assertEqual(projection.call_count, 2)
        maturity_input = projection.call_args_list[1].args[0]
        self.assertEqual(len(maturity_input["final_deltas"]), 1)
        self.assertEqual(maturity_input["final_deltas"][0]["model_version"], "2.5")
        self.assertEqual(
            result["maturity_assessment"]["evidence_cohort"],
            {
                "model": "C-DANCE",
                "model_version": "2.5",
                "exact_candidate_lesson_payload": "lesson-A",
            },
        )
        self.assertTrue(result["source_binding"]["maturity_is_cohort_scoped"])


if __name__ == "__main__":
    unittest.main()
