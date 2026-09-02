import unittest
from unittest.mock import patch

import yaml

from learning_retriever import camera_authority as cam
from learning_retriever.camera_authority_test_fixture import read_untrusted_camera_fixture

MAIN = "a" * 40
MATERIALIZATION = "b" * 40
ACTIVE = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
SHOT = "SHOT-001"
SCENE = "EUS-SCN-000005"
CAMERA = "EUS-CAM-000009"
VIEW = "EUS-VIEW-000010"
ASSET = "EUS-AST-000010"
VERSION = "EUS-VER-000010"
RELATION = "EUS-REL-000004"


def binding():
    return {
        "work_item_id": ACTIVE, "shot_id": SHOT, "scene_id": SCENE,
        "camera_anchor_id": CAMERA, "view_id": VIEW, "asset_id": ASSET,
        "relation_id": RELATION, "media_version_id": VERSION,
        "binding_status": "LOCKED", "provenance": {"source": "TEST_FIXTURE"},
        "writeback_verified_commit": MATERIALIZATION,
    }


def continuity(with_binding=True):
    block = ""
    if with_binding:
        block = cam.BINDINGS_BEGIN + "\n```yaml\n" + yaml.safe_dump(
            {"shot_camera_bindings": [binding()]}, allow_unicode=True, sort_keys=False
        ) + "```\n" + cam.BINDINGS_END
    return "CONTINUITY\n" + block


def graph(facing="N", relation_members=None):
    return {
        "scenes": {SCENE: {"status": "active"}},
        "camera_anchors": {CAMERA: {"status": "active", "scene_id": SCENE, "world_position_relation": "south_plaza", "camera_height_m": 1.7}},
        "views": {VIEW: {"status": "active", "scene_id": SCENE, "camera_anchor_id": CAMERA, "view_class": "perspective", "facing_cardinal": facing, "focal_length_mm": 35}},
        "media_assets": {ASSET: {"status": "active", "view_id": VIEW}},
        "relations": {RELATION: {"status": "active", "member_view_ids": relation_members or [VIEW, "EUS-VIEW-000011"]}},
    }


def resolver(version_asset=ASSET):
    return {"assets": {ASSET: {"current_version_id": VERSION, "versions": [{"version_id": VERSION, "asset_id": version_asset, "lifecycle_status": "active"}]}}}


def fixture_read(*, with_binding=True, graph_value=None, resolver_value=None, shot_id=SHOT):
    return read_untrusted_camera_fixture(
        main_sha=MAIN, continuity_text=continuity(with_binding),
        active_state={"work_item_id": ACTIVE}, identity_graph=graph_value or graph(),
        resolver=resolver_value or resolver(), materialization_verified=True, shot_id=shot_id,
    )


class CameraAuthorityReadbackTests(unittest.TestCase):
    def test_current_active_work_item_without_binding_is_unbound(self):
        receipt = fixture_read(with_binding=False)
        self.assertEqual(receipt.status, "CAMERA_AUTHORITY_UNBOUND")
        self.assertFalse(receipt.camera_authority_available)

    def test_verified_receipt_is_recursively_immutable_and_projection_is_detached(self):
        receipt = fixture_read()
        self.assertEqual(receipt.status, "UNTRUSTED_TEST_FIXTURE_BOUND")
        self.assertFalse(receipt.camera_authority_available)
        projected = receipt.as_dict()
        self.assertFalse(projected["camera_authority_available"])
        self.assertFalse(projected["pixels_seen"])

    def test_display_name_cannot_mint_missing_orientation_metadata(self):
        with self.assertRaises(cam.CameraAuthorityError) as caught:
            fixture_read(graph_value=graph(facing=None))
        self.assertEqual(caught.exception.code, "CAMERA_ORIENTATION_METADATA_INVALID")

    def test_relation_must_contain_selected_view(self):
        with self.assertRaises(cam.CameraAuthorityError) as caught:
            fixture_read(graph_value=graph(relation_members=["EUS-VIEW-999999"]))
        self.assertEqual(caught.exception.code, "CAMERA_IDENTITY_CHAIN_INVALID")

    def test_resolver_version_cannot_claim_a_different_asset(self):
        with self.assertRaises(cam.CameraAuthorityError) as caught:
            fixture_read(resolver_value=resolver(version_asset="EUS-AST-999999"))
        self.assertEqual(caught.exception.code, "CAMERA_MEDIA_RESOLVER_INVALID")

    def test_identity_schema_cannot_redirect_canonical_registry(self):
        malicious = {
            "schema_id": "EUSTIA_SCENE_ASSET_IDENTITY", "status": "active",
            "source_authority": {
                "formal_logical_asset_registry": "fake-registry.md",
                "media_version_and_locator_resolver": cam.RESOLVER_PATH.as_posix(),
                "current_binding_state": cam.CONTINUITY_PATH.as_posix(),
            },
        }
        with patch.object(cam, "_REMOTE_FILE_TEXT", return_value=yaml.safe_dump(malicious, allow_unicode=True)):
            with self.assertRaises(cam.CameraAuthorityError) as caught:
                cam._load_identity_schema(MAIN)
        self.assertEqual(caught.exception.code, "CAMERA_IDENTITY_SCHEMA_INVALID")

    def test_public_api_has_no_work_item_or_authority_injection(self):
        import inspect
        signature = inspect.signature(cam.read_camera_authority)
        self.assertEqual(set(signature.parameters), {"shot_id"})


if __name__ == "__main__":
    unittest.main()
