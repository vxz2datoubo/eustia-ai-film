from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever.expected_observed import evaluate_expected_vs_observed
from learning_retriever.final_delta import (
    STRUCTURAL_GATE_CODES,
    FinalDeltaEvidenceError,
    compile_final_delta_learning_evidence,
)
from learning_retriever.targeted_repair import plan_targeted_repair


REPO_ROOT = Path(__file__).resolve().parents[3]
EOE_SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)
POLICY = yaml.safe_load(
    (REPO_ROOT / "10_运行时/final_delta_learning_policy.yaml").read_text(encoding="utf-8")
)
SOAC_SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
CONTROL_REQUIREMENTS = list(SOAC_SCHEMA["validation"]["controlled_eval_requirements"])


def _case_payload(case_id: str) -> dict:
    case = next(item for item in EOE_SUITE["cases"] if item["id"] == case_id)
    return deepcopy(case["payload"])


def _change(change_id: str, changed: list[str], preserved: list[str] | None = None) -> dict:
    return {
        "change_id": change_id,
        "changed_variables": changed,
        "preserved_variables": preserved or [],
        "revoked_variables": [],
        "experimental_variables": [],
        "scope": "EPISODIC_WORK_ITEM",
        "evidence_refs": [f"evidence::{change_id}"],
        "user_confirmation_state": "CONFIRMED_BETTER",
        "rationale": "source-bound regression fixture",
    }


def _learning(**overrides) -> dict:
    value = {
        "candidate_lesson": None,
        "inferred_intent": None,
        "real_goal": None,
        "value_priority": [],
        "alternative_explanations": [],
        "counterfactuals": [],
        "applicable_context": [],
        "non_applicable_context": [],
        "boundaries": [],
        "failure_conditions": [],
        "model_or_tool_dependency": None,
        "user_feedback_refs": [],
    }
    value.update(overrides)
    return value


def _compile(before_input: dict, after_input: dict, change: dict, learning: dict | None = None) -> dict:
    return compile_final_delta_learning_evidence(
        {
            "before_eval_input": before_input,
            "after_eval_input": after_input,
            "change_record": change,
            "learning_context": learning or _learning(),
        },
        project_root=REPO_ROOT,
    )


def _controlled_payload(*, eval_id: str, density_pass: bool, composition_pass: bool = True) -> dict:
    density_expected = {"detail_budget": "selective"}
    composition_expected = {"primary_mechanism": "lateral_pressure"}
    return {
        "eval_id": eval_id,
        "expectations": [
            {
                "field": "visual_density",
                "declared_value": density_expected,
                "provenance": {"source": "cinematic_intent_contract"},
            },
            {
                "field": "composition",
                "declared_value": composition_expected,
                "provenance": {"source": "cinematic_intent_contract"},
            },
        ],
        "reverse_observation": {
            "fields": {},
            "expectation_observations": {
                "visual_density": {
                    "comparison_mode": "exact_value",
                    "observed_value": density_expected if density_pass else {"detail_budget": "overloaded"},
                    **({} if density_pass else {"failure_category": "visual_density"}),
                    "evidence_refs": [f"{eval_id}::density"],
                },
                "composition": {
                    "comparison_mode": "exact_value",
                    "observed_value": composition_expected if composition_pass else {"primary_mechanism": "flat_centered"},
                    **({} if composition_pass else {"failure_category": "aesthetic_composition"}),
                    "evidence_refs": [f"{eval_id}::composition"],
                },
            },
            "provenance": {
                "evidence_source": "controlled_generation_review",
                "inspection_mode": "manual_structured_review",
                "temporal_coverage": {"type": "relevant_shot_full_duration"},
                "confidence": "HIGH",
                "media_refs": [f"media::{eval_id}"],
                "claimed_frame_by_frame_review": False,
            },
        },
        "controlled_eval": {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": {
                "source": "generation_manifest_pair",
                "verified_equal": list(CONTROL_REQUIREMENTS),
                "not_applicable": [],
                "not_applicable_reasons": {},
                "evidence_refs": [f"{eval_id}::manifest_a", f"{eval_id}::manifest_b"],
            },
        },
        "context": {
            "model": "C-DANCE",
            "model_version": "2.5",
            "work_item_id": "FD-SOURCE-BOUND-001",
        },
    }


class FinalDeltaSourceBoundTests(unittest.TestCase):
    def test_policy_keeps_final_delta_non_promoting(self):
        principles = POLICY["principles"]
        self.assertTrue(principles["observation_is_not_causality"])
        self.assertTrue(principles["single_success_cannot_universalize"])
        self.assertTrue(principles["automatic_maturity_promotion_forbidden"])
        self.assertTrue(principles["automatic_canonical_writeback_forbidden"])

    def test_kaim_production_repair_resolves_from_source_inputs_only(self):
        before = _case_payload("EOE-PROD-KAIM-DISAPPEARANCE-001")
        after = deepcopy(before)
        after["eval_id"] = "EOE-PROD-KAIM-DISAPPEARANCE-AFTER-SOURCE-BOUND"
        observation = after["reverse_observation"]["expectation_observations"]["attention_handoff"]
        observation["match_state"] = "MATCH"
        observation["observed_value"] = {
            "first_returned_master_state": "kaim_already_absent",
            "exit_visibility": "withheld_during_cutaway",
        }
        observation.pop("failure_category", None)
        observation["evidence_refs"] = ["issue_19_after_sampled_review"]
        result = _compile(
            before,
            after,
            _change(
                "FD-KAIM-SOURCE-BOUND",
                ["attention_handoff_transition_design"],
                ["story_goal", "character_identity", "scene_topology"],
            ),
            _learning(
                candidate_lesson="Hide departure during cutaway and reveal absence on return.",
                alternative_explanations=["edit timing may also contribute"],
                counterfactuals=["return before exit completes should restore failure"],
                boundaries=["only sampled production repair is evidenced"],
            ),
        )
        transitions = {item["field"]: item["transition"] for item in result["field_transitions"]}
        self.assertEqual(transitions["attention_handoff"], "RESOLVED")
        self.assertEqual(result["causal_evidence"]["status"], "OBSERVATIONAL_ONLY")
        self.assertFalse(result["causal_evidence"]["causal_claim_authorized"])
        self.assertTrue(result["regression_candidate_handoff"]["eligible"])
        binding = result["source_binding"]
        self.assertFalse(binding["before_eval"]["serialized_eval_result_accepted"])
        self.assertFalse(binding["after_eval"]["serialized_eval_result_accepted"])
        self.assertFalse(binding["repair_plan"]["serialized_repair_plan_accepted"])
        self.assertEqual(
            binding["repair_plan"]["mode"], "canonical_targeted_repair_reexecution"
        )

    def test_legacy_serialized_eval_and_repair_plan_are_rejected_even_if_consistent(self):
        before_input = _controlled_payload(eval_id="FD-LEGACY-BEFORE", density_pass=False)
        after_input = _controlled_payload(eval_id="FD-LEGACY-AFTER", density_pass=True)
        before_result = evaluate_expected_vs_observed(before_input, project_root=REPO_ROOT)
        after_result = evaluate_expected_vs_observed(after_input, project_root=REPO_ROOT)
        repair_plan = plan_targeted_repair(before_input, project_root=REPO_ROOT)
        with self.assertRaises(FinalDeltaEvidenceError) as ctx:
            compile_final_delta_learning_evidence(
                {
                    "before_eval": before_result,
                    "after_eval": after_result,
                    "repair_plan": repair_plan,
                    "change_record": _change("FD-LEGACY", ["reference_signal_decoupling"]),
                    "learning_context": _learning(),
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "FINAL_DELTA_UNKNOWN_FIELD")

    def test_joint_tampering_of_serialized_result_cannot_suppress_source_failure(self):
        before_input = _controlled_payload(eval_id="FD-JOINT-BEFORE", density_pass=False)
        after_input = _controlled_payload(eval_id="FD-JOINT-AFTER", density_pass=True)
        forged_result = evaluate_expected_vs_observed(before_input, project_root=REPO_ROOT)
        forged_result["results"][0]["outcome"] = "PASS"
        forged_result["status"] = "PASS"
        forged_result["targeted_repair_handoff"]["items"] = []
        forged_result["targeted_repair_handoff"]["requires_director_or_targeted_repair_step"] = False
        result = _compile(
            before_input,
            after_input,
            _change("FD-JOINT-TAMPER", ["reference_signal_decoupling"]),
        )
        transitions = {item["field"]: item["transition"] for item in result["field_transitions"]}
        self.assertEqual(transitions["visual_density"], "RESOLVED")
        self.assertEqual(result["source_repair_plan_id"], "TARGETED_REPAIR::FD-JOINT-BEFORE")
        self.assertNotEqual(forged_result["status"], "FAIL")

    def test_joint_tampering_of_serialized_repair_plan_has_no_input_surface(self):
        before_input = _controlled_payload(eval_id="FD-PLAN-BEFORE", density_pass=False)
        after_input = _controlled_payload(eval_id="FD-PLAN-AFTER", density_pass=True)
        forged_plan = plan_targeted_repair(before_input, project_root=REPO_ROOT)
        forged_plan["repair_items"] = []
        package = {
            "before_eval_input": before_input,
            "after_eval_input": after_input,
            "repair_plan": forged_plan,
            "change_record": _change("FD-PLAN-TAMPER", ["reference_signal_decoupling"]),
        }
        with self.assertRaises(FinalDeltaEvidenceError) as ctx:
            compile_final_delta_learning_evidence(package, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "FINAL_DELTA_UNKNOWN_FIELD")

    def test_invalid_before_source_preserves_upstream_rejection(self):
        before = _controlled_payload(eval_id="FD-BAD-BEFORE", density_pass=False)
        before["reverse_observation"]["provenance"] = {}
        after = _controlled_payload(eval_id="FD-BAD-AFTER", density_pass=True)
        with self.assertRaises(FinalDeltaEvidenceError) as ctx:
            _compile(before, after, _change("FD-BAD-SOURCE", ["reference_signal_decoupling"]))
        self.assertEqual(ctx.exception.code, "FINAL_DELTA_BEFORE_EVAL_REJECTED")
        self.assertIn("EVAL_MISSING_PROVENANCE", ctx.exception.message)
        self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_same_eval_id_is_rejected_as_before_after_collision(self):
        before = _controlled_payload(eval_id="FD-SAME-ID", density_pass=False)
        after = _controlled_payload(eval_id="FD-SAME-ID", density_pass=True)
        with self.assertRaises(FinalDeltaEvidenceError) as ctx:
            _compile(before, after, _change("FD-SAME-ID-CHANGE", ["reference_signal_decoupling"]))
        self.assertEqual(ctx.exception.code, "FINAL_DELTA_EVAL_ID_COLLISION")

    def test_model_version_mismatch_is_not_comparable(self):
        before = _controlled_payload(eval_id="FD-VERSION-BEFORE", density_pass=False)
        after = _controlled_payload(eval_id="FD-VERSION-AFTER", density_pass=True)
        after["context"]["model_version"] = "2.6"
        result = _compile(
            before,
            after,
            _change("FD-VERSION", ["reference_signal_decoupling"]),
        )
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("MODEL_VERSION_MISMATCH", result["comparison_reasons"])
        self.assertEqual(result["field_transitions"], [])

    def test_pass_regression_blocks_regression_candidate(self):
        before = _controlled_payload(
            eval_id="FD-REG-BEFORE", density_pass=False, composition_pass=True
        )
        after = _controlled_payload(
            eval_id="FD-REG-AFTER", density_pass=True, composition_pass=False
        )
        result = _compile(
            before,
            after,
            _change("FD-PASS-REGRESSION", ["reference_signal_decoupling"], ["composition"]),
        )
        transitions = {item["field"]: item["transition"] for item in result["field_transitions"]}
        self.assertEqual(transitions["visual_density"], "RESOLVED")
        self.assertEqual(transitions["composition"], "REGRESSED")
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_caller_declared_complete_controls_cannot_mint_clean_or_causality(self):
        before = _controlled_payload(eval_id="FD-CONTROL-BEFORE", density_pass=False)
        after = _controlled_payload(eval_id="FD-CONTROL-AFTER", density_pass=True)
        result = _compile(
            before,
            after,
            _change("FD-CONTROL", ["reference_signal_decoupling"]),
        )
        self.assertEqual(result["causal_evidence"]["before_control_status"], "UNVERIFIED_CONTROL")
        self.assertEqual(result["causal_evidence"]["after_control_status"], "UNVERIFIED_CONTROL")
        self.assertEqual(result["causal_evidence"]["status"], "CONTROL_NOT_VERIFIED")
        self.assertFalse(result["causal_evidence"]["eligible_for_causal_analysis"])
        self.assertFalse(result["candidate_learning_evidence"]["generalization_authorized"])


if __name__ == "__main__":
    unittest.main()
