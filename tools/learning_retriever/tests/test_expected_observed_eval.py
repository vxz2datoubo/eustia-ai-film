from pathlib import Path
import unittest

import yaml

from learning_retriever.expected_observed import (
    ExpectedObservedEvalError,
    STRUCTURAL_GATE_CODES,
    evaluate_expected_vs_observed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)
SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)


class ExpectedObservedEvalTests(unittest.TestCase):
    def test_compile_cases_are_executable(self):
        for case in SUITE["cases"]:
            with self.subTest(case=case["id"]):
                result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
                self.assertEqual(result["status"], case["expected_status"])
                by_field = {item["field"]: item for item in result["results"]}
                for field, outcome in (case.get("expected_field_outcomes") or {}).items():
                    self.assertEqual(by_field[field]["outcome"], outcome)
                if "expected_control_status" in case:
                    self.assertEqual(result["control_status"], case["expected_control_status"])
                if "expected_failure_categories" in case:
                    categories = {
                        item["failure_category"]
                        for item in result["results"]
                        if item["failure_category"]
                    }
                    self.assertEqual(categories, set(case["expected_failure_categories"]))
                if "expected_repair_fields" in case:
                    repair_fields = {
                        item["field"] for item in result["targeted_repair_handoff"]["items"]
                    }
                    self.assertEqual(repair_fields, set(case["expected_repair_fields"]))
                if "expected_sampled_temporal_evidence" in case:
                    self.assertEqual(
                        result["observation_provenance"]["sampled_temporal_evidence"],
                        case["expected_sampled_temporal_evidence"],
                    )
                if "expected_frame_by_frame_claim" in case:
                    self.assertEqual(
                        result["observation_provenance"]["claimed_frame_by_frame_review"],
                        case["expected_frame_by_frame_claim"],
                    )

    def test_structural_gate_cases_fail_closed(self):
        for case in SUITE["structural_gate_cases"]:
            with self.subTest(case=case["id"]):
                with self.assertRaises(ExpectedObservedEvalError) as ctx:
                    evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
                self.assertEqual(ctx.exception.code, case["expected_error_code"])
                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_missing_observation_is_unknown_not_fail(self):
        case = next(
            item for item in SUITE["cases"]
            if item["id"] == "EOE-MISSING-OBSERVATION-UNKNOWN-001"
        )
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["results"][0]["outcome"], "UNKNOWN")
        self.assertIsNone(result["results"][0]["failure_category"])

    def test_failure_categories_are_canonical_reverse_compiler_vocabulary(self):
        canonical = set(SCHEMA["reverse_compiler"]["failure_categories"])
        for case in SUITE["cases"]:
            result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
            for item in result["results"]:
                if item["failure_category"]:
                    self.assertIn(item["failure_category"], canonical)

    def test_sampled_evidence_never_becomes_frame_by_frame_claim(self):
        case = next(
            item for item in SUITE["cases"] if item["id"] == "EOE-SAMPLED-EVIDENCE-001"
        )
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        provenance = result["observation_provenance"]
        self.assertTrue(provenance["sampled_temporal_evidence"])
        self.assertFalse(provenance["claimed_frame_by_frame_review"])
        self.assertEqual(provenance["inspection_mode"], "fixed_interval_sampling")

    def test_eval_never_mints_aesthetic_score_or_automatic_media_grade(self):
        case = SUITE["cases"][0]
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        self.assertIsNone(result["aesthetic_score"])
        self.assertFalse(result["automatic_media_grading_performed"])
        self.assertEqual(
            result["reverse_observation_boundary"],
            SCHEMA["reverse_compiler"]["boundary"],
        )

    def test_targeted_repair_handoff_does_not_mutate_prompt(self):
        case = next(
            item for item in SUITE["cases"] if item["id"] == "EOE-EXPLICIT-FAIL-001"
        )
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        handoff = result["targeted_repair_handoff"]
        self.assertTrue(handoff["items"])
        self.assertFalse(handoff["prompt_mutation_authorized"])
        self.assertNotIn("prompt", handoff)

    def test_learning_handoff_is_evidence_only(self):
        case = next(
            item for item in SUITE["cases"] if item["id"] == "EOE-EXPLICIT-FAIL-001"
        )
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        handoff = result["learning_evidence_handoff"]
        self.assertEqual(handoff["maturity_effect"], "none")
        self.assertFalse(handoff["promotion_authorized"])
        self.assertFalse(handoff["writeback_authorized"])

    def test_control_status_distinguishes_confounded_eval(self):
        case = next(
            item for item in SUITE["cases"] if item["id"] == "EOE-CONFOUNDED-CONTROL-001"
        )
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        self.assertEqual(result["control_status"], "CONFOUNDED")
        self.assertEqual(result["controlled_eval"]["confounds"], ["camera_position_changed"])


if __name__ == "__main__":
    unittest.main()
