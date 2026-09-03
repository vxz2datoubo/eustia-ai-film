from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from learning_retriever.binary_artifact_evidence import ArtifactEvidenceError, observe_artifact_bytes


class BinaryArtifactEvidenceBridgeLocatorBoundaryTests(unittest.TestCase):
    def test_non_path_metadata_string_cannot_mint_byte_verification(self):
        for value in (
            "file_00000000000000000000000000000000",
            "library://example",
            "GEN::123",
            "media::example",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactEvidenceError):
                    observe_artifact_bytes(value)

    def test_actual_existing_regular_file_is_required(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "real.bin"
            path.write_bytes(b"x")
            receipt = observe_artifact_bytes(path)
            self.assertEqual(receipt["byte_verification_state"], "BYTE_VERIFIED")


if __name__ == "__main__":
    unittest.main()
