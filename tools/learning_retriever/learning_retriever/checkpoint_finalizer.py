"""Trust-bound second-phase checkpoint finalization.

The public finalizer accepts no serialized verification receipt and no
caller-supplied pending document. It re-executes checkpoint compilation from the
fixed-GitHub baseline, verifies the exact materialization commit in the fixed
repository, then emits only a second write proposal. Actual persistence and
governed-ref confirmation remain external.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .checkpoint_compiler import (
    CheckpointCompilationError,
    CheckpointWriteVerification,
    _extract_block_parts,
    _fingerprint,
    _parse_state,
    _render_state_block,
    verify_post_write_document,
)
from .checkpoint_trust import fetch_fixed_continuity_at_commit, validate_live_checkpoint


class CheckpointFinalizationError(CheckpointCompilationError):
    pass


def _error(code: str, **details: Any) -> CheckpointFinalizationError:
    return CheckpointFinalizationError(code, details=details or None)


@dataclass(frozen=True)
class CheckpointFinalizationProposal:
    work_item_id: str
    checkpoint_ref: str
    materialization_commit_sha: str
    source_fingerprint: str
    proposed_state: dict[str, Any]
    replacement_block: str
    source_issue: str | int | None
    status: str = "PENDING_FINALIZATION_WRITE"
    authority_boundary: str = "proposal_only_external_final_write_and_ref_confirmation_required"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_FINALIZATION_PROPOSAL/v2",
            "status": self.status,
            "work_item_id": self.work_item_id,
            "checkpoint_ref": self.checkpoint_ref,
            "materialization_commit_sha": self.materialization_commit_sha,
            "source_fingerprint": self.source_fingerprint,
            "proposed_state": copy.deepcopy(self.proposed_state),
            "replacement_block": self.replacement_block,
            "source_issue": self.source_issue,
            "authority_boundary": self.authority_boundary,
            "finalization_persistence_verified": False,
        }


def _from_materialization(verification: CheckpointWriteVerification) -> CheckpointFinalizationProposal:
    pending = verification.fetched_pending_markdown
    state = _parse_state(pending)
    proposal = verification.proposal
    if str(state.get("work_item_id") or "").strip() != proposal.work_item_id:
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="work_item_id")
    if str(state.get("latest_applied_checkpoint_ref") or "").strip() != proposal.proposed_checkpoint_ref:
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="latest_applied_checkpoint_ref")
    if str(state.get("checkpoint_writeback_status") or "").strip().casefold() != "pending_write":
        raise _error("CHECKPOINT_FINALIZATION_STATE_NOT_PENDING")
    if state.get("writeback_verified_commit") not in (None, ""):
        raise _error("CHECKPOINT_FINALIZATION_STATE_ALREADY_STAMPED")
    if str(state.get("canonical_merge_status") or "").strip() != "pending_checkpoint_write":
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="canonical_merge_status")

    validate_live_checkpoint(proposal.source_issue, proposal.proposed_checkpoint_ref, require_latest=True)
    final_state = copy.deepcopy(state)
    final_state["checkpoint_writeback_status"] = "verified"
    final_state["writeback_verified_commit"] = verification.commit_sha
    final_state["canonical_merge_status"] = "checkpoint_materialization_verified"
    return CheckpointFinalizationProposal(
        work_item_id=proposal.work_item_id,
        checkpoint_ref=proposal.proposed_checkpoint_ref,
        materialization_commit_sha=verification.commit_sha,
        source_fingerprint=_fingerprint(pending),
        proposed_state=final_state,
        replacement_block=_render_state_block(final_state),
        source_issue=proposal.source_issue,
    )


def compile_checkpoint_finalization_proposal(
    project_root: str | Path,
    events: Iterable[dict[str, Any]],
    *,
    materialization_commit_sha: str,
    expected_work_item_id: str,
    expected_baseline_checkpoint_ref: str,
    expected_parent_revision: str | None = None,
) -> CheckpointFinalizationProposal:
    """Public second-phase entry with mandatory fixed-GitHub materialization readback."""
    verification = verify_post_write_document(
        project_root,
        list(events),
        materialization_commit_sha=materialization_commit_sha,
        expected_work_item_id=expected_work_item_id,
        expected_baseline_checkpoint_ref=expected_baseline_checkpoint_ref,
        expected_parent_revision=expected_parent_revision,
    )
    return _from_materialization(verification)


def apply_finalization_to_document(
    fetched_pending_markdown: str,
    proposal: CheckpointFinalizationProposal,
) -> str:
    """Pure in-memory materialization helper; it grants no persistence authority."""
    if _fingerprint(fetched_pending_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_FINALIZATION_SOURCE_CHANGED")
    prefix, _, suffix = _extract_block_parts(fetched_pending_markdown)
    return prefix + proposal.replacement_block + suffix


def verify_finalization_document(
    project_root: str | Path,
    events: Iterable[dict[str, Any]],
    *,
    materialization_commit_sha: str,
    finalization_commit_sha: str,
    expected_work_item_id: str,
    expected_baseline_checkpoint_ref: str,
    expected_parent_revision: str | None = None,
) -> dict[str, Any]:
    """Verify the actual finalization commit in the fixed repository.

    This receipt still does not prove that the commit is on the governed target
    ref; external orchestration must confirm that before canonical reporting.
    """
    raw_events = list(events)
    verification = verify_post_write_document(
        project_root,
        raw_events,
        materialization_commit_sha=materialization_commit_sha,
        expected_work_item_id=expected_work_item_id,
        expected_baseline_checkpoint_ref=expected_baseline_checkpoint_ref,
        expected_parent_revision=expected_parent_revision,
    )
    proposal = _from_materialization(verification)
    fetched_final = fetch_fixed_continuity_at_commit(finalization_commit_sha)
    pending = verification.fetched_pending_markdown
    pending_prefix, _, pending_suffix = _extract_block_parts(pending)
    final_prefix, final_block, final_suffix = _extract_block_parts(fetched_final.continuity_markdown)
    if pending_prefix != final_prefix or pending_suffix != final_suffix:
        raise _error("CHECKPOINT_FINALIZATION_UNRELATED_MUTATION")
    if final_block != proposal.replacement_block:
        raise _error("CHECKPOINT_FINALIZATION_POST_WRITE_MISMATCH")
    if _parse_state(fetched_final.continuity_markdown) != proposal.proposed_state:
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="final_document")
    validate_live_checkpoint(proposal.source_issue, proposal.checkpoint_ref, require_latest=True)
    return {
        "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_FINALIZATION_VERIFICATION/v2",
        "status": "VERIFIED_FIXED_GITHUB_FINALIZATION_DOCUMENT",
        "work_item_id": proposal.work_item_id,
        "checkpoint_ref": proposal.checkpoint_ref,
        "materialization_commit_sha": proposal.materialization_commit_sha,
        "finalization_commit_sha": fetched_final.commit_sha,
        "final_fingerprint": _fingerprint(fetched_final.continuity_markdown),
        "runtime_confirms_governed_branch_or_ref": False,
        "canonical_reporting_requires_external_ref_confirmation": True,
    }
