from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = "10_运行时/post_final_delta_validation_policy.yaml"
REGRESSION = "11_验收/post_final_delta_validation_regression_cases.yaml"
WRAPPER = "tools/learning_retriever/learning_retriever/post_final_delta_source_bound.py"
PUBLIC_FACADE = "tools/learning_retriever/learning_retriever/post_final_delta.py"
PRIVATE_CORE = "tools/learning_retriever/learning_retriever/_post_final_delta_core_v3.py"
CLI = "tools/learning_retriever/learning_retriever/post_final_delta_cli.py"


class PostFinalDeltaBindingTests(unittest.TestCase):
    def test_candidate_stack_does_not_self_promote_over_project_index(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        canonical = project.get("canonical") or {}
        effective = project.get("effective_sources") or {}
        self.assertNotIn("post_final_delta_validation_policy", canonical)
        self.assertNotIn("post_final_delta_validation_regression_cases", canonical)
        self.assertNotIn(POLICY, effective)
        self.assertNotIn(REGRESSION, effective)

    def test_candidate_stack_does_not_amplify_ordinary_directing_reads(self):
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        directing = read_sets["read_sets"]["directing"]
        self.assertNotIn("post_final_delta_validation_policy", directing["always"])
        self.assertNotIn("post_final_delta_validation_policy", directing.get("conditional") or {})
        self.assertNotIn("post_final_delta_validation_regression", directing.get("conditional") or {})

    def test_candidate_stack_has_no_post_final_delta_write_route(self):
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertNotIn("post_final_delta_validation_regression_case", routes)
        self.assertNotIn("maturity_promotion", routes)
        self.assertNotIn("evidence_cohort", routes)
        self.assertNotIn("regression_proposal", routes)

    def test_policy_requires_source_bound_reexecution_and_artifact_gate_propagation(self):
        policy = yaml.safe_load((REPO_ROOT / POLICY).read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "candidate_stacked")
        binding = policy["source_binding"]
        self.assertEqual(binding["public_input"], "final_delta_inputs")
        self.assertFalse(binding["serialized_final_deltas_accepted"])
        self.assertTrue(binding["canonical_final_delta_reexecution_required"])
        self.assertEqual(binding["source_bound_wrapper"], WRAPPER)
        self.assertTrue(binding["caller_consistent_serialized_artifacts_are_not_source_truth"])
        self.assertTrue(binding["upstream_artifact_provenance_gate_must_be_preserved"])
        gate = policy["artifact_gate_propagation"]
        self.assertTrue(gate["final_delta_not_comparable_is_inconclusive"])
        self.assertTrue(gate["unattributed_transition_candidates_are_diagnostic_only"])
        self.assertTrue(gate["downstream_cannot_restore_final_delta_attribution"])
        self.assertTrue(gate["byte_content_distinction_alone_is_insufficient_generation_provenance"])

    def test_public_facade_private_core_and_source_wrapper_are_separated(self):
        facade = (REPO_ROOT / PUBLIC_FACADE).read_text(encoding="utf-8")
        core = (REPO_ROOT / PRIVATE_CORE).read_text(encoding="utf-8")
        wrapper = (REPO_ROOT / WRAPPER).read_text(encoding="utf-8")
        self.assertIn("serialized Final-Delta projection is internal-only", facade)
        self.assertIn("assess_post_final_delta_validation", core)
        self.assertIn("_assess_internal_projection", wrapper)
        self.assertIn("compile_final_delta_learning_evidence", wrapper)
        self.assertIn("unattributed_transition_candidates", wrapper)
        self.assertNotIn("write_regression", wrapper)
        self.assertNotIn("promote_maturity", wrapper)

    def test_cli_routes_only_through_source_bound_wrapper(self):
        cli = (REPO_ROOT / CLI).read_text(encoding="utf-8")
        self.assertIn("assess_source_bound_post_final_delta", cli)
        self.assertNotIn("from .post_final_delta import PostFinalDeltaValidationError, assess_post_final_delta_validation", cli)
        self.assertIn("final_delta_inputs", cli)

    def test_policy_output_contract_has_zero_mutation_or_promotion_authority(self):
        policy = yaml.safe_load((REPO_ROOT / POLICY).read_text(encoding="utf-8"))
        output = policy["output_contract"]
        self.assertTrue(output["evidence_cohorts_are_ephemeral"])
        self.assertTrue(output["regression_proposals_are_ephemeral"])
        self.assertTrue(output["diagnostic_unattributed_transitions_are_not_regression_evidence"])
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
