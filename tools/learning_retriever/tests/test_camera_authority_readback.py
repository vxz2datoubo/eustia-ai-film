from __future__ import annotations

import unittest
from unittest.mock import patch

import yaml

from learning_retriever import camera_authority as cam

ACTIVE = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
SHOT = "SHOT-KAIM-SCARF-001"
MAIN = "a" * 40
WRITEBACK = "b" * 40
SCENE = "EUS-SCN-000001"
CAMERA = "EUS-CAM-000001"
VIEW = "EUS-VIEW-000001"
ASSET = "EUS-AST-000001"
VERSION = "EUS-VER-000001"
RELATION = "EUS-REL-000001"


def binding(**overrides):
    value = {
        "work_item_id": ACTIVE,
        "shot_id": SHOT,
        "scene_id": SCENE,
        "camera_anchor_id": CAMERA,
        "view_id": VIEW,
        "asset_id": ASSET,
        "relation_id": RELATION,
        "media_version_id": None,
        "binding_status": "LOCKED",
        "provenance": {"source": "canonical-continuity", "decision": "user-confirmed"},
        "writeback_verified_commit": WRITEBACK,
    }
    value.update(overrides)
    return value


def graph(*, facing="N", relation_members=None, asset_view=VIEW):
    view = {
        "view_id": VIEW,
        "scene_id": SCENE,
        "camera_anchor_id": CAMERA,
        "display_name_zh": "测试机位·朝北视图",
        "view_class": "perspective",
        "status": "active",
    }
    if facing is not None:
        view["facing_cardinal"] = facing
    return {
        "scenes": {
            SCENE: {"scene_id": SCENE, "display_name_zh": "测试场景", "map_node": "TEST", "status": "active"}
        },
        "camera_anchors": {
            CAMERA: {
                "camera_anchor_id": CAMERA,
                "scene_id": SCENE,
                "display_name_zh": "测试机位",
                "world_position_relation": "测试场景南侧",
                "status": "active",
            }
        },
        "views": {VIEW: view},
        "media_assets": {
            ASSET: {
                "asset_id": ASSET,
                "view_id": asset_view,
                "display_name_zh": "测试彩色母图",
                "media_role": "color_master",
                "status": "active",
            }
        },
        "relations": {
            RELATION: {
                "relation_id": RELATION,
                "relation_type": "continuity_match",
                "member_view_ids": relation_members if relation_members is not None else [VIEW],
                "status": "active",
            }
        },
    }


def resolver(*, version_asset=ASSET):
    return {
        "assets": {
            ASSET: {
                "current_version_id": VERSION,
                "versions": [
                    {
                        "version_id": VERSION,
                        "asset_id": version_asset,
                        "lifecycle_status": "current",
                        "pixel_verified": True,
                    }
                ],
            }
        }
    }


class CameraAuthorityReadbackTests(unittest.TestCase):
    def _bound_context(self, *, graph_value=None, resolver_value=None, binding_value=None):
        graph_value = graph_value or graph()
        resolver_value = resolver_value or resolver()
        binding_value = binding_value or binding()

        def file_text(path, ref):
            if path == cam.RESOLVER_PATH:
                return yaml.safe_dump(resolver_value, allow_unicode=True, sort_keys=False)
            return "fixture"

        patches = [
            patch.object(cam, "_current_main_sha", return_value=MAIN),
            patch.object(cam, "_load_project_index", return_value={}),
            patch.object(cam, "_load_identity_schema", return_value={}),
            patch.object(cam._remote, "_github_file_text", side_effect=file_text),
            patch.object(cam._remote, "_extract_state_payload", return_value={"work_item_id": ACTIVE}),
            patch.object(cam, "_extract_binding_payload", return_value=[binding_value]),
            patch.object(cam, "_verify_materialization", return_value=WRITEBACK),
            patch.object(cam, "_identity_graph", return_value=graph_value),
        ]
        return patches

    def _read_bound(self, *, graph_value=None, resolver_value=None, binding_value=None):
        patches = self._bound_context(
            graph_value=graph_value,
            resolver_value=resolver_value,
            binding_value=binding_value,
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        return cam.read_camera_authority(shot_id=SHOT)

    def test_public_api_has_no_raw_work_item_selector(self):
        with self.assertRaises(TypeError):
            cam.read_camera_authority(work_item_id="OLD-WORK-ITEM")

    def test_current_active_work_item_without_binding_is_unbound(self):
        with patch.object(cam, "_current_main_sha", return_value=MAIN), patch.object(
            cam, "_load_project_index", return_value={}
        ), patch.object(cam, "_load_identity_schema", return_value={}), patch.object(
            cam._remote, "_github_file_text", return_value="continuity-without-camera-bindings"
        ), patch.object(
            cam._remote, "_extract_state_payload", return_value={"work_item_id": ACTIVE}
        ):
            receipt = cam.read_camera_authority(shot_id=SHOT)
        self.assertEqual(receipt.status, "CAMERA_AUTHORITY_UNBOUND")
        self.assertFalse(receipt.camera_authority_available)
        self.assertFalse(receipt.camera_choice_performed)
        self.assertFalse(receipt.pixels_seen)

    def test_verified_receipt_is_recursively_immutable_and_projection_is_detached(self):
        receipt = self._read_bound()
        self.assertEqual(receipt.status, "CAMERA_AUTHORITY_BOUND_VERIFIED")
        self.assertTrue(receipt.camera_authority_available)
        with self.assertRaises(TypeError):
            receipt.binding["scene_id"] = "FORGED"
        with self.assertRaises(TypeError):
            receipt.binding["provenance"]["source"] = "FORGED"
        projection = receipt.as_dict()
        projection["binding"]["scene_id"] = "FORGED"
        projection["binding"]["provenance"]["source"] = "FORGED"
        self.assertEqual(receipt.binding["scene_id"], SCENE)
        self.assertEqual(receipt.binding["provenance"]["source"], "canonical-continuity")
        self.assertFalse(projection["pixels_seen"])

    def test_display_name_cannot_mint_missing_orientation_metadata(self):
        with self.assertRaises(cam.CameraAuthorityError) as caught:
            self._read_bound(graph_value=graph(facing=None))
        self.assertEqual(caught.exception.code, "CAMERA_ORIENTATION_METADATA_INVALID")

    def test_relation_must_contain_selected_view(self):
        with self.assertRaises(cam.CameraAuthorityError) as caught:
            self._read_bound(graph_value=graph(relation_members=["EUS-VIEW-999999"]))
        self.assertEqual(caught.exception.code, "CAMERA_IDENTITY_CHAIN_INVALID")
        self.assertEqual(caught.exception.details.get("node"), "relation_view")

    def test_resolver_version_cannot_claim_a_different_asset(self):
        with self.assertRaises(cam.CameraAuthorityError) as caught:
            self._read_bound(resolver_value=resolver(version_asset="EUS-AST-999999"))
        self.assertEqual(caught.exception.code, "CAMERA_MEDIA_RESOLVER_INVALID")

    def test_identity_schema_cannot_redirect_canonical_registry(self):
        malicious = {
            "schema_id": "EUSTIA_SCENE_ASSET_IDENTITY",
            "status": "active",
            "source_authority": {
                "formal_logical_asset_registry": "fake-registry.md",
                "media_version_and_locator_resolver": cam.RESOLVER_PATH.as_posix(),
                "current_binding_state": cam.CONTINUITY_PATH.as_posix(),
            },
        }
        with patch.object(
            cam._remote, "_github_file_text", return_value=yaml.safe_dump(malicious, allow_unicode=True)
        ):
            with self.assertRaises(cam.CameraAuthorityError) as caught:
                cam._load_identity_schema(MAIN)
        self.assertEqual(caught.exception.code, "CAMERA_IDENTITY_SCHEMA_INVALID")

    def test_valid_binding_uses_only_present_camera_and_view_metadata(self):
        receipt = self._read_bound()
        data = receipt.as_dict()
        self.assertEqual(data["orientation"]["facing_cardinal"], "N")
        self.assertEqual(data["physical_position"]["world_position_relation"], "测试场景南侧")
        self.assertIsNone(data["physical_position"]["exact_transform"])
        self.assertIsNone(data["lens"]["focal_length_mm"])
        self.assertIsNone(data["lens"]["lens_intent"])
        self.assertEqual(data["current_media_version_id"], VERSION)
        self.assertFalse(data["pixels_seen"])
        self.assertFalse(data["camera_choice_performed"])
        self.assertFalse(data["caller_camera_proposal_accepted_as_authority"])


if __name__ == "__main__":
    unittest.main()
