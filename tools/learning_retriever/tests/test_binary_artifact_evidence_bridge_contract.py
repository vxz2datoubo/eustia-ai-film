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
        hard = contract["hard_invariants"]
        self.assertTrue(hard["content_hash_must_be_computed_from_actual_bytes_by_runtime"])
        self.assertTrue(hard["distinct_bytes_do_not_prove_distinct_generation_events"])
        self.assertTrue(hard["serialized_receipt_is_not_reusable_verification_authority"])
        self.assertTrue(hard["every_locator_component_must_be_no_follow"])
        self.assertTrue(hard["unsupported_platform_must_fail_before_artifact_filesystem_io"])
        self.assertTrue(hard["unc_and_device_namespaces_forbidden_before_artifact_io"])
        self.assertTrue(hard["read_stability_must_bind_dev_inode_type_size_mtime_ctime_and_link_count"])

    def test_platform_security_contract_is_fail_closed_not_cross_platform_claim_inflation(self):
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        platform = contract["platform_security_contract"]
        self.assertEqual(platform["unsupported_platform_behavior"]["state"], "FAIL_CLOSED")
        self.assertEqual(
            platform["unsupported_platform_behavior"]["error_code"],
            "ARTIFACT_PLATFORM_SECURITY_UNSUPPORTED",
        )
        self.assertEqual(platform["windows_current_state"]["byte_verification"], "unsupported_fail_closed")
        self.assertTrue(platform["network_backed_locator_policy"]["rejection_before_artifact_io"])
        self.assertEqual(
            contract["single_artifact_observation"]["locator_traversal"],
            "component_by_component_pinned_dir_fd",
        )
        stability = set(contract["single_artifact_observation"]["stability_signature"])
        self.assertIn("st_ctime_ns", stability)
        self.assertIn("st_nlink", stability)

    def test_regression_registry_contains_all_fresh_security_attacks(self):
        suite = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        ids = {case["id"] for case in suite["cases"]}
        required = {
            "BAE-INTERMEDIATE-SYMLINK-LOCATOR-001",
            "BAE-SAME-SIZE-MTIME-RESTORED-CTIME-CHANGE-001",
            "BAE-UNSUPPORTED-PLATFORM-FAIL-CLOSED-001",
            "BAE-UNC-NETWORK-LOCATOR-001",
            "BAE-WINDOWS-DEVICE-NAMESPACE-001",
        }
        self.assertTrue(required.issubset(ids))
        invariants = suite["invariants"]
        self.assertTrue(invariants["every_locator_component_no_follow_required"])
        self.assertTrue(invariants["unsupported_platform_fails_before_artifact_io"])
        self.assertTrue(invariants["unc_device_namespaces_rejected_before_artifact_io"])
        self.assertTrue(invariants["read_stability_includes_ctime"])

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
