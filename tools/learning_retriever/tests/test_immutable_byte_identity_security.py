from __future__ import annotations

import ast
from pathlib import Path
import unittest

from learning_retriever.immutable_byte_identity import (
    ByteIdentityError,
    compare_immutable_byte_pair,
    observe_immutable_bytes,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = REPO_ROOT / "tools/learning_retriever/learning_retriever/immutable_byte_identity.py"


class ImmutableByteIdentitySecurityTests(unittest.TestCase):
    def test_runtime_has_no_filesystem_network_process_or_locator_import_surface(self):
        source = RUNTIME_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

        forbidden_modules = {
            "os", "pathlib", "io", "socket", "subprocess", "requests", "urllib",
            "http", "ftplib", "smbclient", "shutil", "tempfile",
        }
        self.assertTrue(forbidden_modules.isdisjoint(imported_roots))

        for forbidden_text in (
            "open(",
            "os.open",
            "os.read",
            "os.stat",
            "os.fstat",
            "Path(",
            ".read_bytes(",
            ".read_text(",
            ".write_bytes(",
            ".write_text(",
            "subprocess",
            "requests",
            "urllib",
            "socket",
        ):
            with self.subTest(forbidden_text=forbidden_text):
                self.assertNotIn(forbidden_text, source)

    def test_path_and_locator_strings_cannot_trigger_hidden_io(self):
        locator_like_values = (
            "/tmp/artifact.bin",
            r"\\attacker\share\artifact.bin",
            r"\\?\C:\artifact.bin",
            "file_00000000000000000000000000000000",
            "library://example",
            "media::example",
            "GEN::123",
            "sha256:" + "0" * 64,
        )
        for value in locator_like_values:
            with self.subTest(value=value):
                with self.assertRaises(ByteIdentityError) as ctx:
                    observe_immutable_bytes(value)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")

    def test_mutable_buffers_cannot_change_after_identity_observation_because_they_are_rejected(self):
        mutable = bytearray(b"before")
        with self.assertRaises(ByteIdentityError):
            observe_immutable_bytes(mutable)  # type: ignore[arg-type]
        mutable[:] = b"after!"
        with self.assertRaises(ByteIdentityError):
            observe_immutable_bytes(memoryview(mutable))  # type: ignore[arg-type]

    def test_distinct_bytes_never_inflate_to_artifact_or_generation_provenance(self):
        pair = compare_immutable_byte_pair(b"before", b"after")
        self.assertTrue(pair.distinct_content_observed)
        diagnostic = pair.diagnostic_dict()
        self.assertFalse(diagnostic["source_artifacts_verified"])
        self.assertFalse(diagnostic["distinct_generation_events_verified"])
        self.assertFalse(diagnostic["formal_assets_verified"])
        self.assertEqual(pair.source_artifact_binding_state, "UNVERIFIED")
        self.assertEqual(pair.generation_binding_state, "UNVERIFIED")
        self.assertEqual(pair.formal_asset_binding_state, "UNVERIFIED")

    def test_no_public_api_can_accept_source_or_generation_metadata(self):
        with self.assertRaises(TypeError):
            observe_immutable_bytes(b"x", source_path="/tmp/x")
        with self.assertRaises(TypeError):
            compare_immutable_byte_pair(b"a", b"b", generation_id="GEN-1")


if __name__ == "__main__":
    unittest.main()
