from pathlib import Path
import unittest

import yaml

from learning_retriever import DirectorLearningRuntime, LearningRetriever
from learning_retriever.feature_compiler import (
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
    validate_semantic_dependencies,
)
from learning_retriever.route_resolver import resolve_hard_routes


REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_PATH = REPO_ROOT / "11_验收/director_feature_compiler_regression_cases.yaml"
REGRESSIONS = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
ROUTES = yaml.safe_load((REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8"))


class DirectorFeatureCompilerRegressionTests(unittest.TestCase):
    def _assert_declared_compatibility(self, case):
        compiled = [compile_director_features(description) for description in case["descriptions"]]
        expected = case["expected"]

        if "compatible_failure_mechanism" in expected:
            value = expected["compatible_failure_mechanism"]
            self.assertTrue(all(value in item.failure_mechanism for item in compiled))

        if "compatible_relation_type" in expected:
            value = expected["compatible_relation_type"]
            self.assertTrue(all(value in item.relation_type for item in compiled))

        for value in expected.get("compatible_spatial_action_features", []):
            self.assertTrue(all(value in item.spatial_action_features for item in compiled))

    def _assert_mandatory_hard_case(self, result, *, route_id, case_id):
        receipt = result["retrieval_receipt"]
        self.assertIn(route_id, result["canonical_runtime_receipt"]["hard_routes"])
        self.assertIn(route_id, receipt["hard_routes"])
        self.assertIn(case_id, receipt["mandatory_case_ids"])
        self.assertTrue(receipt["mandatory_recall_satisfied"])
        self.assertIn(case_id, receipt["selected_case_ids"])
        scored = next(x for x in receipt["scored_candidates"] if x["case_id"] == case_id)
        self.assertTrue(scored["hard"])

    def _assert_feature_expectations(self, compiled, case):
        for field, values in case.get("expected_present", {}).items():
            observed = getattr(compiled, field)
            for value in values:
                self.assertIn(value, observed)
        for field, values in case.get("expected_absent", {}).items():
            observed = getattr(compiled, field)
            for value in values:
                self.assertNotIn(value, observed)

    def test_declared_cross_surface_regressions_are_executable(self):
        for case in REGRESSIONS["cases"]:
            with self.subTest(case=case["id"]):
                self._assert_declared_compatibility(case)

    def test_cross_surface_same_mechanism_recalls_same_canonical_case(self):
        runtime = DirectorLearningRuntime(REPO_ROOT)
        for case in REGRESSIONS["retrieval_cases"]:
            expected = case["expected_case_id"]
            for index, description in enumerate(case["descriptions"]):
                with self.subTest(case=case["id"], description=index):
                    result = runtime.retrieve(description, task_id=f"{case['id']}-{index}", top_k=5)
                    selected = result["retrieval_receipt"]["selected_case_ids"]
                    self.assertIn(expected, selected)
                    self.assertEqual(selected[0], expected)
                    self.assertEqual(result["status"], "PASS")
                    if case.get("expected_hard_route"):
                        self._assert_mandatory_hard_case(
                            result,
                            route_id=case["expected_hard_route"],
                            case_id=case["expected_case_id"],
                        )

    def test_mandatory_learning_routes_bridge_compiled_semantics_without_literal_symptom(self):
        runtime = DirectorLearningRuntime(REPO_ROOT)
        route_map = {route["id"]: route for route in ROUTES["routes"]}
        for case in REGRESSIONS["mandatory_learning_route_paraphrases"]:
            with self.subTest(case=case["id"]):
                route = route_map[case["expected_hard_route"]]
                description = case["description"]
                self.assertFalse(
                    any(str(symptom).casefold() in description.casefold() for symptom in route.get("symptoms", []))
                )
                compiled = compile_director_features(description)
                expected_feature = case["expected_compiled_feature"]
                self.assertIn(expected_feature["value"], getattr(compiled, expected_feature["field"]))
                result = runtime.retrieve(description, task_id=case["id"], top_k=5)
                self._assert_mandatory_hard_case(
                    result,
                    route_id=case["expected_hard_route"],
                    case_id=case["expected_mandatory_case_id"],
                )

    def test_production_language_synonyms_and_event_target_carry_recall_mandatory_learning(self):
        runtime = DirectorLearningRuntime(REPO_ROOT)
        for case in REGRESSIONS["production_language_regressions"]:
            with self.subTest(case=case["id"]):
                compiled = compile_director_features(case["description"])
                self._assert_feature_expectations(compiled, case)
                self.assertIn(case["expected_matched_rule"], compiled.matched_rules)
                result = runtime.retrieve(case["description"], task_id=case["id"], top_k=5)
                self.assertEqual(result["status"], "PASS")
                for expected in case["expected_mandatory_cases"]:
                    self._assert_mandatory_hard_case(
                        result,
                        route_id=expected["route_id"],
                        case_id=expected["case_id"],
                    )

    def test_adjacent_event_target_carry_is_bounded(self):
        for case in REGRESSIONS["production_language_negative_regressions"]:
            with self.subTest(case=case["id"]):
                compiled = compile_director_features(case["description"])
                self._assert_feature_expectations(compiled, case)
                self.assertNotIn(case["forbidden_matched_rule"], compiled.matched_rules)

    def test_route_authority_owns_structured_trigger_mappings(self):
        route_map = {route["id"]: route for route in ROUTES["routes"]}
        for route_id in (
            "MOTIVATION_BEFORE_TONE",
            "EXPOSITION_STALL",
            "VN_TO_FILM_DIALOGUE",
            "TARGET_ORIENTED_SPATIAL_BINDING",
        ):
            with self.subTest(route=route_id):
                self.assertIn("machine_triggers", route_map[route_id])

        synthetic = {
            "routes": [
                {
                    "id": "SYNTHETIC_ROUTE_NOT_KNOWN_TO_RESOLVER",
                    "symptoms": ["完全不匹配的中文症状"],
                    "machine_triggers": {"any_of": {"dramatic_function": ["synthetic_function"]}},
                }
            ]
        }
        self.assertEqual(
            resolve_hard_routes({"dramatic_function": ["synthetic_function"]}, synthetic, description="另一种说法"),
            ["SYNTHETIC_ROUTE_NOT_KNOWN_TO_RESOLVER"],
        )

    def test_negative_semantic_regressions(self):
        for case in REGRESSIONS["negative_semantic_cases"]:
            with self.subTest(case=case["id"]):
                result = compile_director_features(case["description"], strict=case.get("strict", True))
                for field, values in case.get("expected_present", {}).items():
                    observed = getattr(result, field)
                    for value in values:
                        self.assertIn(value, observed)
                for field, values in case.get("expected_absent", {}).items():
                    observed = getattr(result, field)
                    for value in values:
                        self.assertNotIn(value, observed)

    def test_agent_only_orientation_never_activates_target_hard_route(self):
        runtime = DirectorLearningRuntime(REPO_ROOT)
        for case in REGRESSIONS["negative_target_route_cases"]:
            with self.subTest(case=case["id"]):
                result = runtime.retrieve(case["description"], task_id=case["id"], top_k=5)
                self.assertNotIn(case["forbidden_hard_route"], result["canonical_runtime_receipt"]["hard_routes"])
                self.assertNotIn(case["forbidden_hard_route"], result["retrieval_receipt"]["hard_routes"])
                compiled = result["canonical_runtime_receipt"]["feature_compiler_receipt"]
                self.assertNotIn(case["forbidden_hard_route"], compiled["hard_routes"])

    def test_background_crowd_does_not_force_motive_learning_case(self):
        case = next(x for x in REGRESSIONS["negative_semantic_cases"] if x["id"] == "background_crowd_is_not_crowd_reaction")
        features = compile_director_features(case["description"], strict=False)
        result = LearningRetriever(REPO_ROOT).retrieve({"task_id": "REG-BACKGROUND-CROWD", **features.as_dict()}, top_k=5)
        self.assertNotIn("MOTIVE-FIRST-CROWD-001", result["retrieval_receipt"]["selected_case_ids"])

    def test_unrecognized_description_fails_closed(self):
        case = next(x for x in REGRESSIONS["fail_closed_cases"] if x["id"] == "unrecognized_generic_scene")
        with self.assertRaisesRegex(FeatureCompilationError, case["expected_error"]):
            compile_director_features(case["description"])

    def test_natural_language_compile_requires_route_authority(self):
        case = next(x for x in REGRESSIONS["fail_closed_cases"] if x["id"] == "natural_language_without_route_authority")
        with self.assertRaisesRegex(FeatureCompilationError, case["expected_error"]):
            compile_retrieval_task(case["description"])

    def test_target_input_uses_mandatory_hard_route(self):
        gate = REGRESSIONS["hard_route_gate"]
        result = DirectorLearningRuntime(REPO_ROOT).retrieve(gate["description"], task_id="REG-HARD-ROUTE", top_k=5)
        self._assert_mandatory_hard_case(
            result,
            route_id=gate["expected_hard_route"],
            case_id=gate["expected_mandatory_case_id"],
        )

    def test_objective_word_does_not_activate_target_hard_route(self):
        gate = REGRESSIONS["negative_route_gate"]
        result = DirectorLearningRuntime(REPO_ROOT).retrieve(gate["description"], task_id="REG-OBJECTIVE-NOT-TARGET", top_k=5)
        self.assertNotIn(gate["forbidden_hard_route"], result["canonical_runtime_receipt"]["hard_routes"])
        self.assertNotIn(gate["forbidden_hard_route"], result["retrieval_receipt"]["hard_routes"])

    def test_canonical_runtime_binding_cannot_silently_bypass_compiler(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        gate = yaml.safe_load((REPO_ROOT / "10_运行时/learning_application_gate.yaml").read_text(encoding="utf-8"))
        compiler = yaml.safe_load((REPO_ROOT / "10_运行时/director_feature_compiler.yaml").read_text(encoding="utf-8"))
        source_authority = yaml.safe_load((REPO_ROOT / "10_运行时/source_authority.yaml").read_text(encoding="utf-8"))

        self.assertTrue(source_authority["rules"]["file_self_declared_active_cannot_override_project_index"])
        self.assertEqual(project["canonical"]["director_feature_compiler"], "10_运行时/director_feature_compiler.yaml")
        self.assertEqual(project["effective_sources"]["10_运行时/director_feature_compiler.yaml"], "github_verified")
        self.assertTrue(project["policy"]["director_feature_compiler_required_for_natural_language_directing"])

        always = read_sets["read_sets"]["directing"]["always"]
        compiler_pos = next(i for i, item in enumerate(always) if item.startswith("director_feature_compiler"))
        route_pos = next(i for i, item in enumerate(always) if item.startswith("director_route_index"))
        recall_pos = next(i for i, item in enumerate(always) if item.startswith("learning_recall_index"))
        self.assertLess(compiler_pos, route_pos)
        self.assertLess(route_pos, recall_pos)
        self.assertTrue(read_sets["rules"]["directing_must_invoke_director_feature_compiler_before_route_and_recall"])

        self.assertEqual(gate["authority"]["director_feature_compiler"], "10_运行时/director_feature_compiler.yaml")
        self.assertEqual(gate["smart_recall_runtime"]["fixed_flow"][:3], ["director_feature_compiler", "hard_route", "semantic_recall"])
        self.assertTrue(gate["smart_recall_runtime"]["natural_language_bypass_forbidden"])
        self.assertTrue(compiler["runtime_binding"]["natural_language_bypass_forbidden"])
        carry = compiler["resolution_rule"]["adjacent_event_target_carry"]
        self.assertTrue(carry["allowed"])
        self.assertTrue(carry["fail_closed_when_ambiguous"])

        result = DirectorLearningRuntime(REPO_ROOT).retrieve("角色下跪并面向门口圣女", task_id="REG-CANONICAL-RUNTIME")
        runtime_receipt = result["canonical_runtime_receipt"]
        self.assertTrue(runtime_receipt["compiler_invoked"])
        self.assertEqual(runtime_receipt["flow"], ["director_feature_compiler", "hard_route", "semantic_recall"])
        self.assertEqual(runtime_receipt["feature_compiler_receipt"]["status"], "PASS")

    def test_semantic_dependencies_bind_existing_soac_eventgraph_blocking_visibleir(self):
        self.assertEqual(validate_semantic_dependencies(REPO_ROOT), [])

    def test_structured_features_are_preserved_when_natural_language_is_compiled(self):
        task = compile_retrieval_task(
            "角色面向门口目标",
            task_id="REG-MERGE",
            base_task={"dramatic_function": ["explicit_user_feature"]},
            route_data=ROUTES,
        )
        self.assertIn("explicit_user_feature", task["dramatic_function"])
        self.assertIn("target_oriented_action", task["dramatic_function"])

    def test_compiler_is_query_only_and_does_not_duplicate_learning_authority(self):
        task = compile_retrieval_task("普通对白场景", task_id="REG-AUTHORITY", route_data=ROUTES)
        self.assertEqual(task["feature_compiler_receipt"]["authority_boundary"], "retrieval_query_only")
        self.assertEqual(task["feature_compiler_receipt"]["route_resolution"], "director_route_index")
        self.assertNotIn("learning_rules", task)
        self.assertNotIn("authority_ref", task)
        self.assertNotIn("maturity", task)
        self.assertNotIn("scope", task)


if __name__ == "__main__":
    unittest.main()
