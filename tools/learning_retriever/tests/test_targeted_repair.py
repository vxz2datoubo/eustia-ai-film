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


def _case_payload(case_id: str) -> dict:
    case = next(item for item in EOE_SUITE["cases"] if item["id"] == case_id)
    return deepcopy(case["payload"])


def _serialized_eval(case_id: str) -> dict:
    return evaluate_expected_vs_observed(_case_payload(case_id), project_root=REPO_ROOT)


class TargetedRepairPlannerTests(unittest.TestCase):
    def test_policy_covers_canonical_failure_vocabulary_exactly(self):
        canonical = set(SOAC["reverse_compiler"]["failure_categories"])
        routes = POLICY["failure_category_routes"]
        surfaces = set(POLICY["repair_surfaces"])
        self.assertEqual(set(routes), canonical)
        self.assertTrue(set(routes.values()).issubset(surfaces))
        self.assertIn(POLICY["unknown_outcome_route"], surfaces)

    def test_regression_cases_route_expected_surfaces_from_source_payload(self):
        for case in REPAIR_SUITE["cases"]:
            with self.subTest(case=case["id"]):
                plan = plan_targeted_repair(
                    _case_payload(case["source_eval_case"]),
                    project_root=REPO_ROOT,
                )
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
                self.assertEqual(
                    plan["source_binding"]["mode"],
                    "canonical_expected_observed_reexecution",
                )
                self.assertFalse(plan["source_binding"]["serialized_eval_result_accepted"])
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

        plan = plan_targeted_repair(
            _case_payload("EOE-EXPLICIT-FAIL-001"),
            project_root=REPO_ROOT,
        )
        self.assertEqual(plan["repair_items"][0]["failure_category"], "camera")
        self.assertEqual(
            plan["repair_items"][0]["repair_surface"],
            "UPSTREAM_CAMERA_CONTRACT_REVIEW",
        )

    def test_pass_dimensions_are_preserved_and_never_repaired(self):
        plan = plan_targeted_repair(
            _case_payload("EOE-EXACT-PASS-001"),
            project_root=REPO_ROOT,
        )
        self.assertFalse(plan["repair_required"])
        self.assertEqual(plan["repair_items"], [])
        self.assertEqual(plan["preserved_pass_fields"], ["composition"])

    def test_fail_is_prioritized_before_unknown_from_same_source_payload(self):
        payload = _case_payload("EOE-EXPLICIT-FAIL-001")
        payload["eval_id"] = "TR-FAIL-THEN-UNKNOWN"
        payload["expectations"].append(
            {
                "field": "color_intent",
                "declared_value": {"color_thesis": "cold_stone"},
                "provenance": {"source": "cinematic_intent_contract"},
            }
        )
        plan = plan_targeted_repair(payload, project_root=REPO_ROOT)
        self.assertEqual([item["priority"] for item in plan["repair_items"]], [1, 2])
        self.assertEqual(plan["repair_items"][0]["failure_category"], "camera")
        self.assertEqual(plan["repair_items"][1]["field"], "color_intent")
        self.assertEqual(plan["repair_items"][1]["repair_surface"], "EVIDENCE_ACQUISITION")
        self.assertFalse(plan["repair_items"][1]["creative_mutation_authorized"])

    def test_serialized_evaluator_output_is_never_a_planner_authority(self):
        serialized = _serialized_eval("EOE-EXPLICIT-FAIL-001")
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(serialized, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_UPSTREAM_EVAL_REJECTED")
        self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_joint_category_substitution_is_rejected_even_when_result_and_handoff_match(self):
        forged = _serialized_eval("EOE-EXPLICIT-FAIL-001")
        forged["results"][0]["failure_category"] = "dialogue"
        forged["targeted_repair_handoff"]["items"][0]["failure_category"] = "dialogue"
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_UPSTREAM_EVAL_REJECTED")

    def test_joint_fail_to_pass_suppression_is_rejected_even_when_document_is_consistent(self):
        forged = _serialized_eval("EOE-EXPLICIT-FAIL-001")
        forged["results"][0]["outcome"] = "PASS"
        forged["results"][0]["failure_category"] = None
        forged["status"] = "PASS"
        forged["targeted_repair_handoff"]["items"] = []
        forged["targeted_repair_handoff"]["requires_director_or_targeted_repair_step"] = False
        with self.assertRaises(TargetedRepairPlanError) as ctx:
            plan_targeted_repair(forged, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "REPAIR_UPSTREAM_EVAL_REJECTED")

    def test_declared_structural_attacks_are_source_binding_regressions(self):
        declared = {case["id"]: case for case in REPAIR_SUITE["structural_gate_cases"]}
        self.assertIn("TRP-SERIALIZED-RESULT-REJECTED-001", declared)
        self.assertIn("TRP-JOINT-CATEGORY-SUBSTITUTION-001", declared)
        self.assertIn("TRP-JOINT-FAIL-PASS-SUPPRESSION-001", declared)
        for case in declared.values():
            self.assertEqual(case["expected_error_code"], "REPAIR_UPSTREAM_EVAL_REJECTED")

    def test_kaim_production_failure_routes_only_edit_handoff(self):
        plan = plan_targeted_repair(
            _case_payload("EOE-PROD-KAIM-DISAPPEARANCE-001"),
            project_root=REPO_ROOT,
        )
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
