from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from learning_retriever.binary_artifact_evidence import compare_artifact_bytes


class BinaryArtifactEvidenceBridgeCopyIdentityTests(unittest.TestCase):
    def test_copied_binary_is_same_content_even_with_new_locator(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.video"
            copied = root / "copy.bin"
            source.write_bytes(b"\x00\x01\x02\x03")
            shutil.copyfile(source, copied)
            result = compare_artifact_bytes(source, copied)
            self.assertEqual(result["content_relation"], "SAME_CONTENT")
            self.assertFalse(result["distinct_content_verified"])
            self.assertFalse(result["distinct_generation_event_verified"])


if __name__ == "__main__":
    unittest.main()
