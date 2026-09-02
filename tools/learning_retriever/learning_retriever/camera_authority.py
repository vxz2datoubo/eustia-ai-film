"""Read-only canonical camera authority adapter candidate.

P1a is intentionally narrow: it can read camera authority only for the current
canonical active work item. It never chooses a camera, never accepts a caller-supplied
binding/receipt/root, and never promotes an AI camera proposal into authority.
Historical work items require a later canonical historical-resolution integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from types import MappingProxyType
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
    "work_item_id", "shot_id", "scene_id", "camera_anchor_id", "view_id", "asset_id",
    "relation_id", "media_version_id", "binding_status", "provenance", "writeback_verified_commit",
}
_REQUIRED_BINDING_FIELDS = {
    "work_item_id", "shot_id", "scene_id", "camera_anchor_id", "view_id", "asset_id",
    "binding_status", "provenance", "writeback_verified_commit",
}

_REMOTE_MODULE = _remote
_REMOTE_API_JSON = _remote._github_api_json
_REMOTE_FILE_TEXT = _remote._github_file_text
_REMOTE_EXTRACT_STATE = _remote._extract_state_payload
_REMOTE_REPOSITORY = _remote.CANONICAL_REPOSITORY
_REMOTE_BRANCH = _remote.CANONICAL_BRANCH
_REMOTE_SOURCE_PATH = Path(_remote.__file__).resolve()
_REMOTE_SOURCE_DIGEST = sha256(_REMOTE_SOURCE_PATH.read_bytes()).hexdigest()
_THIS_PACKAGE_DIR = Path(__file__).resolve().parent


class CameraAuthorityError(ValueError):
    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(code)


def _fail(code: str, **details: Any) -> CameraAuthorityError:
    return CameraAuthorityError(code, details=details or None)


def _verify_remote_provenance() -> None:
    try:
        current_path = Path(_remote.__file__).resolve()
        current_digest = sha256(current_path.read_bytes()).hexdigest()
    except Exception as exc:
        raise _fail("CAMERA_REMOTE_PROVENANCE_INVALID", reason=type(exc).__name__) from exc
    if (
        _remote is not _REMOTE_MODULE
        or _remote._github_api_json is not _REMOTE_API_JSON
        or _remote._github_file_text is not _REMOTE_FILE_TEXT
        or _remote._extract_state_payload is not _REMOTE_EXTRACT_STATE
        or _remote.CANONICAL_REPOSITORY != _REMOTE_REPOSITORY
        or _remote.CANONICAL_BRANCH != _REMOTE_BRANCH
        or current_path != _REMOTE_SOURCE_PATH
        or current_path.parent != _THIS_PACKAGE_DIR
        or current_digest != _REMOTE_SOURCE_DIGEST
    ):
        raise _fail("CAMERA_REMOTE_PROVENANCE_SUBSTITUTED")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class CameraAuthorityReceipt:
    status: str
    work_item_id: str
    shot_id: str | None
    camera_authority_available: bool
    binding: Mapping[str, Any] | None
    scene: Mapping[str, Any] | None
    camera_anchor: Mapping[str, Any] | None
    view: Mapping[str, Any] | None
    media_asset: Mapping[str, Any] | None
    current_media_version_id: str | None
    orientation: Mapping[str, Any] | None
    physical_position: Mapping[str, Any] | None
    lens: Mapping[str, Any] | None
    canonical_main_sha: str
    pixels_seen: bool = False
    caller_camera_proposal_accepted_as_authority: bool = False
    camera_choice_performed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status, "work_item_id": self.work_item_id, "shot_id": self.shot_id,
            "camera_authority_available": self.camera_authority_available,
            "binding": _thaw(self.binding) if self.binding is not None else None,
            "scene": _thaw(self.scene) if self.scene is not None else None,
            "camera_anchor": _thaw(self.camera_anchor) if self.camera_anchor is not None else None,
            "view": _thaw(self.view) if self.view is not None else None,
            "media_asset": _thaw(self.media_asset) if self.media_asset is not None else None,
            "current_media_version_id": self.current_media_version_id,
            "orientation": _thaw(self.orientation) if self.orientation is not None else None,
            "physical_position": _thaw(self.physical_position) if self.physical_position is not None else None,
            "lens": _thaw(self.lens) if self.lens is not None else None,
            "canonical_main_sha": self.canonical_main_sha,
            "pixels_seen": False, "caller_camera_proposal_accepted_as_authority": False,
            "camera_choice_performed": False,
            "authority_boundary": "fixed_github_current_active_work_item_readback_only",
        }


def _full_sha(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="commit_not_full_sha")
    return text


def _current_main_sha() -> str:
    branch = _REMOTE_API_JSON(f"/repos/{_REMOTE_REPOSITORY}/branches/{_REMOTE_BRANCH}")
    sha = str(((branch.get("commit") or {}) if isinstance(branch, Mapping) else {}).get("sha") or "")
    return _full_sha(sha)


def _parse_yaml(text: str, *, code: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise _fail(code) from exc
    if not isinstance(parsed, Mapping):
        raise _fail(code)
    return dict(parsed)


def _load_project_index(ref: str) -> dict[str, Any]:
    parsed = _parse_yaml(_REMOTE_FILE_TEXT(PROJECT_INDEX_PATH, ref), code="CAMERA_CANONICAL_INDEX_INVALID")
    if parsed.get("project_id") != "EUSTIA_AI_FILM":
        raise _fail("CAMERA_CANONICAL_INDEX_INVALID")
    canonical = parsed.get("canonical")
    if not isinstance(canonical, Mapping):
        raise _fail("CAMERA_CANONICAL_INDEX_INVALID")
    required = {
        "continuity": CONTINUITY_PATH.as_posix(), "asset_registry": ASSET_REGISTRY_PATH.as_posix(),
        "scene_asset_identity_schema": IDENTITY_SCHEMA_PATH.as_posix(),
        "scene_media_resolver_manifest": RESOLVER_PATH.as_posix(),
    }
    for key, path in required.items():
        if canonical.get(key) != path:
            raise _fail("CAMERA_CANONICAL_INDEX_INVALID", field=key, expected=path)
    return parsed


def _load_identity_schema(ref: str) -> dict[str, Any]:
    schema = _parse_yaml(_REMOTE_FILE_TEXT(IDENTITY_SCHEMA_PATH, ref), code="CAMERA_IDENTITY_SCHEMA_INVALID")
    if schema.get("schema_id") != "EUSTIA_SCENE_ASSET_IDENTITY" or schema.get("status") != "active":
        raise _fail("CAMERA_IDENTITY_SCHEMA_INVALID")
    source_authority = schema.get("source_authority")
    if not isinstance(source_authority, Mapping):
        raise _fail("CAMERA_IDENTITY_SCHEMA_INVALID")
    if source_authority.get("formal_logical_asset_registry") != ASSET_REGISTRY_PATH.as_posix():
        raise _fail("CAMERA_IDENTITY_SCHEMA_INVALID", field="formal_logical_asset_registry")
    if source_authority.get("media_version_and_locator_resolver") != RESOLVER_PATH.as_posix():
        raise _fail("CAMERA_IDENTITY_SCHEMA_INVALID", field="media_version_and_locator_resolver")
    if source_authority.get("current_binding_state") != CONTINUITY_PATH.as_posix():
        raise _fail("CAMERA_IDENTITY_SCHEMA_INVALID", field="current_binding_state")
    return schema


def _extract_binding_payload(continuity_text: str) -> list[dict[str, Any]]:
    start = continuity_text.find(BINDINGS_BEGIN); end = continuity_text.find(BINDINGS_END)
    if start < 0 and end < 0: return []
    if start < 0 or end <= start: raise _fail("CAMERA_BINDING_BLOCK_INVALID")
    raw = continuity_text[start + len(BINDINGS_BEGIN):end].strip()
    for fence in ("```yaml", "```yml", "```"):
        if raw.startswith(fence): raw = raw[len(fence):].strip(); break
    if raw.endswith("```"): raw = raw[:-3].strip()
    parsed = _parse_yaml(raw, code="CAMERA_BINDING_BLOCK_INVALID")
    bindings = parsed.get("shot_camera_bindings")
    if not isinstance(bindings, list): raise _fail("CAMERA_BINDING_BLOCK_INVALID")
    result = []
    for index, item in enumerate(bindings):
        if not isinstance(item, Mapping): raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index)
        record = dict(item); unknown = set(record) - _ALLOWED_BINDING_FIELDS; missing = _REQUIRED_BINDING_FIELDS - set(record)
        if unknown or missing: raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, unknown=sorted(unknown), missing=sorted(missing))
        for key in _REQUIRED_BINDING_FIELDS - {"provenance"}:
            if not str(record.get(key) or "").strip(): raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, field=key)
        provenance = record.get("provenance")
        if isinstance(provenance, str):
            if not provenance.strip(): raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, field="provenance")
        elif isinstance(provenance, Mapping):
            if not provenance: raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, field="provenance")
        else: raise _fail("CAMERA_BINDING_RECORD_INVALID", index=index, field="provenance")
        if str(record["binding_status"]).upper() not in {"CONFIRMED", "LOCKED"}: raise _fail("CAMERA_BINDING_STATUS_NOT_AUTHORITATIVE", index=index)
        result.append(record)
    return result


def _identity_graph(registry_text: str) -> dict[str, Any]:
    match = re.search(r"(?s)# 5\. 新体系正式场景身份图\s*```ya?ml\s*(.*?)\s*```", registry_text)
    if not match: raise _fail("CAMERA_IDENTITY_GRAPH_MISSING")
    parsed = _parse_yaml(match.group(1), code="CAMERA_IDENTITY_GRAPH_INVALID")
    required = {"scenes", "camera_anchors", "views", "media_assets"}
    if not required.issubset(parsed): raise _fail("CAMERA_IDENTITY_GRAPH_INVALID")
    for key in required:
        if not isinstance(parsed.get(key), Mapping): raise _fail("CAMERA_IDENTITY_GRAPH_INVALID", field=key)
    if "relations" in parsed and not isinstance(parsed.get("relations"), Mapping): raise _fail("CAMERA_IDENTITY_GRAPH_INVALID", field="relations")
    return parsed


def _verify_materialization(binding: Mapping[str, Any], *, main_sha: str) -> str:
    declared = _full_sha(binding.get("writeback_verified_commit"))
    commit = _REMOTE_API_JSON(f"/repos/{_REMOTE_REPOSITORY}/commits/{declared}")
    if not isinstance(commit, Mapping) or commit.get("sha") != declared: raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="commit_missing")
    compare = _REMOTE_API_JSON(f"/repos/{_REMOTE_REPOSITORY}/compare/{declared}...{main_sha}")
    merge_base = compare.get("merge_base_commit") if isinstance(compare, Mapping) else None
    status = str(compare.get("status") or "") if isinstance(compare, Mapping) else ""
    if not isinstance(merge_base, Mapping) or merge_base.get("sha") != declared or status not in {"ahead", "identical"}: raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="commit_not_canonical_ancestor")
    historical = _extract_binding_payload(_REMOTE_FILE_TEXT(CONTINUITY_PATH, declared))
    identity_keys = ("work_item_id", "shot_id", "scene_id", "camera_anchor_id", "view_id", "asset_id", "relation_id", "media_version_id", "binding_status", "provenance")
    target = {key: binding.get(key) for key in identity_keys}
    if not any({key: item.get(key) for key in identity_keys} == target for item in historical): raise _fail("CAMERA_BINDING_MATERIALIZATION_INVALID", reason="binding_not_present_at_declared_commit")
    return declared


def _select_binding(bindings: list[dict[str, Any]], *, active_work_item_id: str, shot_id: str | None) -> dict[str, Any] | None:
    matches = [item for item in bindings if str(item.get("work_item_id")) == active_work_item_id]
    if shot_id is not None: matches = [item for item in matches if str(item.get("shot_id")) == shot_id]
    if not matches: return None
    if len(matches) > 1: raise _fail("CAMERA_BINDING_AMBIGUOUS", work_item_id=active_work_item_id, shot_id=shot_id, count=len(matches))
    return matches[0]


def _active_record(graph: Mapping[str, Any], group: str, record_id: str, *, node: str) -> Mapping[str, Any]:
    records = graph.get(group); record = records.get(record_id) if isinstance(records, Mapping) else None
    if not isinstance(record, Mapping) or record.get("status") != "active": raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node=node, record_id=record_id)
    return record


def _resolve_media_version(resolver: Mapping[str, Any], binding: Mapping[str, Any], asset_id: str) -> str:
    assets = resolver.get("assets"); resolver_asset = assets.get(asset_id) if isinstance(assets, Mapping) else None
    if not isinstance(resolver_asset, Mapping): raise _fail("CAMERA_MEDIA_RESOLVER_INVALID", asset_id=asset_id)
    versions = resolver_asset.get("versions")
    if not isinstance(versions, list): raise _fail("CAMERA_MEDIA_RESOLVER_INVALID", asset_id=asset_id, reason="versions_missing")
    pinned = str(binding.get("media_version_id") or "").strip() or None
    selected = pinned or (str(resolver_asset.get("current_version_id") or "").strip() or None)
    if selected is None: raise _fail("CAMERA_MEDIA_RESOLVER_INVALID", asset_id=asset_id, reason="current_version_missing")
    version = next((item for item in versions if isinstance(item, Mapping) and item.get("version_id") == selected and item.get("asset_id") == asset_id), None)
    if not isinstance(version, Mapping):
        code = "CAMERA_MEDIA_VERSION_PIN_INVALID" if pinned else "CAMERA_MEDIA_RESOLVER_INVALID"; raise _fail(code, asset_id=asset_id, media_version_id=selected)
    if version.get("lifecycle_status") == "rejected": raise _fail("CAMERA_MEDIA_VERSION_PIN_INVALID", asset_id=asset_id, media_version_id=selected, reason="rejected")
    return selected


def _unbound_receipt(*, work_item_id: str, shot_id: str | None, main_sha: str) -> CameraAuthorityReceipt:
    return CameraAuthorityReceipt(status="CAMERA_AUTHORITY_UNBOUND", work_item_id=work_item_id, shot_id=shot_id, camera_authority_available=False, binding=None, scene=None, camera_anchor=None, view=None, media_asset=None, current_media_version_id=None, orientation=None, physical_position=None, lens=None, canonical_main_sha=main_sha)


def read_camera_authority(*, shot_id: str | None = None) -> CameraAuthorityReceipt:
    """Read camera authority for the current canonical active work item only."""
    _verify_remote_provenance()
    main_sha = _current_main_sha()
    _load_project_index(main_sha); _load_identity_schema(main_sha)
    continuity_text = _REMOTE_FILE_TEXT(CONTINUITY_PATH, main_sha)
    active_state = _REMOTE_EXTRACT_STATE(continuity_text)
    active_work_item = str(active_state.get("work_item_id") or "").strip()
    if not active_work_item: raise _fail("CAMERA_ACTIVE_WORK_ITEM_UNAVAILABLE")
    requested_shot = str(shot_id).strip() if shot_id is not None else None
    if shot_id is not None and not requested_shot: raise _fail("CAMERA_SHOT_SELECTOR_INVALID")
    binding = _select_binding(_extract_binding_payload(continuity_text), active_work_item_id=active_work_item, shot_id=requested_shot)
    if binding is None: return _unbound_receipt(work_item_id=active_work_item, shot_id=requested_shot, main_sha=main_sha)
    _verify_materialization(binding, main_sha=main_sha)
    graph = _identity_graph(_REMOTE_FILE_TEXT(ASSET_REGISTRY_PATH, main_sha))
    resolver = _parse_yaml(_REMOTE_FILE_TEXT(RESOLVER_PATH, main_sha), code="CAMERA_MEDIA_RESOLVER_INVALID")
    scene_id = str(binding["scene_id"]); camera_id = str(binding["camera_anchor_id"]); view_id = str(binding["view_id"]); asset_id = str(binding["asset_id"])
    scene = _active_record(graph, "scenes", scene_id, node="scene"); camera = _active_record(graph, "camera_anchors", camera_id, node="camera_anchor"); view = _active_record(graph, "views", view_id, node="view"); asset = _active_record(graph, "media_assets", asset_id, node="media_asset")
    if camera.get("scene_id") != scene_id: raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="camera_anchor_scene")
    if view.get("scene_id") != scene_id or view.get("camera_anchor_id") != camera_id: raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="view_scene_anchor")
    if asset.get("view_id") != view_id: raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="asset_view")
    relation_id = str(binding.get("relation_id") or "").strip() or None
    if relation_id:
        relation = _active_record(graph, "relations", relation_id, node="relation"); members = relation.get("member_view_ids")
        if not isinstance(members, list) or view_id not in {str(item) for item in members}: raise _fail("CAMERA_IDENTITY_CHAIN_INVALID", node="relation_view")
    selected_version = _resolve_media_version(resolver, binding, asset_id)
    view_class = str(view.get("view_class") or "")
    if view_class == "perspective":
        facing = view.get("facing_cardinal")
        if facing not in {"N", "S", "E", "W"}: raise _fail("CAMERA_ORIENTATION_METADATA_INVALID")
        orientation = {"view_class": view_class, "facing_cardinal": facing, "yaw_offset_deg": view.get("yaw_offset_deg"), "pitch_deg": view.get("pitch_deg"), "roll_deg": view.get("roll_deg")}
    elif view_class in {"top_orthographic", "top_oblique"}:
        screen_top = view.get("screen_top_cardinal")
        if screen_top not in {"N", "S", "E", "W"}: raise _fail("CAMERA_ORIENTATION_METADATA_INVALID")
        orientation = {"view_class": view_class, "screen_top_cardinal": screen_top, "projection": view.get("projection")}
    else: orientation = {"view_class": view_class, "direction_authority": "not_applicable"}
    physical_position = {"world_position_relation": camera.get("world_position_relation"), "map_xy_normalized": camera.get("map_xy_normalized"), "elevation_m": camera.get("elevation_m"), "camera_height_m": camera.get("camera_height_m"), "exact_transform": camera.get("exact_transform")}
    lens = {"focal_length_mm": view.get("focal_length_mm"), "lens_intent": view.get("lens_intent")}
    return CameraAuthorityReceipt(status="CAMERA_AUTHORITY_BOUND_VERIFIED", work_item_id=active_work_item, shot_id=str(binding["shot_id"]), camera_authority_available=True, binding=_freeze(binding), scene=_freeze(scene), camera_anchor=_freeze(camera), view=_freeze(view), media_asset=_freeze(asset), current_media_version_id=selected_version, orientation=_freeze(orientation), physical_position=_freeze(physical_position), lens=_freeze(lens), canonical_main_sha=main_sha)
