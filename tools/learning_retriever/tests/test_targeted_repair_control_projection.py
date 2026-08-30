from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever.expected_observed import evaluate_expected_vs_observed
from learning_retriever.targeted_repair import TargetedRepairPlanError, plan_targeted_repair


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
CANONICAL_CONTROLS = list(SCHEMA["validation"]["controlled_eval_requirements"])


def payload(*, controlled_claim: bool = True) -> dict:
    value = {
        "eval_id": "TR-CONTROL-PROJECTION",
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
                    "evidence_refs": ["frame_review_001"],
                }
            },
            "provenance": {
                "evidence_source": "controlled_generation_review",
                "inspection_mode": "manual_structured_review",
                "temporal_coverage": {"type": "relevant_shot_full_duration"},
                "confidence": "HIGH",
                "media_refs": ["generation_A", "generation_B"],
                "claimed_frame_by_frame_review": False,
            },
        },
    }
    if controlled_claim:
        value["controlled_eval"] = {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": {
                "source": "generation_manifest_pair",
                "verified_equal": list(CANONICAL_CONTROLS),
                "not_applicable": [],
                "not_applicable_reasons": {},
                "evidence_refs": ["generation_A_manifest", "generation_B_manifest"],
            },
        }
    return value


def evaluated(*, controlled_claim: bool = True) -> dict:
    return evaluate_expected_vs_observed(payload(controlled_claim=controlled_claim), project_root=REPO_ROOT)


class TargetedRepairControlProjectionTests(unittest.TestCase):
    def test_complete_caller_control_declaration_remains_unverified_and_is_accepted_as_unverified(self):
        result = evaluated(controlled_claim=True)
        self.assertEqual(result["control_status"], "UNVERIFIED_CONTROL")
        self.assertFalse(result["controlled_eval"]["non_target_controls_verified"])
        self.assertTrue(result["controlled_eval"]["caller_claimed_non_target_controls_verified"])
        self.assertEqual(result["controlled_eval"]["control_verification_state"], "DECLARED_BY_CALLER")
        plan = plan_targeted_repair(result, project_root=REPO_ROOT)
        self.assertEqual(plan["control_status"], "UNVERIFIED_CONTROL")
        self.assertEqual(plan["controlled_eval"]["canonical_control_requirements"], CANONICAL_CONTROLS)
        self.assertTrue(plan["controlled_eval"]["control_provenance"]["complete_against_canonical"])
        self.assertFalse(plan["causal_claim_authorized"])

    def test_caller_cannot_flip_uncontrolled_result_to_clean(self):
        forged = evaluated(controlled_claim=False)
        forged["control_status"] = "CLEAN"
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_CONTROL_PROJECTION_MISMATCH")

    def test_caller_cannot_flip_unverified_complete_declaration_to_clean(self):
        forged = deepcopy(evaluated(controlled_claim=True))
        forged["control_status"] = "CLEAN"
        forged["controlled_eval"]["non_target_controls_verified"] = True
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_CONTROL_PROJECTION_MISMATCH")

    def test_caller_cannot_replace_canonical_requirement_projection(self):
        forged = deepcopy(evaluated(controlled_claim=True))
        forged["controlled_eval"]["canonical_control_requirements"] = ["caller_defined_control"]
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_CONTROL_PROJECTION_MISMATCH")

    def test_caller_cannot_claim_actual_verification_on_unverified_projection(self):
        forged = deepcopy(evaluated(controlled_claim=True))
        forged["controlled_eval"]["non_target_controls_verified"] = True
        forged["control_status"] = "CLEAN"
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_CONTROL_PROJECTION_MISMATCH")

    def test_confounded_status_requires_explicit_confounds(self):
        forged = deepcopy(evaluated(controlled_claim=True))
        forged["control_status"] = "CONFOUNDED"
        forged["controlled_eval"]["confounds"] = []
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_CONTROL_PROJECTION_MISMATCH")


if __name__ == "__main__":
    unittest.main()
