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
FD_SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/final_delta_learning_regression_cases.yaml").read_text(encoding="utf-8")
)
POLICY = yaml.safe_load(
    (REPO_ROOT / "10_运行时/final_delta_learning_policy.yaml").read_text(encoding="utf-8")
)
SOAC_SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
CANONICAL_CONTROL_REQUIREMENTS = list(
    SOAC_SCHEMA["validation"]["controlled_eval_requirements"]
)


def _case_payload(case_id: str) -> dict:
    case = next(item for item in EOE_SUITE["cases"] if item["id"] == case_id)
    return deepcopy(case["payload"])


def _evaluate(payload: dict) -> dict:
    return evaluate_expected_vs_observed(payload, project_root=REPO_ROOT)


def _change_record(
    *,
    change_id: str,
    changed: list[str],
    preserved: list[str] | None = None,
    scope: str = "EPISODIC_WORK_ITEM",
) -> dict:
    return {
        "change_id": change_id,
        "changed_variables": changed,
        "preserved_variables": preserved or [],
        "revoked_variables": [],
        "experimental_variables": [],
        "scope": scope,
        "evidence_refs": [f"evidence::{change_id}"],
        "user_confirmation_state": "CONFIRMED_BETTER",
        "rationale": "bounded regression fixture",
    }


def _learning_context(**overrides) -> dict:
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


def _compile(before: dict, after: dict, change: dict, learning_context: dict | None = None) -> dict:
    plan = plan_targeted_repair(before, project_root=REPO_ROOT)
    return compile_final_delta_learning_evidence(
        {
            "before_eval": before,
            "after_eval": after,
            "repair_plan": plan,
            "change_record": change,
            "learning_context": learning_context or _learning_context(),
        },
        project_root=REPO_ROOT,
    )


def _controlled_visual_density_payload(*, eval_id: str, density_pass: bool, composition_pass: bool) -> dict:
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
                "verified_equal": list(CANONICAL_CONTROL_REQUIREMENTS),
                "not_applicable": [],
                "not_applicable_reasons": {},
                "evidence_refs": [
                    f"{eval_id}::generation_A_manifest",
                    f"{eval_id}::generation_B_manifest",
                ],
            },
        },
        "context": {
            "model": "C-DANCE",
            "model_version": "2.5",
            "work_item_id": "CONTROLLED-FD-001",
        },
    }


class FinalDeltaLearningTests(unittest.TestCase):
    def test_policy_keeps_learning_non_promoting_and_non_causal(self):
        principles = POLICY["principles"]
        self.assertTrue(principles["observation_is_not_causality"])
        self.assertTrue(principles["single_success_cannot_universalize"])
        self.assertTrue(principles["automatic_maturity_promotion_forbidden"])
        self.assertTrue(principles["automatic_canonical_writeback_forbidden"])
        self.assertTrue(principles["camera_authority_mutation_forbidden"])
        contract = POLICY["candidate_learning_contract"]
        self.assertEqual(contract["emitted_maturity"], "candidate")
        self.assertFalse(contract["promotion_authorized"])
        self.assertFalse(contract["writeback_authorized"])
        self.assertFalse(contract["generalization_authorized"])

    def test_real_kaim_repair_can_resolve_without_claiming_causality(self):
        before_payload = _case_payload("EOE-PROD-KAIM-DISAPPEARANCE-001")
        before = _evaluate(before_payload)
        after_payload = deepcopy(before_payload)
        after_payload["eval_id"] = "EOE-PROD-KAIM-DISAPPEARANCE-AFTER-001"
        observation = after_payload["reverse_observation"]["expectation_observations"]["attention_handoff"]
        observation["match_state"] = "MATCH"
        observation["observed_value"] = {
            "first_returned_master_state": "kaim_already_absent",
            "exit_visibility": "withheld_during_cutaway",
        }
        observation.pop("failure_category", None)
        observation["evidence_refs"] = ["issue_19_repair_after_sampled_review"]
        observation["note"] = "first returned master image already shows the Kaim position empty"
        after = _evaluate(after_payload)
        result = _compile(
            before,
            after,
            _change_record(
                change_id="KAIM-DISAPPEARANCE-REPAIR-001",
                changed=["attention_handoff_transition_design"],
                preserved=["story_goal", "character_identity", "scene_topology"],
            ),
            _learning_context(
                candidate_lesson="Hide the departure during the cutaway and reveal absence on return.",
                alternative_explanations=["edit timing may also contribute"],
                counterfactuals=["returning before the exit completes should restore the failure"],
                boundaries=["only this sampled production repair is evidenced"],
                user_feedback_refs=["issue_19_comment_5454103847"],
            ),
        )
        transitions = {item["field"]: item["transition"] for item in result["field_transitions"]}
        self.assertEqual(transitions["attention_handoff"], "RESOLVED")
        self.assertEqual(result["causal_evidence"]["status"], "OBSERVATIONAL_ONLY")
        self.assertFalse(result["causal_evidence"]["causal_claim_authorized"])
        evidence = result["candidate_learning_evidence"]
        self.assertEqual(evidence["maturity"], "candidate")
        self.assertFalse(evidence["generalization_authorized"])
        self.assertFalse(evidence["promotion_authorized"])
        self.assertFalse(evidence["writeback_authorized"])
        self.assertTrue(result["regression_candidate_handoff"]["eligible"])
        self.assertFalse(result["regression_candidate_handoff"]["write_authorized"])

    def test_clean_single_variable_repair_is_only_causal_analysis_candidate(self):
        before = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-CLEAN-BEFORE", density_pass=False, composition_pass=True
            )
        )
        after = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-CLEAN-AFTER", density_pass=True, composition_pass=True
            )
        )
        result = _compile(
            before,
            after,
            _change_record(
                change_id="FD-CLEAN-SINGLE-VARIABLE",
                changed=["reference_signal_decoupling"],
                preserved=["composition"],
                scope="MODEL_VERSION_BOUND",
            ),
            _learning_context(
                candidate_lesson="Decoupling reference signal roles may reduce density overload.",
                alternative_explanations=["seed variance remains possible"],
                counterfactuals=["re-run without decoupling while controls remain locked"],
                applicable_context=["C-DANCE 2.5 controlled reference-role tests"],
                failure_conditions=["non-target controls drift"],
                model_or_tool_dependency="C-DANCE 2.5",
            ),
        )
        transitions = {item["field"]: item["transition"] for item in result["field_transitions"]}
        self.assertEqual(transitions["visual_density"], "RESOLVED")
        self.assertEqual(transitions["composition"], "PRESERVED")
        self.assertEqual(
            result["causal_evidence"]["status"], "CONTROLLED_SINGLE_VARIABLE_CANDIDATE"
        )
        self.assertTrue(result["causal_evidence"]["eligible_for_causal_analysis"])
        self.assertFalse(result["causal_evidence"]["causal_claim_authorized"])
        self.assertFalse(result["candidate_learning_evidence"]["generalization_authorized"])

    def test_pass_regression_blocks_clean_repair_evidence(self):
        before = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-REGRESSION-BEFORE", density_pass=False, composition_pass=True
            )
        )
        after = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-REGRESSION-AFTER", density_pass=True, composition_pass=False
            )
        )
        result = _compile(
            before,
            after,
            _change_record(
                change_id="FD-PASS-REGRESSION",
                changed=["reference_signal_decoupling"],
                preserved=["composition"],
                scope="MODEL_VERSION_BOUND",
            ),
        )
        transitions = {item["field"]: item["transition"] for item in result["field_transitions"]}
        self.assertEqual(transitions["visual_density"], "RESOLVED")
        self.assertEqual(transitions["composition"], "REGRESSED")
        self.assertEqual(
            result["causal_evidence"]["status"], "TARGET_IMPROVED_WITH_REGRESSION"
        )
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_model_version_mismatch_is_not_comparable(self):
        before_payload = _controlled_visual_density_payload(
            eval_id="FD-VERSION-BEFORE", density_pass=False, composition_pass=True
        )
        after_payload = _controlled_visual_density_payload(
            eval_id="FD-VERSION-AFTER", density_pass=True, composition_pass=True
        )
        after_payload["context"]["model_version"] = "2.6"
        before = _evaluate(before_payload)
        after = _evaluate(after_payload)
        result = _compile(
            before,
            after,
            _change_record(
                change_id="FD-VERSION-SPLIT",
                changed=["reference_signal_decoupling"],
                scope="MODEL_VERSION_BOUND",
            ),
        )
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("MODEL_VERSION_MISMATCH", result["comparison_reasons"])
        self.assertEqual(result["field_transitions"], [])
        self.assertEqual(
            result["causal_evidence"]["status"], "NOT_ELIGIBLE_NOT_COMPARABLE"
        )

    def test_expected_contract_change_is_not_comparable(self):
        before_payload = _controlled_visual_density_payload(
            eval_id="FD-CONTRACT-BEFORE", density_pass=False, composition_pass=True
        )
        after_payload = _controlled_visual_density_payload(
            eval_id="FD-CONTRACT-AFTER", density_pass=True, composition_pass=True
        )
        after_payload["expectations"][0]["declared_value"] = {"detail_budget": "minimal"}
        after_payload["reverse_observation"]["expectation_observations"]["visual_density"][
            "observed_value"
        ] = {"detail_budget": "minimal"}
        before = _evaluate(before_payload)
        after = _evaluate(after_payload)
        result = _compile(
            before,
            after,
            _change_record(
                change_id="FD-CONTRACT-CHANGED",
                changed=["reference_signal_decoupling"],
                scope="MODEL_VERSION_BOUND",
            ),
        )
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertTrue(
            any(reason.startswith("EXPECTED_VALUE_CHANGED:") for reason in result["comparison_reasons"])
        )

    def test_unknown_to_pass_is_evidence_gain_not_repair_resolution(self):
        before_payload = _case_payload("EOE-MISSING-OBSERVATION-UNKNOWN-001")
        before_payload["context"] = {
            "model": "C-DANCE",
            "model_version": "2.5",
            "work_item_id": "FD-UNKNOWN-GAIN",
        }
        after_payload = deepcopy(before_payload)
        after_payload["eval_id"] = "FD-UNKNOWN-GAIN-AFTER"
        after_payload["reverse_observation"]["expectation_observations"] = {
            "color_intent": {
                "comparison_mode": "exact_value",
                "observed_value": {"color_thesis": "cold_stone_with_natural_skin"},
                "evidence_refs": ["new_observation_001"],
            }
        }
        after_payload["reverse_observation"]["provenance"] = {
            "evidence_source": "reviewed_generation",
            "inspection_mode": "manual_structured_review",
            "temporal_coverage": {"type": "relevant_shot_full_duration"},
            "confidence": "HIGH",
            "media_refs": ["generation_after"],
            "claimed_frame_by_frame_review": False,
        }
        before = _evaluate(before_payload)
        after = _evaluate(after_payload)
        result = _compile(
            before,
            after,
            _change_record(
                change_id="FD-UNKNOWN-EVIDENCE-GAIN",
                changed=["evidence_acquisition"],
            ),
        )
        transition = result["field_transitions"][0]["transition"]
        self.assertEqual(transition, "EVIDENCE_GAINED_PASS")
        self.assertNotEqual(transition, "RESOLVED")

    def test_missing_alternatives_and_counterfactuals_are_not_invented(self):
        before = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-UNKNOWN-CONTEXT-BEFORE", density_pass=False, composition_pass=True
            )
        )
        after = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-UNKNOWN-CONTEXT-AFTER", density_pass=True, composition_pass=True
            )
        )
        result = _compile(
            before,
            after,
            _change_record(
                change_id="FD-UNKNOWN-CONTEXT",
                changed=["reference_signal_decoupling"],
                scope="MODEL_VERSION_BOUND",
            ),
            _learning_context(),
        )
        self.assertEqual(
            result["causal_evidence"]["alternative_explanations"], ["UNKNOWN_NOT_SUPPLIED"]
        )
        self.assertEqual(result["causal_evidence"]["counterfactuals"], ["UNKNOWN_NOT_SUPPLIED"])
        self.assertIsNone(result["candidate_learning_evidence"]["candidate_lesson"])

    def test_repair_plan_tampering_fails_closed(self):
        before = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-TAMPER-BEFORE", density_pass=False, composition_pass=True
            )
        )
        after = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-TAMPER-AFTER", density_pass=True, composition_pass=True
            )
        )
        plan = plan_targeted_repair(before, project_root=REPO_ROOT)
        plan["repair_items"] = []
        with self.assertRaises(FinalDeltaEvidenceError) as ctx:
            compile_final_delta_learning_evidence(
                {
                    "before_eval": before,
                    "after_eval": after,
                    "repair_plan": plan,
                    "change_record": _change_record(
                        change_id="FD-TAMPER", changed=["reference_signal_decoupling"]
                    ),
                    "learning_context": _learning_context(),
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "FINAL_DELTA_REPAIR_PLAN_MISMATCH")

    def test_authority_escalation_fails_closed(self):
        before = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-AUTH-BEFORE", density_pass=False, composition_pass=True
            )
        )
        after = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-AUTH-AFTER", density_pass=True, composition_pass=True
            )
        )
        for key in ("learning_writeback_authorized", "maturity_promotion_authorized", "camera_authority_mutation_authorized"):
            with self.subTest(key=key):
                plan = plan_targeted_repair(before, project_root=REPO_ROOT)
                plan[key] = True
                with self.assertRaises(FinalDeltaEvidenceError) as ctx:
                    compile_final_delta_learning_evidence(
                        {
                            "before_eval": before,
                            "after_eval": after,
                            "repair_plan": plan,
                            "change_record": _change_record(
                                change_id=f"FD-AUTH-{key}", changed=["reference_signal_decoupling"]
                            ),
                            "learning_context": _learning_context(),
                        },
                        project_root=REPO_ROOT,
                    )
                self.assertEqual(ctx.exception.code, "FINAL_DELTA_AUTHORITY_VIOLATION")
                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_change_record_requires_changed_variable_and_evidence(self):
        before = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-CHANGE-BEFORE", density_pass=False, composition_pass=True
            )
        )
        after = _evaluate(
            _controlled_visual_density_payload(
                eval_id="FD-CHANGE-AFTER", density_pass=True, composition_pass=True
            )
        )
        plan = plan_targeted_repair(before, project_root=REPO_ROOT)
        for mutation in ("changed_variables", "evidence_refs"):
            with self.subTest(mutation=mutation):
                change = _change_record(
                    change_id=f"FD-MISSING-{mutation}", changed=["reference_signal_decoupling"]
                )
                change[mutation] = []
                with self.assertRaises(FinalDeltaEvidenceError) as ctx:
                    compile_final_delta_learning_evidence(
                        {
                            "before_eval": before,
                            "after_eval": after,
                            "repair_plan": plan,
                            "change_record": change,
                            "learning_context": _learning_context(),
                        },
                        project_root=REPO_ROOT,
                    )
                self.assertEqual(ctx.exception.code, "FINAL_DELTA_CHANGE_RECORD_REQUIRED")

    def test_regression_registry_declares_non_promotion_gates(self):
        self.assertEqual(FD_SUITE["suite_id"], "FINAL_DELTA_LEARNING_EVIDENCE_REGRESSION_V1")
        gates = FD_SUITE["gates"]
        self.assertTrue(gates["single_success_cannot_promote"])
        self.assertTrue(gates["causal_claim_never_auto_authorized"])
        self.assertTrue(gates["camera_authority_cannot_reappear"])
        self.assertTrue(gates["regression_candidate_does_not_authorize_regression_write"])
        self.assertTrue(gates["no_second_learning_authority"])


if __name__ == "__main__":
    unittest.main()
