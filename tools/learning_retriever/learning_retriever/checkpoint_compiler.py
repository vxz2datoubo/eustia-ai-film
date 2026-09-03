"""Pure Active Work Item checkpoint proposal compiler.

The compiler has no persistence authority. It turns a verified current
ACTIVE_WORK_ITEM_STATE plus a structured revision trajectory into a deterministic
pending-write proposal. An external governed orchestrator remains responsible
for GitHub FETCH -> EDIT -> COMMIT -> FETCH VERIFY.
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
)


ALLOWED_EVENT_TYPES = {"ADD", "MODIFY", "REVOKE", "EXPERIMENT", "LOCK", "CHECKPOINT", "CLOSE"}
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
FORBIDDEN_EVENT_AUTHORITY_FIELDS = {
    "story_scope_ref",
    "status",
    "writeback_verified_commit",
    "checkpoint_writeback_status",
    "canonical_merge_status",
    "previous_work_item_id",
}
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


def _error(code: str, **details: Any) -> CheckpointCompilationError:
    return CheckpointCompilationError(code, details=details or None)


def _text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise _error("CHECKPOINT_EVENT_INVALID", field=field, reason="empty")
    return result


def _items(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        raise _error("CHECKPOINT_EVENT_INVALID", field=field, reason="must_be_sequence")
    result: list[str] = []
    for item in value:
        normalized = str(item).strip()
        if not normalized:
            raise _error("CHECKPOINT_EVENT_INVALID", field=field, reason="empty_item")
        if normalized not in result:
            result.append(normalized)
    return result


def _union(*groups: Iterable[str]) -> list[str]:
    result: list[str] = []
    for group in groups:
        for item in group:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
    return result


def _remove(values: Iterable[str], removed: set[str]) -> list[str]:
    return [value for value in values if value not in removed]


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _error("CHECKPOINT_EVENT_INVALID", reason="event_not_mapping")
    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in raw]
    if missing:
        raise _error("CHECKPOINT_EVENT_INVALID", missing_fields=missing)
    forbidden = sorted(FORBIDDEN_EVENT_AUTHORITY_FIELDS.intersection(raw))
    if forbidden:
        raise _error("CHECKPOINT_EVENT_AUTHORITY_FIELD_FORBIDDEN", fields=forbidden)

    event_type = _text(raw.get("event_type"), "event_type").upper()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise _error("CHECKPOINT_EVENT_TYPE_INVALID", event_type=event_type)
    parent_raw = raw.get("parent_revision")
    event = {
        "revision_id": _text(raw.get("revision_id"), "revision_id"),
        "work_item_id": _text(raw.get("work_item_id"), "work_item_id"),
        "event_type": event_type,
        "source_ref": _text(raw.get("source_ref"), "source_ref"),
        "parent_revision": None if parent_raw in (None, "") else str(parent_raw).strip(),
        "changed": _items(raw.get("changed"), "changed"),
        "preserved": _items(raw.get("preserved"), "preserved"),
        "revoked": _items(raw.get("revoked"), "revoked"),
        "experimental": _items(raw.get("experimental"), "experimental"),
    }
    for optional in ("effective_state_summary", "next_expected_action", "current_best_ref"):
        if optional in raw and raw[optional] is not None:
            value = str(raw[optional]).strip()
            if value:
                event[optional] = value
    for optional_list in (
        "bound_media_or_reference_refs",
        "unresolved_failures",
        "resolved_failures",
    ):
        if optional_list in raw:
            event[optional_list] = _items(raw.get(optional_list), optional_list)
    return event


def _validate_event_chain(
    events: list[dict[str, Any]],
    *,
    work_item_id: str,
    expected_parent_revision: str | None,
) -> None:
    if not events:
        raise _error("CHECKPOINT_EVENTS_EMPTY")
    seen_ids: set[str] = set()
    seen_identity: set[tuple[str, str]] = set()
    previous = expected_parent_revision
    terminal_seen = False

    for index, event in enumerate(events):
        revision_id = event["revision_id"]
        identity = (revision_id, event["source_ref"])
        if revision_id in seen_ids or identity in seen_identity:
            raise _error(
                "CHECKPOINT_REVISION_DUPLICATE",
                revision_id=revision_id,
                source_ref=event["source_ref"],
            )
        seen_ids.add(revision_id)
        seen_identity.add(identity)
        if event["work_item_id"] != work_item_id:
            raise _error(
                "CHECKPOINT_WORK_ITEM_MISMATCH",
                expected=work_item_id,
                observed=event["work_item_id"],
                revision_id=revision_id,
            )

        observed_parent = event["parent_revision"]
        if index == 0:
            if expected_parent_revision is None and observed_parent is not None:
                raise _error(
                    "CHECKPOINT_PARENT_BASELINE_UNKNOWN",
                    revision_id=revision_id,
                    observed_parent=observed_parent,
                )
            if expected_parent_revision is not None and observed_parent != expected_parent_revision:
                raise _error(
                    "CHECKPOINT_PARENT_CHAIN_BROKEN",
                    revision_id=revision_id,
                    expected_parent=expected_parent_revision,
                    observed_parent=observed_parent,
                )
        elif observed_parent != previous:
            raise _error(
                "CHECKPOINT_PARENT_CHAIN_BROKEN",
                revision_id=revision_id,
                expected_parent=previous,
                observed_parent=observed_parent,
            )
        previous = revision_id

        if terminal_seen:
            raise _error("CHECKPOINT_EVENT_AFTER_TERMINAL", revision_id=revision_id)
        if event["event_type"] in {"CHECKPOINT", "CLOSE"}:
            terminal_seen = True

    if events[-1]["event_type"] not in {"CHECKPOINT", "CLOSE"}:
        raise _error("CHECKPOINT_TERMINAL_EVENT_REQUIRED", last_event_type=events[-1]["event_type"])


def _extract_block_parts(markdown: str) -> tuple[str, str, str]:
    start = markdown.find(STATE_BEGIN)
    end = markdown.find(STATE_END)
    if start < 0 or end < 0 or end <= start:
        raise _error("ACTIVE_WORK_ITEM_STATE_MISSING")
    end_with_marker = end + len(STATE_END)
    return markdown[:start], markdown[start:end_with_marker], markdown[end_with_marker:]


def _parse_state(markdown: str) -> dict[str, Any]:
    _, block, _ = _extract_block_parts(markdown)
    payload = block[len(STATE_BEGIN): -len(STATE_END)].strip()
    for fence in ("```yaml", "```yml", "```"):
        if payload.startswith(fence):
            payload = payload[len(fence):].strip()
            break
    if payload.endswith("```"):
        payload = payload[:-3].strip()
    try:
        parsed = yaml.safe_load(payload) or {}
    except yaml.YAMLError as exc:
        raise _error("CHECKPOINT_BASELINE_STATE_INVALID", yaml_error=str(exc)) from exc
    state = parsed.get("active_work_item")
    if not isinstance(state, dict):
        raise _error("CHECKPOINT_BASELINE_STATE_INVALID")
    return copy.deepcopy(state)


def _render_state_block(state: dict[str, Any]) -> str:
    payload = yaml.safe_dump(
        {"active_work_item": state},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()
    return f"{STATE_BEGIN}\n```yaml\n{payload}\n```\n{STATE_END}"


def _fingerprint(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _validate_baseline(state: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_STATE_FIELDS if field not in state]
    if missing:
        raise _error("CHECKPOINT_BASELINE_STATE_INVALID", missing_fields=missing)
    if str(state.get("checkpoint_writeback_status") or "").strip().casefold() != "verified":
        raise _error(
            "CHECKPOINT_BASELINE_UNVERIFIED",
            checkpoint_writeback_status=state.get("checkpoint_writeback_status"),
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
    """Compile a deterministic pending-write snapshot without persisting it."""
    if not isinstance(continuity_markdown, str) or not continuity_markdown:
        raise _error("CHECKPOINT_CONTINUITY_INPUT_REQUIRED")
    baseline = _parse_state(continuity_markdown)
    _validate_baseline(baseline)

    work_item_id = str(expected_work_item_id or "").strip()
    observed_work_item = str(baseline.get("work_item_id") or "").strip()
    if not work_item_id or observed_work_item != work_item_id:
        raise _error("CHECKPOINT_WORK_ITEM_MISMATCH", expected=work_item_id or None, observed=observed_work_item or None)

    baseline_ref = str(expected_baseline_checkpoint_ref or "").strip()
    observed_ref = str(baseline.get("latest_applied_checkpoint_ref") or "").strip()
    if not baseline_ref or observed_ref != baseline_ref:
        raise _error("CHECKPOINT_BASELINE_STALE", expected=baseline_ref or None, observed=observed_ref or None)

    checkpoint_ref = str(proposed_checkpoint_ref or "").strip()
    if not checkpoint_ref or checkpoint_ref == baseline_ref:
        raise _error("CHECKPOINT_REF_INVALID", proposed_checkpoint_ref=checkpoint_ref or None)

    normalized = [_normalize_event(event) for event in events]
    _validate_event_chain(
        normalized,
        work_item_id=work_item_id,
        expected_parent_revision=expected_parent_revision,
    )

    locked = _union(baseline.get("locked_constraints") or [])
    preserved = _union(baseline.get("preserved_constraints") or [])
    revoked = _union(baseline.get("revoked_constraints") or [])
    experimental = _union(baseline.get("experimental_constraints") or [])
    unresolved = _union(baseline.get("unresolved_failures") or [])
    media_refs = _union(baseline.get("bound_media_or_reference_refs") or [])
    state = copy.deepcopy(baseline)

    for event in normalized:
        event_type = event["event_type"]
        changed = event["changed"]
        explicit_preserved = event["preserved"]
        explicit_revoked = set(event["revoked"])
        experiment_adds = event["experimental"]
        revision_id = event["revision_id"]

        same_event_adds = set(changed) | set(explicit_preserved) | set(experiment_adds)
        same_event_conflict = sorted(same_event_adds.intersection(explicit_revoked))
        if same_event_conflict:
            code = "CHECKPOINT_LOCK_CONFLICT" if event_type == "LOCK" else "CHECKPOINT_EVENT_CONSTRAINT_CONFLICT"
            raise _error(code, revision_id=revision_id, constraints=same_event_conflict)

        preserve_revoked = sorted(set(explicit_preserved).intersection(revoked))
        if preserve_revoked:
            raise _error(
                "CHECKPOINT_PRESERVE_REVOKED_CONFLICT",
                revision_id=revision_id,
                constraints=preserve_revoked,
            )

        changed_revoked = set(changed).intersection(revoked)
        if changed_revoked and event_type in {"MODIFY", "CHECKPOINT", "CLOSE"}:
            raise _error(
                "CHECKPOINT_REINTRODUCTION_REQUIRES_ADD_OR_LOCK",
                revision_id=revision_id,
                constraints=sorted(changed_revoked),
            )
        if changed_revoked and event_type in {"ADD", "LOCK"}:
            revoked = _remove(revoked, changed_revoked)

        if event_type == "LOCK":
            locked = _union(locked, changed, explicit_preserved)
            experimental = _union(experimental, experiment_adds)
        elif event_type == "EXPERIMENT":
            experimental = _union(experimental, changed, experiment_adds)
            preserved = _union(preserved, explicit_preserved)
        elif event_type == "REVOKE":
            if changed:
                raise _error("CHECKPOINT_REVOKE_AMBIGUOUS", revision_id=revision_id, changed=changed)
            preserved = _union(preserved, explicit_preserved)
        else:
            preserved = _union(preserved, explicit_preserved, changed)
            experimental = _union(experimental, experiment_adds)

        if explicit_revoked:
            locked_conflicts = sorted(set(locked).intersection(explicit_revoked))
            if locked_conflicts and event_type != "REVOKE":
                raise _error("CHECKPOINT_LOCK_CONFLICT", revision_id=revision_id, constraints=locked_conflicts)
            locked = _remove(locked, explicit_revoked)
            preserved = _remove(preserved, explicit_revoked)
            experimental = _remove(experimental, explicit_revoked)
            revoked = _union(revoked, explicit_revoked)

        if "resolved_failures" in event:
            unresolved = _remove(unresolved, set(event["resolved_failures"]))
        if "unresolved_failures" in event:
            unresolved = _union(unresolved, event["unresolved_failures"])
        if "bound_media_or_reference_refs" in event:
            media_refs = _union(media_refs, event["bound_media_or_reference_refs"])
        if event.get("effective_state_summary"):
            state["current_effective_state_summary"] = event["effective_state_summary"]
        if event.get("next_expected_action"):
            state["next_expected_action"] = event["next_expected_action"]
        if event.get("current_best_ref"):
            state["current_best_ref"] = event["current_best_ref"]

    terminal = normalized[-1]
    state["status"] = "CLOSED" if terminal["event_type"] == "CLOSE" else "CHECKPOINTED"
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

    return CheckpointProposal(
        work_item_id=work_item_id,
        baseline_checkpoint_ref=baseline_ref,
        proposed_checkpoint_ref=checkpoint_ref,
        source_fingerprint=_fingerprint(continuity_markdown),
        proposed_state=state,
        replacement_block=_render_state_block(state),
        applied_revision_ids=tuple(event["revision_id"] for event in normalized),
        event_count=len(normalized),
    )


def apply_proposal_to_document(continuity_markdown: str, proposal: CheckpointProposal) -> str:
    """Materialize the block in memory only; this function performs no write."""
    prefix, _, suffix = _extract_block_parts(continuity_markdown)
    if _fingerprint(continuity_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_SOURCE_CHANGED")
    return prefix + proposal.replacement_block + suffix


def verify_post_write_document(
    before_markdown: str,
    fetched_after_markdown: str,
    proposal: CheckpointProposal,
    *,
    verified_commit_sha: str,
) -> dict[str, Any]:
    """Verify externally fetched post-write content without claiming branch authority."""
    commit_sha = str(verified_commit_sha or "").strip().casefold()
    if not HEX40.fullmatch(commit_sha):
        raise _error("CHECKPOINT_VERIFIED_COMMIT_INVALID", verified_commit_sha=verified_commit_sha)
    if _fingerprint(before_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_SOURCE_CHANGED")

    before_prefix, _, before_suffix = _extract_block_parts(before_markdown)
    after_prefix, after_block, after_suffix = _extract_block_parts(fetched_after_markdown)
    if before_prefix != after_prefix or before_suffix != after_suffix:
        raise _error("CHECKPOINT_UNRELATED_CONTINUITY_MUTATION")
    if after_block != proposal.replacement_block:
        raise _error("CHECKPOINT_POST_WRITE_MISMATCH")
    if _parse_state(fetched_after_markdown) != proposal.proposed_state:
        raise _error("CHECKPOINT_POST_WRITE_STATE_MISMATCH")

    return {
        "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_WRITE_VERIFICATION/v1",
        "status": "VERIFIED_POST_WRITE_DOCUMENT",
        "work_item_id": proposal.work_item_id,
        "baseline_checkpoint_ref": proposal.baseline_checkpoint_ref,
        "checkpoint_ref": proposal.proposed_checkpoint_ref,
        "verified_commit_sha": commit_sha,
        "post_write_fingerprint": _fingerprint(fetched_after_markdown),
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
    root = Path(project_root)
    continuity = (root / CONTINUITY_PATH).read_text(encoding="utf-8")
    return compile_checkpoint_proposal(continuity, events, **kwargs)
