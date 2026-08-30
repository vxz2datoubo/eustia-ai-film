from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever.expected_observed import evaluate_expected_vs_observed
from learning_retriever.targeted_repair import (
    STRUCTURAL_GATE_CODES,
    TargetedRepairPlanError,
    plan_targeted_repair,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EOE_SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)
REPAIR_SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/targeted_repair_regression_cases.yaml").read_text(encoding="utf-8")
)
POLICY = yaml.safe_load(
    (REPO_ROOT / "10_运行时/targeted_repair_policy.yaml").read_text(encoding="utf-8")
)
SOAC = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
PROJECT = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))


def _eval_case(case_id: str):
    case = next(item for item in EOE_SUITE["cases"] if item["id"] == case_id)
    return evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)


class TargetedRepairPlannerTests(unittest.TestCase):
    def test_policy_covers_canonical_failure_vocabulary_exactly(self):
        canonical = set(SOAC["reverse_compiler"]["failure_categories"])
        routes = POLICY["failure_category_routes"]
        surfaces = set(POLICY["repair_surfaces"])
        self.assertEqual(set(routes), canonical)
        self.assertTrue(set(routes.values()).issubset(surfaces))
        self.assertIn(POLICY["unknown_outcome_route"], surfaces)

    def test_regression_cases_route_expected_surfaces(self):
        for case in REPAIR_SUITE["cases"]:
            with self.subTest(case=case["id"]):
                evaluated = _eval_case(case["source_eval_case"])
                plan = plan_targeted_repair(evaluated, project_root=REPO_ROOT)
                self.assertEqual(plan["source_eval_status"], case["expected_source_eval_status"])
                self.assertEqual(
                    [item["field"] for item in plan["repair_items"]],
                    case["expected_repair_fields"],
                )
                expected_surfaces = case.get("expected_surface_by_field") or {}
                actual_surfaces = {
                    item["field"]: item["repair_surface"] for item in plan["repair_items"]
                }
                self.assertEqual(actual_surfaces, expected_surfaces)
                if "expected_control_status" in case:
                    self.assertEqual(plan["control_status"], case["expected_control_status"])
                if "expected_causal_evidence_status" in case:
                    self.assertEqual(
                        plan["causal_evidence_status"], case["expected_causal_evidence_status"]
                    )
                if case.get("expected_observation_sampled"):
                    self.assertTrue(plan["observation_provenance"]["sampled_temporal_evidence"])
                self.assertFalse(plan["prompt_mutation_authorized"])
                self.assertFalse(plan["generation_authorized"])
                self.assertFalse(plan["camera_authority_mutation_authorized"])
                self.assertFalse(plan["canonical_mutation_authorized"])
                self.assertFalse(plan["learning_writeback_authorized"])
                self.assertFalse(plan["maturity_promotion_authorized"])
                self.assertFalse(plan["causal_claim_authorized"])

    def test_camera_failure_routes_to_review_without_minting_authority(self):
        self.assertEqual(
            POLICY["failure_category_routes"]["camera"],
            "UPSTREAM_CAMERA_CONTRACT_REVIEW",
        )
        surface = POLICY["repair_surfaces"]["UPSTREAM_CAMERA_CONTRACT_REVIEW"]
        self.assertEqual(surface["authority_role"], "canonical_upstream_camera_readback_required")
        self.assertFalse(surface["may_mutate_prompt"])
        self.assertTrue(PROJECT["policy"]["cinematic_intent_camera_authority_requires_canonical_readback"])
        self.assertTrue(PROJECT["policy"]["cinematic_intent_callers_cannot_supply_or_mint_camera_authority"])
        self.assertTrue(POLICY["principles"]["camera_authority_mutation_forbidden"])

    def test_pass_dimensions_are_preserved_and_never_repaired(self):
        result = _eval_case("EOE-EXACT-PASS-001")
        plan = plan_targeted_repair(result, project_root=REPO_ROOT)
        self.assertFalse(plan["repair_required"])
        self.assertEqual(plan["repair_items"], [])
        self.assertEqual(plan["preserved_pass_fields"], ["composition"])

    def test_fail_is_prioritized_before_unknown(self):
        evaluated = _eval_case("EOE-EXPLICIT-FAIL-001")
        fail_item = deepcopy(evaluated["results"][0])
        unknown_item = {
            "field": "color_intent",
            "outcome": "UNKNOWN",
            "expected_value": {"color_thesis": "cold_stone"},
            "observed_value": None,
            "failure_category": None,
            "expectation_provenance": {"source": "contract"},
            "evidence_refs": [],
            "note": "not observed",
        }
        evaluated["results"].append(unknown_item)
        evaluated["targeted_repair_handoff"]["items"] = [
            {
                "field": fail_item["field"],
                "outcome": fail_item["outcome"],
                "expected_value": fail_item["expected_value"],
                "observed_value": fail_item["observed_value"],
                "failure_category": fail_item["failure_category"],
                "evidence_refs": fail_item["evidence_refs"],
            },
            {
                "field": unknown_item["field"],
                "outcome": unknown_item["outcome"],
                "expected_value": unknown_item["expected_value"],
                "observed_value": unknown_item["observed_value"],
                "failure_category": None,
                "evidence_refs": [],
            },
        ]
        plan = plan_targeted_repair(evaluated, project_root=REPO_ROOT)
        self.assertEqual([item["priority"] for item in plan["repair_items"]], [1, 2])
        self.assertEqual(plan["repair_items"][1]["repair_surface"], "EVIDENCE_ACQUISITION")
        self.assertFalse(plan["repair_items"][1]["creative_mutation_authorized"])

    def test_structural_attack_cases_fail_closed(self):
        for case in REPAIR_SUITE["structural_gate_cases"]:
            with self.subTest(case=case["id"]):
                evaluated = _eval_case(case["source_eval_case"])
                mutation = case["mutation"]
                if mutation == "remove_first_handoff_item":
                    evaluated["targeted_repair_handoff"]["items"] = []
                elif mutation == "set_prompt_mutation_authorized_true":
                    evaluated["targeted_repair_handoff"]["prompt_mutation_authorized"] = True
                elif mutation == "replace_failure_category_with_unknown":
                    evaluated["results"][0]["failure_category"] = "invented_failure_category"
                    evaluated["targeted_repair_handoff"]["items"][0][
                        "failure_category"
                    ] = "invented_failure_category"
                else:
                    self.fail(f"unsupported test mutation: {mutation}")
                with self.assertRaises(TargetedRepairPlanError) as ctx:
                    plan_targeted_repair(evaluated, project_root=REPO_ROOT)
                self.assertEqual(ctx.exception.code, case["expected_error_code"])
                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_kaim_production_failure_routes_only_edit_handoff(self):
        evaluated = _eval_case("EOE-PROD-KAIM-DISAPPEARANCE-001")
        plan = plan_targeted_repair(evaluated, project_root=REPO_ROOT)
        self.assertEqual(len(plan["repair_items"]), 1)
        item = plan["repair_items"][0]
        self.assertEqual(item["field"], "attention_handoff")
        self.assertEqual(item["repair_surface"], "TRANSITION_EDIT_REVIEW")
        self.assertEqual(item["failure_category"], "attention_handoff")
        self.assertIn("issue_19_comment_5454103847", item["evidence_refs"])
        self.assertTrue(plan["observation_provenance"]["sampled_temporal_evidence"])
        self.assertFalse(plan["prompt_mutation_authorized"])


if __name__ == "__main__":
    unittest.main()