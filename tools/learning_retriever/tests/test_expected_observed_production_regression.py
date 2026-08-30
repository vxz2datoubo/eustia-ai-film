from pathlib import Path
import unittest

import yaml

from learning_retriever.expected_observed import evaluate_expected_vs_observed


REPO_ROOT = Path(__file__).resolve().parents[3]
SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)


class ExpectedObservedProductionRegressionTests(unittest.TestCase):
    def test_kaim_disappearance_case_is_sampled_attention_handoff_failure(self):
        case = next(
            item for item in SUITE["cases"]
            if item["id"] == "EOE-PROD-KAIM-DISAPPEARANCE-001"
        )
        self.assertIn("Issue #19 comment 5454103847", case["provenance_note"])
        result = evaluate_expected_vs_observed(case["payload"], project_root=REPO_ROOT)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["results"][0]["outcome"], "FAIL")
        self.assertEqual(result["results"][0]["failure_category"], "attention_handoff")
        self.assertTrue(result["observation_provenance"]["sampled_temporal_evidence"])
        self.assertFalse(result["observation_provenance"]["claimed_frame_by_frame_review"])
        self.assertEqual(
            result["observation_provenance"]["temporal_coverage"]["sample_count"],
            60,
        )
        self.assertEqual(
            result["observation_provenance"]["temporal_coverage"]["readable_samples"],
            59,
        )
        repair = result["targeted_repair_handoff"]
        self.assertEqual([item["field"] for item in repair["items"]], ["attention_handoff"])
        self.assertFalse(repair["prompt_mutation_authorized"])
        self.assertFalse(result["learning_evidence_handoff"]["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
