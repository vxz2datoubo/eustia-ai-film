from pathlib import Path
import inspect
import unittest

import yaml

import learning_retriever.learning_pipeline as pipeline_module


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "10_运行时/learning_evidence_pipeline_orchestrator.yaml"
REGRESSION = "11_验收/learning_evidence_pipeline_regression_cases.yaml"


class LearningEvidencePipelineBindingTests(unittest.TestCase):
    def test_contract_is_orchestration_only_non_writing_and_source_bound(self):
        contract = yaml.safe_load((REPO_ROOT / CONTRACT).read_text(encoding="utf-8"))
        boundary = contract["authority_boundary"]
        for key in ("this_file_is_orchestration_contract_only", "this_file_is_not_director_authority", "this_file_is_not_eval_authority", "this_file_is_not_repair_authority", "this_file_is_not_learning_authority", "this_file_is_not_maturity_authority", "this_file_is_not_write_authority"):
            self.assertTrue(boundary[key], key)
        binding = contract["source_binding"]
        self.assertTrue(binding["targeted_repair_uses_raw_before_source"])
        self.assertTrue(binding["final_delta_uses_raw_before_after_sources"])
        self.assertTrue(binding["post_final_delta_uses_final_delta_source_packages"])
        self.assertFalse(binding["serialized_eval_results_accepted"])
        self.assertFalse(binding["serialized_repair_plans_accepted"])
        self.assertFalse(binding["serialized_prior_final_deltas_accepted"])

    def test_stage_contract_matches_runtime_order_and_source_bound_post_stage(self):
        contract = yaml.safe_load((REPO_ROOT / CONTRACT).read_text(encoding="utf-8"))
        self.assertEqual(contract["fixed_stage_order"], list(pipeline_module.PIPELINE_STAGE_ORDER))
        self.assertIn("evaluate_expected_vs_observed", contract["stage_implementations"]["BEFORE_EXPECTED_OBSERVED"])
        self.assertIn("plan_targeted_repair", contract["stage_implementations"]["TARGETED_REPAIR"])
        self.assertIn("compile_final_delta_learning_evidence", contract["stage_implementations"]["FINAL_DELTA"])
        self.assertIn("assess_source_bound_post_final_delta", contract["stage_implementations"]["POST_FINAL_DELTA"])

    def test_pipeline_module_has_no_writer_network_or_promotion_helpers(self):
        source = inspect.getsource(pipeline_module)
        for token in ("requests", "urllib", "github", "subprocess", "socket"):
            self.assertNotIn(f"import {token}", source)
            self.assertNotIn(f"from {token}", source)
        for name in ("write_learning_evidence", "write_regression", "promote_maturity", "trigger_generation", "rewrite_prompt", "mint_camera_authority"):
            self.assertFalse(hasattr(pipeline_module, name))

    def test_candidate_registration_and_write_routes_are_deferred(self):
        contract = yaml.safe_load((REPO_ROOT / CONTRACT).read_text(encoding="utf-8"))
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertTrue(contract["stack_dependency"]["canonical_registration_deferred_until_upstream_canonical"])
        self.assertNotIn("learning_evidence_pipeline_orchestrator", project.get("canonical", {}))
        self.assertNotIn(CONTRACT, project.get("effective_sources", {}))
        self.assertFalse(any("learning_evidence_pipeline" in str(name) for name in routes))
        self.assertFalse(any(str(target).endswith("learning_evidence_pipeline_regression_cases.yaml") for target in routes.values()))

    def test_regression_contract_requires_source_reexecution_and_zero_authority(self):
        suite = yaml.safe_load((REPO_ROOT / REGRESSION).read_text(encoding="utf-8"))
        self.assertEqual(suite["suite_id"], "LEARNING_EVIDENCE_PIPELINE_REGRESSION_V2")
        policy = suite["policy"]
        self.assertTrue(policy["targeted_repair_source_reexecution_required"])
        self.assertTrue(policy["final_delta_source_reexecution_required"])
        self.assertTrue(policy["post_final_delta_source_reexecution_required"])
        self.assertTrue(policy["serialized_prior_final_delta_forbidden"])
        self.assertTrue(policy["prior_final_delta_source_input_must_be_reexecuted"])
        for key in ("prompt_mutation_forbidden", "generation_forbidden", "camera_authority_forbidden", "canonical_write_forbidden", "learning_write_forbidden", "regression_write_forbidden", "maturity_promotion_forbidden", "automatic_causal_claim_forbidden"):
            self.assertTrue(policy[key], key)


if __name__ == "__main__":
    unittest.main()
