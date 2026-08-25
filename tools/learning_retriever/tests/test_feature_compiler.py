from pathlib import Path
import unittest

import yaml

from learning_retriever import LearningRetriever
from learning_retriever.feature_compiler import (
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
    validate_semantic_dependencies,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_PATH = REPO_ROOT / "11_验收/director_feature_compiler_regression_cases.yaml"
REGRESSIONS = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))


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

    def test_declared_cross_surface_regressions_are_executable(self):
        for case in REGRESSIONS["cases"]:
            with self.subTest(case=case["id"]):
                self._assert_declared_compatibility(case)

    def test_cross_surface_same_mechanism_recalls_same_canonical_case(self):
        retriever = LearningRetriever(REPO_ROOT)
        for case in REGRESSIONS["retrieval_cases"]:
            expected = case["expected_case_id"]
            for index, description in enumerate(case["descriptions"]):
                with self.subTest(case=case["id"], description=index):
                    task = compile_retrieval_task(description, task_id=f"{case['id']}-{index}")
                    result = retriever.retrieve(task, top_k=5)
                    selected = result["retrieval_receipt"]["selected_case_ids"]
                    self.assertIn(expected, selected)
                    self.assertEqual(selected[0], expected)
                    self.assertEqual(result["status"], "PASS")

    def test_negative_semantic_regressions(self):
        for case in REGRESSIONS["negative_semantic_cases"]:
            with self.subTest(case=case["id"]):
                result = compile_director_features(case["description"])
                for field, values in case.get("expected_present", {}).items():
                    observed = getattr(result, field)
                    for value in values:
                        self.assertIn(value, observed)
                for field, values in case.get("expected_absent", {}).items():
                    observed = getattr(result, field)
                    for value in values:
                        self.assertNotIn(value, observed)

    def test_unrecognized_description_fails_closed(self):
        for case in REGRESSIONS["fail_closed_cases"]:
            with self.subTest(case=case["id"]):
                with self.assertRaisesRegex(FeatureCompilationError, case["expected_error"]):
                    compile_director_features(case["description"])

    def test_semantic_dependencies_bind_existing_soac_eventgraph_blocking_visibleir(self):
        self.assertEqual(validate_semantic_dependencies(REPO_ROOT), [])

    def test_structured_features_are_preserved_when_natural_language_is_compiled(self):
        task = compile_retrieval_task(
            "角色面向门口目标",
            task_id="REG-MERGE",
            base_task={"dramatic_function": ["explicit_user_feature"]},
        )
        self.assertIn("explicit_user_feature", task["dramatic_function"])
        self.assertIn("target_oriented_action", task["dramatic_function"])

    def test_compiler_is_query_only_and_does_not_duplicate_learning_authority(self):
        task = compile_retrieval_task("普通对白场景", task_id="REG-AUTHORITY")
        self.assertEqual(
            set(task["feature_compiler_receipt"]),
            {
                "component",
                "status",
                "input_fingerprint",
                "compiled_feature_keys",
                "matched_rules",
                "semantic_trace",
                "authority_boundary",
            },
        )
        self.assertEqual(task["feature_compiler_receipt"]["authority_boundary"], "retrieval_query_only")
        self.assertNotIn("learning_rules", task)
        self.assertNotIn("authority_ref", task)
        self.assertNotIn("maturity", task)
        self.assertNotIn("scope", task)


if __name__ == "__main__":
    unittest.main()
