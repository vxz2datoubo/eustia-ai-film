from pathlib import Path
import unittest

from learning_retriever.expected_observed import (
    ExpectedObservedEvalError,
    evaluate_expected_vs_observed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def payload_with_observation(observation: dict, *, provenance: dict | None = None) -> dict:
    return {
        "eval_id": "EOE-TRUTHFULNESS",
        "expectations": [
            {
                "field": "composition",
                "declared_value": {"primary_mechanism": "lateral_pressure"},
                "provenance": {"source": "cinematic_intent_contract"},
            }
        ],
        "reverse_observation": {
            "fields": {},
            "expectation_observations": {"composition": observation},
            "provenance": provenance
            or {
                "evidence_source": "review_notes",
                "inspection_mode": "manual_structured_review",
                "temporal_coverage": {"type": "partial"},
                "confidence": "MEDIUM",
                "claimed_frame_by_frame_review": False,
            },
        },
    }


class ExpectedObservedTruthfulnessTests(unittest.TestCase):
    def test_unknown_outcome_cannot_smuggle_failure_category(self):
        payload = payload_with_observation(
            {
                "comparison_mode": "explicit_observation_judgment",
                "match_state": "UNKNOWN",
                "failure_category": "aesthetic_composition",
            }
        )
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_INVALID_FAILURE_CATEGORY")

    def test_pass_outcome_cannot_smuggle_failure_category(self):
        payload = payload_with_observation(
            {
                "comparison_mode": "exact_value",
                "observed_value": {"primary_mechanism": "lateral_pressure"},
                "failure_category": "aesthetic_composition",
            }
        )
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_INVALID_FAILURE_CATEGORY")

    def test_empty_explicit_match_requires_field_evidence(self):
        payload = payload_with_observation(
            {
                "comparison_mode": "explicit_observation_judgment",
                "match_state": "MATCH",
            }
        )
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_MISSING_PROVENANCE")

    def test_sampled_inspection_cannot_use_frame_by_frame_coverage_label(self):
        provenance = {
            "evidence_source": "fixed_interval_screenshot_archive",
            "inspection_mode": "fixed_interval_sampling",
            "temporal_coverage": {"type": "frame_by_frame", "sample_interval_seconds": 0.25},
            "confidence": "MEDIUM",
            "claimed_frame_by_frame_review": False,
        }
        payload = payload_with_observation(
            {
                "comparison_mode": "explicit_observation_judgment",
                "match_state": "UNKNOWN",
            },
            provenance=provenance,
        )
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_FRAME_BY_FRAME_CLAIM_CONFLICT")

    def test_temporal_coverage_type_is_required(self):
        provenance = {
            "evidence_source": "review_notes",
            "inspection_mode": "manual_structured_review",
            "temporal_coverage": {"sample_interval_seconds": 0.25},
            "confidence": "MEDIUM",
            "claimed_frame_by_frame_review": False,
        }
        payload = payload_with_observation(
            {
                "comparison_mode": "explicit_observation_judgment",
                "match_state": "UNKNOWN",
            },
            provenance=provenance,
        )
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_MISSING_PROVENANCE")


if __name__ == "__main__":
    unittest.main()
