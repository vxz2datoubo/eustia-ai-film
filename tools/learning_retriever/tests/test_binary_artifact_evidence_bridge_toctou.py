from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest import mock

from learning_retriever.binary_artifact_evidence import ArtifactEvidenceError, observe_artifact_bytes


class BinaryArtifactEvidenceBridgeTOCTOUTests(unittest.TestCase):
    def test_regular_file_read_succeeds_without_mutation(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "stable.bin"
            path.write_bytes(b"stable")
            receipt = observe_artifact_bytes(path)
            self.assertEqual(receipt["byte_verification_state"], "BYTE_VERIFIED")
            self.assertEqual(receipt["byte_length"], 6)

    def test_mutation_during_read_is_fail_closed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutable.bin"
            path.write_bytes(b"abcdef")
            real_fstat = os.fstat
            calls = {"count": 0}

            def changing_fstat(fd):
                st = real_fstat(fd)
                calls["count"] += 1
                if calls["count"] >= 2:
                    class Changed:
                        st_dev = st.st_dev
                        st_ino = st.st_ino
                        st_mode = st.st_mode
                        st_size = st.st_size + 1
                        st_mtime_ns = st.st_mtime_ns + 1
                    return Changed()
                return st

            with mock.patch("learning_retriever.binary_artifact_evidence.os.fstat", side_effect=changing_fstat):
                with self.assertRaises(ArtifactEvidenceError) as ctx:
                    observe_artifact_bytes(path)
            self.assertEqual(ctx.exception.code, "ARTIFACT_MUTATED_DURING_READ")


if __name__ == "__main__":
    unittest.main()
