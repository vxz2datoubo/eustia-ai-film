"""Candidate WorkItem Context Materialization P0.

This module does not create story/world authority. It resolves the current work item
through the existing fixed-GitHub Active Work Item runtime, verifies the live source
revision, and compiles a bounded *projection candidate* from a reviewed profile.

The public function intentionally takes no arguments. Caller-selected project roots,
work-item ids, entities, semantic locks, provenance refs, or authority flags are not an
input surface. Until this candidate is independently accepted and separately integrated,
its output is explicitly non-authoritative and cannot satisfy an execution gate.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from .active_work_item import (
    ActiveWorkItemResolutionError,
    build_work_item_context_packet,
    revalidate_source_revision,
    resolve_work_item,
)


POLICY_PATH = Path("10_运行时/work_item_context_materialization_candidate.yaml")
_CURRENT_DESCRIPTION = "继续当前工作项"


class WorkItemMaterializationError(ValueError):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = dict(details or {})


def _fail(code: str, message: str, **details: Any) -> WorkItemMaterializationError:
    return WorkItemMaterializationError(code, message, details=details or None)


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _governed_project_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    required = (
        root / "PROJECT_INDEX.yaml",
        root / "10_运行时" / "active_work_item_resolution_gate.yaml",
        root / POLICY_PATH,
    )
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_GOVERNED_ROOT_INVALID",
            "candidate checkout is missing required materializer anchors",
            missing=missing,
        )
    return root


def _load_policy(root: Path) -> dict[str, Any]:
    raw = yaml.safe_load((root / POLICY_PATH).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "policy must be a mapping")
    policy = dict(raw)
    if policy.get("component_id") != "EUSTIA_WORK_ITEM_CONTEXT_MATERIALIZATION_P0":
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "component id mismatch")
    if policy.get("status") != "candidate":
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "P0 policy must remain candidate")
    boundary = policy.get("trust_boundary")
    if not isinstance(boundary, Mapping):
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "trust boundary missing")
    required_false = (
        "caller_project_root_supported",
        "caller_work_item_id_supported",
        "caller_entities_supported",
        "caller_lock_semantics_supported",
        "caller_source_refs_supported",
        "caller_authority_booleans_supported",
    )
    if any(boundary.get(key) is not False for key in required_false):
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "caller authority surface leaked")
    output = policy.get("output_contract")
    if not isinstance(output, Mapping) or output.get("serialized_output_is_authority") is not False:
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "serialized projection cannot be authority")
    return policy


def _require_provenance(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING",
            f"{field} requires non-empty provenance",
        )
    refs: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _fail(
                "WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING",
                f"{field} contains invalid provenance",
            )
        refs.append(item.strip())
    return refs


def _validate_profile(profile: Mapping[str, Any], *, work_item_id: str) -> None:
    required_locks = profile.get("required_locked_constraints")
    if not isinstance(required_locks, list) or not required_locks:
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "required LOCK set missing")
    if len(required_locks) != len(set(map(str, required_locks))):
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "duplicate required LOCK id")

    semantics = profile.get("locked_constraint_semantics")
    if not isinstance(semantics, Mapping) or set(map(str, semantics)) != set(map(str, required_locks)):
        raise _fail(
            "WORK_ITEM_MATERIALIZER_PROFILE_INVALID",
            "LOCK semantic profile must exactly cover the required LOCK set",
            work_item_id=work_item_id,
        )
    for lock_id, raw in semantics.items():
        if not isinstance(raw, Mapping):
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"semantic {lock_id} invalid")
        text = raw.get("text")
        provenance = raw.get("provenance")
        if not isinstance(text, str) or not text.strip():
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"semantic {lock_id} has no text")
        if not isinstance(provenance, str) or not provenance.strip():
            raise _fail("WORK_ITEM_MATERIALIZER_PROVENANCE_MISSING", f"semantic {lock_id} has no provenance")

    baseline = profile.get("world_state_baseline")
    if not isinstance(baseline, Mapping):
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "world baseline missing")
    entities = baseline.get("entities")
    invariants = baseline.get("invariants")
    if not isinstance(entities, Mapping) or not entities:
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "baseline entities missing")
    if not isinstance(invariants, list) or not invariants:
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "baseline invariants missing")
    for entity_id, raw in entities.items():
        if not isinstance(raw, Mapping):
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"entity {entity_id} invalid")
        if set(raw) != {"kind", "position", "state", "provenance"}:
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"entity {entity_id} field set invalid")
        for key in ("kind", "position", "state"):
            if not isinstance(raw.get(key), str) or not str(raw.get(key)).strip():
                raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"entity {entity_id}.{key} invalid")
        _require_provenance(raw.get("provenance"), field=f"baseline.entities.{entity_id}.provenance")
    for index, raw in enumerate(invariants):
        if not isinstance(raw, Mapping):
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"invariant[{index}] invalid")
        if not isinstance(raw.get("invariant_id"), str) or not str(raw.get("invariant_id")).strip():
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"invariant[{index}] id invalid")
        if not isinstance(raw.get("description"), str) or not str(raw.get("description")).strip():
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"invariant[{index}] description invalid")
        _require_provenance(raw.get("provenance"), field=f"baseline.invariants[{index}].provenance")

    baseline_ids = set(map(str, entities))
    for section in ("authorized_scope_entities", "authorized_explicit_entries"):
        entries = profile.get(section) or {}
        if not isinstance(entries, Mapping):
            raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"{section} invalid")
        overlap = baseline_ids.intersection(map(str, entries))
        if overlap:
            raise _fail(
                "WORK_ITEM_MATERIALIZER_PROFILE_INVALID",
                f"{section} may not duplicate baseline entities",
                overlap=sorted(overlap),
            )
        for entity_id, raw in entries.items():
            if not isinstance(raw, Mapping):
                raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", f"{section}.{entity_id} invalid")
            _require_provenance(raw.get("provenance"), field=f"{section}.{entity_id}.provenance")


def _compile_projection(
    context: Mapping[str, Any],
    profile: Mapping[str, Any],
    *,
    source_revision_revalidation: Mapping[str, Any],
    policy_digest: str,
) -> dict[str, Any]:
    work_item_id = str(context.get("work_item_id") or "").strip()
    if not work_item_id:
        raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "trusted context has no work item id")
    _validate_profile(profile, work_item_id=work_item_id)

    required_story_scope = str(profile.get("story_scope_ref_required") or "").strip()
    observed_story_scope = str(context.get("story_scope_ref") or "").strip()
    if not required_story_scope or observed_story_scope != required_story_scope:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_STORY_SCOPE_MISMATCH",
            "current story scope does not match the bounded profile",
            expected=required_story_scope or None,
            observed=observed_story_scope or None,
        )

    summary = str(context.get("effective_state_summary") or "").strip()
    missing_tokens = [
        str(token)
        for token in profile.get("required_summary_tokens") or []
        if str(token) not in summary
    ]
    if missing_tokens:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_SUMMARY_DRIFT",
            "current effective-state summary no longer satisfies the profile",
            missing_tokens=missing_tokens,
        )

    constraints = context.get("constraints")
    if not isinstance(constraints, Mapping):
        raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "trusted constraints missing")
    observed_locks = [str(item).strip() for item in constraints.get("locked") or [] if str(item).strip()]
    required_locks = [str(item).strip() for item in profile.get("required_locked_constraints") or []]
    if observed_locks != required_locks:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_LOCK_SET_MISMATCH",
            "canonical LOCK set/order drifted from the bounded profile",
            expected=required_locks,
            observed=observed_locks,
        )
    preserved = {str(item).strip() for item in constraints.get("preserved") or [] if str(item).strip()}
    required_preserved = {str(item).strip() for item in profile.get("required_preserved_constraints") or []}
    missing_preserved = sorted(required_preserved - preserved)
    if missing_preserved:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_PRESERVED_CONSTRAINT_MISSING",
            "required preserved constraints are no longer canonical",
            missing=missing_preserved,
        )

    verification_basis = str(context.get("verification_basis") or "").strip()
    if not verification_basis.startswith("canonical_github_readback_"):
        raise _fail(
            "WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED",
            "trusted context lacks fixed-GitHub verification basis",
            verification_basis=verification_basis or None,
        )
    if context.get("authority_boundary") != "coordination_projection_only":
        raise _fail("WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED", "unexpected WorkItemContext authority boundary")

    baseline_profile = profile["world_state_baseline"]
    baseline_entities: dict[str, dict[str, str]] = {}
    provenance_manifest: dict[str, Any] = {"baseline_entities": {}, "baseline_invariants": {}}
    for entity_id, raw in baseline_profile["entities"].items():
        baseline_entities[str(entity_id)] = {
            "kind": str(raw["kind"]),
            "position": str(raw["position"]),
            "state": str(raw["state"]),
        }
        provenance_manifest["baseline_entities"][str(entity_id)] = list(raw["provenance"])

    invariant_descriptions: list[str] = []
    for raw in baseline_profile["invariants"]:
        invariant_id = str(raw["invariant_id"])
        invariant_descriptions.append(str(raw["description"]))
        provenance_manifest["baseline_invariants"][invariant_id] = list(raw["provenance"])

    semantics_profile = profile["locked_constraint_semantics"]
    semantics = {
        lock_id: str(semantics_profile[lock_id]["text"]).strip()
        for lock_id in required_locks
    }
    provenance_manifest["locked_constraint_semantics"] = {
        lock_id: str(semantics_profile[lock_id]["provenance"]).strip()
        for lock_id in required_locks
    }

    source_payload = {
        "work_item_id": work_item_id,
        "story_scope_ref": observed_story_scope,
        "effective_state_summary": summary,
        "constraints": {
            "locked": observed_locks,
            "preserved": sorted(preserved),
            "revoked": list(constraints.get("revoked") or []),
            "experimental": list(constraints.get("experimental") or []),
            "unresolved": list(constraints.get("unresolved") or []),
        },
        "checkpoint_ref": context.get("checkpoint_ref"),
        "source_issue": context.get("source_issue"),
        "snapshot_fingerprint": context.get("snapshot_fingerprint"),
        "verification_basis": verification_basis,
    }
    source_digest = _stable_digest(source_payload)
    projection_payload = {
        "world_state_baseline": {
            "entities": baseline_entities,
            "invariants": invariant_descriptions,
        },
        "authorized_scope_entities": dict(profile.get("authorized_scope_entities") or {}),
        "authorized_explicit_entries": dict(profile.get("authorized_explicit_entries") or {}),
        "locked_constraint_semantics": semantics,
    }
    projection_digest = _stable_digest(projection_payload)

    return {
        "schema": "WORK_ITEM_MATERIALIZATION_CANDIDATE/v1",
        "status": "CANDIDATE_READY",
        "work_item_id": work_item_id,
        **projection_payload,
        "materialization_receipt": {
            "component_id": "EUSTIA_WORK_ITEM_CONTEXT_MATERIALIZATION_P0",
            "source_issue": context.get("source_issue"),
            "checkpoint_ref": context.get("checkpoint_ref"),
            "latest_source_checkpoint_ref": context.get("latest_source_checkpoint_ref"),
            "source_snapshot_fingerprint": context.get("snapshot_fingerprint"),
            "source_context_digest": source_digest,
            "profile_digest": policy_digest,
            "projection_digest": projection_digest,
            "source_revision_revalidation": dict(source_revision_revalidation),
            "projection_provenance": provenance_manifest,
            "fixed_github_context_verified": True,
            "projection_only": True,
            "serialized_output_is_authority": False,
            "fresh_materialization_required_before_consumption": True,
        },
        "execution_authorized": False,
        "canonical_write_authorized": False,
        "learning_writeback_authorized": False,
        "maturity_promotion_authorized": False,
    }


def materialize_current_work_item() -> dict[str, Any]:
    """Fresh-materialize the one current work item supported by P0.

    No caller input is accepted. Any attempt to pass a root, work-item id, profile,
    entities or semantics fails at the Python call surface with ``TypeError``.
    """
    root = _governed_project_root()
    policy = _load_policy(root)
    profiles = policy.get("profiles")
    if not isinstance(profiles, Mapping):
        raise _fail("WORK_ITEM_MATERIALIZER_PROFILE_INVALID", "profiles registry missing")

    try:
        resolution = resolve_work_item(_CURRENT_DESCRIPTION, project_root=root)
        context = build_work_item_context_packet(root, resolution)
        source_revision_revalidation = revalidate_source_revision(resolution)
    except ActiveWorkItemResolutionError as exc:
        raise _fail(
            "WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED",
            "canonical Active Work Item resolution failed",
            upstream_code=exc.code,
            upstream_details=exc.details,
        ) from exc

    work_item_id = str(context.get("work_item_id") or "").strip()
    profile = profiles.get(work_item_id)
    if not isinstance(profile, Mapping):
        raise _fail(
            "WORK_ITEM_MATERIALIZER_UNSUPPORTED_WORK_ITEM",
            "P0 has no reviewed materialization profile for the current work item",
            work_item_id=work_item_id or None,
        )
    return _compile_projection(
        context,
        profile,
        source_revision_revalidation=source_revision_revalidation,
        policy_digest=_stable_digest(policy),
    )


__all__ = [
    "WorkItemMaterializationError",
    "materialize_current_work_item",
]
