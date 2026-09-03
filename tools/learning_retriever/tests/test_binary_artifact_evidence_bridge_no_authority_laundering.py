from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from learning_retriever.binary_artifact_evidence import compare_artifact_bytes, observe_artifact_bytes


class BinaryArtifactEvidenceBridgeAuthorityLaunderingTests(unittest.TestCase):
    def test_byte_receipt_never_claims_pixels_generation_or_asset_authority(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.bin"
            path.write_bytes(b"artifact")
            receipt = observe_artifact_bytes(path)
            self.assertEqual(receipt["byte_verification_state"], "BYTE_VERIFIED")
            self.assertEqual(receipt["generation_binding_state"], "UNVERIFIED")
            self.assertEqual(receipt["formal_asset_state"], "UNVERIFIED")
            self.assertEqual(receipt["pixel_semantic_state"], "UNVERIFIED")

    def test_distinct_content_receipt_never_promotes_generation_binding(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = root / "before.bin"
            after = root / "after.bin"
            before.write_bytes(b"before")
            after.write_bytes(b"after")
            pair = compare_artifact_bytes(before, after)
            self.assertTrue(pair["distinct_content_verified"])
            self.assertFalse(pair["distinct_generation_event_verified"])
            self.assertEqual(pair["generation_binding_state"], "UNVERIFIED")
            self.assertEqual(pair["formal_asset_state"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
