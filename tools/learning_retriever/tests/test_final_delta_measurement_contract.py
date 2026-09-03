from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever.final_delta import compile_final_delta_learning_evidence


REPO_ROOT = Path(__file__).resolve().parents[3]
EOE_SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)


def _fixture(case_id: str) -> dict:
    case = next(item for item in EOE_SUITE["cases"] if item["id"] == case_id)
    return deepcopy(case["payload"])


def _base_pair() -> tuple[dict, dict]:
    before = _fixture("EOE-EXPLICIT-FAIL-001")
    before["eval_id"] = "FD-MEASURE-BEFORE"
    context = before.setdefault("context", {})
    context.update(
        {
            "work_item_id": "FD-MEASURE-WORK-ITEM",
            "model": "C-DANCE",
            "model_version": "2.5",
            "generation_id": "GEN::FD-MEASURE-BEFORE",
        }
    )
    after = deepcopy(before)
    after["eval_id"] = "FD-MEASURE-AFTER"
    after["context"]["generation_id"] = "GEN::FD-MEASURE-AFTER"
    return before, after


def _change() -> dict:
    return {
        "change_id": "FD-MEASUREMENT-CONTRACT-CHANGE",
        "changed_variables": ["camera_execution"],
        "preserved_variables": ["story_goal"],
        "revoked_variables": [],
        "experimental_variables": [],
        "scope": "EPISODIC_WORK_ITEM",
        "evidence_refs": ["measurement_contract_regression"],
        "user_confirmation_state": "NOT_CONFIRMED",
    }


def _compile(before: dict, after: dict) -> dict:
    return compile_final_delta_learning_evidence(
        {
            "before_eval_input": before,
            "after_eval_input": after,
            "change_record": _change(),
            "learning_context": {"candidate_lesson": "measurement contract must remain stable"},
        },
        project_root=REPO_ROOT,
    )


def _make_after_exact_pass(after: dict) -> None:
    observation = after["reverse_observation"]["expectation_observations"]["capture_intent"]
    observation["comparison_mode"] = "exact_value"
    observation["observed_value"] = {"camera_physical_position": "exterior_side"}
    observation.pop("match_state", None)
    observation.pop("failure_category", None)
    observation["evidence_refs"] = ["after_frame"]


class FinalDeltaMeasurementContractTests(unittest.TestCase):
    def test_same_observed_value_cannot_resolve_by_switching_comparison_mode(self):
        before, after = _base_pair()
        observation = after["reverse_observation"]["expectation_observations"]["capture_intent"]
        observation["comparison_mode"] = "explicit_observation_judgment"
        observation["match_state"] = "MATCH"
        observation.pop("failure_category", None)
        observation["evidence_refs"] = ["same_observed_value_different_judgment"]
        result = _compile(before, after)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("MEASUREMENT_CONTRACT_MISMATCH", result["comparison_reasons"])
        self.assertIn("COMPARISON_MODE_MISMATCH", result["comparison_reasons"])
        self.assertFalse(result["measurement_contract_binding"]["matched"])
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_expectation_provenance_drift_blocks_real_pass_from_being_attributed(self):
        before, after = _base_pair()
        _make_after_exact_pass(after)
        after["expectations"][0]["provenance"] = {"source": "different_expectation_authority"}
        result = _compile(before, after)
        self.assertIn("EXPECTATION_CONTRACT_MISMATCH", result["comparison_reasons"])
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_observation_method_drift_blocks_attribution(self):
        before, after = _base_pair()
        _make_after_exact_pass(after)
        provenance = after["reverse_observation"]["provenance"]
        provenance["inspection_mode"] = "selected_frames"
        provenance["temporal_coverage"] = {"type": "selected_frames"}
        result = _compile(before, after)
        self.assertIn("OBSERVATION_METHOD_MISMATCH", result["comparison_reasons"])
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_evidence_source_drift_is_measurement_ruler_drift(self):
        before, after = _base_pair()
        _make_after_exact_pass(after)
        after["reverse_observation"]["provenance"]["evidence_source"] = "substituted_reviewer"
        result = _compile(before, after)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("OBSERVATION_METHOD_MISMATCH", result["comparison_reasons"])
        self.assertTrue(result["measurement_contract_binding"]["evidence_source_bound"])
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_same_measurement_contract_is_only_diagnostic_without_artifact_verifier(self):
        before, after = _base_pair()
        _make_after_exact_pass(after)
        result = _compile(before, after)
        self.assertTrue(result["measurement_contract_binding"]["matched"])
        self.assertTrue(result["source_pair_identity_binding"]["matched"])
        self.assertFalse(result["artifact_provenance_binding"]["verified"])
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("ARTIFACT_PROVENANCE_REQUIRED", result["comparison_reasons"])
        diagnostic = {
            item["field"]: item["transition"]
            for item in result["unattributed_transition_candidates"]
        }
        self.assertEqual(diagnostic["capture_intent"], "RESOLVED")
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])


if __name__ == "__main__":
    unittest.main()
