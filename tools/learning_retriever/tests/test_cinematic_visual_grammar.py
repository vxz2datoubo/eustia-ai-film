from pathlib import Path
import unittest

import yaml

from learning_retriever import DirectorLearningRuntime
from learning_retriever.feature_compiler import compile_director_features, validate_semantic_dependencies


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTES = yaml.safe_load((REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8"))
SUITE = yaml.safe_load((REPO_ROOT / "11_验收/cinematic_visual_grammar_regression_cases.yaml").read_text(encoding="utf-8"))


class CinematicVisualGrammarCompilerTests(unittest.TestCase):
    def _runtime(self, description: str, task_id: str):
        result = DirectorLearningRuntime(REPO_ROOT).retrieve(description, task_id=task_id, top_k=5)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("CINEMATIC_VISUAL_GRAMMAR", result["canonical_runtime_receipt"]["hard_routes"])
        self.assertIn("CINEMATIC_VISUAL_GRAMMAR", result["retrieval_receipt"]["hard_routes"])
        return result

    def test_static_runtime_cases_are_executable(self):
        field_map = {
            "dramatic_function": "dramatic_function",
            "relation_type": "relation_type",
            "spatial_action_feature": "spatial_action_features",
            "failure_mechanism": "failure_mechanism",
        }
        for case in SUITE["static_runtime_cases"]:
            with self.subTest(case=case["id"]):
                compiled = compile_director_features(case["input"])
                expected = case["expected"]
                for expected_key, compiled_field in field_map.items():
                    if expected_key in expected:
                        self.assertIn(expected[expected_key], getattr(compiled, compiled_field))
                self.assertIn(expected["matched_rule"], compiled.matched_rules)
                result = self._runtime(case["input"], case["id"])
                self.assertIn(expected["hard_route"], result["canonical_runtime_receipt"]["hard_routes"])

    def test_positive_guard_cases_route_without_inventing_failure(self):
        present_map = {
            "dramatic_function": "dramatic_function",
            "relation_type": "relation_type",
            "spatial_action_feature": "spatial_action_features",
            "failure_mechanism": "failure_mechanism",
        }
        for case in SUITE["positive_guard_cases"]:
            with self.subTest(case=case["id"]):
                compiled = compile_director_features(case["input"])
                for key, value in case.get("expected_present", {}).items():
                    self.assertIn(value, getattr(compiled, present_map[key]))
                for key, value in case.get("expected_absent", {}).items():
                    self.assertNotIn(value, getattr(compiled, present_map[key]))
                result = self._runtime(case["input"], case["id"])
                self.assertIn(case["expected_route"], result["canonical_runtime_receipt"]["hard_routes"])

    def test_visual_grammar_keeps_four_feature_authority_keys(self):
        route = next(route for route in ROUTES["routes"] if route["id"] == "CINEMATIC_VISUAL_GRAMMAR")
        allowed = {"dramatic_function", "relation_type", "spatial_action_features", "failure_mechanism"}
        self.assertEqual(set(route["machine_triggers"]["any_of"]), allowed)
        compiler = yaml.safe_load((REPO_ROOT / "10_运行时/director_feature_compiler.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            set(compiler["cinematic_visual_vocabulary"]["failure_mechanisms"]),
            {
                "generic_cinematic_style_stacking",
                "composition_without_pressure",
                "attention_flow_break",
                "color_as_filter",
                "visual_density_overload",
                "reference_appearance_contamination",
                "template_composition_repetition",
                "unmotivated_capture_style",
            },
        )
        self.assertEqual(set(compiler["output"]), allowed)
        self.assertTrue(SUITE["gates"]["four_feature_keys_unchanged"])

    def test_cinematic_intent_ir_is_between_blocking_and_shot_plan(self):
        schema = yaml.safe_load((REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8"))
        chain = schema["compiler_chain"]
        blocking = chain.index("BlockingIR")
        cinematic = chain.index("CinematicIntentIR")
        shot = chain.index("ShotPlanIR")
        self.assertLess(blocking, cinematic)
        self.assertLess(cinematic, shot)
        required = SUITE["cinematic_intent_ir_gate"]["required_position"]
        self.assertEqual(chain[cinematic - 1], required["after"])
        self.assertEqual(chain[cinematic + 1], required["before"])
        layer = schema["ir_layers"]["CinematicIntentIR"]
        for field in SUITE["cinematic_intent_ir_gate"]["required_fields"]:
            self.assertIn(field, layer["fields"])

    def test_compiler_semantic_dependencies_include_cinematic_intent(self):
        self.assertEqual(validate_semantic_dependencies(REPO_ROOT), [])

    def test_route_does_not_create_second_learning_or_director_authority(self):
        route = next(route for route in ROUTES["routes"] if route["id"] == "CINEMATIC_VISUAL_GRAMMAR")
        self.assertEqual(route["maturity"], "candidate")
        self.assertIn("10_运行时/screen_observable_audible_ir_schema.yaml#CinematicIntentIR", route["mandatory_reads"])
        self.assertIn("01_AI电影系统/AI电影系统.md#CINEMATIC-VISUAL-GRAMMAR-001", route["mandatory_reads"])
        self.assertFalse(any("导演反馈学习案例" in ref for ref in route["mandatory_reads"]))
        self.assertTrue(SUITE["gates"]["no_second_director_authority"])
        self.assertTrue(SUITE["gates"]["no_second_learning_authority"])
        self.assertTrue(SUITE["gates"]["cinema_dna_is_evidence_only"])

    def test_project_index_registers_evidence_and_regression_not_external_authority(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            project["canonical"]["cinematic_visual_grammar_evidence"],
            "09_资料证据/Cinematic Visual Grammar外部研究与融合证据.md",
        )
        self.assertEqual(
            project["canonical"]["cinematic_visual_grammar_regression_cases"],
            "11_验收/cinematic_visual_grammar_regression_cases.yaml",
        )
        source = project["external_research_sources"]["cinema_dna_21x9x3"]
        self.assertEqual(source["status"], "pinned_evidence_only")
        self.assertEqual(source["authority_role"], "external_candidate_research_only")
        self.assertNotIn("cinema_dna_21x9x3", project.get("external_skills", {}))
        self.assertEqual(
            project["effective_sources"]["11_验收/canonical_migration_integrity_audit.md"],
            "github_verified",
        )

    def test_canonical_method_anchor_and_director_skill_registration_exist(self):
        method = (REPO_ROOT / "01_AI电影系统/AI电影系统.md").read_text(encoding="utf-8")
        self.assertIn("CINEMATIC-VISUAL-GRAMMAR-001", method)
        self.assertIn("S25-23 / CINEMATIC-VISUAL-GRAMMAR-001", method)

    def test_read_write_and_evidence_bindings_are_consistent(self):
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        directing = read_sets["read_sets"]["directing"]["conditional"]
        research = read_sets["read_sets"]["system_research"]["conditional"]
        for bindings in (directing, research):
            self.assertIn("cinematic_visual_grammar_evidence", bindings)
            self.assertIn("cinematic_visual_grammar_regression", bindings)

        write_routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertEqual(
            write_routes["cinematic_visual_grammar_research_evidence"],
            "09_资料证据/Cinematic Visual Grammar外部研究与融合证据.md",
        )
        self.assertEqual(
            write_routes["cinematic_visual_grammar_regression_case"],
            "11_验收/cinematic_visual_grammar_regression_cases.yaml",
        )

        schema = yaml.safe_load((REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            schema["authority_and_interfaces"]["research_evidence"],
            "09_资料证据/Cinematic Visual Grammar外部研究与融合证据.md",
        )
        self.assertTrue((REPO_ROOT / schema["authority_and_interfaces"]["research_evidence"]).exists())

    def test_candidate_skill_suite_never_self_promotes(self):
        self.assertEqual(SUITE["status"], "candidate")
        self.assertTrue(SUITE["gates"]["all_new_skills_candidate"])
        self.assertTrue(SUITE["gates"]["external_research_cannot_promote_maturity"])
        self.assertTrue(SUITE["gates"]["real_generation_required_for_scene_verified"])
        reference_case = next(
            case for case in SUITE["candidate_skill_cases"] if case["id"] == "REG-REFERENCE-DECOUPLING-001"
        )
        self.assertEqual(reference_case["evidence_status"], "candidate_planned_AB")
        self.assertIn("当前不得晋级scene_verified", reference_case["promotion_gate"])


if __name__ == "__main__":
    unittest.main()
