"""Explicit non-production seam for Camera Authority semantic validators.

This module is test-only in authority terms. It never reads GitHub, never verifies a
canonical materialization and can never emit ``CAMERA_AUTHORITY_BOUND_VERIFIED`` or
``camera_authority_available=True``. It exists so deterministic unit fixtures do not
monkeypatch production authority-bearing dependencies.
"""
from __future__ import annotations

from typing import Any, Mapping

from . import camera_authority as cam


def read_untrusted_camera_fixture(*, main_sha: str, continuity_text: str,
                                  active_state: Mapping[str, Any],
                                  identity_graph: Mapping[str, Any], resolver: Mapping[str, Any],
                                  materialization_verified: bool, shot_id: str | None = None):
    active_work_item = str(active_state.get("work_item_id") or "").strip()
    if not active_work_item:
        raise cam._fail("CAMERA_ACTIVE_WORK_ITEM_UNAVAILABLE")
    requested_shot = str(shot_id).strip() if shot_id is not None else None
    binding = cam._select_binding(
        cam._extract_binding_payload(continuity_text),
        active_work_item_id=active_work_item,
        shot_id=requested_shot,
    )
    if binding is None:
        return cam._unbound_receipt(work_item_id=active_work_item, shot_id=requested_shot, main_sha=main_sha)
    if materialization_verified is not True:
        raise cam._fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="untrusted_fixture_not_verified")

    scene_id = str(binding["scene_id"]); camera_id = str(binding["camera_anchor_id"])
    view_id = str(binding["view_id"]); asset_id = str(binding["asset_id"])
    scene = cam._active_record(identity_graph, "scenes", scene_id, node="scene")
    camera = cam._active_record(identity_graph, "camera_anchors", camera_id, node="camera_anchor")
    view = cam._active_record(identity_graph, "views", view_id, node="view")
    asset = cam._active_record(identity_graph, "media_assets", asset_id, node="media_asset")
    if camera.get("scene_id") != scene_id:
        raise cam._fail("CAMERA_IDENTITY_CHAIN_INVALID", node="camera_anchor_scene")
    if view.get("scene_id") != scene_id or view.get("camera_anchor_id") != camera_id:
        raise cam._fail("CAMERA_IDENTITY_CHAIN_INVALID", node="view_scene_anchor")
    if asset.get("view_id") != view_id:
        raise cam._fail("CAMERA_IDENTITY_CHAIN_INVALID", node="asset_view")
    relation_id = str(binding.get("relation_id") or "").strip() or None
    if relation_id:
        relation = cam._active_record(identity_graph, "relations", relation_id, node="relation")
        members = relation.get("member_view_ids")
        if not isinstance(members, list) or view_id not in {str(item) for item in members}:
            raise cam._fail("CAMERA_IDENTITY_CHAIN_INVALID", node="relation_view")
    selected_version = cam._resolve_media_version(resolver, binding, asset_id)

    view_class = str(view.get("view_class") or "")
    if view_class == "perspective":
        facing = view.get("facing_cardinal")
        if facing not in {"N", "S", "E", "W"}:
            raise cam._fail("CAMERA_ORIENTATION_METADATA_INVALID")
        orientation = {"view_class": view_class, "facing_cardinal": facing,
                       "yaw_offset_deg": view.get("yaw_offset_deg"), "pitch_deg": view.get("pitch_deg"),
                       "roll_deg": view.get("roll_deg")}
    elif view_class in {"top_orthographic", "top_oblique"}:
        screen_top = view.get("screen_top_cardinal")
        if screen_top not in {"N", "S", "E", "W"}:
            raise cam._fail("CAMERA_ORIENTATION_METADATA_INVALID")
        orientation = {"view_class": view_class, "screen_top_cardinal": screen_top,
                       "projection": view.get("projection")}
    else:
        orientation = {"view_class": view_class, "direction_authority": "not_applicable"}

    physical_position = {"world_position_relation": camera.get("world_position_relation"),
                         "map_xy_normalized": camera.get("map_xy_normalized"),
                         "elevation_m": camera.get("elevation_m"), "camera_height_m": camera.get("camera_height_m"),
                         "exact_transform": camera.get("exact_transform")}
    lens = {"focal_length_mm": view.get("focal_length_mm"), "lens_intent": view.get("lens_intent")}
    return cam.CameraAuthorityReceipt(
        status="UNTRUSTED_TEST_FIXTURE_BOUND", work_item_id=active_work_item,
        shot_id=str(binding["shot_id"]), camera_authority_available=False,
        binding=cam._freeze(binding), scene=cam._freeze(scene), camera_anchor=cam._freeze(camera),
        view=cam._freeze(view), media_asset=cam._freeze(asset), current_media_version_id=selected_version,
        orientation=cam._freeze(orientation), physical_position=cam._freeze(physical_position),
        lens=cam._freeze(lens), canonical_main_sha=main_sha,
    )


__all__ = ["read_untrusted_camera_fixture"]
