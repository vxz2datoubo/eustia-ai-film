from pathlib import Path
import unittest
from unittest.mock import patch

from learning_retriever.post_final_delta import PostFinalDeltaValidationError
from learning_retriever.post_final_delta_source_bound import assess_source_bound_post_final_delta


REPO_ROOT = Path(__file__).resolve().parents[3]


def _delta(
    delta_id: str,
    *,
    model="C-DANCE",
    model_version="2.5",
    lesson="lesson-A",
) -> dict:
    candidate = {} if lesson is None else {"candidate_lesson": lesson}
    return {
        "final_delta_id": delta_id,
        "comparison_status": "COMPARABLE",
        "artifact_provenance_binding": {"verified": True},
        "field_transitions": [],
        "repair_outcome": {
            "resolved_fields": [],
            "persistent_failure_fields": [],
            "regressed_fields": [],
        },
        "regression_candidate_handoff": {"eligible": False},
        "candidate_learning_evidence": candidate,
        "model": model,
        "model_version": model_version,
    }


def _projection_result() -> dict:
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


class PostFinalDeltaExactPartitionIdentityTests(unittest.TestCase):
    def _assert_missing_rejected(self, delta: dict):
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
        self.assertEqual(ctx.exception.code, "POST_FD_COHORT_IDENTITY_INCOMPLETE")
        projection.assert_not_called()

    def test_missing_model_is_rejected_before_any_cohort_projection(self):
        self._assert_missing_rejected(_delta("FD-NO-MODEL", model=None))

    def test_missing_model_version_is_rejected_before_any_cohort_projection(self):
        self._assert_missing_rejected(_delta("FD-NO-VERSION", model_version=None))

    def test_missing_candidate_lesson_is_rejected_before_any_cohort_projection(self):
        self._assert_missing_rejected(_delta("FD-NO-LESSON", lesson=None))

    def test_blank_partition_values_are_rejected_not_sentinelized(self):
        for kwargs in (
            {"model": ""},
            {"model": "   "},
            {"model_version": ""},
            {"lesson": ""},
        ):
            with self.subTest(kwargs=kwargs):
                self._assert_missing_rejected(_delta("FD-BLANK", **kwargs))

    def test_literal_unknown_sentinel_text_is_valid_business_value_not_missing(self):
        deltas = [
            _delta(
                "FD-LITERAL-UNKNOWN",
                model="UNKNOWN_MODEL",
                model_version="UNKNOWN_VERSION",
                lesson="UNKNOWN_LESSON_PAYLOAD",
            ),
            _delta(
                "FD-NORMAL",
                model="C-DANCE",
                model_version="2.5",
                lesson="lesson-A",
            ),
        ]
        overall = _projection_result()
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            side_effect=deltas,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection",
            return_value=overall,
        ) as projection:
            result = assess_source_bound_post_final_delta(
                {
                    "assessment_id": "A",
                    "hypothesis_id": "H",
                    "final_delta_inputs": [{"source": "a"}, {"source": "b"}],
                },
                project_root=REPO_ROOT,
            )

        internal = projection.call_args.args[0]
        self.assertEqual(len(internal["final_deltas"]), 2)
        self.assertEqual(
            internal["final_deltas"][0]["candidate_learning_evidence"]["candidate_lesson"],
            "UNKNOWN_LESSON_PAYLOAD",
        )
        self.assertTrue(
            result["source_binding"]["cohort_partition_requires_explicit_nonempty_values"]
        )
        self.assertFalse(result["source_binding"]["missing_value_sentinels_used"])

    def test_literal_unknown_and_normal_values_require_explicit_maturity_target(self):
        deltas = [
            _delta(
                "FD-LITERAL-UNKNOWN",
                model="UNKNOWN_MODEL",
                model_version="UNKNOWN_VERSION",
                lesson="UNKNOWN_LESSON_PAYLOAD",
            ),
            _delta("FD-NORMAL"),
        ]
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            side_effect=deltas,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection",
            return_value=_projection_result(),
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


if __name__ == "__main__":
    unittest.main()
