from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import yaml

from learning_retriever.binary_artifact_evidence import (
    ArtifactByteObservation,
    ArtifactEvidenceError,
    inspect_artifact_bytes,
    verify_distinct_artifact_pair,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "10_运行时/binary_artifact_evidence_bridge_candidate.yaml"
REGRESSION_PATH = REPO_ROOT / "11_验收/binary_artifact_evidence_bridge_regression_cases.yaml"


class BinaryArtifactEvidenceBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_single_artifact_hash_is_computed_from_actual_bytes(self):
        path = self._write("artifact.bin", b"actual-media-bytes\x00\x01")
        observation = inspect_artifact_bytes(path)
        self.assertEqual(observation.content_sha256, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(observation.byte_length, path.stat().st_size)
        self.assertEqual(observation.byte_verification_state, "BYTE_VERIFIED")
        self.assertEqual(observation.generation_binding_state, "UNVERIFIED")
        self.assertEqual(observation.formal_asset_state, "UNVERIFIED")
        self.assertEqual(observation.pixel_semantic_verification_state, "NOT_PERFORMED")

    def test_same_bytes_under_different_paths_are_same_content(self):
        first = self._write("first.mp4", b"same-real-bytes")
        second = self.root / "renamed-copy.mov"
        shutil.copyfile(first, second)
        pair = verify_distinct_artifact_pair(first, second)
        self.assertTrue(pair.same_content)
        self.assertFalse(pair.distinct_content_verified)
        self.assertEqual(pair.before.content_identity, pair.after.content_identity)
        self.assertNotEqual(pair.before.locator_fingerprint, pair.after.locator_fingerprint)
        self.assertEqual(pair.generation_binding_state, "UNVERIFIED")
        self.assertFalse(pair.diagnostic_dict()["distinct_generation_events_verified"])

    def test_one_byte_difference_proves_content_difference_only(self):
        before = self._write("before.bin", b"abcdef")
        after = self._write("after.bin", b"abcdeg")
        pair = verify_distinct_artifact_pair(before, after)
        self.assertFalse(pair.same_content)
        self.assertTrue(pair.distinct_content_verified)
        self.assertNotEqual(pair.before.content_sha256, pair.after.content_sha256)
        self.assertEqual(pair.claim_scope, "BYTE_CONTENT_IDENTITY_ONLY")
        self.assertEqual(pair.generation_binding_state, "UNVERIFIED")
        diagnostic = pair.diagnostic_dict()
        self.assertFalse(diagnostic["distinct_generation_events_verified"])
        self.assertFalse(diagnostic["formal_assets_verified"])

    def test_empty_file_is_real_byte_identity(self):
        path = self._write("empty.bin", b"")
        observation = inspect_artifact_bytes(path)
        self.assertEqual(observation.byte_length, 0)
        self.assertEqual(
            observation.content_sha256,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        self.assertEqual(observation.byte_verification_state, "BYTE_VERIFIED")

    def test_public_surface_has_no_caller_digest_or_verified_parameters(self):
        single = inspect.signature(inspect_artifact_bytes).parameters
        pair = inspect.signature(verify_distinct_artifact_pair).parameters
        for forbidden in ("sha256", "digest", "byte_length", "verified", "receipt", "generation_id"):
            self.assertNotIn(forbidden, single)
            self.assertNotIn(forbidden, pair)
        with self.assertRaises(TypeError):
            inspect_artifact_bytes(self._write("x.bin", b"x"), sha256="0" * 64)

    def test_serialized_receipt_cannot_be_replayed_as_verifier_input(self):
        path = self._write("receipt-source.bin", b"receipt-source")
        observation = inspect_artifact_bytes(path)
        forged = observation.diagnostic_dict()
        forged["content_sha256"] = "0" * 64
        forged["byte_verification_state"] = "BYTE_VERIFIED"
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            inspect_artifact_bytes(forged)
        self.assertEqual(ctx.exception.code, "ARTIFACT_LOCATOR_INVALID")
        self.assertFalse(observation.diagnostic_dict()["serialized_receipt_reusable_as_authority"])

    def test_constructed_dataclass_is_not_pair_verifier_authority(self):
        forged = ArtifactByteObservation(
            content_sha256="0" * 64,
            byte_length=999,
            locator_fingerprint="forged",
        )
        path = self._write("actual.bin", b"actual")
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            verify_distinct_artifact_pair(forged, path)
        self.assertEqual(ctx.exception.code, "ARTIFACT_LOCATOR_INVALID")

    def test_missing_and_directory_locators_fail_closed(self):
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            inspect_artifact_bytes(self.root / "missing.bin")
        self.assertEqual(ctx.exception.code, "ARTIFACT_NOT_FOUND")
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            inspect_artifact_bytes(self.root)
        self.assertEqual(ctx.exception.code, "ARTIFACT_NOT_REGULAR_FILE")

    def test_symlink_locator_is_rejected(self):
        target = self._write("target.bin", b"target")
        link = self.root / "link.bin"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            inspect_artifact_bytes(link)
        self.assertEqual(ctx.exception.code, "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN")

    def test_chunk_size_is_bounded_and_cannot_change_identity(self):
        path = self._write("large.bin", b"0123456789" * 10000)
        small = inspect_artifact_bytes(path, chunk_size=4096)
        large = inspect_artifact_bytes(path, chunk_size=1024 * 1024)
        self.assertEqual(small.content_identity, large.content_identity)
        for invalid in (0, 1024, 9 * 1024 * 1024):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ArtifactEvidenceError) as ctx:
                    inspect_artifact_bytes(path, chunk_size=invalid)
                self.assertEqual(ctx.exception.code, "ARTIFACT_LOCATOR_INVALID")

    def test_candidate_policy_and_machine_registry_lock_claim_scope(self):
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        regression = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "candidate")
        self.assertTrue(policy["hard_invariants"]["locator_is_not_identity"])
        self.assertTrue(policy["hard_invariants"]["distinct_bytes_do_not_prove_distinct_generation_events"])
        self.assertEqual(policy["pair_verification"]["output_claim_limit"], "byte_content_identity_only")
        self.assertEqual(policy["pair_verification"]["generation_event_distinct_claim"], "forbidden")
        self.assertTrue(regression["invariants"]["serialized_receipt_never_verifier_input"])
        self.assertTrue(regression["isolation_gates"]["no_second_asset_authority"] if "no_second_asset_authority" in regression["isolation_gates"] else True)

    def test_candidate_is_not_registered_or_activated(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        read_sets = (REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8")
        write_routes = (REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8")
        self.assertNotIn("binary_artifact_evidence_bridge", project.get("canonical") or {})
        self.assertNotIn("binary_artifact_evidence_bridge_candidate.yaml", project.get("effective_sources") or {})
        self.assertNotIn("binary_artifact_evidence_bridge", read_sets)
        self.assertNotIn("binary_artifact_evidence_bridge", write_routes)

    def test_runtime_source_contains_no_writer_network_or_git_surface(self):
        source = (
            REPO_ROOT
            / "tools/learning_retriever/learning_retriever/binary_artifact_evidence.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "O_WRONLY",
            "O_RDWR",
            ".write_bytes(",
            ".write_text(",
            "open(\"w",
            "git ",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
