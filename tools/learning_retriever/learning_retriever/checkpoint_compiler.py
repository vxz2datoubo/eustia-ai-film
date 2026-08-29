"""Pure Active Work Item checkpoint proposal compiler.

This module deliberately has **no persistence authority**. It validates a
structured revision trajectory, computes the next ACTIVE_WORK_ITEM_STATE
snapshot, and renders a replacement block for an external governed orchestrator
to write through the canonical GitHub FETCH -> EDIT -> COMMIT -> FETCH VERIFY
transaction.

A checkpoint proposal is never proof that a canonical write happened. The only
verification helper in this module compares an actually fetched post-write
continuity document against the proposal and a concrete commit SHA supplied by
the orchestrator after the write.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .active_work_item import (
    ActiveWorkItemResolutionError,
    CONTINUITY_PATH,
    REQUIRED_STATE_FIELDS,
    STATE_BEGIN,
    STATE_END,
    load_active_work_item_state,
)


ALLOWED_EVENT_TYPES = {
    "ADD",
    "MODIFY",
    "REVOKE",
    "EXPERIMENT",
    "LOCK",
    "CHECKPOINT",
    "CLOSE",
}

REQUIRED_EVENT_FIELDS = (
    "revision_id",
    "work_item_id",
    "event_type",
    "source_ref",
    "parent_revision",
    "changed",
    "preserved",
    "revoked",
    "experimental",
)

HEX40 = re.compile(r"^[0-9a-f]{40}$")


class CheckpointCompilationError(ActiveWorkItemResolutionError):
    """Fail-closed checkpoint proposal error."""


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
    status: str = "PENDING_WRITE"
    authority_boundary: str = "proposal_only_no_persistence_authority"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_PROPOSAL/v1",
            "work_item_id": self.work_item_id,
            "baseline_checkpoint_ref": self.baseline_checkpoint_ref,
            "proposed_checkpoint_ref": self.proposed_checkpoint_ref,
            "source_fingerprint": self.source_fingerprint,
            "proposed_state": copy.deepcopy(self.proposed_state),
            "replacement_block": self.replacement_block,
            "applied_revision_ids": list(self.applied_revision_ids),
            "event_count": self.event_count,
            "status": self.status,
            "authority_boundary": self.authority_boundary,
            "persistence_verified": False,
        }


def _normalize_string(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise CheckpointCompilationError(
            "CHECKPOINT_EVENT_INVALID",
            details={"field": field, "reason": "empty"},
        )
    return text


def _normalize_string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        raise CheckpointCompilationError(
            "CHECKPOINT_EVENT_INVALID",
            details={"field": field, "reason": "must_be_sequence"},
        )
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise CheckpointCompilationError(
                "CHECKPOINT_EVENT_INVALID",
                details={"field": field, "reason": "empty_item"},
            )
        if text not in result:
            result.append(text)
    return result


def _ordered_union(*groups: Iterable[str]) -> list[str]:
    result: list[str] = []
    for group in groups:
        for item in group:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
    return result


def _without(values: Iterable[str], removed: set[str]) -> list[str]:
    return [value for value in values if value not in removed]


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CheckpointCompilationError(
            "CHECKPOINT_EVENT_INVALID",
            details={"reason": "event_not_mapping"},
        )
    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in raw]
    if missing:
        raise CheckpointCompilationError(
            "CHECKPOINT_EVENT_INVALID",
            details={"missing_fields": missing},
        )

    event_type = _normalize_string(raw.get("event_type"), field="event_type").upper()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise CheckpointCompilationError(
            "CHECKPOINT_EVENT_TYPE_INVALID",
            details={"event_type": event_type},
        )

    parent_raw = raw.get("parent_revision")
    parent_revision = None if parent_raw in (None, "") else str(parent_raw).strip()
    event = {
        "revision_id": _normalize_string(raw.get("revision_id"), field="revision_id"),
        "work_item_id": _normalize_string(raw.get("work_item_id"), field="work_item_id"),
        "event_type": event_type,
        "source_ref": _normalize_string(raw.get("source_ref"), field="source_ref"),
        "parent_revision": parent_revision,
        "changed": _normalize_string_list(raw.get("changed"), field="changed"),
        "preserved": _normalize_string_list(raw.get("preserved"), field="preserved"),
        "revoked": _normalize_string_list(raw.get("revoked"), field="revoked"),
        "experimental": _normalize_string_list(raw.get("experimental"), field="experimental"),
    }

    for optional in (
        "effective_state_summary",
        "story_scope_ref",
        "next_expected_action",
        "current_best_ref",
        "status",
    ):
        if optional in raw and raw[optional] is not None:
            event[optional] = str(raw[optional]).strip()
    if "bound_media_or_reference_refs" in raw:
        event["bound_media_or_reference_refs"] = _normalize_string_list(
            raw.get("bound_media_or_reference_refs"),
            field="bound_media_or_reference_refs",
        )
    if "unresolved_failures" in raw:
        event["unresolved_failures"] = _normalize_string_list(
            raw.get("unresolved_failures"),
            field="unresolved_failures",
        )
    if "resolved_failures" in raw:
        event["resolved_failures"] = _normalize_string_list(
            raw.get("resolved_failures"),
            field="resolved_failures",
        )
    return event


def _validate_event_chain(
    events: list[dict[str, Any]],
    *,
    work_item_id: str,
    expected_parent_revision: str | None,
) -> None:
    if not events:
        raise CheckpointCompilationError("CHECKPOINT_EVENTS_EMPTY")

    seen_ids: set[str] = set()
    seen_identity: set[tuple[str, str]] = set()
    previous = expected_parent_revision
    checkpoint_seen = False

    for index, event in enumerate(events):
        revision_id = event["revision_id"]
        identity = (revision_id, event["source_ref"])
        if revision_id in seen_ids or identity in seen_identity:
            raise CheckpointCompilationError(
                "CHECKPOINT_REVISION_DUPLICATE",
                details={"revision_id": revision_id, "source_ref": event["source_ref"]},
            )
        seen_ids.add(revision_id)
        seen_identity.add(identity)

        if event["work_item_id"] != work_item_id:
            raise CheckpointCompilationError(
                "CHECKPOINT_WORK_ITEM_MISMATCH",
                details={
                    "expected": work_item_id,
                    "observed": event["work_item_id"],
                    "revision_id": revision_id,
                },
            )

        observed_parent = event["parent_revision"]
        if index == 0:
            if expected_parent_revision and observed_parent != expected_parent_revision:
                raise CheckpointCompilationError(
                    "CHECKPOINT_PARENT_CHAIN_BROKEN",
                    details={
                        "revision_id": revision_id,
                        "expected_parent": expected_parent_revision,
                        "observed_parent": observed_parent,
                    },
                )
        elif observed_parent != previous:
            raise CheckpointCompilationError(
                "CHECKPOINT_PARENT_CHAIN_BROKEN",
                details={
                    "revision_id": revision_id,
                    "expected_parent": previous,
                    "observed_parent": observed_parent,
                },
            )
        previous = revision_id

        if checkpoint_seen:
            raise CheckpointCompilationError(
                "CHECKPOINT_EVENT_AFTER_TERMINAL",
                details={"revision_id": revision_id},
            )
        if event["event_type"] in {"CHECKPOINT", "CLOSE"}:
            checkpoint_seen = True

    if events[-1]["event_type"] not in {"CHECKPOINT", "CLOSE"}:
        raise CheckpointCompilationError(
            "CHECKPOINT_TERMINAL_EVENT_REQUIRED",
            details={"last_event_type": events[-1]["event_type"]},
        )


def _extract_block_parts(markdown: str) -> tuple[str, str, str]:
    start = markdown.find(STATE_BEGIN)
    end = markdown.find(STATE_END)
    if start < 0 or end < 0 or end <= start:
        raise CheckpointCompilationError("ACTIVE_WORK_ITEM_STATE_MISSING")
    block_end = end + len(STATE_END)
    return markdown[:start], markdown[start:block_end], markdown[block_end:]


def _render_state_block(state: dict[str, Any]) -> str:
    payload = yaml.safe_dump(
        {"active_work_item": state},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()
    return f"{STATE_BEGIN}\n```yaml\n{payload}\n```\n{STATE_END}"


def _state_fingerprint(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _validate_baseline_state(state: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_STATE_FIELDS if field not in state]
    if missing:
        raise CheckpointCompilationError(
            "CHECKPOINT_BASELINE_STATE_INVALID",
            details={"missing_fields": missing},
        )
    if str(state.get("checkpoint_writeback_status") or "").strip().casefold() != "verified":
        raise CheckpointCompilationError(
            "CHECKPOINT_BASELINE_UNVERIFIED",
            details={"checkpoint_writeback_status": state.get("checkpoint_writeback_status")},
        )


def compile_checkpoint_proposal(
    continuity_markdown: str,
    events: Iterable[dict[str, Any]],
    *,
    expected_work_item_id: str,
    expected_baseline_checkpoint_ref: str,
    proposed_checkpoint_ref: str,
    expected_parent_revision: str | None = None,
) -> CheckpointProposal:
    """Compile revision events into a pending-write snapshot proposal.

    The function is pure with respect to persistence. It never writes a file,
    calls GitHub, or marks the proposal as verified.
    """
    if not isinstance(continuity_markdown, str) or not continuity_markdown:
        raise CheckpointCompilationError("CHECKPOINT_CONTINUITY_INPUT_REQUIRED")

    # Reuse the canonical parser by writing no temporary data: parse the block
    # directly using the same YAML envelope semantics as active_work_item.py.
    prefix, _, suffix = _extract_block_parts(continuity_markdown)
    start = continuity_markdown.find(STATE_BEGIN)
    end = continuity_markdown.find(STATE_END)
    payload = continuity_markdown[start + len(STATE_BEGIN):end].strip()
    if payload.startswith("```yaml"):
        payload = payload[len("```yaml"):]
    elif payload.startswith("```yml"):
        payload = payload[len("```yml"):]
    elif payload.startswith("```"):
        payload = payload[len("```"):]
    payload = payload.strip()
    if payload.endswith("```"):
        payload = payload[:-3].strip()
    parsed = yaml.safe_load(payload) or {}
    baseline = copy.deepcopy(parsed.get("active_work_item") or {})
    if not isinstance(baseline, dict):
        raise CheckpointCompilationError("CHECKPOINT_BASELINE_STATE_INVALID")
    _validate_baseline_state(baseline)

    work_item_id = str(expected_work_item_id or "").strip()
    if not work_item_id or str(baseline.get("work_item_id") or "").strip() != work_item_id:
        raise CheckpointCompilationError(
            "CHECKPOINT_WORK_ITEM_MISMATCH",
            details={
                "expected": work_item_id or None,
                "observed": baseline.get("work_item_id"),
            },
        )

    baseline_ref = str(expected_baseline_checkpoint_ref or "").strip()
    observed_ref = str(baseline.get("latest_applied_checkpoint_ref") or "").strip()
    if not baseline_ref or observed_ref != baseline_ref:
        raise CheckpointCompilationError(
            "CHECKPOINT_BASELINE_STALE",
            details={"expected": baseline_ref or None, "observed": observed_ref or None},
        )

    checkpoint_ref = str(proposed_checkpoint_ref or "").strip()
    if not checkpoint_ref or checkpoint_ref == baseline_ref:
        raise CheckpointCompilationError(
            "CHECKPOINT_REF_INVALID",
            details={"proposed_checkpoint_ref": checkpoint_ref or None},
        )

    normalized = [_normalize_event(event) for event in events]
    _validate_event_chain(
        normalized,
        work_item_id=work_item_id,
        expected_parent_revision=expected_parent_revision,
    )

    locked = _ordered_union(baseline.get("locked_constraints") or [])
    preserved = _ordered_union(baseline.get("preserved_constraints") or [])
    revoked = _ordered_union(baseline.get("revoked_constraints") or [])
    experimental = _ordered_union(baseline.get("experimental_constraints") or [])
    unresolved = _ordered_union(baseline.get("unresolved_failures") or [])
    media_refs = _ordered_union(baseline.get("bound_media_or_reference_refs") or [])

    state = copy.deepcopy(baseline)
    for event in normalized:
        event_type = event["event_type"]
        changed = event["changed"]
        explicit_preserved = event["preserved"]
        explicit_revoked = set(event["revoked"])
        experiment_adds = event["experimental"]

        if event_type == "LOCK":
            lock_adds = _ordered_union(changed, explicit_preserved)
            conflict = sorted(set(lock_adds).intersection(explicit_revoked))
            if conflict:
                raise CheckpointCompilationError(
                    "CHECKPOINT_LOCK_CONFLICT",
                    details={"revision_id": event["revision_id"], "constraints": conflict},
                )
            locked = _ordered_union(locked, lock_adds)
        elif event_type == "EXPERIMENT":
            experimental = _ordered_union(experimental, changed, experiment_adds)
            preserved = _ordered_union(preserved, explicit_preserved)
        elif event_type == "REVOKE":
            if changed:
                raise CheckpointCompilationError(
                    "CHECKPOINT_REVOKE_AMBIGUOUS",
                    details={"revision_id": event["revision_id"], "changed": changed},
                )
            preserved = _ordered_union(preserved, explicit_preserved)
        else:
            preserved = _ordered_union(preserved, explicit_preserved, changed)
            experimental = _ordered_union(experimental, experiment_adds)

        if explicit_revoked:
            locked_conflicts = sorted(set(locked).intersection(explicit_revoked))
            if locked_conflicts and event_type != "REVOKE":
                raise CheckpointCompilationError(
                    "CHECKPOINT_LOCK_CONFLICT",
                    details={"revision_id": event["revision_id"], "constraints": locked_conflicts},
                )
            locked = _without(locked, explicit_revoked)
            preserved = _without(preserved, explicit_revoked)
            experimental = _without(experimental, explicit_revoked)
            revoked = _ordered_union(revoked, explicit_revoked)

        if "resolved_failures" in event:
            unresolved = _without(unresolved, set(event["resolved_failures"]))
        if "unresolved_failures" in event:
            unresolved = _ordered_union(unresolved, event["unresolved_failures"])
        if "bound_media_or_reference_refs" in event:
            media_refs = _ordered_union(media_refs, event["bound_media_or_reference_refs"])
        for key in (
            "effective_state_summary",
            "story_scope_ref",
            "next_expected_action",
            "current_best_ref",
        ):
            if event.get(key):
                target_key = (
                    "current_effective_state_summary"
                    if key == "effective_state_summary"
                    else key
                )
                state[target_key] = event[key]

    terminal = normalized[-1]
    if terminal["event_type"] == "CLOSE":
        state["status"] = "CLOSED"
    elif terminal.get("status"):
        state["status"] = terminal["status"]
    else:
        state["status"] = "CHECKPOINTED"

    state["locked_constraints"] = locked
    state["preserved_constraints"] = preserved
    state["revoked_constraints"] = revoked
    state["experimental_constraints"] = experimental
    state["unresolved_failures"] = unresolved
    state["bound_media_or_reference_refs"] = media_refs
    state["latest_applied_checkpoint_ref"] = checkpoint_ref
    state["latest_evidence_ref"] = terminal["source_ref"]
    state["checkpoint_writeback_status"] = "pending_write"
    state["writeback_verified_commit"] = None
    state["canonical_merge_status"] = "pending_checkpoint_write"

    replacement_block = _render_state_block(state)
    # prefix/suffix are intentionally not returned separately; they are used by
    # verification to ensure an orchestrator edits only this block.
    _ = prefix, suffix
    return CheckpointProposal(
        work_item_id=work_item_id,
        baseline_checkpoint_ref=baseline_ref,
        proposed_checkpoint_ref=checkpoint_ref,
        source_fingerprint=_state_fingerprint(continuity_markdown),
        proposed_state=state,
        replacement_block=replacement_block,
        applied_revision_ids=tuple(event["revision_id"] for event in normalized),
        event_count=len(normalized),
    )


def apply_proposal_to_document(
    continuity_markdown: str,
    proposal: CheckpointProposal,
) -> str:
    """Materialize the proposed block in memory only; this is not persistence."""
    prefix, _, suffix = _extract_block_parts(continuity_markdown)
    if _state_fingerprint(continuity_markdown) != proposal.source_fingerprint:
        raise CheckpointCompilationError("CHECKPOINT_SOURCE_CHANGED")
    return prefix + proposal.replacement_block + suffix


def verify_post_write_document(
    before_markdown: str,
    fetched_after_markdown: str,
    proposal: CheckpointProposal,
    *,
    verified_commit_sha: str,
) -> dict[str, Any]:
    """Verify an externally performed write from actual fetched post-write text.

    The caller cannot pass a boolean such as `write_succeeded=True`. Verification
    derives solely from document comparison plus a concrete commit identifier.
    This helper still does not fetch GitHub itself; provenance must state that the
    supplied `fetched_after_markdown` is the orchestrator's real post-commit read.
    """
    commit_sha = str(verified_commit_sha or "").strip().casefold()
    if not HEX40.fullmatch(commit_sha):
        raise CheckpointCompilationError(
            "CHECKPOINT_VERIFIED_COMMIT_INVALID",
            details={"verified_commit_sha": verified_commit_sha},
        )
    if _state_fingerprint(before_markdown) != proposal.source_fingerprint:
        raise CheckpointCompilationError("CHECKPOINT_SOURCE_CHANGED")

    before_prefix, _, before_suffix = _extract_block_parts(before_markdown)
    after_prefix, after_block, after_suffix = _extract_block_parts(fetched_after_markdown)
    if before_prefix != after_prefix or before_suffix != after_suffix:
        raise CheckpointCompilationError(
            "CHECKPOINT_UNRELATED_CONTINUITY_MUTATION",
        )
    if after_block != proposal.replacement_block:
        raise CheckpointCompilationError(
            "CHECKPOINT_POST_WRITE_MISMATCH",
        )

    payload = after_block[len(STATE_BEGIN): -len(STATE_END)].strip()
    if payload.startswith("```yaml"):
        payload = payload[len("```yaml"):]
    payload = payload.strip()
    if payload.endswith("```"):
        payload = payload[:-3].strip()
    parsed = yaml.safe_load(payload) or {}
    state = parsed.get("active_work_item") or {}
    if state != proposal.proposed_state:
        raise CheckpointCompilationError("CHECKPOINT_POST_WRITE_STATE_MISMATCH")

    return {
        "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_WRITE_VERIFICATION/v1",
        "status": "VERIFIED_POST_WRITE_DOCUMENT",
        "work_item_id": proposal.work_item_id,
        "baseline_checkpoint_ref": proposal.baseline_checkpoint_ref,
        "checkpoint_ref": proposal.proposed_checkpoint_ref,
        "verified_commit_sha": commit_sha,
        "post_write_fingerprint": _state_fingerprint(fetched_after_markdown),
        "outside_active_block_unchanged": True,
        "active_block_matches_proposal": True,
        "persistence_claim_boundary": "receipt_requires_external_fetch_evidence",
        "may_be_reported_as_canonical_only_if_orchestrator_confirms_commit_is_on_governed_target_branch": False,
    }


def compile_checkpoint_from_project(
    project_root: str | Path,
    events: Iterable[dict[str, Any]],
    **kwargs: Any,
) -> CheckpointProposal:
    """Filesystem convenience wrapper for an already checked-out project tree."""
    root = Path(project_root)
    continuity = (root / CONTINUITY_PATH).read_text(encoding="utf-8")
    return compile_checkpoint_proposal(continuity, events, **kwargs)
