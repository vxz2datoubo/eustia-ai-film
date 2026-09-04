from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest import mock

from learning_retriever.binary_artifact_evidence import (
    ArtifactEvidenceError,
    inspect_artifact_bytes,
    verify_distinct_artifact_pair,
)


def _secure_byte_platform() -> bool:
    return bool(
        os.name == "posix"
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and os.open in getattr(os, "supports_dir_fd", set())
        and os.stat in getattr(os, "supports_dir_fd", set())
        and os.stat in getattr(os, "supports_follow_symlinks", set())
    )


SECURE_BYTE_PLATFORM = _secure_byte_platform()


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

    def test_unc_and_device_namespaces_are_rejected_without_artifact_io(self):
        for value in (r"\\attacker\share\artifact.bin", r"\\?\C:\artifact.bin", r"\\.\PhysicalDrive0"):
            with self.subTest(value=value):
                with mock.patch("learning_retriever.binary_artifact_evidence.os.open") as open_mock:
                    with self.assertRaises(ArtifactEvidenceError) as ctx:
                        inspect_artifact_bytes(value)
                self.assertEqual(ctx.exception.code, "ARTIFACT_NETWORK_OR_DEVICE_LOCATOR_FORBIDDEN")
                open_mock.assert_not_called()

    @unittest.skipUnless(SECURE_BYTE_PLATFORM, "secure no-follow byte inspection unavailable")
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

    @unittest.skipUnless(SECURE_BYTE_PLATFORM, "secure no-follow byte inspection unavailable")
    def test_actual_existing_regular_file_is_required(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ArtifactEvidenceError) as ctx:
                inspect_artifact_bytes(root)
            self.assertEqual(ctx.exception.code, "ARTIFACT_NOT_REGULAR_FILE")
            with self.assertRaises(ArtifactEvidenceError) as ctx:
                inspect_artifact_bytes(root / "missing.bin")
            self.assertEqual(ctx.exception.code, "ARTIFACT_NOT_FOUND")

    @unittest.skipIf(SECURE_BYTE_PLATFORM, "test applies to unsupported platforms")
    def test_unsupported_platform_cannot_emit_byte_verified(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "actual.bin"
            path.write_bytes(b"actual")
            with mock.patch("learning_retriever.binary_artifact_evidence.os.open") as open_mock:
                with self.assertRaises(ArtifactEvidenceError) as ctx:
                    inspect_artifact_bytes(path)
            self.assertEqual(ctx.exception.code, "ARTIFACT_PLATFORM_SECURITY_UNSUPPORTED")
            open_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
