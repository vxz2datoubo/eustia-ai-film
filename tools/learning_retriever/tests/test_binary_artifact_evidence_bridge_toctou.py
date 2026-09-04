from pathlib import Path
from tempfile import TemporaryDirectory
import os
import stat
import unittest
from unittest import mock

from learning_retriever.binary_artifact_evidence import ArtifactEvidenceError, inspect_artifact_bytes


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


@unittest.skipUnless(SECURE_BYTE_PLATFORM, "secure no-follow byte inspection unavailable")
class BinaryArtifactEvidenceBridgeTOCTOUTests(unittest.TestCase):
    def test_regular_file_read_succeeds_without_mutation(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "stable.bin"
            path.write_bytes(b"stable")
            receipt = inspect_artifact_bytes(path)
            self.assertEqual(receipt.byte_verification_state, "BYTE_VERIFIED")
            self.assertEqual(receipt.byte_length, 6)

    def test_size_or_mtime_mutation_during_read_is_fail_closed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutable.bin"
            path.write_bytes(b"abcdef")
            real_fstat = os.fstat
            regular_calls = {"count": 0}

            def changing_fstat(fd):
                st = real_fstat(fd)
                if stat.S_ISREG(st.st_mode):
                    regular_calls["count"] += 1
                    # regular #1 = secure-open postcheck; #2 = read-before;
                    # regular #3 = read-after, where mutation must be detected.
                    if regular_calls["count"] >= 3:
                        class Changed:
                            st_dev = st.st_dev
                            st_ino = st.st_ino
                            st_mode = st.st_mode
                            st_size = st.st_size + 1
                            st_mtime_ns = st.st_mtime_ns + 1
                            st_ctime_ns = st.st_ctime_ns
                            st_nlink = st.st_nlink
                        return Changed()
                return st

            with mock.patch(
                "learning_retriever.binary_artifact_evidence.os.fstat",
                side_effect=changing_fstat,
            ):
                with self.assertRaises(ArtifactEvidenceError) as ctx:
                    inspect_artifact_bytes(path)
            self.assertEqual(ctx.exception.code, "ARTIFACT_MUTATED_DURING_READ")

    def test_same_size_restored_mtime_but_ctime_change_is_fail_closed(self):
        """Regression for the reviewed same-size/restored-mtime mutation attack."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ctime-only.bin"
            path.write_bytes(b"abcdef")
            real_fstat = os.fstat
            regular_calls = {"count": 0}

            def ctime_only_change(fd):
                st = real_fstat(fd)
                if stat.S_ISREG(st.st_mode):
                    regular_calls["count"] += 1
                    if regular_calls["count"] >= 3:
                        class Changed:
                            st_dev = st.st_dev
                            st_ino = st.st_ino
                            st_mode = st.st_mode
                            st_size = st.st_size
                            st_mtime_ns = st.st_mtime_ns
                            st_ctime_ns = st.st_ctime_ns + 1
                            st_nlink = st.st_nlink
                        return Changed()
                return st

            with mock.patch(
                "learning_retriever.binary_artifact_evidence.os.fstat",
                side_effect=ctime_only_change,
            ):
                with self.assertRaises(ArtifactEvidenceError) as ctx:
                    inspect_artifact_bytes(path)
            self.assertEqual(ctx.exception.code, "ARTIFACT_MUTATED_DURING_READ")


if __name__ == "__main__":
    unittest.main()
