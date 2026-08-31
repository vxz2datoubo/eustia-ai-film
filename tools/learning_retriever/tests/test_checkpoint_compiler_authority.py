from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


class CheckpointCompilerAuthorityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        cls.read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        cls.write_routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))
        cls.contract = yaml.safe_load(
            (REPO_ROOT / "10_运行时/active_work_item_checkpoint_compiler.yaml").read_text(encoding="utf-8")
        )
        cls.regressions = yaml.safe_load(
            (REPO_ROOT / "11_验收/active_work_item_checkpoint_compiler_regression_cases.yaml").read_text(encoding="utf-8")
        )

    def test_candidate_is_not_activated_in_project_index_before_independent_review(self) -> None:
        canonical = self.project["canonical"]
        effective = self.project["effective_sources"]
        policy = self.project["policy"]
        self.assertNotIn("active_work_item_checkpoint_compiler", canonical)
        self.assertNotIn("active_work_item_checkpoint_compiler_regression_cases", canonical)
        self.assertNotIn(
            "10_运行时/active_work_item_checkpoint_compiler.yaml",
            effective,
        )
        self.assertNotIn("active_work_item_checkpoint_compiler_is_proposal_only", policy)
        self.assertEqual(self.contract["status"], "candidate")

    def test_candidate_does_not_inflate_normal_directing_reads(self) -> None:
        directing_always = self.read_sets["read_sets"]["directing"]["always"]
        self.assertFalse(any("checkpoint_compiler" in item for item in directing_always))
        self.assertNotIn("revision_checkpoint_compilation", self.read_sets["read_sets"])

    def test_existing_write_route_remains_single_continuity_target(self) -> None:
        routes = self.write_routes["routes"]
        self.assertEqual(
            routes["revision_checkpoint_current_state"],
            "07_连续性与生产状态/连续性与当前生产状态.md",
        )
        self.assertNotIn("active_work_item_current_state", routes)
        continuity_targets = [
            value
            for key, value in routes.items()
            if key in {"revision_checkpoint_current_state", "active_work_item_current_state"}
        ]
        self.assertEqual(
            continuity_targets,
            ["07_连续性与生产状态/连续性与当前生产状态.md"],
        )
        self.assertEqual(
            self.write_routes["write_protocol"],
            [
                "fetch_current_blob",
                "edit_current_content",
                "commit_serially",
                "fetch_again",
                "verify_new_content_and_status",
                "report_committed_only_after_verification",
            ],
        )

    def test_contract_points_to_existing_unique_authorities_without_claiming_registration(self) -> None:
        dependency = self.contract["dependency"]
        self.assertEqual(
            dependency["runtime_gate"],
            "10_运行时/active_work_item_resolution_gate.yaml",
        )
        self.assertEqual(
            dependency["continuity_authority"],
            "07_连续性与生产状态/连续性与当前生产状态.md#ACTIVE_WORK_ITEM_STATE",
        )
        self.assertEqual(
            dependency["write_route"],
            "10_运行时/write_routes.yaml#revision_checkpoint_current_state",
        )

    def test_contract_cannot_mint_persistence_authority(self) -> None:
        boundary = self.contract["authority_boundary"]
        self.assertTrue(boundary["this_component_has_no_persistence_authority"])
        self.assertTrue(boundary["proposal_is_not_committed_state"])
        self.assertTrue(boundary["finalization_proposal_is_not_committed_state"])
        self.assertTrue(boundary["runtime_may_not_write_github"])
        self.assertTrue(boundary["runtime_may_not_accept_serialized_write_success_claim"])
        self.assertTrue(boundary["runtime_may_not_claim_governed_branch_or_ref"])
        steps = self.contract["write_transaction_external_contract"]["steps"]
        self.assertEqual(steps[:2], ["FETCH_current_continuity", "compile_checkpoint_proposal"])
        self.assertIn("compile_checkpoint_finalization_proposal", steps)
        self.assertIn("verify_finalization_document", steps)

    def test_finalization_is_two_phase_and_non_self_referential(self) -> None:
        finalization = self.contract["finalization_phase"]
        proposal = finalization["finalization_proposal"]
        self.assertEqual(proposal["status"], "PENDING_FINALIZATION_WRITE")
        self.assertTrue(proposal["self_referential_commit_sha_forbidden"])
        rules = proposal["proposed_snapshot_rules"]
        self.assertEqual(rules["checkpoint_writeback_status"], "verified")
        self.assertEqual(rules["writeback_verified_commit"], "verified_materialization_commit_sha")
        receipt_boundary = finalization["second_write_verification"]["receipt_boundary"]
        self.assertIn("runtime does not confirm governed branch or ref", receipt_boundary)

    def test_regression_contract_is_eval_only_and_machine_backed(self) -> None:
        self.assertTrue(self.regressions["authority_boundary"]["eval_fixture_only"])
        self.assertTrue(self.regressions["authority_boundary"]["proposal_is_not_persistence"])
        self.assertTrue(self.regressions["authority_boundary"]["finalization_proposal_is_not_persistence"])
        acceptance = self.regressions["acceptance"]
        expected_suites = {
            "primary_machine_suite": "tools/learning_retriever/tests/test_checkpoint_compiler.py",
            "hardening_machine_suite": "tools/learning_retriever/tests/test_checkpoint_compiler_hardening.py",
            "authority_machine_suite": "tools/learning_retriever/tests/test_checkpoint_compiler_authority.py",
            "finalization_machine_suite": "tools/learning_retriever/tests/test_checkpoint_finalizer.py",
        }
        for field, path in expected_suites.items():
            self.assertEqual(acceptance[field], path)
            self.assertTrue((REPO_ROOT / path).is_file(), path)
        self.assertTrue(acceptance["exact_head_ci_required"])

    def test_activation_is_a_separate_post_acceptance_slice(self) -> None:
        self.assertEqual(self.contract["maturity"]["current"], "candidate")
        self.assertIn("independent_review", self.contract["maturity"]["promotion_gate"])
        self.assertNotIn("revision_checkpoint_compilation", self.read_sets["read_sets"])


if __name__ == "__main__":
    unittest.main()
