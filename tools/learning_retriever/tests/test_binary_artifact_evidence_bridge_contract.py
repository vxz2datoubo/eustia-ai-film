from pathlib import Path
import unittest

import yaml

from learning_retriever import binary_artifact_evidence as bridge


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "10_运行时/binary_artifact_evidence_bridge_candidate.yaml"
REGRESSION_PATH = REPO_ROOT / "11_验收/binary_artifact_evidence_bridge_regression_cases.yaml"
PROJECT_INDEX_PATH = REPO_ROOT / "PROJECT_INDEX.yaml"
READ_SETS_PATH = REPO_ROOT / "10_运行时/read_sets.yaml"
WRITE_ROUTES_PATH = REPO_ROOT / "10_运行时/write_routes.yaml"


class BinaryArtifactEvidenceBridgeContractTests(unittest.TestCase):
    def test_candidate_contract_and_machine_registry_exist_and_remain_candidate(self):
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        suite = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["component_id"], "BINARY_ARTIFACT_EVIDENCE_BRIDGE")
        self.assertEqual(contract["status"], "candidate")
        self.assertEqual(suite["status"], "candidate")
        self.assertTrue(contract["hard_invariants"]["content_hash_must_be_computed_from_actual_bytes_by_runtime"])
        self.assertTrue(contract["hard_invariants"]["distinct_bytes_do_not_prove_distinct_generation_events"])
        self.assertTrue(contract["hard_invariants"]["serialized_receipt_is_not_reusable_verification_authority"])

    def test_candidate_is_not_registered_or_writable_through_canonical_runtime(self):
        index = yaml.safe_load(PROJECT_INDEX_PATH.read_text(encoding="utf-8"))
        read_sets = READ_SETS_PATH.read_text(encoding="utf-8")
        write_routes = WRITE_ROUTES_PATH.read_text(encoding="utf-8")

        self.assertNotIn("binary_artifact_evidence_bridge", index.get("canonical") or {})
        self.assertNotIn(
            "10_运行时/binary_artifact_evidence_bridge_candidate.yaml",
            index.get("effective_sources") or {},
        )
        self.assertNotIn("binary_artifact_evidence_bridge", read_sets)
        self.assertNotIn("binary_artifact_evidence_bridge", write_routes)

    def test_public_module_exposes_observation_only_not_registration_or_generation_binding(self):
        forbidden = {
            "register_asset",
            "write_asset",
            "write_continuity",
            "write_learning",
            "bind_generation",
            "verify_generation",
            "promote_maturity",
        }
        public = {name for name in dir(bridge) if not name.startswith("_")}
        self.assertTrue(forbidden.isdisjoint(public))
        self.assertTrue(callable(bridge.inspect_artifact_bytes))
        self.assertTrue(callable(bridge.verify_distinct_artifact_pair))


if __name__ == "__main__":
    unittest.main()
