from pathlib import Path
import unittest

import yaml

import learning_retriever


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = "10_运行时/final_delta_learning_policy.yaml"
REGRESSION = "11_验收/final_delta_learning_regression_cases.yaml"


class FinalDeltaBindingTests(unittest.TestCase):
    def test_project_index_registers_execution_only_final_delta_runtime(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        policy = project["policy"]
        self.assertTrue(policy["final_delta_learning_runtime_is_execution_only"])
        self.assertTrue(policy["final_delta_learning_cannot_promote_or_writeback"])
        self.assertTrue(policy["final_delta_single_success_cannot_generalize"])
        self.assertEqual(project["canonical"]["final_delta_learning_policy"], POLICY)
        self.assertEqual(project["canonical"]["final_delta_learning_regression_cases"], REGRESSION)
        self.assertEqual(project["effective_sources"][POLICY], "github_verified")
        self.assertEqual(project["effective_sources"][REGRESSION], "github_verified")

    def test_read_sets_bind_final_delta_conditionally_not_always(self):
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        directing = read_sets["read_sets"]["directing"]
        system_research = read_sets["read_sets"]["system_research"]
        self.assertNotIn("final_delta_learning_policy", directing["always"])
        self.assertNotIn("final_delta_learning_regression_cases", directing["always"])
        self.assertEqual(
            directing["conditional"]["final_delta_learning_policy"],
            "final_delta_learning_policy#when_repair_outcome_before_after_final_delta_or_candidate_learning_evidence_is_relevant",
        )
        self.assertEqual(
            directing["conditional"]["final_delta_learning_regression"],
            "final_delta_learning_regression_cases#when_repair_outcome_final_delta_or_learning_evidence_regression_is_relevant",
        )
        self.assertEqual(
            system_research["conditional"]["final_delta_learning_policy"],
            "final_delta_learning_policy#when_continual_learning_final_delta_causal_boundary_or_maturity_handoff_is_under_review",
        )
        self.assertEqual(
            system_research["conditional"]["final_delta_learning_regression"],
            "final_delta_learning_regression_cases#when_final_delta_learning_runtime_or_non_promotion_gates_are_under_review",
        )

    def test_write_route_is_regression_only_and_does_not_create_learning_authority(self):
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertEqual(routes["final_delta_learning_regression_case"], REGRESSION)
        matches = [name for name, target in routes.items() if target == REGRESSION]
        self.assertEqual(matches, ["final_delta_learning_regression_case"])
        self.assertNotIn("candidate_learning_evidence", routes)
        self.assertNotIn("final_delta_learning_evidence", routes)
        self.assertNotEqual(routes["revision_trace_and_learning"], REGRESSION)
        self.assertNotEqual(routes["learning_evidence_and_outcome"], REGRESSION)

    def test_package_exports_compiler_but_no_promotion_or_camera_authority_helper(self):
        self.assertTrue(hasattr(learning_retriever, "FinalDeltaEvidenceError"))
        self.assertTrue(hasattr(learning_retriever, "compile_final_delta_learning_evidence"))
        forbidden = {
            "promote_final_delta_learning",
            "write_candidate_learning_evidence",
            "mint_camera_authority",
            "_mint_camera_authority",
            "TrustedUpstreamLockEnvelope",
            "_mint_trusted_upstream_lock_for_orchestration",
        }
        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse(hasattr(learning_retriever, name))

    def test_ci_runs_final_delta_regressions_without_write_permission(self):
        workflow = (REPO_ROOT / ".github/workflows/learning-feature-compiler.yml").read_text(encoding="utf-8")
        self.assertIn(POLICY, workflow)
        self.assertIn(REGRESSION, workflow)
        self.assertIn("test_final_delta_learning.py", workflow)
        self.assertIn("test_final_delta_bindings.py", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("tmp-wire-final-delta", workflow)

    def test_policy_output_contract_has_no_canonical_write_or_promotion(self):
        policy = yaml.safe_load((REPO_ROOT / POLICY).read_text(encoding="utf-8"))
        output = policy["output_contract"]
        self.assertIsNone(output["canonical_write_target"])
        self.assertFalse(output["prompt_mutation_authorized"])
        self.assertFalse(output["generation_authorized"])
        self.assertFalse(output["camera_authority_mutation_authorized"])
        self.assertFalse(output["canonical_mutation_authorized"])
        self.assertFalse(output["learning_writeback_authorized"])
        self.assertFalse(output["maturity_promotion_authorized"])
        self.assertFalse(output["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
