from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from learning_retriever.binary_artifact_evidence import (
    ArtifactEvidenceError,
    inspect_artifact_bytes,
    verify_distinct_artifact_pair,
)


class BinaryArtifactEvidenceBridgeSecurityTests(unittest.TestCase):
    def test_metadata_strings_cannot_mint_byte_verification(self):
        for value in (
            "sha256:" + "0" * 64,
            "file_00000000000000000000000000000000",
            "library://example",
            "GEN::123",
            "media::example",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactEvidenceError):
                    inspect_artifact_bytes(value)

    def test_serialized_receipt_mapping_cannot_be_replayed_as_authority(self):
        forged = {
            "content_sha256": "0" * 64,
            "byte_length": 1,
            "byte_verification_state": "BYTE_VERIFIED",
            "generation_binding_state": "VERIFIED",
        }
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            inspect_artifact_bytes(forged)
        self.assertEqual(ctx.exception.code, "ARTIFACT_LOCATOR_INVALID")
        with self.assertRaises(ArtifactEvidenceError) as ctx:
            verify_distinct_artifact_pair(forged, forged)
        self.assertEqual(ctx.exception.code, "ARTIFACT_LOCATOR_INVALID")

    def test_distinct_content_is_never_promoted_to_generation_event_identity(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = root / "before.bin"
            after = root / "after.bin"
            before.write_bytes(b"before")
            after.write_bytes(b"after")
            pair = verify_distinct_artifact_pair(before, after)
            self.assertTrue(pair.distinct_content_verified)
            self.assertFalse(pair.same_content)
            self.assertEqual(pair.claim_scope, "BYTE_CONTENT_IDENTITY_ONLY")
            self.assertEqual(pair.generation_binding_state, "UNVERIFIED")
            self.assertEqual(pair.formal_asset_binding_state, "UNVERIFIED")
            diagnostic = pair.diagnostic_dict()
            self.assertFalse(diagnostic["distinct_generation_events_verified"])
            self.assertFalse(diagnostic["formal_assets_verified"])

    def test_actual_existing_regular_file_is_required(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ArtifactEvidenceError) as ctx:
                inspect_artifact_bytes(root)
            self.assertEqual(ctx.exception.code, "ARTIFACT_NOT_REGULAR_FILE")
            with self.assertRaises(ArtifactEvidenceError) as ctx:
                inspect_artifact_bytes(root / "missing.bin")
            self.assertEqual(ctx.exception.code, "ARTIFACT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
