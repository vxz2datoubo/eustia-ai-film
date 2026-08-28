from pathlib import Path
import unittest

from learning_retriever.expected_observed import (
    ExpectedObservedEvalError,
    evaluate_expected_vs_observed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def base_payload() -> dict:
    return {
        "eval_id": "EOE-CONTROL-HARDENING",
        "expectations": [
            {
                "field": "composition",
                "declared_value": {"primary_mechanism": "lateral_pressure"},
                "provenance": {"source": "cinematic_intent_contract"},
            }
        ],
        "reverse_observation": {
            "fields": {},
            "expectation_observations": {
                "composition": {
                    "comparison_mode": "exact_value",
                    "observed_value": {"primary_mechanism": "lateral_pressure"},
                }
            },
            "provenance": {
                "evidence_source": "controlled_generation_review",
                "inspection_mode": "manual_structured_review",
                "temporal_coverage": {"type": "relevant_shot_full_duration"},
                "confidence": "HIGH",
                "claimed_frame_by_frame_review": False,
            },
        },
    }


class ExpectedObservedControlHardeningTests(unittest.TestCase):
    def test_target_variable_without_control_evidence_is_not_clean(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "UNVERIFIED_CONTROL")
        self.assertFalse(result["controlled_eval"]["non_target_controls_verified"])

    def test_clean_requires_explicit_control_verification_and_provenance(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": {
                "source": "generation_manifest_pair",
                "verified_equal": [
                    "screenplay",
                    "assets_and_reference_responsibilities",
                    "model_version",
                    "generation_settings",
                    "duration",
                    "story_goal",
                    "camera_contract",
                ],
            },
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "CLEAN")
        self.assertTrue(result["controlled_eval"]["non_target_controls_verified"])
        self.assertTrue(result["controlled_eval"]["control_provenance"])

    def test_verified_controls_without_provenance_fail_closed(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
        }
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_MISSING_PROVENANCE")

    def test_explicit_confound_overrides_clean_assertion(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": ["camera_position_changed"],
            "non_target_controls_verified": True,
            "control_provenance": {"source": "generation_manifest_pair"},
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "CONFOUNDED")
        self.assertEqual(result["controlled_eval"]["confounds"], ["camera_position_changed"])


if __name__ == "__main__":
    unittest.main()
