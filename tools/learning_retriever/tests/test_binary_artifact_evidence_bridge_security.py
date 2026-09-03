from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from learning_retriever.binary_artifact_evidence import (
    ArtifactEvidenceError,
    compare_artifact_bytes,
    observe_artifact_bytes,
)


class BinaryArtifactEvidenceBridgeSecurityTests(unittest.TestCase):
    def test_path_text_difference_cannot_mint_distinct_content(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.bin"
            b = root / "renamed-copy.data"
            payload = b"same-content"
            a.write_bytes(payload)
            b.write_bytes(payload)
            result = compare_artifact_bytes(a, b)
            self.assertEqual(result["content_relation"], "SAME_CONTENT")
            self.assertFalse(result["distinct_content_verified"])
            self.assertEqual(result["generation_binding_state"], "UNVERIFIED")

    def test_one_byte_difference_is_content_distinct_but_not_generation_distinct(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.bin"
            b = root / "b.bin"
            a.write_bytes(b"abcdef")
            b.write_bytes(b"abcdeg")
            result = compare_artifact_bytes(a, b)
            self.assertEqual(result["content_relation"], "DISTINCT_CONTENT")
            self.assertTrue(result["distinct_content_verified"])
            self.assertFalse(result["distinct_generation_event_verified"])
            self.assertEqual(result["generation_binding_state"], "UNVERIFIED")
            self.assertEqual(result["formal_asset_state"], "UNVERIFIED")

    def test_serialized_receipt_mapping_is_not_an_authority_input(self):
        forged = {
            "content_sha256": "0" * 64,
            "byte_length": 1,
            "byte_verification_state": "BYTE_VERIFIED",
        }
        with self.assertRaises((ArtifactEvidenceError, TypeError)):
            observe_artifact_bytes(forged)
        with self.assertRaises((ArtifactEvidenceError, TypeError)):
            compare_artifact_bytes(forged, forged)

    def test_caller_digest_string_is_not_a_locator_or_proof(self):
        with self.assertRaises(ArtifactEvidenceError):
            observe_artifact_bytes("sha256:" + "0" * 64)

    def test_directory_and_missing_path_fail_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ArtifactEvidenceError):
                observe_artifact_bytes(root)
            with self.assertRaises(ArtifactEvidenceError):
                observe_artifact_bytes(root / "missing.bin")

    def test_empty_file_has_real_byte_identity(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.bin"
            path.write_bytes(b"")
            receipt = observe_artifact_bytes(path)
            self.assertEqual(receipt["byte_length"], 0)
            self.assertEqual(receipt["byte_verification_state"], "BYTE_VERIFIED")
            self.assertEqual(receipt["generation_binding_state"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
