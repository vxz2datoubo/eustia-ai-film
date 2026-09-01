"""Trust-bound Active Work Item revision checkpoint compiler.

Public compilation accepts no caller continuity snapshot and no caller checkpoint
identity. It obtains the baseline from the canonical fixed-GitHub v3 trust root,
then applies a private deterministic revision reducer. Persistence remains
external.
"""
from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from . import _active_work_item_remote as _remote
from .active_work_item import ActiveWorkItemResolutionError, validate_state_transition
from .checkpoint_trust import (
    FixedCommitContinuity,
    TrustedCheckpointBaseline,
    fetch_fixed_continuity_at_commit,
    load_trusted_checkpoint_baseline,
    validate_live_checkpoint,
)

STATE_BEGIN = _remote.STATE_BEGIN
STATE_END = _remote.STATE_END
ALLOWED_EVENT_TYPES = {"ADD", "MODIFY", "REVOKE", "EXPERIMENT", "LOCK", "CHECKPOINT", "CLOSE"}
REQUIRED_EVENT_FIELDS = (
    "revision_id", "work_item_id", "event_type", "source_ref", "parent_revision",
    "changed", "preserved", "revoked", "experimental",
)
FORBIDDEN_EVENT_AUTHORITY_FIELDS = {
    "story_scope_ref", "status", "writeback_verified_commit", "checkpoint_writeback_status",
    "canonical_merge_status", "previous_work_item_id",
}


class CheckpointCompilationError(ActiveWorkItemResolutionError):
    pass


def _error(code: str, **details: Any) -> CheckpointCompilationError:
    return CheckpointCompilationError(code, details=details or None)


def _text(value: Any, field_name: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise _error("CHECKPOINT_EVENT_INVALID", field=field_name, reason="empty")
    return value


def _items(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        raise _error("CHECKPOINT_EVENT_INVALID", field=field_name, reason="must_be_sequence")
    result: list[str] = []
    for item in value:
        item = str(item).strip()
        if not item:
            raise _error("CHECKPOINT_EVENT_INVALID", field=field_name, reason="empty_item")
        if item not in result:
            result.append(item)
    return result


def _union(*groups: Iterable[str]) -> list[str]:
    out: list[str] = []
    for group in groups:
        for item in group:
            item = str(item).strip()
            if item and item not in out:
                out.append(item)
    return out


def _remove(values: Iterable[str], removed: set[str]) -> list[str]:
    return [item for item in values if item not in removed]


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _error("CHECKPOINT_EVENT_INVALID", reason="event_not_mapping")
    missing = [key for key in REQUIRED_EVENT_FIELDS if key not in raw]
    if missing:
        raise _error("CHECKPOINT_EVENT_INVALID", missing_fields=missing)
    forbidden = sorted(FORBIDDEN_EVENT_AUTHORITY_FIELDS.intersection(raw))
    if forbidden:
        raise _error("CHECKPOINT_EVENT_AUTHORITY_FIELD_FORBIDDEN", fields=forbidden)
    event_type = _text(raw.get("event_type"), "event_type").upper()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise _error("CHECKPOINT_EVENT_TYPE_INVALID", event_type=event_type)
    parent = raw.get("parent_revision")
    event = {
        "revision_id": _text(raw.get("revision_id"), "revision_id"),
        "work_item_id": _text(raw.get("work_item_id"), "work_item_id"),
        "event_type": event_type,
        "source_ref": _text(raw.get("source_ref"), "source_ref"),
        "parent_revision": None if parent in (None, "") else str(parent).strip(),
        "changed": _items(raw.get("changed"), "changed"),
        "preserved": _items(raw.get("preserved"), "preserved"),
        "revoked": _items(raw.get("revoked"), "revoked"),
        "experimental": _items(raw.get("experimental"), "experimental"),
    }
    for key in ("effective_state_summary", "next_expected_action", "current_best_ref"):
        if raw.get(key) is not None and str(raw.get(key)).strip():
            event[key] = str(raw[key]).strip()
    for key in ("bound_media_or_reference_refs", "unresolved_failures", "resolved_failures"):
        if key in raw:
            event[key] = _items(raw.get(key), key)
    return event


def _validate_event_chain(events: list[dict[str, Any]], work_item_id: str, expected_parent: str | None) -> None:
    if not events:
        raise _error("CHECKPOINT_EVENTS_EMPTY")
    previous, seen, terminal_seen = expected_parent, set(), False
    for index, event in enumerate(events):
        rid = event["revision_id"]
        if rid in seen:
            raise _error("CHECKPOINT_REVISION_DUPLICATE", revision_id=rid)
        seen.add(rid)
        if event["work_item_id"] != work_item_id:
            raise _error("CHECKPOINT_WORK_ITEM_MISMATCH", expected=work_item_id, observed=event["work_item_id"])
        observed_parent = event["parent_revision"]
        if index == 0:
            if expected_parent is None and observed_parent is not None:
                raise _error("CHECKPOINT_PARENT_BASELINE_UNKNOWN", revision_id=rid)
            if expected_parent is not None and observed_parent != expected_parent:
                raise _error("CHECKPOINT_PARENT_CHAIN_BROKEN", revision_id=rid)
        elif observed_parent != previous:
            raise _error("CHECKPOINT_PARENT_CHAIN_BROKEN", revision_id=rid)
        previous = rid
        if terminal_seen:
            raise _error("CHECKPOINT_EVENT_AFTER_TERMINAL", revision_id=rid)
        terminal_seen = event["event_type"] in {"CHECKPOINT", "CLOSE"}
    if events[-1]["event_type"] not in {"CHECKPOINT", "CLOSE"}:
        raise _error("CHECKPOINT_TERMINAL_EVENT_REQUIRED")


def _extract_block_parts(markdown: str) -> tuple[str, str, str]:
    start, end = markdown.find(STATE_BEGIN), markdown.find(STATE_END)
    if start < 0 or end <= start:
        raise _error("ACTIVE_WORK_ITEM_STATE_MISSING")
    end += len(STATE_END)
    return markdown[:start], markdown[start:end], markdown[end:]


def _parse_state(markdown: str) -> dict[str, Any]:
    _, block, _ = _extract_block_parts(markdown)
    payload = block[len(STATE_BEGIN):-len(STATE_END)].strip()
    for fence in ("```yaml", "```yml", "```"):
        if payload.startswith(fence):
            payload = payload[len(fence):].strip()
            break
    if payload.endswith("```"):
        payload = payload[:-3].strip()
    try:
        parsed = yaml.safe_load(payload) or {}
    except yaml.YAMLError as exc:
        raise _error("CHECKPOINT_STATE_INVALID") from exc
    state = parsed.get("active_work_item")
    if not isinstance(state, dict):
        raise _error("CHECKPOINT_STATE_INVALID")
    return copy.deepcopy(state)


def _render_state_block(state: dict[str, Any]) -> str:
    payload = yaml.safe_dump({"active_work_item": state}, allow_unicode=True, sort_keys=False).rstrip()
    return f"{STATE_BEGIN}\n```yaml\n{payload}\n```\n{STATE_END}"


def _fingerprint(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CheckpointProposal:
    work_item_id: str
    baseline_checkpoint_ref: str
    proposed_checkpoint_ref: str
    source_fingerprint: str
    proposed_state: dict[str, Any]
    replacement_block: str
    applied_revision_ids: tuple[str, ...]
    event_count: int
    canonical_baseline_sha: str | None = None
    source_issue: str | int | None = None
    trusted_snapshot_fingerprint: str | None = None
    status: str = "PENDING_WRITE"
    authority_boundary: str = "proposal_only_no_persistence_authority"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_PROPOSAL/v2",
            "status": self.status,
            "work_item_id": self.work_item_id,
            "baseline_checkpoint_ref": self.baseline_checkpoint_ref,
            "proposed_checkpoint_ref": self.proposed_checkpoint_ref,
            "canonical_baseline_sha": self.canonical_baseline_sha,
            "source_issue": self.source_issue,
            "trusted_snapshot_fingerprint": self.trusted_snapshot_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "proposed_state": copy.deepcopy(self.proposed_state),
            "replacement_block": self.replacement_block,
            "applied_revision_ids": list(self.applied_revision_ids),
            "event_count": self.event_count,
            "authority_boundary": self.authority_boundary,
            "persistence_verified": False,
        }


@dataclass(frozen=True)
class CheckpointWriteVerification:
    proposal: CheckpointProposal = field(repr=False)
    commit_sha: str = ""
    fetched_pending_markdown: str = field(default="", repr=False)
    post_write_fingerprint: str = ""
    status: str = "VERIFIED_FIXED_GITHUB_MATERIALIZATION"
    authority_boundary: str = "document_and_commit_existence_only_no_governed_ref_claim"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_WRITE_VERIFICATION/v2",
            "status": self.status,
            "work_item_id": self.proposal.work_item_id,
            "checkpoint_ref": self.proposal.proposed_checkpoint_ref,
            "verified_commit_sha": self.commit_sha,
            "post_write_fingerprint": self.post_write_fingerprint,
            "authority_boundary": self.authority_boundary,
            "runtime_confirms_governed_branch_or_ref": False,
        }


def _compile_checkpoint_core(
    continuity_markdown: str,
    events: Iterable[dict[str, Any]],
    *, expected_work_item_id: str, expected_baseline_checkpoint_ref: str,
    proposed_checkpoint_ref: str, expected_parent_revision: str | None = None,
) -> CheckpointProposal:
    """Private pure reducer. No authority is derived from these inputs."""
    baseline = _parse_state(continuity_markdown)
    work_item = str(expected_work_item_id or "").strip()
    baseline_ref = str(expected_baseline_checkpoint_ref or "").strip()
    if str(baseline.get("work_item_id") or "").strip() != work_item:
        raise _error("CHECKPOINT_WORK_ITEM_MISMATCH")
    if str(baseline.get("latest_applied_checkpoint_ref") or "").strip() != baseline_ref:
        raise _error("CHECKPOINT_BASELINE_STALE")
    checkpoint_ref = str(proposed_checkpoint_ref or "").strip()
    if not checkpoint_ref or checkpoint_ref == baseline_ref:
        raise _error("CHECKPOINT_REF_INVALID")
    normalized = [_normalize_event(item) for item in events]
    _validate_event_chain(normalized, work_item, expected_parent_revision)

    locked = _union(baseline.get("locked_constraints") or [])
    preserved = _union(baseline.get("preserved_constraints") or [])
    revoked = _union(baseline.get("revoked_constraints") or [])
    experimental = _union(baseline.get("experimental_constraints") or [])
    unresolved = _union(baseline.get("unresolved_failures") or [])
    media_refs = _union(baseline.get("bound_media_or_reference_refs") or [])
    state = copy.deepcopy(baseline)

    for event in normalized:
        etype, rid = event["event_type"], event["revision_id"]
        changed, keep, experiments = event["changed"], event["preserved"], event["experimental"]
        removed = set(event["revoked"])
        overlap = (set(changed) | set(keep) | set(experiments)).intersection(removed)
        if overlap:
            code = "CHECKPOINT_LOCK_CONFLICT" if etype == "LOCK" else "CHECKPOINT_EVENT_CONSTRAINT_CONFLICT"
            raise _error(code, revision_id=rid, constraints=sorted(overlap))
        if set(keep).intersection(revoked):
            raise _error("CHECKPOINT_PRESERVE_REVOKED_CONFLICT", revision_id=rid)
        reintroduced = set(changed).intersection(revoked)
        if reintroduced and etype in {"MODIFY", "CHECKPOINT", "CLOSE"}:
            raise _error("CHECKPOINT_REINTRODUCTION_REQUIRES_ADD_OR_LOCK", revision_id=rid)
        if reintroduced and etype in {"ADD", "LOCK"}:
            revoked = _remove(revoked, reintroduced)
        if etype == "REVOKE" and changed:
            raise _error("CHECKPOINT_REVOKE_AMBIGUOUS", revision_id=rid)
        if removed:
            lock_conflict = set(locked).intersection(removed)
            if lock_conflict and etype != "REVOKE":
                raise _error("CHECKPOINT_LOCK_CONFLICT", revision_id=rid)
            locked, preserved = _remove(locked, removed), _remove(preserved, removed)
            experimental, revoked = _remove(experimental, removed), _union(revoked, removed)

        if etype == "LOCK":
            locked = _union(locked, changed, keep)
            experimental = _union(experimental, experiments)
        elif etype == "EXPERIMENT":
            experimental = _union(experimental, changed, experiments)
            preserved = _union(preserved, keep)
        elif etype == "REVOKE":
            preserved = _union(preserved, keep)
        else:
            preserved = _union(preserved, keep, changed)
            experimental = _union(experimental, experiments)

        if "resolved_failures" in event:
            unresolved = _remove(unresolved, set(event["resolved_failures"]))
        if "unresolved_failures" in event:
            unresolved = _union(unresolved, event["unresolved_failures"])
        if "bound_media_or_reference_refs" in event:
            media_refs = _union(media_refs, event["bound_media_or_reference_refs"])
        for source, target in (("effective_state_summary", "current_effective_state_summary"), ("next_expected_action", "next_expected_action"), ("current_best_ref", "current_best_ref")):
            if event.get(source):
                state[target] = event[source]

    terminal = normalized[-1]
    state.update({
        "status": "CLOSED" if terminal["event_type"] == "CLOSE" else "CHECKPOINTED",
        "locked_constraints": locked, "preserved_constraints": preserved,
        "revoked_constraints": revoked, "experimental_constraints": experimental,
        "unresolved_failures": unresolved, "bound_media_or_reference_refs": media_refs,
        "latest_applied_checkpoint_ref": checkpoint_ref, "latest_evidence_ref": terminal["source_ref"],
        "checkpoint_writeback_status": "pending_write", "writeback_verified_commit": None,
        "canonical_merge_status": "pending_checkpoint_write",
    })
    return CheckpointProposal(
        work_item_id=work_item, baseline_checkpoint_ref=baseline_ref,
        proposed_checkpoint_ref=checkpoint_ref, source_fingerprint=_fingerprint(continuity_markdown),
        proposed_state=state, replacement_block=_render_state_block(state),
        applied_revision_ids=tuple(item["revision_id"] for item in normalized), event_count=len(normalized),
    )


def compile_checkpoint_proposal(
    project_root: str | Path, events: Iterable[dict[str, Any]], *,
    expected_work_item_id: str, expected_baseline_checkpoint_ref: str,
    expected_parent_revision: str | None = None,
) -> CheckpointProposal:
    raw = list(events)
    normalized = [_normalize_event(item) for item in raw]
    if not normalized:
        raise _error("CHECKPOINT_EVENTS_EMPTY")
    terminal = normalized[-1]
    if terminal["event_type"] not in {"CHECKPOINT", "CLOSE"}:
        raise _error("CHECKPOINT_TERMINAL_EVENT_REQUIRED")
    trusted: TrustedCheckpointBaseline = load_trusted_checkpoint_baseline(project_root)
    baseline = trusted.state
    work_item = str(expected_work_item_id or "").strip()
    baseline_ref = str(expected_baseline_checkpoint_ref or "").strip()
    if str(baseline.get("work_item_id") or "").strip() != work_item:
        raise _error("CHECKPOINT_WORK_ITEM_MISMATCH")
    if str(baseline.get("latest_applied_checkpoint_ref") or "").strip() != baseline_ref:
        raise _error("CHECKPOINT_BASELINE_STALE")
    target = "CLOSED" if terminal["event_type"] == "CLOSE" else "CHECKPOINTED"
    try:
        validate_state_transition(str(baseline.get("status") or ""), target)
    except ActiveWorkItemResolutionError as exc:
        raise _error("CHECKPOINT_LIFECYCLE_TRANSITION_INVALID", **exc.details) from exc
    checkpoint_ref = validate_live_checkpoint(baseline.get("source_issue"), terminal["source_ref"], require_latest=True)
    if checkpoint_ref == baseline_ref:
        raise _error("CHECKPOINT_REF_INVALID")
    core = _compile_checkpoint_core(
        trusted.continuity_markdown, raw, expected_work_item_id=work_item,
        expected_baseline_checkpoint_ref=baseline_ref, proposed_checkpoint_ref=checkpoint_ref,
        expected_parent_revision=expected_parent_revision,
    )
    return CheckpointProposal(**{
        **core.__dict__, "canonical_baseline_sha": trusted.canonical_sha,
        "source_issue": baseline.get("source_issue"),
        "trusted_snapshot_fingerprint": trusted.snapshot_fingerprint,
    })


def apply_proposal_to_document(continuity_markdown: str, proposal: CheckpointProposal) -> str:
    prefix, _, suffix = _extract_block_parts(continuity_markdown)
    if _fingerprint(continuity_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_SOURCE_CHANGED")
    return prefix + proposal.replacement_block + suffix


def _verify_fixed_materialization(proposal: CheckpointProposal, fetched: FixedCommitContinuity) -> CheckpointWriteVerification:
    if not proposal.canonical_baseline_sha or not proposal.trusted_snapshot_fingerprint:
        raise _error("CHECKPOINT_PROPOSAL_NOT_TRUST_BOUND")
    baseline = fetch_fixed_continuity_at_commit(proposal.canonical_baseline_sha)
    if _fingerprint(baseline.continuity_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_TRUSTED_BASELINE_CHANGED")
    before_prefix, _, before_suffix = _extract_block_parts(baseline.continuity_markdown)
    after_prefix, after_block, after_suffix = _extract_block_parts(fetched.continuity_markdown)
    if before_prefix != after_prefix or before_suffix != after_suffix:
        raise _error("CHECKPOINT_UNRELATED_CONTINUITY_MUTATION")
    if after_block != proposal.replacement_block or _parse_state(fetched.continuity_markdown) != proposal.proposed_state:
        raise _error("CHECKPOINT_POST_WRITE_MISMATCH")
    validate_live_checkpoint(proposal.source_issue, proposal.proposed_checkpoint_ref, require_latest=True)
    return CheckpointWriteVerification(
        proposal=proposal, commit_sha=fetched.commit_sha,
        fetched_pending_markdown=fetched.continuity_markdown,
        post_write_fingerprint=_fingerprint(fetched.continuity_markdown),
    )


def verify_post_write_document(
    project_root: str | Path, events: Iterable[dict[str, Any]], *,
    materialization_commit_sha: str, expected_work_item_id: str,
    expected_baseline_checkpoint_ref: str, expected_parent_revision: str | None = None,
) -> CheckpointWriteVerification:
    raw = list(events)
    proposal = compile_checkpoint_proposal(
        project_root, raw, expected_work_item_id=expected_work_item_id,
        expected_baseline_checkpoint_ref=expected_baseline_checkpoint_ref,
        expected_parent_revision=expected_parent_revision,
    )
    return _verify_fixed_materialization(proposal, fetch_fixed_continuity_at_commit(materialization_commit_sha))
