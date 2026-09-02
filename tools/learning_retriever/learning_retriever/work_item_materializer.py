"""Read-only WorkItem structured-context materialization candidate.

Trusted structured world baseline and LOCK semantics can come only from a machine block
already materialized in canonical continuity. The block cannot self-attest semantics:
its source-context digest and every LOCK semantic are re-bound to fixed-GitHub evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from .active_work_item import (
    ActiveWorkItemResolutionError,
    build_work_item_context_packet,
    revalidate_source_revision,
    resolve_work_item,
)
from . import _active_work_item_remote as _remote

POLICY_PATH = Path("10_运行时/work_item_context_materialization_candidate.yaml")
CONTINUITY_PATH = Path("07_连续性与生产状态/连续性与当前生产状态.md")
BEGIN = "<!-- WORK_ITEM_STRUCTURED_CONTEXT_BEGIN -->"
END = "<!-- WORK_ITEM_STRUCTURED_CONTEXT_END -->"
_CURRENT_DESCRIPTION = "继续当前工作项"
_ALLOWED_ENTITY_KINDS = {"character", "object", "environment_anchor", "group"}

_RESOLVE_WORK_ITEM = resolve_work_item
_BUILD_CONTEXT = build_work_item_context_packet
_REVALIDATE_SOURCE = revalidate_source_revision
_REMOTE_MODULE = _remote
_REMOTE_API_JSON = _remote._github_api_json
_REMOTE_FILE_TEXT = _remote._github_file_text
_REMOTE_ISSUE_COMMENTS = _remote._github_issue_comments
_REMOTE_REPOSITORY = _remote.CANONICAL_REPOSITORY
_REMOTE_BRANCH = _remote.CANONICAL_BRANCH
_THIS_PACKAGE_DIR = Path(__file__).resolve().parent


def _source_fingerprint(obj: Any) -> tuple[Path, str]:
    module = sys.modules.get(getattr(obj, "__module__", ""))
    source = getattr(module, "__file__", None)
    if not source:
        raise RuntimeError("dependency source unavailable")
    path = Path(source).resolve()
    return path, sha256(path.read_bytes()).hexdigest()


_DEPENDENCY_SOURCES = {
    "resolve_work_item": _source_fingerprint(resolve_work_item),
    "build_work_item_context_packet": _source_fingerprint(build_work_item_context_packet),
    "revalidate_source_revision": _source_fingerprint(revalidate_source_revision),
    "remote": (Path(_remote.__file__).resolve(), sha256(Path(_remote.__file__).resolve().read_bytes()).hexdigest()),
}


class WorkItemMaterializationError(ValueError):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = dict(details or {})


def _fail(code: str, message: str, **details: Any) -> WorkItemMaterializationError:
    return WorkItemMaterializationError(code, message, details=details or None)


def _verify_runtime_provenance() -> None:
    if resolve_work_item is not _RESOLVE_WORK_ITEM:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "resolve_work_item binding changed")
    if build_work_item_context_packet is not _BUILD_CONTEXT:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "context builder binding changed")
    if revalidate_source_revision is not _REVALIDATE_SOURCE:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "source revalidation binding changed")
    if _remote is not _REMOTE_MODULE:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "remote module changed")
    if _remote._github_api_json is not _REMOTE_API_JSON or _remote._github_file_text is not _REMOTE_FILE_TEXT or _remote._github_issue_comments is not _REMOTE_ISSUE_COMMENTS:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "remote reader binding changed")
    if _remote.CANONICAL_REPOSITORY != _REMOTE_REPOSITORY or _remote.CANONICAL_BRANCH != _REMOTE_BRANCH:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "canonical repository binding changed")
    for name, obj in {
        "resolve_work_item": resolve_work_item,
        "build_work_item_context_packet": build_work_item_context_packet,
        "revalidate_source_revision": revalidate_source_revision,
    }.items():
        try:
            path, digest = _source_fingerprint(obj)
        except Exception as exc:
            raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", f"{name} source unavailable") from exc
        expected_path, expected_digest = _DEPENDENCY_SOURCES[name]
        if path != expected_path or path.parent != _THIS_PACKAGE_DIR or digest != expected_digest:
            raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", f"{name} source changed")
    remote_path = Path(_remote.__file__).resolve()
    expected_path, expected_digest = _DEPENDENCY_SOURCES["remote"]
    try:
        remote_digest = sha256(remote_path.read_bytes()).hexdigest()
    except Exception as exc:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "remote source unavailable") from exc
    if remote_path != expected_path or remote_path.parent != _THIS_PACKAGE_DIR or remote_digest != expected_digest:
        raise _fail("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", "remote source changed")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list): return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple): return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping): return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple): return [_thaw(item) for item in value]
    return value


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(_thaw(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _full_sha(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise _fail("WORK_ITEM_MATERIALIZER_CANONICAL_MAIN_INVALID", "main SHA is invalid")
    return text


def _current_main_sha() -> str:
    branch = _REMOTE_API_JSON(f"/repos/{_REMOTE_REPOSITORY}/branches/{_REMOTE_BRANCH}")
    commit = branch.get("commit") if isinstance(branch, Mapping) else None
    return _full_sha(commit.get("sha") if isinstance(commit, Mapping) else None)


def _governed_project_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    required = (root / "PROJECT_INDEX.yaml", root / "10_运行时" / "active_work_item_resolution_gate.yaml", root / POLICY_PATH)
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        raise _fail("WORK_ITEM_MATERIALIZER_GOVERNED_ROOT_INVALID", "candidate checkout is missing required code/config anchors", missing=missing)
    return root


def _load_policy(root: Path) -> dict[str, Any]:
    try: raw = yaml.safe_load((root / POLICY_PATH).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc: raise _fail("WORK_ITEM_MATERIALIZER_POLICY_INVALID", "policy YAML invalid") from exc
    if not isinstance(raw, Mapping): raise _fail("WORK_ITEM_MATERIALIZER_POLICY_INVALID", "policy must be a mapping")
    policy = dict(raw)
    if policy.get("component_id") != "EUSTIA_WORK_ITEM_CONTEXT_MATERIALIZATION_P0" or policy.get("status") != "candidate":
        raise _fail("WORK_ITEM_MATERIALIZER_POLICY_INVALID", "component/status mismatch")
    boundary = policy.get("trust_boundary")
    if not isinstance(boundary, Mapping): raise _fail("WORK_ITEM_MATERIALIZER_POLICY_INVALID", "trust boundary missing")
    forbidden = ("caller_project_root_supported", "caller_work_item_id_supported", "caller_structured_context_supported", "caller_entities_supported", "caller_lock_semantics_supported", "caller_authority_booleans_supported")
    if any(boundary.get(key) is not False for key in forbidden): raise _fail("WORK_ITEM_MATERIALIZER_POLICY_INVALID", "caller authority surface leaked")
    if boundary.get("static_proposal_can_satisfy_trusted_readback") is not False: raise _fail("WORK_ITEM_MATERIALIZER_POLICY_INVALID", "proposal laundering is enabled")
    return policy


def _parse_yaml(text: str, *, code: str) -> dict[str, Any]:
    try: raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc: raise _fail(code, "YAML parsing failed") from exc
    if not isinstance(raw, Mapping): raise _fail(code, "YAML root must be a mapping")
    return dict(raw)


def _extract_structured_block(continuity_text: str) -> dict[str, Any] | None:
    start, end = continuity_text.find(BEGIN), continuity_text.find(END)
    if start < 0 and end < 0: return None
    if start < 0 or end <= start or continuity_text.find(BEGIN, start + len(BEGIN)) >= 0:
        raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "structured context markers malformed")
    raw = continuity_text[start + len(BEGIN):end].strip()
    for fence in ("```yaml", "```yml", "```"):
        if raw.startswith(fence): raw = raw[len(fence):].strip(); break
    if raw.endswith("```"): raw = raw[:-3].strip()
    parsed = _parse_yaml(raw, code="WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID")
    block = parsed.get("work_item_structured_context")
    if not isinstance(block, Mapping): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "root key missing")
    return dict(block)


def _require_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", f"{field} must be non-empty text")
    return value.strip()


def _require_refs(value: Any, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value: raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", f"{field} requires provenance")
    return tuple(_require_text(item, field=f"{field}[]") for item in value)


def _validate_lock_source_bindings(*, bindings_raw: Any, semantics: Mapping[str, str], locked: list[str], source_issue: Any) -> dict[str, Any]:
    if not isinstance(bindings_raw, Mapping) or set(map(str, bindings_raw)) != set(locked):
        raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", "source binding coverage mismatch")
    try: issue_number = int(str(source_issue).strip())
    except (TypeError, ValueError) as exc: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", "source issue invalid") from exc
    try: comments = _REMOTE_ISSUE_COMMENTS(issue_number)
    except ActiveWorkItemResolutionError as exc: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", "fixed source issue unavailable", upstream_code=exc.code) from exc
    by_id = {int(item["id"]): item for item in comments if isinstance(item, Mapping) and isinstance(item.get("id"), int)}
    verified: dict[str, Any] = {}
    for lock_id in locked:
        record = bindings_raw.get(lock_id)
        if not isinstance(record, Mapping) or set(record) != {"source_issue", "comment_id", "source_body_sha256", "exact_text"}:
            raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} binding shape invalid")
        if str(record.get("source_issue")) != str(issue_number): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} source issue mismatch")
        try: comment_id = int(str(record.get("comment_id")).strip())
        except (TypeError, ValueError) as exc: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} comment id invalid") from exc
        comment = by_id.get(comment_id)
        body = comment.get("body") if isinstance(comment, Mapping) else None
        if not isinstance(body, str) or not body: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} source comment missing")
        observed_digest = sha256(body.encode("utf-8")).hexdigest()
        declared_digest = str(record.get("source_body_sha256") or "").strip().lower()
        if declared_digest != observed_digest: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} source body digest mismatch")
        exact_text = _require_text(record.get("exact_text"), field=f"source_semantic_bindings.{lock_id}.exact_text")
        if exact_text not in body: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} exact source text missing")
        if semantics.get(lock_id) != exact_text: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", f"{lock_id} semantic differs from source evidence")
        verified[lock_id] = {"source_issue": issue_number, "comment_id": comment_id, "source_body_sha256": observed_digest, "exact_text": exact_text}
    return verified


def _validate_block(block: Mapping[str, Any], *, context: Mapping[str, Any], context_digest: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any], dict[str, Any]]:
    allowed = {"work_item_id", "story_scope_ref", "source_checkpoint_ref", "source_context_digest", "materialization_status", "world_state_baseline", "authorized_explicit_entries", "locked_constraint_semantics", "source_semantic_bindings", "provenance"}
    unknown, missing = set(block) - allowed, allowed - set(block)
    if unknown or missing: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "structured context field set invalid", unknown=sorted(unknown), missing=sorted(missing))
    work_item_id = _require_text(block.get("work_item_id"), field="work_item_id")
    if work_item_id != str(context.get("work_item_id") or "").strip(): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_WORK_ITEM_MISMATCH", "structured context work item mismatch")
    if block.get("materialization_status") != "VERIFIED": raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_STATUS_INVALID", "materialization status is not VERIFIED")
    if _require_text(block.get("story_scope_ref"), field="story_scope_ref") != str(context.get("story_scope_ref") or "").strip(): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_STORY_SCOPE_MISMATCH", "story scope mismatch")
    expected_checkpoint = str(context.get("checkpoint_ref") or "").strip()
    if _require_text(block.get("source_checkpoint_ref"), field="source_checkpoint_ref") != expected_checkpoint: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_CHECKPOINT_MISMATCH", "structured context was not materialized for the current applied checkpoint", expected=expected_checkpoint or None)
    if _require_text(block.get("source_context_digest"), field="source_context_digest") != context_digest: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_SOURCE_CONTEXT_MISMATCH", "structured block is not bound to fresh WorkItemContext")

    baseline = block.get("world_state_baseline")
    if not isinstance(baseline, Mapping) or set(baseline) != {"entities", "invariants"}: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "world_state_baseline invalid")
    entities_raw, invariants_raw = baseline.get("entities"), baseline.get("invariants")
    if not isinstance(entities_raw, Mapping) or not entities_raw or not isinstance(invariants_raw, list): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "baseline invalid")
    entities: dict[str, dict[str, str]] = {}
    for entity_id, raw in entities_raw.items():
        entity_id = _require_text(str(entity_id), field="entity_id")
        if not isinstance(raw, Mapping) or set(raw) != {"kind", "position", "state"}: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", f"entity {entity_id} invalid")
        kind = _require_text(raw.get("kind"), field=f"entities.{entity_id}.kind")
        if kind not in _ALLOWED_ENTITY_KINDS: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", f"entity {entity_id} kind invalid")
        entities[entity_id] = {"kind": kind, "position": _require_text(raw.get("position"), field=f"entities.{entity_id}.position"), "state": _require_text(raw.get("state"), field=f"entities.{entity_id}.state")}
    invariants = [_require_text(item, field="world_state_baseline.invariants[]") for item in invariants_raw]
    if len(invariants) != len(set(invariants)): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "duplicate baseline invariant")

    entries_raw = block.get("authorized_explicit_entries")
    if not isinstance(entries_raw, Mapping): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", "authorized_explicit_entries invalid")
    entries: dict[str, Any] = {}
    for entity_id, raw in entries_raw.items():
        entity_id = _require_text(str(entity_id), field="authorized_explicit_entries id")
        if entity_id in entities or not isinstance(raw, Mapping): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", f"entry {entity_id} invalid")
        if set(raw) != {"kind", "entry_condition", "exact_entry_time_authorized", "exact_entry_position_authorized"}: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", f"entry {entity_id} field set invalid")
        kind = _require_text(raw.get("kind"), field=f"entry.{entity_id}.kind")
        if kind not in _ALLOWED_ENTITY_KINDS or raw.get("exact_entry_time_authorized") is not False or raw.get("exact_entry_position_authorized") is not False: raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_BLOCK_INVALID", f"entry {entity_id} over-authorized")
        entries[entity_id] = {"kind": kind, "entry_condition": _require_text(raw.get("entry_condition"), field=f"entry.{entity_id}.entry_condition"), "exact_entry_time_authorized": False, "exact_entry_position_authorized": False}

    constraints = context.get("constraints")
    if not isinstance(constraints, Mapping): raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "trusted constraint packet missing")
    locked = [_require_text(item, field="constraints.locked[]") for item in list(constraints.get("locked") or [])]
    semantics_raw = block.get("locked_constraint_semantics")
    if not isinstance(semantics_raw, Mapping) or set(map(str, semantics_raw)) != set(locked): raise _fail("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_COVERAGE_MISMATCH", "LOCK semantics must exactly cover canonical LOCK ids", expected=locked)
    semantics = {lock_id: _require_text(semantics_raw.get(lock_id), field=f"locked_constraint_semantics.{lock_id}") for lock_id in locked}
    source_bindings = _validate_lock_source_bindings(bindings_raw=block.get("source_semantic_bindings"), semantics=semantics, locked=locked, source_issue=context.get("source_issue"))

    provenance = block.get("provenance")
    if not isinstance(provenance, Mapping): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "provenance manifest missing")
    allowed_prov = {"world_state_entities", "world_state_invariants", "authorized_explicit_entries", "locked_constraint_semantics"}
    if set(provenance) != allowed_prov: raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "provenance field set invalid")
    entity_prov = provenance.get("world_state_entities")
    if not isinstance(entity_prov, Mapping) or set(map(str, entity_prov)) != set(entities): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "entity provenance coverage mismatch")
    for entity_id in entities: _require_refs(entity_prov.get(entity_id), field=f"provenance.world_state_entities.{entity_id}")
    inv_prov = provenance.get("world_state_invariants")
    if not isinstance(inv_prov, list) or len(inv_prov) != len(invariants): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "invariant provenance coverage mismatch")
    seen: set[str] = set()
    for item in inv_prov:
        if not isinstance(item, Mapping) or set(item) != {"invariant", "refs"}: raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "invariant provenance record invalid")
        invariant = _require_text(item.get("invariant"), field="provenance.world_state_invariants.invariant")
        if invariant not in invariants or invariant in seen: raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "invariant provenance mismatch")
        seen.add(invariant); _require_refs(item.get("refs"), field=f"provenance.world_state_invariants[{invariant}]")
    if seen != set(invariants): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "invariant provenance incomplete")
    entry_prov = provenance.get("authorized_explicit_entries")
    if not isinstance(entry_prov, Mapping) or set(map(str, entry_prov)) != set(entries): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "explicit-entry provenance coverage mismatch")
    for entity_id in entries: _require_refs(entry_prov.get(entity_id), field=f"provenance.authorized_explicit_entries.{entity_id}")
    lock_prov = provenance.get("locked_constraint_semantics")
    if not isinstance(lock_prov, Mapping) or set(map(str, lock_prov)) != set(locked): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", "LOCK provenance coverage mismatch")
    for lock_id in locked:
        refs = _require_refs(lock_prov.get(lock_id), field=f"provenance.locked_constraint_semantics.{lock_id}")
        comment_id = str(source_bindings[lock_id]["comment_id"])
        if not any(comment_id in ref for ref in refs): raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", f"LOCK provenance is not bound to verified comment {comment_id}")
    return ({"entities": entities, "invariants": invariants}, entries, semantics, _thaw(provenance), source_bindings)


@dataclass(frozen=True)
class WorkItemMaterializationReadback:
    status: str
    work_item_id: str
    trusted_materialization_available: bool
    world_state_baseline: Mapping[str, Any] | None
    authorized_explicit_entries: Mapping[str, Any]
    locked_constraint_semantics: Mapping[str, str]
    materialization_receipt: Mapping[str, Any]
    execution_authorized: bool = False
    canonical_write_authorized: bool = False
    learning_writeback_authorized: bool = False
    maturity_promotion_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"schema": "WORK_ITEM_STRUCTURED_CONTEXT_READBACK/v1", "status": self.status, "work_item_id": self.work_item_id, "trusted_materialization_available": self.trusted_materialization_available, "world_state_baseline": _thaw(self.world_state_baseline) if self.world_state_baseline is not None else None, "authorized_explicit_entries": _thaw(self.authorized_explicit_entries), "locked_constraint_semantics": _thaw(self.locked_constraint_semantics), "materialization_receipt": _thaw(self.materialization_receipt), "execution_authorized": False, "canonical_write_authorized": False, "learning_writeback_authorized": False, "maturity_promotion_authorized": False, "serialized_output_is_authority": False, "fresh_readback_required_before_consumption": True}


def materialize_current_work_item() -> WorkItemMaterializationReadback:
    _verify_runtime_provenance()
    root = _governed_project_root(); policy = _load_policy(root); policy_digest = _stable_digest(policy)
    try:
        resolution = _RESOLVE_WORK_ITEM(_CURRENT_DESCRIPTION, project_root=root)
        context = _BUILD_CONTEXT(root, resolution)
        source_revision_revalidation = _REVALIDATE_SOURCE(resolution)
    except ActiveWorkItemResolutionError as exc:
        raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "canonical Active Work Item resolution failed", upstream_code=exc.code, upstream_details=exc.details) from exc
    if source_revision_revalidation.get("status") != "PASS": raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "source revision revalidation did not pass")
    work_item_id = str(context.get("work_item_id") or "").strip()
    if not work_item_id or not str(context.get("verification_basis") or "").startswith("canonical_github_readback_") or context.get("authority_boundary") != "coordination_projection_only": raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "trusted context verification failed")
    context_digest = _stable_digest({"work_item_id": work_item_id, "story_scope_ref": context.get("story_scope_ref"), "effective_state_summary": context.get("effective_state_summary"), "constraints": context.get("constraints"), "checkpoint_ref": context.get("checkpoint_ref"), "source_issue": context.get("source_issue"), "snapshot_fingerprint": context.get("snapshot_fingerprint"), "verification_basis": context.get("verification_basis")})
    main_sha = _current_main_sha(); continuity_text = _REMOTE_FILE_TEXT(CONTINUITY_PATH, main_sha); block = _extract_structured_block(continuity_text)
    common_receipt = {"component_id": "EUSTIA_WORK_ITEM_CONTEXT_MATERIALIZATION_P0", "canonical_main_sha": main_sha, "source_issue": context.get("source_issue"), "checkpoint_ref": context.get("checkpoint_ref"), "latest_source_checkpoint_ref": context.get("latest_source_checkpoint_ref"), "source_snapshot_fingerprint": context.get("snapshot_fingerprint"), "source_context_digest": context_digest, "policy_digest": policy_digest, "source_revision_revalidation": dict(source_revision_revalidation), "fixed_github_context_verified": True, "runtime_dependency_provenance_verified": True, "static_proposal_used_as_authority": False, "serialized_output_is_authority": False, "fresh_readback_required_before_consumption": True}
    if block is None:
        return WorkItemMaterializationReadback(status="STRUCTURED_CONTEXT_UNAVAILABLE", work_item_id=work_item_id, trusted_materialization_available=False, world_state_baseline=None, authorized_explicit_entries=_freeze({}), locked_constraint_semantics=_freeze({}), materialization_receipt=_freeze({**common_receipt, "structured_block_present": False}))
    baseline, entries, semantics, provenance, source_bindings = _validate_block(block, context=context, context_digest=context_digest)
    receipt = {**common_receipt, "structured_block_present": True, "structured_block_digest": _stable_digest(block), "projection_digest": _stable_digest({"world_state_baseline": baseline, "authorized_explicit_entries": entries, "locked_constraint_semantics": semantics}), "provenance": provenance, "verified_source_semantic_bindings": source_bindings}
    return WorkItemMaterializationReadback(status="STRUCTURED_CONTEXT_READY", work_item_id=work_item_id, trusted_materialization_available=True, world_state_baseline=_freeze(baseline), authorized_explicit_entries=_freeze(entries), locked_constraint_semantics=_freeze(semantics), materialization_receipt=_freeze(receipt))


__all__ = ["WorkItemMaterializationError", "WorkItemMaterializationReadback", "materialize_current_work_item"]
