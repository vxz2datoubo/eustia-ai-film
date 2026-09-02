import unittest
from unittest.mock import patch

from learning_retriever import camera_authority
from learning_retriever.camera_authority import CameraAuthorityError, read_camera_authority


class CameraAuthorityRemoteProvenanceTests(unittest.TestCase):
    def test_remote_api_reader_substitution_fails_before_trusted_read(self):
        called = {"value": False}

        def forged_api(_path):
            called["value"] = True
            return {"commit": {"sha": "0" * 40}}

        with patch.object(camera_authority._remote, "_github_api_json", forged_api):
            with self.assertRaises(CameraAuthorityError) as ctx:
                read_camera_authority()

        self.assertEqual(ctx.exception.code, "CAMERA_REMOTE_PROVENANCE_SUBSTITUTED")
        self.assertFalse(called["value"])

    def test_remote_file_reader_substitution_fails_before_trusted_read(self):
        with patch.object(camera_authority._remote, "_github_file_text", lambda *_args, **_kwargs: "forged"):
            with self.assertRaises(CameraAuthorityError) as ctx:
                read_camera_authority()
        self.assertEqual(ctx.exception.code, "CAMERA_REMOTE_PROVENANCE_SUBSTITUTED")

    def test_remote_state_parser_substitution_fails_before_trusted_read(self):
        with patch.object(camera_authority._remote, "_extract_state_payload", lambda _text: {"work_item_id": "FAKE"}):
            with self.assertRaises(CameraAuthorityError) as ctx:
                read_camera_authority()
        self.assertEqual(ctx.exception.code, "CAMERA_REMOTE_PROVENANCE_SUBSTITUTED")


if __name__ == "__main__":
    unittest.main()
