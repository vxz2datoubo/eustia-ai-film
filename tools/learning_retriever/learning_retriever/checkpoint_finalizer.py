"""Second-phase Active Work Item checkpoint finalization proposals.

This module deliberately has no GitHub, git, network, branch, or ref authority.
It starts only after the first checkpoint materialization has been externally
written, fetched again, and verified by ``verify_post_write_document``.

The finalizer turns that verified pending snapshot into a second *proposal* that
records the verified materialization commit inside ACTIVE_WORK_ITEM_STATE. An
external governed orchestrator must still perform the final write, fetch it
again, verify the resulting document, and independently confirm the target ref.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .checkpoint_compiler import (
    HEX40,
    STATE_BEGIN,
    STATE_END,
    _extract_block_parts,
    _fingerprint,
    _parse_state,
    _render_state_block,
    CheckpointCompilationError,
)


class CheckpointFinalizationError(CheckpointCompilationError):
    """Fail-closed error for the second-phase checkpoint proposal."""


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
    status: str = "PENDING_FINALIZATION_WRITE"
    authority_boundary: str = "proposal_only_external_final_write_required"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_FINALIZATION_PROPOSAL/v1",
            "status": self.status,
            "work_item_id": self.work_item_id,
            "checkpoint_ref": self.checkpoint_ref,
            "materialization_commit_sha": self.materialization_commit_sha,
            "source_fingerprint": self.source_fingerprint,
            "proposed_state": copy.deepcopy(self.proposed_state),
            "replacement_block": self.replacement_block,
            "authority_boundary": self.authority_boundary,
            "finalization_persistence_verified": False,
        }


def compile_checkpoint_finalization_proposal(
    fetched_pending_markdown: str,
    materialization_verification_receipt: dict[str, Any],
    *,
    expected_work_item_id: str,
    expected_checkpoint_ref: str,
    expected_materialization_commit_sha: str,
) -> CheckpointFinalizationProposal:
    """Compile a verified pending checkpoint into a second pending proposal.

    The verification receipt must come from ``verify_post_write_document`` and
    must match the exact fetched pending document. This function cannot prove
    that the materialization commit is on a governed branch, and it cannot write
    the finalization proposal anywhere.
    """
    if not isinstance(fetched_pending_markdown, str) or not fetched_pending_markdown:
        raise _error("CHECKPOINT_FINALIZATION_DOCUMENT_REQUIRED")
    if not isinstance(materialization_verification_receipt, dict):
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_INVALID")

    receipt = materialization_verification_receipt
    if receipt.get("schema") != "ACTIVE_WORK_ITEM_CHECKPOINT_WRITE_VERIFICATION/v1":
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_INVALID", reason="schema")
    if receipt.get("status") != "VERIFIED_POST_WRITE_DOCUMENT":
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_INVALID", reason="status")
    if receipt.get("outside_active_block_unchanged") is not True:
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_INVALID", reason="outside_block")
    if receipt.get("active_block_matches_proposal") is not True:
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_INVALID", reason="active_block")

    materialization_sha = str(expected_materialization_commit_sha or "").strip().casefold()
    if not HEX40.fullmatch(materialization_sha):
        raise _error(
            "CHECKPOINT_FINALIZATION_MATERIALIZATION_COMMIT_INVALID",
            materialization_commit_sha=expected_materialization_commit_sha,
        )
    if str(receipt.get("verified_commit_sha") or "").strip().casefold() != materialization_sha:
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_MISMATCH", field="verified_commit_sha")

    pending_fingerprint = _fingerprint(fetched_pending_markdown)
    if receipt.get("post_write_fingerprint") != pending_fingerprint:
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_MISMATCH", field="post_write_fingerprint")

    work_item_id = str(expected_work_item_id or "").strip()
    checkpoint_ref = str(expected_checkpoint_ref or "").strip()
    if not work_item_id or not checkpoint_ref:
        raise _error("CHECKPOINT_FINALIZATION_EXPECTATION_REQUIRED")
    if str(receipt.get("work_item_id") or "").strip() != work_item_id:
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_MISMATCH", field="work_item_id")
    if str(receipt.get("checkpoint_ref") or "").strip() != checkpoint_ref:
        raise _error("CHECKPOINT_FINALIZATION_RECEIPT_MISMATCH", field="checkpoint_ref")

    state = _parse_state(fetched_pending_markdown)
    if str(state.get("work_item_id") or "").strip() != work_item_id:
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="work_item_id")
    if str(state.get("latest_applied_checkpoint_ref") or "").strip() != checkpoint_ref:
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="latest_applied_checkpoint_ref")
    if str(state.get("checkpoint_writeback_status") or "").strip().casefold() != "pending_write":
        raise _error(
            "CHECKPOINT_FINALIZATION_STATE_NOT_PENDING",
            checkpoint_writeback_status=state.get("checkpoint_writeback_status"),
        )
    if state.get("writeback_verified_commit") not in (None, ""):
        raise _error("CHECKPOINT_FINALIZATION_STATE_ALREADY_STAMPED")
    if str(state.get("canonical_merge_status") or "").strip() != "pending_checkpoint_write":
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="canonical_merge_status")

    final_state = copy.deepcopy(state)
    final_state["checkpoint_writeback_status"] = "verified"
    final_state["writeback_verified_commit"] = materialization_sha
    final_state["canonical_merge_status"] = "checkpoint_materialization_verified"

    return CheckpointFinalizationProposal(
        work_item_id=work_item_id,
        checkpoint_ref=checkpoint_ref,
        materialization_commit_sha=materialization_sha,
        source_fingerprint=pending_fingerprint,
        proposed_state=final_state,
        replacement_block=_render_state_block(final_state),
    )


def apply_finalization_to_document(
    fetched_pending_markdown: str,
    proposal: CheckpointFinalizationProposal,
) -> str:
    """Materialize the finalization block in memory only."""
    if _fingerprint(fetched_pending_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_FINALIZATION_SOURCE_CHANGED")
    prefix, _, suffix = _extract_block_parts(fetched_pending_markdown)
    return prefix + proposal.replacement_block + suffix


def verify_finalization_document(
    fetched_pending_markdown: str,
    fetched_final_markdown: str,
    proposal: CheckpointFinalizationProposal,
    *,
    finalization_commit_sha: str,
) -> dict[str, Any]:
    """Verify the externally written second-phase document.

    The returned receipt proves document equivalence only. A separate external
    ref/branch check is still required before reporting the checkpoint as
    canonical.
    """
    final_sha = str(finalization_commit_sha or "").strip().casefold()
    if not HEX40.fullmatch(final_sha):
        raise _error(
            "CHECKPOINT_FINALIZATION_COMMIT_INVALID",
            finalization_commit_sha=finalization_commit_sha,
        )
    if _fingerprint(fetched_pending_markdown) != proposal.source_fingerprint:
        raise _error("CHECKPOINT_FINALIZATION_SOURCE_CHANGED")

    pending_prefix, _, pending_suffix = _extract_block_parts(fetched_pending_markdown)
    final_prefix, final_block, final_suffix = _extract_block_parts(fetched_final_markdown)
    if pending_prefix != final_prefix or pending_suffix != final_suffix:
        raise _error("CHECKPOINT_FINALIZATION_UNRELATED_MUTATION")
    if final_block != proposal.replacement_block:
        raise _error("CHECKPOINT_FINALIZATION_POST_WRITE_MISMATCH")
    if _parse_state(fetched_final_markdown) != proposal.proposed_state:
        raise _error("CHECKPOINT_FINALIZATION_STATE_MISMATCH", field="final_document")

    return {
        "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_FINALIZATION_VERIFICATION/v1",
        "status": "VERIFIED_FINALIZATION_DOCUMENT",
        "work_item_id": proposal.work_item_id,
        "checkpoint_ref": proposal.checkpoint_ref,
        "materialization_commit_sha": proposal.materialization_commit_sha,
        "finalization_commit_sha": final_sha,
        "final_fingerprint": _fingerprint(fetched_final_markdown),
        "outside_active_block_unchanged": True,
        "active_block_matches_finalization_proposal": True,
        "runtime_confirms_governed_branch_or_ref": False,
        "canonical_reporting_requires_external_ref_confirmation": True,
    }
