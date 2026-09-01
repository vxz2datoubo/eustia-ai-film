from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from learning_retriever.checkpoint_compiler import (
    CheckpointProposal,
    CheckpointWriteVerification,
    _compile_checkpoint_core,
    apply_proposal_to_document,
)
from learning_retriever.checkpoint_finalizer import (
    compile_checkpoint_finalization_proposal,
    verify_finalization_document,
)
from learning_retriever.checkpoint_trust import FixedCommitContinuity

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTINUITY = (REPO_ROOT / "07_连续性与生产状态/连续性与当前生产状态.md").read_text(encoding="utf-8")
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
BASELINE_REF = "5454103847"
CHECKPOINT_REF = "5500000001"
MATERIALIZATION_SHA = "2" * 40
FINALIZATION_SHA = "3" * 40


def events():
    return [{
        "revision_id": "R1",
        "work_item_id": WORK_ITEM,
        "event_type": "CHECKPOINT",
        "source_ref": CHECKPOINT_REF,
        "parent_revision": None,
        "changed": [],
        "preserved": ["screen_right_to_screen_left_side_on_traverse"],
        "revoked": [],
        "experimental": [],
    }]


def trusted_proposal():
    core = _compile_checkpoint_core(
        CONTINUITY,
        events(),
        expected_work_item_id=WORK_ITEM,
        expected_baseline_checkpoint_ref=BASELINE_REF,
        proposed_checkpoint_ref=CHECKPOINT_REF,
    )
    return CheckpointProposal(
        **{
            **core.__dict__,
            "canonical_baseline_sha": "1" * 40,
            "source_issue": 19,
            "trusted_snapshot_fingerprint": "f" * 64,
        }
    )


def verification():
    proposal = trusted_proposal()
    pending = apply_proposal_to_document(CONTINUITY, proposal)
    return CheckpointWriteVerification(
        proposal=proposal,
        commit_sha=MATERIALIZATION_SHA,
        fetched_pending_markdown=pending,
        post_write_fingerprint="a" * 64,
    )


class CheckpointFinalizerTrustBoundTests(unittest.TestCase):
    def test_finalizer_stamps_only_fixed_materialization_returned_by_reexecution(self):
        verified = verification()
        with patch(
            "learning_retriever.checkpoint_finalizer.verify_post_write_document",
            return_value=verified,
        ), patch(
            "learning_retriever.checkpoint_finalizer.validate_live_checkpoint",
            return_value=CHECKPOINT_REF,
        ):
            proposal = compile_checkpoint_finalization_proposal(
                REPO_ROOT,
                events(),
                materialization_commit_sha=MATERIALIZATION_SHA,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
        self.assertEqual(proposal.proposed_state["checkpoint_writeback_status"], "verified")
        self.assertEqual(proposal.proposed_state["writeback_verified_commit"], MATERIALIZATION_SHA)
        self.assertEqual(proposal.proposed_state["canonical_merge_status"], "checkpoint_materialization_verified")
        self.assertFalse(proposal.as_dict()["finalization_persistence_verified"])

    def test_serialized_receipt_cannot_mint_verified_finalization(self):
        fake = {
            "schema": "ACTIVE_WORK_ITEM_CHECKPOINT_WRITE_VERIFICATION/v2",
            "status": "VERIFIED_FIXED_GITHUB_MATERIALIZATION",
            "verified_commit_sha": MATERIALIZATION_SHA,
        }
        with self.assertRaises(TypeError):
            compile_checkpoint_finalization_proposal(
                REPO_ROOT,
                events(),
                materialization_commit_sha=MATERIALIZATION_SHA,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
                materialization_verification_receipt=fake,
            )

    def test_final_verifier_reads_fixed_repository_commit_and_never_claims_branch_authority(self):
        verified = verification()
        with patch(
            "learning_retriever.checkpoint_finalizer.verify_post_write_document",
            return_value=verified,
        ), patch(
            "learning_retriever.checkpoint_finalizer.validate_live_checkpoint",
            return_value=CHECKPOINT_REF,
        ), patch(
            "learning_retriever.checkpoint_finalizer.fetch_fixed_continuity_at_commit",
        ) as fixed_fetch:
            proposal = compile_checkpoint_finalization_proposal(
                REPO_ROOT,
                events(),
                materialization_commit_sha=MATERIALIZATION_SHA,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
            pending = verified.fetched_pending_markdown
            begin = pending.find("<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->")
            end = pending.find("<!-- ACTIVE_WORK_ITEM_STATE_END -->") + len("<!-- ACTIVE_WORK_ITEM_STATE_END -->")
            final_doc = pending[:begin] + proposal.replacement_block + pending[end:]
            fixed_fetch.return_value = FixedCommitContinuity(FINALIZATION_SHA, final_doc, "b" * 64)
            result = verify_finalization_document(
                REPO_ROOT,
                events(),
                materialization_commit_sha=MATERIALIZATION_SHA,
                finalization_commit_sha=FINALIZATION_SHA,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
        self.assertEqual(result["status"], "VERIFIED_FIXED_GITHUB_FINALIZATION_DOCUMENT")
        self.assertFalse(result["runtime_confirms_governed_branch_or_ref"])
        self.assertTrue(result["canonical_reporting_requires_external_ref_confirmation"])


if __name__ == "__main__":
    unittest.main()
