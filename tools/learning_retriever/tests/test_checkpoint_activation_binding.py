from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT_POLICY = "10_运行时/active_work_item_checkpoint_compiler.yaml"
CHECKPOINT_REGRESSION = "11_验收/active_work_item_checkpoint_compiler_regression_cases.yaml"
CONTINUITY = "07_连续性与生产状态/连续性与当前生产状态.md"


class CheckpointActivationBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        self.read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        self.write_routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))

    def test_project_index_registers_accepted_checkpoint_candidate_once(self) -> None:
        policy = self.project["policy"]
        self.assertTrue(policy["active_work_item_checkpoint_compiler_required_for_checkpoint_or_series_close"])
        self.assertTrue(policy["active_work_item_checkpoint_runtime_is_proposal_readback_only"])
        self.assertTrue(policy["active_work_item_checkpoint_runtime_cannot_write_or_confirm_governed_ref"])

        canonical = self.project["canonical"]
        self.assertEqual(canonical["active_work_item_checkpoint_compiler"], CHECKPOINT_POLICY)
        self.assertEqual(
            canonical["active_work_item_checkpoint_compiler_regression_cases"],
            CHECKPOINT_REGRESSION,
        )
        effective = self.project["effective_sources"]
        self.assertEqual(effective[CHECKPOINT_POLICY], "github_verified")
        self.assertEqual(effective[CHECKPOINT_REGRESSION], "github_verified")

    def test_checkpoint_read_set_is_dedicated_and_not_always_on(self) -> None:
        read_sets = self.read_sets["read_sets"]
        checkpoint = read_sets["revision_checkpoint_compilation"]
        self.assertEqual(
            checkpoint["activation"],
            "checkpoint_or_revision_series_close_or_work_item_switch_or_explicit_checkpoint_only",
        )
        self.assertIn("PROJECT_INDEX.yaml", checkpoint["always"])
        self.assertIn(
            "active_work_item_checkpoint_compiler#trust+proposal+materialization_readback+finalization_contract",
            checkpoint["always"],
        )
        self.assertIn(
            "write_routes#revision_checkpoint_current_state+write_protocol",
            checkpoint["always"],
        )

        directing_always = read_sets["directing"]["always"]
        self.assertNotIn("active_work_item_checkpoint_compiler", directing_always)
        self.assertNotIn("revision_checkpoint_compilation", directing_always)
        self.assertEqual(
            directing_always,
            [
                "PROJECT_INDEX.yaml",
                "active_work_item_resolution_gate#continuation_detection+resolution+canonical_snapshot_verification",
                "连续性与当前生产状态#ACTIVE_WORK_ITEM_STATE_first",
                "AI电影系统#relevant_sections_only",
                "当前改编剧本#resolved_work_item_hit_range",
                "连续性与当前生产状态#resolved_work_item_details_only",
                "director_feature_compiler#runtime_binding+fail_closed",
                "director_route_index#symptom_scan+mandatory_reads",
                "learning_application_gate#pre_directing_gate+pre_output_gate",
                "learning_recall_index#compact_router_metadata_only",
                "proactive_execution_opportunity_router#next_step_scan",
            ],
        )

    def test_activation_does_not_create_parallel_checkpoint_write_route(self) -> None:
        routes = self.write_routes["routes"]
        self.assertEqual(routes["revision_checkpoint_current_state"], CONTINUITY)
        matches = [name for name, target in routes.items() if target == CONTINUITY]
        self.assertEqual(matches, ["current_shot_production_state", "revision_checkpoint_current_state"])
        self.assertNotIn("active_work_item_checkpoint_current_state", routes)
        checkpoint_routes = [name for name in routes if "checkpoint" in name]
        self.assertEqual(checkpoint_routes, ["revision_checkpoint_current_state"])

    def test_read_set_rules_preserve_external_write_and_ref_gate(self) -> None:
        rules = self.read_sets["rules"]
        self.assertTrue(rules["revision_checkpoint_compilation_must_use_checkpoint_compiler"])
        self.assertTrue(rules["revision_checkpoint_compiler_must_not_be_in_directing_always"])
        self.assertTrue(rules["revision_checkpoint_runtime_cannot_write_or_claim_persistence"])

        contract = yaml.safe_load((REPO_ROOT / CHECKPOINT_POLICY).read_text(encoding="utf-8"))
        boundary = contract["authority_boundary"]
        self.assertTrue(boundary["this_component_has_no_persistence_authority"])
        self.assertTrue(boundary["this_component_has_no_github_write_capability"])
        self.assertTrue(boundary["this_component_has_no_governed_ref_confirmation_authority"])
        transaction = contract["write_transaction_external_contract"]
        self.assertFalse(transaction["runtime_writes"])
        self.assertEqual(transaction["steps"][-1], "external_confirm_governed_target_ref")
        self.assertEqual(
            transaction["second_write_finalization"]["canonical_reporting_before_external_ref_confirmation"],
            "forbidden",
        )
        isolation = contract["candidate_isolation"]
        self.assertEqual(isolation["ordinary_directing_always_read"], "forbidden")
        self.assertEqual(isolation["new_parallel_continuity_write_route"], "forbidden")


if __name__ == "__main__":
    unittest.main()
