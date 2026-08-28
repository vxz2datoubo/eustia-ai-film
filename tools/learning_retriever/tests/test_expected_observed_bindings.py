from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION = "11_验收/expected_observed_eval_regression_cases.yaml"


class ExpectedObservedBindingTests(unittest.TestCase):
    def test_project_index_registers_execution_only_eval_regression(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        self.assertTrue(project["policy"]["expected_observed_eval_runtime_is_execution_only"])
        self.assertTrue(project["policy"]["expected_observed_eval_cannot_claim_automatic_media_grading"])
        self.assertEqual(project["canonical"]["expected_observed_eval_regression_cases"], REGRESSION)
        self.assertEqual(project["effective_sources"][REGRESSION], "github_verified")

    def test_read_sets_bind_reverse_eval_without_making_it_always_on(self):
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        directing = read_sets["read_sets"]["directing"]
        system_research = read_sets["read_sets"]["system_research"]
        self.assertNotIn("expected_observed_eval_regression_cases", directing["always"])
        self.assertEqual(
            directing["conditional"]["expected_observed_eval_regression"],
            "expected_observed_eval_regression_cases#when_generated_output_reverse_observation_expected_vs_observed_eval_or_targeted_repair_handoff_is_relevant",
        )
        self.assertEqual(
            system_research["conditional"]["expected_observed_eval_regression"],
            "expected_observed_eval_regression_cases#when_reverse_observation_eval_evidence_truthfulness_or_control_status_is_under_review",
        )

    def test_write_route_is_regression_only_and_unique(self):
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        self.assertEqual(routes["expected_observed_eval_regression_case"], REGRESSION)
        matches = [name for name, target in routes.items() if target == REGRESSION]
        self.assertEqual(matches, ["expected_observed_eval_regression_case"])
        self.assertNotEqual(routes["revision_trace_and_learning"], REGRESSION)
        self.assertNotEqual(routes["learning_evidence_and_outcome"], REGRESSION)

    def test_ci_triggers_and_runs_reverse_eval_tests_without_write_permission(self):
        workflow = (REPO_ROOT / ".github/workflows/learning-feature-compiler.yml").read_text(encoding="utf-8")
        self.assertIn(REGRESSION, workflow)
        self.assertIn("test_expected_observed_eval.py", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("tmp-wire-expected-observed", workflow)
        self.assertNotIn("tmp-harden-expected-observed", workflow)

    def test_no_temporary_write_workflows_remain(self):
        self.assertFalse((REPO_ROOT / ".github/workflows/_tmp-wire-expected-observed.yml").exists())
        self.assertFalse((REPO_ROOT / ".github/workflows/_tmp-harden-expected-observed.yml").exists())
        self.assertFalse((REPO_ROOT / "tools/learning_retriever/_tmp_wire_expected_observed.py").exists())
        self.assertFalse((REPO_ROOT / "tools/learning_retriever/_tmp_harden_expected_observed.py").exists())


if __name__ == "__main__":
    unittest.main()
