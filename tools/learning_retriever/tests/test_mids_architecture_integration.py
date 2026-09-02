from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[3]


def load_yaml(relative: str):
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


class MidsArchitectureIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.router = load_yaml("10_运行时/proactive_execution_opportunity_router.yaml")
        self.autonomy = load_yaml("10_运行时/execution_director_autonomy_candidate.yaml")
        self.world = load_yaml("10_运行时/persistent_film_world_state_adapter.yaml")
        self.creator = load_yaml("10_运行时/creator_preference_projection_adapter.yaml")
        self.regression = load_yaml("11_验收/mids_architecture_direction_regression_cases.yaml")
        self.project_index = (ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8")
        self.read_sets = (ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8")
        self.write_routes = (ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8")
        self.evidence = (ROOT / "09_资料证据/MIDS用户确认架构方向证据.md").read_text(encoding="utf-8")

    def test_user_decisions_are_traceable(self):
        self.assertIn("C B C", self.evidence)
        self.assertIn("DEC-MIDS-ARCH-001", self.evidence)
        self.assertIn("DEC-MIDS-ARCH-002", self.evidence)
        self.assertIn("DEC-MIDS-ARCH-003", self.evidence)

    def test_active_opportunity_router_remains_pre_autonomy_canonical_contract(self):
        self.assertEqual(self.router["version"], "1.0.0")
        self.assertNotIn("execution_autonomy_profile", self.router)
        self.assertNotIn("execution_director", self.router["scope"])
        self.assertNotIn("AUTONOMY_BYPASSED_HUMAN_GATE", str(self.router))

    def test_execution_director_autonomy_is_genuinely_unregistered_sidecar(self):
        profile = self.autonomy
        self.assertEqual(profile["profile_id"], "EXECUTION_DIRECTOR_C")
        self.assertEqual(profile["source"], "USER_EXPLICIT_CONFIRMED")
        self.assertEqual(profile["status"], "candidate_unregistered_unactivated")
        boundary = profile["authority_boundary"]
        self.assertFalse(boundary["registered_in_project_index"])
        self.assertFalse(boundary["included_in_directing_always_read_set"])
        self.assertFalse(boundary["included_in_write_routes"])
        self.assertFalse(boundary["can_override_current_proactive_router"])
        self.assertFalse(boundary["can_authorize_execution_by_itself"])
        self.assertTrue(boundary["activation_requires_separate_reviewed_integration_slice"])
        gates = set(profile["human_gate_required_when_any_true"])
        self.assertIn("core_story_or_worldview_change", gates)
        self.assertIn("canonical_map_topology_change", gates)
        self.assertIn("formal_default_asset_replacement", gates)
        self.assertIn("maturity_expansion_materially_broadens_scope", gates)
        self.assertIn("authority_source_change", gates)

        for corpus in (self.project_index, self.read_sets, self.write_routes):
            self.assertNotIn("execution_director_autonomy_candidate", corpus)
            self.assertNotIn("EXECUTION_DIRECTOR_C", corpus)

    def test_world_adapter_is_projection_not_second_authority(self):
        boundary = self.world["not_a_new_authority"]
        for key in (
            "screenplay_authority",
            "character_authority",
            "map_authority",
            "continuity_authority",
            "asset_authority",
            "camera_director_authority",
        ):
            self.assertFalse(boundary[key], key)
        contract = self.world["persistent_state_contract"]
        self.assertIn("omitted_state_is_inherited", contract["inheritance_rule"])
        self.assertTrue(self.world["object_persistence"]["omission_does_not_delete_object"])
        self.assertEqual(
            self.world["rendering_boundary"]["generation_model_role"],
            "renderer_or_executor_not_world_truth_source",
        )
        self.assertTrue(
            self.world["rendering_boundary"]["generated_output_cannot_mutate_world_state_without_reverse_observation_eval_and_governed_update"]
        )

    def test_creator_projection_never_outranks_user_or_project_canonical(self):
        order = self.creator["strict_authority_order"]
        self.assertEqual(order[0], "current_user_explicit_instruction")
        self.assertEqual(order[1], "PROJECT_INDEX_and_project_canonical")
        rules = self.creator["rules"]
        self.assertTrue(rules["current_user_instruction_always_wins"])
        self.assertTrue(rules["project_story_character_map_asset_continuity_always_win"])
        self.assertTrue(rules["one_acceptance_does_not_create_stable_creator_preference"])
        self.assertFalse(self.creator["storage_boundary"]["this_repo_is_global_creator_profile_store"])

    def test_candidate_adapters_are_not_project_index_authorities(self):
        self.assertNotIn("persistent_film_world_state_adapter", self.project_index)
        self.assertNotIn("creator_preference_projection_adapter", self.project_index)
        self.assertNotIn("execution_director_autonomy_candidate", self.project_index)
        self.assertEqual(self.world["activation"]["current"], "candidate")
        self.assertEqual(self.creator["activation"]["current"], "candidate")
        self.assertEqual(self.autonomy["activation_contract"]["current"], "dormant_candidate")

    def test_regression_suite_covers_all_three_confirmed_directions(self):
        cases = self.regression["cases"]
        decisions = {case.get("decision") for case in cases if case.get("decision")}
        self.assertIn("EXECUTION_DIRECTOR_AUTONOMY", decisions)
        self.assertIn("PERSISTENT_FILM_WORLD_MODEL", decisions)
        self.assertIn("CROSS_PROJECT_CREATOR_MODEL", decisions)
        ids = {case["id"] for case in cases}
        self.assertIn("MIDS-ARCH-002", ids)
        self.assertIn("MIDS-ARCH-005", ids)
        self.assertIn("MIDS-ARCH-007", ids)
        self.assertIn("MIDS-ARCH-011", ids)
        self.assertIn("MIDS-ARCH-012", ids)


if __name__ == "__main__":
    unittest.main()
