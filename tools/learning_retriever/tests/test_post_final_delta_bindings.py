from pathlib import Path
import unittest

import yaml

import learning_retriever


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = "10_运行时/post_final_delta_validation_policy.yaml"
REGRESSION = "11_验收/post_final_delta_validation_regression_cases.yaml"


class PostFinalDeltaBindingTests(unittest.TestCase):
    def test_project_index_registers_post_final_delta_as_execution_only(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        policy = project["policy"]
        self.assertTrue(policy["post_final_delta_validation_runtime_is_execution_only"])
        self.assertTrue(policy["post_final_delta_validation_cannot_promote_or_write"])
        self.assertTrue(policy["post_final_delta_cross_version_pooling_forbidden"])
        self.assertEqual(project["canonical"]["post_final_delta_validation_policy"], POLICY)
        self.assertEqual(project["canonical"]["post_final_delta_validation_regression_cases"], REGRESSION)
        self.assertEqual(project["effective_sources"][POLICY], "github_verified")
        self.assertEqual(project["effective_sources"][REGRESSION], "github_verified")

    def test_read_sets_are_conditional_not_always_on(self):
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        directing = read_sets["read_sets"]["directing"]
        system_research = read_sets["read_sets"]["system_research"]
        self.assertNotIn("post_final_delta_validation_policy", directing["always"])
        self.assertEqual(
            directing["conditional"]["post_final_delta_validation_policy"],
            "post_final_delta_validation_policy#when_final_delta_evidence_cohort_regression_proposal_or_maturity_assessment_is_relevant",
        )
        self.assertEqual(
            directing["conditional"]["post_final_delta_validation_regression"],
            "post_final_delta_validation_regression_cases#when_post_final_delta_partition_conflict_or_maturity_gate_is_relevant",
        )
        self.assertEqual(
            system_research["conditional"]["post_final_delta_validation_policy"],
            "post_final_delta_validation_policy#when_evidence_aggregation_regression_proposal_or_maturity_governance_is_under_review",
        )
        self.assertEqual(
            system_research["conditional"]["post_final_delta_validation_regression"],
            "post_final_delta_validation_regression_cases#when_post_final_delta_validation_runtime_is_under_review",
        )

    def test_write_route_is_regression_only_and_no_maturity_or_evidence_write_route_exists(self):
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertEqual(routes["post_final_delta_validation_regression_case"], REGRESSION)
        matches = [name for name, target in routes.items() if target == REGRESSION]
        self.assertEqual(matches, ["post_final_delta_validation_regression_case"])
        self.assertNotIn("maturity_promotion", routes)
        self.assertNotIn("evidence_cohort", routes)
        self.assertNotIn("regression_proposal", routes)
        self.assertNotEqual(routes["revision_trace_and_learning"], REGRESSION)
        self.assertNotEqual(routes["learning_evidence_and_outcome"], REGRESSION)

    def test_package_exports_assessment_but_no_promotion_or_write_helpers(self):
        self.assertTrue(hasattr(learning_retriever, "PostFinalDeltaValidationError"))
        self.assertTrue(hasattr(learning_retriever, "assess_post_final_delta_validation"))
        forbidden = {
            "promote_maturity",
            "write_regression_proposal",
            "write_learning_evidence",
            "mint_trusted_confirmation",
            "mint_camera_authority",
            "_mint_camera_authority",
        }
        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse(hasattr(learning_retriever, name))

    def test_ci_runs_post_final_delta_regressions_without_write_permission(self):
        workflow = (REPO_ROOT / ".github/workflows/learning-feature-compiler.yml").read_text(encoding="utf-8")
        self.assertIn(POLICY, workflow)
        self.assertIn(REGRESSION, workflow)
        self.assertIn("test_post_final_delta_validation.py", workflow)
        self.assertIn("test_post_final_delta_bindings.py", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("tmp-wire-post-final-delta", workflow)

    def test_policy_output_contract_has_zero_mutation_or_promotion_authority(self):
        policy = yaml.safe_load((REPO_ROOT / POLICY).read_text(encoding="utf-8"))
        output = policy["output_contract"]
        self.assertTrue(output["evidence_cohorts_are_ephemeral"])
        self.assertTrue(output["regression_proposals_are_ephemeral"])
        self.assertFalse(output["prompt_mutation_authorized"])
        self.assertFalse(output["generation_authorized"])
        self.assertFalse(output["camera_authority_mutation_authorized"])
        self.assertFalse(output["canonical_mutation_authorized"])
        self.assertFalse(output["learning_writeback_authorized"])
        self.assertFalse(output["regression_write_authorized"])
        self.assertFalse(output["maturity_promotion_authorized"])
        self.assertFalse(output["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
