from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
POLICY = "10_运行时/final_delta_learning_policy.yaml"
REGRESSION = "11_验收/final_delta_learning_regression_cases.yaml"


class FinalDeltaCandidateBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = yaml.safe_load((ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        cls.read_sets = yaml.safe_load((ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        cls.write_routes = yaml.safe_load((ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))
        cls.policy = yaml.safe_load((ROOT / POLICY).read_text(encoding="utf-8"))

    def test_candidate_is_not_registered_or_activated_in_this_slice(self) -> None:
        canonical = self.project.get("canonical") or {}
        effective = self.project.get("effective_sources") or {}
        policy = self.project.get("policy") or {}
        self.assertNotIn("final_delta_learning_policy", canonical)
        self.assertNotIn("final_delta_learning_regression_cases", canonical)
        self.assertNotIn(POLICY, effective)
        self.assertNotIn(REGRESSION, effective)
        self.assertNotIn("final_delta_learning_runtime_is_execution_only", policy)

        for read_set in (self.read_sets.get("read_sets") or {}).values():
            if not isinstance(read_set, dict):
                continue
            always = read_set.get("always") or []
            conditional = read_set.get("conditional") or {}
            self.assertFalse(any("final_delta" in str(item).casefold() for item in always))
            self.assertFalse(any("final_delta" in str(key).casefold() for key in conditional))

    def test_candidate_adds_no_write_route_or_learning_authority(self) -> None:
        routes = self.write_routes.get("routes") or {}
        self.assertNotIn("final_delta_learning_regression_case", routes)
        self.assertNotIn("candidate_learning_evidence", routes)
        self.assertNotIn("final_delta_learning_evidence", routes)
        self.assertNotIn(REGRESSION, set(routes.values()))

    def test_policy_remains_execution_evidence_only(self) -> None:
        self.assertEqual(self.policy["status"], "candidate")
        output = self.policy["output_contract"]
        self.assertIsNone(output["canonical_write_target"])
        self.assertFalse(output["prompt_mutation_authorized"])
        self.assertFalse(output["generation_authorized"])
        self.assertFalse(output["camera_authority_mutation_authorized"])
        self.assertFalse(output["canonical_mutation_authorized"])
        self.assertFalse(output["learning_writeback_authorized"])
        self.assertFalse(output["maturity_promotion_authorized"])
        self.assertFalse(output["causal_claim_authorized"])

    def test_measurement_contract_safety_principles_remain_required(self) -> None:
        principles = self.policy["principles"]
        for key in (
            "observation_is_not_causality",
            "single_success_cannot_universalize",
            "explicit_change_record_required",
            "model_version_mismatch_not_aggregated",
            "automatic_maturity_promotion_forbidden",
            "automatic_canonical_writeback_forbidden",
            "automatic_prompt_mutation_forbidden",
        ):
            self.assertTrue(principles[key], key)


if __name__ == "__main__":
    unittest.main()
