from pathlib import Path
import unittest

import yaml

from learning_retriever.expected_observed import (
    ExpectedObservedEvalError,
    evaluate_expected_vs_observed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
CANONICAL_CONTROL_REQUIREMENTS = list(SCHEMA["validation"]["controlled_eval_requirements"])


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


def complete_control_provenance() -> dict:
    return {
        "source": "generation_manifest_pair",
        "verified_equal": list(CANONICAL_CONTROL_REQUIREMENTS),
        "not_applicable": [],
        "not_applicable_reasons": {},
        "evidence_refs": ["generation_A_manifest", "generation_B_manifest"],
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
        self.assertFalse(result["controlled_eval"]["caller_claimed_non_target_controls_verified"])
        self.assertEqual(result["controlled_eval"]["control_verification_state"], "NOT_VERIFIED")

    def test_complete_caller_control_declaration_cannot_mint_clean(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": complete_control_provenance(),
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "UNVERIFIED_CONTROL")
        self.assertFalse(result["controlled_eval"]["non_target_controls_verified"])
        self.assertTrue(result["controlled_eval"]["caller_claimed_non_target_controls_verified"])
        self.assertEqual(result["controlled_eval"]["control_verification_state"], "DECLARED_BY_CALLER")
        provenance = result["controlled_eval"]["control_provenance"]
        self.assertTrue(provenance["complete_against_canonical"])
        self.assertEqual(provenance["verification_state"], "DECLARED_BY_CALLER")
        self.assertEqual(
            set(provenance["canonical_requirements_covered"]),
            set(CANONICAL_CONTROL_REQUIREMENTS),
        )
        self.assertEqual(
            result["controlled_eval"]["canonical_control_requirements"],
            CANONICAL_CONTROL_REQUIREMENTS,
        )

    def test_reviewer_adversarial_complete_self_attestation_is_not_clean(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "lens_choice",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": {
                "source": "caller-says-so",
                "verified_equal": list(CANONICAL_CONTROL_REQUIREMENTS),
                "not_applicable": [],
                "not_applicable_reasons": {},
                "evidence_refs": ["fake-evidence-ref"],
            },
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertNotEqual(result["control_status"], "CLEAN")
        self.assertEqual(result["control_status"], "UNVERIFIED_CONTROL")
        self.assertFalse(result["controlled_eval"]["non_target_controls_verified"])
        self.assertTrue(result["controlled_eval"]["caller_claimed_non_target_controls_verified"])
        self.assertEqual(result["controlled_eval"]["control_verification_state"], "DECLARED_BY_CALLER")

    def test_boolean_plus_thin_provenance_cannot_mint_clean(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": {
                "source": "caller_assertion",
                "verified_equal": [CANONICAL_CONTROL_REQUIREMENTS[0]],
                "evidence_refs": ["one_note"],
            },
        }
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_CONTROL_REQUIREMENTS_INCOMPLETE")

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

    def test_verified_controls_without_evidence_refs_fail_closed(self):
        payload = base_payload()
        provenance = complete_control_provenance()
        provenance["evidence_refs"] = []
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": provenance,
        }
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_MISSING_PROVENANCE")

    def test_noncanonical_control_requirement_fails_closed(self):
        payload = base_payload()
        provenance = complete_control_provenance()
        provenance["verified_equal"].append("caller_invented_control")
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": provenance,
        }
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_CONTROL_PROVENANCE_INVALID")

    def test_not_applicable_reason_can_complete_declaration_but_not_mint_clean(self):
        payload = base_payload()
        requirement = CANONICAL_CONTROL_REQUIREMENTS[-1]
        provenance = complete_control_provenance()
        provenance["verified_equal"].remove(requirement)
        provenance["not_applicable"] = [requirement]
        provenance["not_applicable_reasons"] = {
            requirement: "this exact authority family is the declared target variable under test"
        }
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": provenance,
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "UNVERIFIED_CONTROL")
        self.assertFalse(result["controlled_eval"]["non_target_controls_verified"])
        self.assertTrue(result["controlled_eval"]["control_provenance"]["complete_against_canonical"])
        self.assertEqual(
            result["controlled_eval"]["control_provenance"]["verification_state"],
            "DECLARED_BY_CALLER",
        )

        payload["controlled_eval"]["control_provenance"]["not_applicable_reasons"] = {}
        with self.assertRaises(ExpectedObservedEvalError) as ctx:
            evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVAL_CONTROL_PROVENANCE_INVALID")

    def test_explicit_confound_stays_confounded_without_clean_claim(self):
        payload = base_payload()
        payload["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": ["camera_position_changed"],
            "non_target_controls_verified": False,
            "control_provenance": {
                "source": "generation_manifest_pair",
                "verified_equal": CANONICAL_CONTROL_REQUIREMENTS[:3],
                "evidence_refs": ["generation_A_manifest", "generation_B_manifest"],
            },
        }
        result = evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "CONFOUNDED")
        self.assertEqual(result["controlled_eval"]["confounds"], ["camera_position_changed"])
        self.assertFalse(result["controlled_eval"]["non_target_controls_verified"])


if __name__ == "__main__":
    unittest.main()
