from pathlib import Path
import unittest

import yaml

from learning_retriever import immutable_byte_identity as primitive


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "10_运行时/immutable_byte_identity_candidate.yaml"
REGRESSION_PATH = REPO_ROOT / "11_验收/immutable_byte_identity_regression_cases.yaml"
PROJECT_INDEX_PATH = REPO_ROOT / "PROJECT_INDEX.yaml"
READ_SETS_PATH = REPO_ROOT / "10_运行时/read_sets.yaml"
WRITE_ROUTES_PATH = REPO_ROOT / "10_运行时/write_routes.yaml"


class ImmutableByteIdentityContractTests(unittest.TestCase):
    def test_candidate_contract_and_registry_are_narrow_and_unactivated(self):
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        suite = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["component_id"], "IMMUTABLE_BYTE_IDENTITY_PRIMITIVE")
        self.assertEqual(contract["status"], "candidate")
        self.assertEqual(suite["suite_id"], "IMMUTABLE_BYTE_IDENTITY_PRIMITIVE_V1")
        self.assertEqual(suite["status"], "candidate")

        hard = contract["hard_invariants"]
        for key in (
            "python_bytes_only",
            "mutable_buffer_input_forbidden",
            "string_or_path_locator_input_forbidden",
            "mapping_or_serialized_receipt_input_forbidden",
            "filesystem_io_forbidden",
            "path_resolution_forbidden",
            "os_mount_or_filesystem_classification_forbidden",
            "network_io_forbidden",
            "device_io_forbidden",
            "distinct_bytes_do_not_prove_distinct_source_artifacts",
            "distinct_bytes_do_not_prove_distinct_generation_events",
            "serialized_receipt_is_not_reusable_identity_authority",
        ):
            with self.subTest(key=key):
                self.assertTrue(hard[key])

    def test_old_path_verifier_attack_classes_are_structurally_retired_not_handwaved(self):
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        retired = contract["reviewer_attack_retirement"]
        for key in (
            "path_symlink_toctou_attacks",
            "nfs_cifs_sshfs_fuse_autofs_attacks",
            "ctime_mtime_change_version_attacks",
            "windows_reparse_unc_device_attacks",
        ):
            with self.subTest(key=key):
                self.assertEqual(retired[key]["state"], "structurally_removed")

        self.assertFalse(contract["single_value_observation"]["filesystem_access"])
        self.assertFalse(contract["single_value_observation"]["network_access"])
        self.assertEqual(
            contract["pair_comparison"]["output_claim_limit"],
            "in_memory_byte_content_identity_only",
        )
        self.assertEqual(contract["pair_comparison"]["source_artifact_distinct_claim"], "forbidden")
        self.assertEqual(contract["pair_comparison"]["generation_event_distinct_claim"], "forbidden")

    def test_regression_registry_contains_all_reframed_security_attacks(self):
        suite = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        ids = {case["id"] for case in suite["cases"]}
        required = {
            "IBI-MUTABLE-BYTEARRAY-REJECT-001",
            "IBI-MEMORYVIEW-REJECT-001",
            "IBI-PATH-STRING-REJECT-001",
            "IBI-PATHLIKE-REJECT-001",
            "IBI-SERIALIZED-RECEIPT-REPLAY-REJECT-001",
            "IBI-NFS-CIFS-FUSE-ATTACK-REMOVED-001",
            "IBI-SYMLINK-TOCTOU-ATTACK-REMOVED-001",
            "IBI-CTIME-MTIME-SEMANTICS-ATTACK-REMOVED-001",
            "IBI-DISTINCT-BYTES-NOT-PROVENANCE-001",
        }
        self.assertTrue(required.issubset(ids))

        invariants = suite["invariants"]
        self.assertTrue(invariants["path_or_locator_input_forbidden"])
        self.assertTrue(invariants["filesystem_io_surface_absent"])
        self.assertTrue(invariants["network_io_surface_absent"])
        self.assertTrue(invariants["distinct_content_does_not_prove_distinct_source_artifacts"])

    def test_candidate_is_not_registered_or_writable_through_canonical_runtime(self):
        index = yaml.safe_load(PROJECT_INDEX_PATH.read_text(encoding="utf-8"))
        read_sets = READ_SETS_PATH.read_text(encoding="utf-8")
        write_routes = WRITE_ROUTES_PATH.read_text(encoding="utf-8")

        self.assertNotIn("immutable_byte_identity", index.get("canonical") or {})
        self.assertNotIn(
            "10_运行时/immutable_byte_identity_candidate.yaml",
            index.get("effective_sources") or {},
        )
        self.assertNotIn("immutable_byte_identity", read_sets)
        self.assertNotIn("immutable_byte_identity", write_routes)

    def test_public_module_exposes_identity_only_not_resolver_or_registration_authority(self):
        forbidden = {
            "open_artifact",
            "resolve_artifact",
            "register_asset",
            "write_asset",
            "write_continuity",
            "write_learning",
            "bind_generation",
            "verify_generation",
            "promote_maturity",
        }
        public = {name for name in dir(primitive) if not name.startswith("_")}
        self.assertTrue(forbidden.isdisjoint(public))
        self.assertTrue(callable(primitive.observe_immutable_bytes))
        self.assertTrue(callable(primitive.compare_immutable_byte_pair))


if __name__ == "__main__":
    unittest.main()
