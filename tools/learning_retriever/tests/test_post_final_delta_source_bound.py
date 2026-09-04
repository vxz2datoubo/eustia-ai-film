from pathlib import Path
import unittest
from unittest.mock import patch

from learning_retriever.post_final_delta import (
    PostFinalDeltaValidationError,
    assess_post_final_delta_validation,
)
from learning_retriever.post_final_delta_source_bound import assess_source_bound_post_final_delta


REPO_ROOT = Path(__file__).resolve().parents[3]


class PostFinalDeltaSourceBindingTests(unittest.TestCase):
    def test_serialized_final_deltas_have_no_source_bound_input_port(self):
        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            assess_source_bound_post_final_delta(
                {
                    "assessment_id": "A",
                    "hypothesis_id": "H",
                    "final_deltas": [{"final_delta_id": "FORGED"}],
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "POST_FD_UNKNOWN_FIELD")

    def test_public_structural_facade_rejects_serialized_projection(self):
        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            assess_post_final_delta_validation(
                {
                    "assessment_id": "A",
                    "hypothesis_id": "H",
                    "final_deltas": [{"final_delta_id": "FORGED", "comparison_status": "COMPARABLE"}],
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "POST_FD_AUTHORITY_VIOLATION")

    def test_each_source_package_is_reexecuted_before_private_projection(self):
        compiled_a = {"final_delta_id": "FD-A"}
        compiled_b = {"final_delta_id": "FD-B"}
        projected = {"assessment_id": "A", "cohorts": []}
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            side_effect=[compiled_a, compiled_b],
        ) as compile_mock, patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection",
            return_value=projected,
        ) as assess_mock:
            result = assess_source_bound_post_final_delta(
                {
                    "assessment_id": "A",
                    "hypothesis_id": "H",
                    "final_delta_inputs": [{"source": "a"}, {"source": "b"}],
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(compile_mock.call_count, 2)
        self.assertEqual(assess_mock.call_count, 1)
        internal = assess_mock.call_args.args[0]
        self.assertEqual(internal["final_deltas"], [compiled_a, compiled_b])
        self.assertNotIn("requested_maturity", internal)
        self.assertEqual(result["source_binding"]["mode"], "canonical_final_delta_reexecution")
        self.assertFalse(result["source_binding"]["serialized_final_deltas_accepted"])
        self.assertEqual(result["source_binding"]["compiled_source_count"], 2)
        self.assertEqual(result["source_binding"]["structural_projection_visibility"], "private_internal_only")
        self.assertTrue(result["source_binding"]["upstream_attribution_gate_preserved"])
        self.assertTrue(result["source_binding"]["upstream_artifact_gate_checked_independently"])
        self.assertTrue(result["source_binding"]["maturity_is_cohort_scoped"])
        self.assertFalse(result["source_binding"]["unattributed_transition_candidates_consumed_as_attributed"])

    def test_empty_source_list_fails_closed(self):
        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            assess_source_bound_post_final_delta(
                {"assessment_id": "A", "hypothesis_id": "H", "final_delta_inputs": []},
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "POST_FD_INVALID_SHAPE")


if __name__ == "__main__":
    unittest.main()
