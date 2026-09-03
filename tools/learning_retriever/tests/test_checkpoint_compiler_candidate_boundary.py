from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


class CheckpointCompilerCandidateBoundaryTests(unittest.TestCase):
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

    def test_candidate_is_not_registered_or_activated_before_independent_accept(self) -> None:
        canonical = self.project.get("canonical") or {}
        effective = self.project.get("effective_sources") or {}
        self.assertNotIn("active_work_item_checkpoint_compiler", canonical)
        self.assertNotIn("active_work_item_checkpoint_compiler_regression_cases", canonical)
        self.assertNotIn("10_运行时/active_work_item_checkpoint_compiler.yaml", effective)
        self.assertNotIn("revision_checkpoint_compilation", self.read_sets.get("read_sets") or {})
        directing_always = ((self.read_sets.get("read_sets") or {}).get("directing") or {}).get("always") or []
        self.assertFalse(any("checkpoint_compiler" in str(item) for item in directing_always))

    def test_existing_write_route_remains_the_only_checkpoint_continuity_target(self) -> None:
        routes = self.write_routes["routes"]
        self.assertEqual(
            routes["revision_checkpoint_current_state"],
            "07_连续性与生产状态/连续性与当前生产状态.md",
        )
        self.assertNotIn("active_work_item_current_state", routes)
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

    def test_candidate_contract_cannot_mint_persistence_or_governed_ref_authority(self) -> None:
        self.assertEqual(self.contract["status"], "candidate")
        boundary = self.contract["authority_boundary"]
        self.assertTrue(boundary["this_component_has_no_persistence_authority"])
        self.assertTrue(boundary["proposal_is_not_committed_state"])
        self.assertTrue(boundary["finalization_proposal_is_not_committed_state"])
        self.assertTrue(boundary["runtime_may_not_write_github"])
        self.assertTrue(boundary["runtime_may_not_accept_serialized_write_success_claim"])
        self.assertTrue(boundary["runtime_may_not_claim_governed_branch_or_ref"])

    def test_two_phase_transaction_stays_external_and_non_self_referential(self) -> None:
        steps = self.contract["write_transaction_external_contract"]["steps"]
        self.assertEqual(steps[:2], ["FETCH_current_continuity", "compile_checkpoint_proposal"])
        self.assertIn("compile_checkpoint_finalization_proposal", steps)
        self.assertIn("verify_finalization_document", steps)
        finalization = self.contract["finalization_phase"]["finalization_proposal"]
        self.assertEqual(finalization["status"], "PENDING_FINALIZATION_WRITE")
        self.assertTrue(finalization["self_referential_commit_sha_forbidden"])

    def test_regression_registry_is_candidate_eval_only(self) -> None:
        self.assertEqual(self.regressions["status"], "candidate_eval_only")
        boundary = self.regressions["authority_boundary"]
        self.assertTrue(boundary["eval_fixture_only"])
        self.assertTrue(boundary["proposal_is_not_persistence"])
        self.assertTrue(boundary["finalization_proposal_is_not_persistence"])
        self.assertTrue(boundary["registration_is_not_activation"])


if __name__ == "__main__":
    unittest.main()
