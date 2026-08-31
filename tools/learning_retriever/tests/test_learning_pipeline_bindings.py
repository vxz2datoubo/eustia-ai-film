from pathlib import Path
import inspect
import unittest

import yaml

import learning_retriever
import learning_retriever.learning_pipeline as pipeline_module


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "10_运行时/learning_evidence_pipeline_orchestrator.yaml"
REGRESSION = "11_验收/learning_evidence_pipeline_regression_cases.yaml"


class LearningEvidencePipelineBindingTests(unittest.TestCase):
    def test_contract_is_orchestration_only_and_non_writing(self):
        contract = yaml.safe_load((REPO_ROOT / CONTRACT).read_text(encoding="utf-8"))
        boundary = contract["authority_boundary"]
        self.assertTrue(boundary["this_file_is_orchestration_contract_only"])
        self.assertTrue(boundary["this_file_is_not_director_authority"])
        self.assertTrue(boundary["this_file_is_not_eval_authority"])
        self.assertTrue(boundary["this_file_is_not_repair_authority"])
        self.assertTrue(boundary["this_file_is_not_learning_authority"])
        self.assertTrue(boundary["this_file_is_not_maturity_authority"])
        self.assertTrue(boundary["this_file_is_not_write_authority"])
        output = contract["output_contract"]
        for key in (
            "prompt_mutation_authorized",
            "generation_authorized",
            "camera_authority_mutation_authorized",
            "canonical_mutation_authorized",
            "learning_writeback_authorized",
            "regression_write_authorized",
            "maturity_promotion_authorized",
            "causal_claim_authorized",
        ):
            self.assertFalse(output[key], key)

    def test_stage_contract_points_to_existing_runtime_implementations(self):
        contract = yaml.safe_load((REPO_ROOT / CONTRACT).read_text(encoding="utf-8"))
        self.assertEqual(
            contract["fixed_stage_order"],
            list(pipeline_module.PIPELINE_STAGE_ORDER),
        )
        expected_functions = {
            "BEFORE_EXPECTED_OBSERVED": "evaluate_expected_vs_observed",
            "TARGETED_REPAIR": "plan_targeted_repair",
            "AFTER_EXPECTED_OBSERVED": "evaluate_expected_vs_observed",
            "FINAL_DELTA": "compile_final_delta_learning_evidence",
            "POST_FINAL_DELTA": "assess_post_final_delta_validation",
        }
        for stage, function_name in expected_functions.items():
            with self.subTest(stage=stage):
                self.assertIn(function_name, contract["stage_implementations"][stage])

    def test_pipeline_module_has_no_writer_or_promotion_helpers(self):
        source = inspect.getsource(pipeline_module)
        forbidden_imports = (
            "requests",
            "urllib",
            "github",
            "subprocess",
            "socket",
        )
        for token in forbidden_imports:
            with self.subTest(token=token):
                self.assertNotIn(f"import {token}", source)
                self.assertNotIn(f"from {token}", source)

        forbidden_exports = (
            "write_learning_evidence",
            "write_regression",
            "promote_maturity",
            "trigger_generation",
            "rewrite_prompt",
            "mint_camera_authority",
        )
        for name in forbidden_exports:
            with self.subTest(name=name):
                self.assertFalse(hasattr(pipeline_module, name))

    def test_package_exports_execution_entrypoint_only(self):
        self.assertTrue(hasattr(learning_retriever, "LearningEvidencePipelineError"))
        self.assertTrue(hasattr(learning_retriever, "run_learning_evidence_pipeline"))
        self.assertFalse(hasattr(learning_retriever, "promote_maturity"))
        self.assertFalse(hasattr(learning_retriever, "write_learning_evidence"))
        self.assertFalse(hasattr(learning_retriever, "write_regression_proposal"))

    def test_candidate_registration_is_deliberately_deferred_until_upstream_canonical(self):
        contract = yaml.safe_load((REPO_ROOT / CONTRACT).read_text(encoding="utf-8"))
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        self.assertTrue(contract["stack_dependency"]["canonical_registration_deferred_until_upstream_canonical"])
        self.assertNotIn("learning_evidence_pipeline_orchestrator", project.get("canonical", {}))
        self.assertNotIn(CONTRACT, project.get("effective_sources", {}))

    def test_no_write_route_is_created_for_pipeline_result(self):
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertFalse(any("learning_evidence_pipeline" in str(name) for name in routes))
        self.assertFalse(any(str(target).endswith("learning_evidence_pipeline_regression_cases.yaml") for target in routes.values()))

    def test_regression_contract_requires_stage_failure_provenance_and_zero_authority(self):
        suite = yaml.safe_load((REPO_ROOT / REGRESSION).read_text(encoding="utf-8"))
        self.assertEqual(suite["suite_id"], "LEARNING_EVIDENCE_PIPELINE_REGRESSION_V1")
        policy = suite["policy"]
        self.assertTrue(policy["fixed_stage_order_required"])
        self.assertTrue(policy["source_stage_error_preservation_required"])
        self.assertTrue(policy["later_stage_execution_after_failure_forbidden"])
        self.assertTrue(policy["prior_final_delta_must_be_revalidated"])
        for key in (
            "prompt_mutation_forbidden",
            "generation_forbidden",
            "camera_authority_forbidden",
            "canonical_write_forbidden",
            "learning_write_forbidden",
            "regression_write_forbidden",
            "maturity_promotion_forbidden",
            "automatic_causal_claim_forbidden",
        ):
            self.assertTrue(policy[key], key)

    def test_ci_runs_pipeline_targeted_and_binding_regressions(self):
        workflow = (REPO_ROOT / ".github/workflows/learning-feature-compiler.yml").read_text(encoding="utf-8")
        self.assertIn(CONTRACT, workflow)
        self.assertIn(REGRESSION, workflow)
        self.assertIn("test_learning_pipeline.py", workflow)
        self.assertIn("test_learning_pipeline_bindings.py", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
