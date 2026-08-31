from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever.learning_pipeline import PIPELINE_STAGE_ORDER, LearningEvidencePipelineError, run_learning_evidence_pipeline


REPO_ROOT = Path(__file__).resolve().parents[3]
EOE_SUITE = yaml.safe_load((REPO_ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8"))


def _fixture(case_id: str) -> dict:
    case = next(item for item in EOE_SUITE["cases"] if item["id"] == case_id)
    return deepcopy(case["payload"])


def _package() -> dict:
    before = _fixture("EOE-PROD-KAIM-DISAPPEARANCE-001")
    before.setdefault("context", {}).update({"model": "C-DANCE", "model_version": "2.5", "work_item_id": "issue-19-kaim-scarf-clothesline"})
    after = deepcopy(before)
    after["eval_id"] = "EOE-PROD-KAIM-DISAPPEARANCE-AFTER-001"
    observation = after["reverse_observation"]["expectation_observations"]["attention_handoff"]
    observation["match_state"] = "MATCH"
    observation["observed_value"] = {"first_returned_master_state": "kaim_already_absent", "exit_visibility": "withheld_during_cutaway"}
    observation.pop("failure_category", None)
    observation["evidence_refs"] = ["issue_19_repair_after_sampled_review"]
    after["reverse_observation"]["fields"]["observed_attention_handoff"] = {"sequence": ["master_with_kaim_and_woman", "woman_closeup", "return_same_master_kaim_already_absent"], "reveal_effect": "absence_surprise_preserved"}
    after["reverse_observation"]["provenance"]["media_refs"] = ["issue_19_repair_after_sampled_review"]
    return {
        "pipeline_id": "PIPELINE-KAIM-DISAPPEARANCE-001",
        "hypothesis_id": "HYP-KAIM-CUTAWAY-ABSENCE-001",
        "before_eval_payload": before,
        "after_eval_payload": after,
        "change_record": {
            "change_id": "KAIM-DISAPPEARANCE-REPAIR-PIPELINE-001",
            "changed_variables": ["attention_handoff_transition_design"],
            "preserved_variables": ["story_goal", "character_identity", "scene_topology"],
            "revoked_variables": [],
            "experimental_variables": [],
            "scope": "EPISODIC_WORK_ITEM",
            "evidence_refs": ["issue_19_repair_after_sampled_review"],
            "user_confirmation_state": "CONFIRMED_BETTER",
            "rationale": "bounded end-to-end production regression fixture",
        },
        "learning_context": {
            "candidate_lesson": "Hide the departure during the cutaway and reveal absence on return.",
            "inferred_intent": "protect the disappearance reveal",
            "real_goal": "make the return cut reveal absence rather than show the exit",
            "value_priority": ["attention_handoff", "reveal_clarity"],
            "alternative_explanations": ["edit timing may also contribute"],
            "counterfactuals": ["returning before the exit completes should restore the failure"],
            "applicable_context": ["same-work-item disappearance reveal repairs"],
            "non_applicable_context": ["visible departure is the intended story beat"],
            "boundaries": ["sampled temporal evidence; not frame-by-frame causal proof"],
            "failure_conditions": ["camera or edit timing changes outside the target variable"],
            "model_or_tool_dependency": "C-DANCE 2.5 production evidence",
            "user_feedback_refs": ["issue_19_comment_5454103847"],
        },
    }


class LearningEvidencePipelineTests(unittest.TestCase):
    def test_issue19_repair_executes_source_bound_pipeline(self):
        result = run_learning_evidence_pipeline(_package(), project_root=REPO_ROOT)
        self.assertEqual(result["schema"], "LEARNING_EVIDENCE_PIPELINE_RESULT/v2")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completed_stages"], list(PIPELINE_STAGE_ORDER))
        self.assertEqual(result["stages"]["before_expected_observed"]["status"], "FAIL")
        self.assertTrue(result["stages"]["targeted_repair"]["repair_required"])
        self.assertEqual(result["artifacts"]["repair_plan"]["repair_items"][0]["repair_surface"], "TRANSITION_EDIT_REVIEW")
        self.assertEqual(result["stages"]["after_expected_observed"]["status"], "PASS")
        self.assertIn("attention_handoff", result["stages"]["final_delta"]["resolved_fields"])
        self.assertEqual(result["stages"]["final_delta"]["causal_evidence_status"], "OBSERVATIONAL_ONLY")
        self.assertEqual(result["stages"]["post_final_delta"]["regression_proposal_count"], 1)
        binding = result["source_binding"]
        self.assertTrue(binding["targeted_repair_source_reexecuted"])
        self.assertTrue(binding["final_delta_source_reexecuted"])
        self.assertTrue(binding["post_final_delta_source_reexecuted"])
        self.assertFalse(binding["serialized_prior_final_deltas_accepted"])
        for key in ("prompt_mutation_authorized", "generation_authorized", "camera_authority_mutation_authorized", "canonical_mutation_authorized", "learning_writeback_authorized", "regression_write_authorized", "maturity_promotion_authorized", "causal_claim_authorized"):
            self.assertFalse(result[key], key)

    def test_before_pass_without_repair_target_fails_before_after(self):
        before = _fixture("EOE-EXACT-PASS-001")
        after = deepcopy(before)
        after["eval_id"] = "EOE-EXACT-PASS-AFTER-001"
        payload = _package()
        payload["before_eval_payload"] = before
        payload["after_eval_payload"] = after
        with self.assertRaises(LearningEvidencePipelineError) as ctx:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "LEARNING_PIPELINE_NO_REPAIR_TARGET")
        self.assertEqual(ctx.exception.stage, "TARGETED_REPAIR_PRECONDITION")

    def test_eval_ids_must_be_distinct(self):
        payload = _package()
        payload["after_eval_payload"]["eval_id"] = payload["before_eval_payload"]["eval_id"]
        with self.assertRaises(LearningEvidencePipelineError) as ctx:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "LEARNING_PIPELINE_EVAL_ID_COLLISION")
        self.assertNotIn("FINAL_DELTA", ctx.exception.completed_stages)

    def test_before_eval_error_preserves_stage_and_code(self):
        payload = _package()
        del payload["before_eval_payload"]["reverse_observation"]["provenance"]
        with self.assertRaises(LearningEvidencePipelineError) as ctx:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.stage, "BEFORE_EXPECTED_OBSERVED")
        self.assertEqual(ctx.exception.underlying_code, "EVAL_MISSING_PROVENANCE")

    def test_serialized_prior_final_delta_is_rejected_at_input_boundary(self):
        payload = _package()
        payload["prior_final_deltas"] = [{"final_delta_id": "CALLER_FAKE"}]
        with self.assertRaises(LearningEvidencePipelineError) as ctx:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "LEARNING_PIPELINE_UNKNOWN_FIELD")
        self.assertEqual(ctx.exception.stage, "ORCHESTRATOR_INPUT")

    def test_invalid_prior_source_is_rejected_by_post_source_reexecution(self):
        payload = _package()
        payload["prior_final_delta_inputs"] = [{"before_eval": {"forged": True}}]
        with self.assertRaises(LearningEvidencePipelineError) as ctx:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.stage, "POST_FINAL_DELTA")
        self.assertEqual(ctx.exception.underlying_code, "POST_FD_INVALID_FINAL_DELTA")

    def test_unknown_maturity_and_unknown_root_fail_closed(self):
        payload = _package()
        payload["requested_maturity"] = "magic_verified"
        with self.assertRaises(LearningEvidencePipelineError) as ctx:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.stage, "POST_FINAL_DELTA")
        self.assertEqual(ctx.exception.underlying_code, "POST_FD_UNKNOWN_MATURITY")

        payload = _package()
        payload["write_learning_now"] = True
        with self.assertRaises(LearningEvidencePipelineError) as ctx2:
            run_learning_evidence_pipeline(payload, project_root=REPO_ROOT)
        self.assertEqual(ctx2.exception.code, "LEARNING_PIPELINE_UNKNOWN_FIELD")
        self.assertEqual(ctx2.exception.stage, "ORCHESTRATOR_INPUT")


if __name__ == "__main__":
    unittest.main()
