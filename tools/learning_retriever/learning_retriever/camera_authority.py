"""Read-only canonical camera authority adapter candidate.

This module never chooses a camera. It reads a materialized ShotCameraBinding from the
fixed GitHub canonical continuity document, verifies Scene -> Camera Anchor -> View ->
Media Asset identity against the canonical visual registry and resolver, and returns a
non-mintable readback result. Absence of a binding is a first-class fail-closed state.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from . import _active_work_item_remote as _remote

PROJECT_INDEX_PATH = Path("PROJECT_INDEX.yaml")
CONTINUITY_PATH = Path("07_连续性与生产状态/连续性与当前生产状态.md")
ASSET_REGISTRY_PATH = Path("06_视觉资产/视觉资产登记库.md")
RESOLVER_PATH = Path("10_运行时/scene_media_resolver_manifest.yaml")
IDENTITY_SCHEMA_PATH = Path("10_运行时/scene_asset_identity_schema.yaml")
BINDINGS_BEGIN = "<!-- SHOT_CAMERA_BINDINGS_BEGIN -->"
BINDINGS_END = "<!-- SHOT_CAMERA_BINDINGS_END -->"
_ALLOWED_BINDING_FIELDS = {
    "work_item_id",
    "shot_id",
    "scene_id",
    "camera_anchor_id",
    "view_id",
    "asset_id",
    "relation_id",
    "media_version_id",
    "binding_status",
    "provenance",
    "writeback_verified_commit",
}
_REQUIRED_BINDING_FIELDS = {
    "work_item_id",
    "shot_id",
    "scene_id",
    "camera_anchor_id",
    "view_id",
    "asset_id",
    "binding_status",
    "provenance",
    "writeback_verified_commit",
}


class CameraAuthorityError(ValueError):
    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(code)


@dataclass(frozen=True)
class CameraAuthorityReceipt:
    status: str
    work_item_id: str
    shot_id: str | None
    camera_authority_available: bool
    binding: dict[str, Any] | None
    scene: dict[str, Any] | None
    camera_anchor: dict[str, Any] | None
    view: dict[str, Any] | None
    media_asset: dict[str, Any] | None
    current_media_version_id: str | None
    orientation: dict[str, Any] | None
    physical_position: dict[str, Any] | None
    lens: dict[str, Any] | None
    canonical_main_sha: str
    pixels_seen: bool = False
    caller_camera_proposal_accepted_as_authority: bool = False
    camera_choice_performed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "work_item_id": self.work_item_id,
            "shot_id": self.shot_id,
            "camera_authority_available": self.camera_authority_available,
            "binding": dict(self.binding or {}) if self.binding else None,
            "scene": dict(self.scene or {}) if self.scene else None,
            "camera_anchor": dict(self.camera_anchor or {}) if self.camera_anchor else None,
            "view": dict(self.view or {}) if self.view else None,
            "media_asset": dict(self.media_asset or {}) if self.media_asset else None,
            "current_media_version_id": self.current_media_version_id,
            "orientation": dict(self.orientation or {}) if self.orientation else None,
            "physical_position": dict(self.physical_position or {}) if self.physical_position else None,
            "lens": dict(self.lens or {}) if self.lens else None,
            "canonical_main_sha": self.canonical_main_sha,
            "pixels_seen": self.pixels_seen,
            "caller_camera_proposal_accepted_as_authority": False,
            "camera_choice_performed": False,
            "authority_boundary": "fixed_github_readback_only",
        }


def _fail(code: str, **details: Any) -> CameraAuthorityError:
    return CameraAuthorityError(code, details=details or None)


def _full_sha(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="commit_not_full_sha")
    return text


def _current_main_sha() -> str:
    branch = _remote._github_api_json(
        f"/repos/{_remote.CANONICAL_REPOSITORY}/branches/{_remote.CANONICAL_BRANCH}"
    )
    sha = str(((branch.get("commit") or {}) if isinstance(branch, Mapping) else {}).get("sha") or "")
    return _full_sha(sha)


def _load_project_index(ref: str) -> dict[str, Any]:
    text = _remote._github_file_text(PROJECT_INDEX_PATH, ref)
    try:
        parsed = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise _fail("CAMERA_CANONICAL_INDEX_INVALID") from exc
    if not isinstance(parsed, Mapping) or parsed.get("project_id") != "EUSTIA_AI_FILM":
        raise _fail("CAMERA_CANONICAL_INDEX_INVALID")
    canonical = parsed.get("canonical")
    if not isinstance(canonical, Mapping):
        raise _fail("CAMERA_CANONICAL_INDEX_INVALID")
    required = {
        "continuity": CONTINUITY_PATH.as_posix(),
        "asset_registry": ASSET_REGISTRY_PATH.as_posix(),
        "scene_asset_identity_schema": IDENTITY_SCHEMA_PATH.as_posix(),
        "scene_media_resolver_manifest": RESOLVER_PATH.as_posix(),
    }
    for key, path in required.items():
        if canonical.get(key) != path:
            raise _fail("CAMERA_CANONICAL_INDEX_INVALID", field=key, expected=path)
    return dict(parsed)


def _extract_binding_payload(continuity_text: str) -> list[dict[str, Any]]:
    start = continuity_text.find(BINDINGS_BEGIN)
    end = continuity_text.find(BINDINGS_END)
    if start < 0 and end < 0:
        return []
    if start < 0 or end <= start:
        raise _fail("CAMERA_BINDING_BLOCK_INVALID")
    raw = continuity_text[start + len(BINDINGS_BEGIN):end].strip()
    for fence in ("```yaml", "```yml", "```"):
        if raw.startswith(fence):
            raw = raw[len(fence):].strip()
            break
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise _fail("CAMERA_BINDING_BLOCK_INVALID") from exc
    if not isinstance(parsed, Mapping):
        raise _fail("CAMERA_BINDING_BLOCK_INVALID")
    bindings = parsed.get("shot_camera_bindings")
    if not isinstance(bindings, list):
        raise _fail("CAMERA_BINDING_BLOCK_INVALID")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(bindings):
        if not isinstance(item, Mapping):
            raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index)
        record = dict(item)
        unknown = set(record) - _ALLOWED_BINDING_FIELDS
        missing = _REQUIRED_BINDING_FIELDS - set(record)
        if unknown or missing:
            raise _fail(
                "CAMERA_BINDING_RECORD_INVALID",
                index=index,
                unknown=sorted(unknown),
                missing=sorted(missing),
            )
        for key in _REQUIRED_BINDING_FIELDS - {"provenance"}:
            if not str(record.get(key) or "").strip():
                raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, field=key)
        if not record.get("provenance"):
            raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, field="provenance")
        if str(record["binding_status"]).upper() not in {"CONFIRMED", "LOCKED"}:
            raise _fail("CAMERA_BINDING_STATUS_NOT_AUTHORITATIVE", index=index)
        result.append(record)
    return result


def _identity_graph(registry_text: str) -> dict[str, Any]:
    match = re.search(
        r"(?s)# 5\. 新体系正式场景身份图\s*```ya?ml\s*(.*?)\s*```",
        registry_text,
    )
    if not match:
        raise _fail("CAMERA_IDENTITY_GRAPH_MISSING")
    try:
        parsed = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise _fail("CAMERA_IDENTITY_GRAPH_INVALID") from exc
    required = {"scenes", "camera_anchors", "views", "media_assets"}
    if not isinstance(parsed, Mapping) or not required.issubset(parsed):
        raise _fail("CAMERA_IDENTITY_GRAPH_INVALID")
    return dict(parsed)


def _verify_materialization(binding: Mapping[str, Any], *, main_sha: str) -> str:
    declared = _full_sha(binding.get("writeback_verified_commit"))
    commit = _remote._github_api_json(f"/repos/{_remote.CANONICAL_REPOSITORY}/commits/{declared}")
    if not isinstance(commit, Mapping) or commit.get("sha") != declared:
        raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="commit_missing")
    compare = _remote._github_api_json(
        f"/repos/{_remote.CANONICAL_REPOSITORY}/compare/{declared}...{main_sha}"
    )
    merge_base = compare.get("merge_base_commit") if isinstance(compare, Mapping) else None
    status = str(compare.get("status") or "") if isinstance(compare, Mapping) else ""
    if not isinstance(merge_base, Mapping) or merge_base.get("sha") != declared or status not in {"ahead", "identical"}:
        raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="commit_not_canonical_ancestor")

    historical = _extract_binding_payload(_remote._github_file_text(CONTINUITY_PATH, declared))
    identity_keys = (
        "work_item_id",
        "shot_id",
        "scene_id",
        "camera_anchor_id",
        "view_id",
        "asset_id",
        "relation_id",
        "media_version_id",
        "binding_status",
        "provenance",
    )
    target = {key: binding.get(key) for key in identity_keys}
    if not any({key: item.get(key) for key in identity_keys} == target for item in historical):
        raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="binding_not_present_at_declared_commit")
    return declared


def _select_binding(
    bindings: list[dict[str, Any]], *, work_item_id: str, shot_id: str | None
) -> dict[str, Any] | None:
    matches = [item for item in bindings if str(item.get("work_item_id")) == work_item_id]
    if shot_id is not None:
        matches = [item for item in matches if str(item.get("shot_id")) == shot_id]
    if not matches:
        return None
    if len(matches) > 1:
        raise _fail(
            "CAMERA_BINDING_AMBIGUOUS",
            work_item_id=work_item_id,
            shot_id=shot_id,
            count=len(matches),
        )
    return matches[0]


def read_camera_authority(
    *,
    work_item_id: str | None = None,
    shot_id: str | None = None,
) -> CameraAuthorityReceipt:
    """Read camera authority from fixed GitHub canonical state only.

    ``work_item_id`` and ``shot_id`` are selectors, never authority claims. No caller
    document, callback, binding object or verified boolean is accepted.
    """
    main_sha = _current_main_sha()
    _load_project_index(main_sha)
    continuity_text = _remote._github_file_text(CONTINUITY_PATH, main_sha)
    active_state = _remote._extract_state_payload(continuity_text)
    active_work_item = str(active_state.get("work_item_id") or "").strip()
    requested_work_item = str(work_item_id or active_work_item).strip()
    requested_shot = str(shot_id).strip() if shot_id is not None else None
    if not requested_work_item:
        raise _fail("CAMERA_WORK_ITEM_SELECTOR_INVALID")

    bindings = _extract_binding_payload(continuity_text)
    binding = _select_binding(bindings, work_item_id=requested_work_item, shot_id=requested_shot)
    if binding is None:
        return CameraAuthorityReceipt(
            status="CAMERA_AUTHORITY_UNBOUND",
            work_item_id=requested_work_item,
            shot_id=requested_shot,
            camera_authority_available=False,
            binding=None,
            scene=None,
            camera_anchor=None,
            view=None,
            media_asset=None,
            current_media_version_id=None,
            orientation=None,
            physical_position=None,
            lens=None,
            canonical_main_sha=main_sha,
        )

    _verify_materialization(binding, main_sha=main_sha)
    registry_text = _remote._github_file_text(ASSET_REGISTRY_PATH, main_sha)
    graph = _identity_graph(registry_text)
    resolver_text = _remote._github_file_text(RESOLVER_PATH, main_sha)
    try:
        resolver = yaml.safe_load(resolver_text) or {}
    except yaml.YAMLError as exc:
        raise _fail("CAMERA_MEDIA_RESOLVER_INVALID") from exc
    if not isinstance(resolver, Mapping):
        raise _fail("CAMERA_MEDIA_RESOLVER_INVALID")

    scene_id = str(binding["scene_id"])
    camera_id = str(binding["camera_anchor_id"])
    view_id = str(binding["view_id"])
    asset_id = str(binding["asset_id"])
    scene = (graph.get("scenes") or {}).get(scene_id)
    camera = (graph.get("camera_anchors") or {}).get(camera_id)
    view = (graph.get("views") or {}).get(view_id)
    asset = (graph.get("media_assets") or {}).get(asset_id)
    for label, record in (("scene", scene), ("camera_anchor", camera), ("view", view), ("media_asset", asset)):
        if not isinstance(record, Mapping) or record.get("status") != "active":
            raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node=label)
    if camera.get("scene_id") != scene_id:
        raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="camera_anchor_scene")
    if view.get("scene_id") != scene_id or view.get("camera_anchor_id") != camera_id:
        raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="view_scene_anchor")
    if asset.get("view_id") != view_id:
        raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="asset_view")

    resolver_asset = (resolver.get("assets") or {}).get(asset_id)
    if not isinstance(resolver_asset, Mapping):
        raise _fail("CAMERA_MEDIA_RESOLVER_INVALID", asset_id=asset_id)
    current_version = str(resolver_asset.get("current_version_id") or "").strip() or None
    pinned_version = str(binding.get("media_version_id") or "").strip() or None
    if pinned_version:
        versions = resolver_asset.get("versions") or []
        if not any(isinstance(item, Mapping) and item.get("version_id") == pinned_version for item in versions):
            raise _fail("CAMERA_MEDIA_VERSION_PIN_INVALID", media_version_id=pinned_version)
        selected_version = pinned_version
    else:
        selected_version = current_version

    view_class = str(view.get("view_class") or "")
    if view_class == "perspective":
        facing = view.get("facing_cardinal")
        if facing not in {"N", "S", "E", "W"}:
            raise _fail("CAMERA_ORIENTATION_METADATA_INVALID")
        orientation = {
            "view_class": view_class,
            "facing_cardinal": facing,
            "yaw_offset_deg": view.get("yaw_offset_deg"),
            "pitch_deg": view.get("pitch_deg"),
            "roll_deg": view.get("roll_deg"),
        }
    elif view_class in {"top_orthographic", "top_oblique"}:
        screen_top = view.get("screen_top_cardinal")
        if screen_top not in {"N", "S", "E", "W"}:
            raise _fail("CAMERA_ORIENTATION_METADATA_INVALID")
        orientation = {
            "view_class": view_class,
            "screen_top_cardinal": screen_top,
            "projection": view.get("projection"),
        }
    else:
        orientation = {"view_class": view_class, "direction_authority": "not_applicable"}

    physical_position = {
        "world_position_relation": camera.get("world_position_relation"),
        "map_xy_normalized": camera.get("map_xy_normalized"),
        "elevation_m": camera.get("elevation_m"),
        "camera_height_m": camera.get("camera_height_m"),
        "exact_transform": camera.get("exact_transform"),
    }
    lens = {
        "focal_length_mm": view.get("focal_length_mm"),
        "lens_intent": view.get("lens_intent"),
    }

    return CameraAuthorityReceipt(
        status="CAMERA_AUTHORITY_BOUND_VERIFIED",
        work_item_id=requested_work_item,
        shot_id=str(binding["shot_id"]),
        camera_authority_available=True,
        binding=dict(binding),
        scene=dict(scene),
        camera_anchor=dict(camera),
        view=dict(view),
        media_asset=dict(asset),
        current_media_version_id=selected_version,
        orientation=orientation,
        physical_position=physical_position,
        lens=lens,
        canonical_main_sha=main_sha,
    )
