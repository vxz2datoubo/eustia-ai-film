import ast
from pathlib import Path

import pytest

from learning_retriever.checkpoint_compiler import STATE_BEGIN, STATE_END, _fingerprint, _render_state_block
from learning_retriever.checkpoint_finalizer import (
    CheckpointFinalizationError,
    apply_finalization_to_document,
    compile_checkpoint_finalization_proposal,
    verify_finalization_document,
)


WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
CHECKPOINT = "5454999999"
MATERIALIZATION_SHA = "1" * 40
FINALIZATION_SHA = "2" * 40


def pending_state():
    return {
        "work_item_id": WORK_ITEM,
        "status": "CHECKPOINTED",
        "source_issue": 19,
        "baseline_checkpoint_ref": "5454103847",
        "latest_applied_checkpoint_ref": CHECKPOINT,
        "latest_evidence_ref": "issue19-comment-5454999999",
        "story_scope_ref": "03_剧本与改编/当前改编剧本.md#凯姆高位搜索之后的屋顶横向移动/当前制作扩展",
        "current_effective_state_summary": "凯姆继续围巾晾衣绳横移修订",
        "locked_constraints": ["scarf_clothesline_geometry"],
        "preserved_constraints": ["mass_laundry_collision"],
        "revoked_constraints": ["over_specified_setup_micro_choreography"],
        "experimental_constraints": ["clean_white_model_motion_geometry_reference"],
        "unresolved_failures": ["launch_momentum_naturalness"],
        "bound_media_or_reference_refs": ["issue19_actual_motion_reference"],
        "current_best_ref": "issue19-comment-5454999999",
        "previous_work_item_id": "KAIM-HIGH-SEARCH-30S",
        "next_expected_action": "continue_targeted_validation",
        "checkpoint_writeback_status": "pending_write",
        "writeback_verified_commit": None,
        "canonical_merge_status": "pending_checkpoint_write",
    }


def document(state=None, *, prefix="# continuity\n\n", suffix="\n\n# history\nkeep me\n"):
    state = pending_state() if state is None else state
    return prefix + _render_state_block(state) + suffix


def receipt(markdown, *, sha=MATERIALIZATION_SHA):
    return {
        "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_WRITE_VERIFICATION/v1",
        "status": "VERIFIED_POST_WRITE_DOCUMENT",
        "work_item_id": WORK_ITEM,
        "baseline_checkpoint_ref": "5454103847",
        "checkpoint_ref": CHECKPOINT,
        "verified_commit_sha": sha,
        "post_write_fingerprint": _fingerprint(markdown),
        "outside_active_block_unchanged": True,
        "active_block_matches_proposal": True,
        "persistence_claim_boundary": "receipt_requires_external_fetch_evidence",
        "may_be_reported_as_canonical_only_if_orchestrator_confirms_commit_is_on_governed_target_branch": False,
    }


def compile_ok(markdown=None):
    markdown = document() if markdown is None else markdown
    return compile_checkpoint_finalization_proposal(
        markdown,
        receipt(markdown),
        expected_work_item_id=WORK_ITEM,
        expected_checkpoint_ref=CHECKPOINT,
        expected_materialization_commit_sha=MATERIALIZATION_SHA,
    )


def test_compile_finalization_records_verified_materialization_without_claiming_final_write():
    markdown = document()
    proposal = compile_ok(markdown)
    assert proposal.status == "PENDING_FINALIZATION_WRITE"
    assert proposal.proposed_state["checkpoint_writeback_status"] == "verified"
    assert proposal.proposed_state["writeback_verified_commit"] == MATERIALIZATION_SHA
    assert proposal.proposed_state["canonical_merge_status"] == "checkpoint_materialization_verified"
    assert proposal.as_dict()["finalization_persistence_verified"] is False


def test_apply_and_verify_second_phase_preserve_everything_outside_active_block():
    pending = document(prefix="# exact-prefix\n", suffix="\n# exact-suffix\n")
    proposal = compile_ok(pending)
    final_doc = apply_finalization_to_document(pending, proposal)
    result = verify_finalization_document(
        pending,
        final_doc,
        proposal,
        finalization_commit_sha=FINALIZATION_SHA,
    )
    assert result["status"] == "VERIFIED_FINALIZATION_DOCUMENT"
    assert result["materialization_commit_sha"] == MATERIALIZATION_SHA
    assert result["finalization_commit_sha"] == FINALIZATION_SHA
    assert result["runtime_confirms_governed_branch_or_ref"] is False
    assert result["canonical_reporting_requires_external_ref_confirmation"] is True


def test_receipt_must_match_exact_pending_document_fingerprint():
    pending = document()
    bad = receipt(pending)
    bad["post_write_fingerprint"] = "0" * 64
    with pytest.raises(CheckpointFinalizationError, match="CHECKPOINT_FINALIZATION_RECEIPT_MISMATCH"):
        compile_checkpoint_finalization_proposal(
            pending,
            bad,
            expected_work_item_id=WORK_ITEM,
            expected_checkpoint_ref=CHECKPOINT,
            expected_materialization_commit_sha=MATERIALIZATION_SHA,
        )


def test_caller_cannot_finalize_unverified_or_already_stamped_state():
    state = pending_state()
    state["checkpoint_writeback_status"] = "verified"
    state["writeback_verified_commit"] = MATERIALIZATION_SHA
    pending = document(state)
    with pytest.raises(CheckpointFinalizationError, match="CHECKPOINT_FINALIZATION_STATE_NOT_PENDING"):
        compile_checkpoint_finalization_proposal(
            pending,
            receipt(pending),
            expected_work_item_id=WORK_ITEM,
            expected_checkpoint_ref=CHECKPOINT,
            expected_materialization_commit_sha=MATERIALIZATION_SHA,
        )


def test_materialization_receipt_cannot_swap_work_item_checkpoint_or_commit():
    pending = document()
    for field, value in (
        ("work_item_id", "OTHER-WORK"),
        ("checkpoint_ref", "OTHER-CHECKPOINT"),
        ("verified_commit_sha", "3" * 40),
    ):
        bad = receipt(pending)
        bad[field] = value
        with pytest.raises(CheckpointFinalizationError, match="CHECKPOINT_FINALIZATION_RECEIPT_MISMATCH"):
            compile_checkpoint_finalization_proposal(
                pending,
                bad,
                expected_work_item_id=WORK_ITEM,
                expected_checkpoint_ref=CHECKPOINT,
                expected_materialization_commit_sha=MATERIALIZATION_SHA,
            )


def test_finalization_rejects_unrelated_continuity_mutation():
    pending = document()
    proposal = compile_ok(pending)
    final_doc = apply_finalization_to_document(pending, proposal) + "outside mutation"
    with pytest.raises(CheckpointFinalizationError, match="CHECKPOINT_FINALIZATION_UNRELATED_MUTATION"):
        verify_finalization_document(
            pending,
            final_doc,
            proposal,
            finalization_commit_sha=FINALIZATION_SHA,
        )


def test_finalization_requires_real_40_hex_commit():
    pending = document()
    proposal = compile_ok(pending)
    final_doc = apply_finalization_to_document(pending, proposal)
    with pytest.raises(CheckpointFinalizationError, match="CHECKPOINT_FINALIZATION_COMMIT_INVALID"):
        verify_finalization_document(pending, final_doc, proposal, finalization_commit_sha="not-a-sha")


def test_finalizer_has_no_network_git_writer_or_branch_authority_input():
    source_path = Path(__file__).resolve().parents[1] / "learning_retriever" / "checkpoint_finalizer.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_roots = {"requests", "httpx", "urllib", "socket", "subprocess", "git", "github"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(forbidden_roots)
    assert "governed_branch_verified" not in source
    assert "write_succeeded" not in source
    assert "git push" not in source.casefold()
