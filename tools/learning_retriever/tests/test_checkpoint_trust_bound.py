from __future__ import annotations

import copy
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from learning_retriever.checkpoint_compiler import (
    CheckpointCompilationError,
    CheckpointProposal,
    CheckpointWriteVerification,
    _compile_checkpoint_core,
    _parse_state,
    _render_state_block,
    compile_checkpoint_proposal,
    verify_post_write_document,
)
from learning_retriever.checkpoint_finalizer import compile_checkpoint_finalization_proposal
from learning_retriever.checkpoint_trust import FixedCommitContinuity, TrustedCheckpointBaseline

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTINUITY = (REPO_ROOT / "07_连续性与生产状态/连续性与当前生产状态.md").read_text(encoding="utf-8")
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
BASELINE_REF = "5454103847"
NEW_REF = "5500000001"
BASELINE_SHA = "1" * 40
MATERIALIZATION_SHA = "2" * 40


def event(revision_id: str, event_type: str, parent: str | None, **extra):
    payload = {
        "revision_id": revision_id,
        "work_item_id": WORK_ITEM,
        "event_type": event_type,
        "source_ref": NEW_REF if event_type in {"CHECKPOINT", "CLOSE"} else "5499999999",
        "parent_revision": parent,
        "changed": [],
        "preserved": [],
        "revoked": [],
        "experimental": [],
    }
    payload.update(extra)
    return payload


def events(terminal: str = "CHECKPOINT"):
    return [
        event("R1", "MODIFY", None, changed=["reaction_cutaway_keeps_kaim_offscreen"]),
        event("R2", "LOCK", "R1", changed=["same_master_return_reveals_kaim_absent"]),
        event("R3", terminal, "R2", effective_state_summary="accepted current revision state"),
    ]


def trusted_baseline(*, status: str = "ACTIVE_REVISION") -> TrustedCheckpointBaseline:
    state = _parse_state(CONTINUITY)
    state["status"] = status
    return TrustedCheckpointBaseline(
        canonical_sha=BASELINE_SHA,
        state=state,
        continuity_markdown=CONTINUITY,
        snapshot_fingerprint="f" * 64,
        latest_structured_source_checkpoint=NEW_REF,
        materialization_commit_sha=str(state["writeback_verified_commit"]),
    )


class CheckpointTrustBoundTests(unittest.TestCase):
    def test_public_compiler_has_no_raw_continuity_or_arbitrary_checkpoint_id_port(self):
        params = inspect.signature(compile_checkpoint_proposal).parameters
        self.assertNotIn("continuity_markdown", params)
        self.assertNotIn("proposed_checkpoint_ref", params)
        self.assertIn("project_root", params)

    def test_public_finalizer_has_no_serialized_receipt_or_pending_markdown_port(self):
        params = inspect.signature(compile_checkpoint_finalization_proposal).parameters
        self.assertNotIn("materialization_verification_receipt", params)
        self.assertNotIn("fetched_pending_markdown", params)
        self.assertNotIn("expected_checkpoint_ref", params)
        self.assertIn("materialization_commit_sha", params)

    def test_forged_local_verified_markdown_cannot_be_supplied_to_public_compiler(self):
        forged = CONTINUITY.replace("KAIM-SCARF-CLOTHESLINE-TRAVERSE", "ATTACKER-WORK", 1)
        self.assertIn("ATTACKER-WORK", forged)
        with self.assertRaises(TypeError):
            compile_checkpoint_proposal(
                REPO_ROOT,
                events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
                continuity_markdown=forged,
            )

    def test_public_compile_uses_trusted_baseline_and_terminal_live_comment_as_checkpoint_id(self):
        with patch(
            "learning_retriever.checkpoint_compiler.load_trusted_checkpoint_baseline",
            return_value=trusted_baseline(),
        ), patch(
            "learning_retriever.checkpoint_compiler.validate_live_checkpoint",
            return_value=NEW_REF,
        ) as live:
            proposal = compile_checkpoint_proposal(
                REPO_ROOT,
                events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
        self.assertEqual(proposal.proposed_checkpoint_ref, NEW_REF)
        self.assertEqual(proposal.canonical_baseline_sha, BASELINE_SHA)
        self.assertEqual(proposal.trusted_snapshot_fingerprint, "f" * 64)
        live.assert_called_once_with(19, NEW_REF, require_latest=True)

    def test_caller_cannot_substitute_checkpoint_ref_different_from_terminal_source_comment(self):
        with self.assertRaises(TypeError):
            compile_checkpoint_proposal(
                REPO_ROOT,
                events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
                proposed_checkpoint_ref="9999999999",
            )

    def test_canonical_lifecycle_closed_to_checkpointed_fails_closed(self):
        with patch(
            "learning_retriever.checkpoint_compiler.load_trusted_checkpoint_baseline",
            return_value=trusted_baseline(status="CLOSED"),
        ):
            with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_LIFECYCLE_TRANSITION_INVALID"):
                compile_checkpoint_proposal(
                    REPO_ROOT,
                    events("CHECKPOINT"),
                    expected_work_item_id=WORK_ITEM,
                    expected_baseline_checkpoint_ref=BASELINE_REF,
                )

    def test_canonical_lifecycle_resolved_unverified_to_checkpointed_fails_closed(self):
        with patch(
            "learning_retriever.checkpoint_compiler.load_trusted_checkpoint_baseline",
            return_value=trusted_baseline(status="RESOLVED_UNVERIFIED"),
        ):
            with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_LIFECYCLE_TRANSITION_INVALID"):
                compile_checkpoint_proposal(
                    REPO_ROOT,
                    events(),
                    expected_work_item_id=WORK_ITEM,
                    expected_baseline_checkpoint_ref=BASELINE_REF,
                )

    def test_active_revision_to_checkpointed_uses_existing_transition_authority(self):
        with patch(
            "learning_retriever.checkpoint_compiler.load_trusted_checkpoint_baseline",
            return_value=trusted_baseline(status="ACTIVE_REVISION"),
        ), patch(
            "learning_retriever.checkpoint_compiler.validate_live_checkpoint",
            return_value=NEW_REF,
        ):
            proposal = compile_checkpoint_proposal(
                REPO_ROOT,
                events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
        self.assertEqual(proposal.proposed_state["status"], "CHECKPOINTED")

    def test_private_reducer_preserves_omission_and_revoke_semantics_without_claiming_authority(self):
        core_events = [
            event("R1", "REVOKE", None, revoked=["clothes_on_chest"]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        proposal = _compile_checkpoint_core(
            CONTINUITY,
            core_events,
            expected_work_item_id=WORK_ITEM,
            expected_baseline_checkpoint_ref=BASELINE_REF,
            proposed_checkpoint_ref=NEW_REF,
        )
        self.assertNotIn("clothes_on_chest", proposal.proposed_state["preserved_constraints"])
        self.assertIn("clothes_on_chest", proposal.proposed_state["revoked_constraints"])
        self.assertIn("mass_laundry_collision", proposal.proposed_state["preserved_constraints"])
        self.assertIsNone(proposal.canonical_baseline_sha)

    def test_plain_serialized_receipt_has_no_finalizer_input_surface(self):
        fake_receipt = {
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
                materialization_verification_receipt=fake_receipt,
            )

    def test_materialization_verifier_reexecutes_compile_and_reads_fixed_commit(self):
        with patch(
            "learning_retriever.checkpoint_compiler.load_trusted_checkpoint_baseline",
            return_value=trusted_baseline(),
        ), patch(
            "learning_retriever.checkpoint_compiler.validate_live_checkpoint",
            return_value=NEW_REF,
        ), patch(
            "learning_retriever.checkpoint_compiler.fetch_fixed_continuity_at_commit",
        ) as fixed_fetch:
            proposal = compile_checkpoint_proposal(
                REPO_ROOT,
                events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
            pending = CONTINUITY.replace(
                CONTINUITY[CONTINUITY.find("<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->"):CONTINUITY.find("<!-- ACTIVE_WORK_ITEM_STATE_END -->") + len("<!-- ACTIVE_WORK_ITEM_STATE_END -->")],
                proposal.replacement_block,
            )
            fixed_fetch.side_effect = [
                FixedCommitContinuity(MATERIALIZATION_SHA, pending, "x" * 64),
                FixedCommitContinuity(BASELINE_SHA, CONTINUITY, "y" * 64),
            ]
            verification = verify_post_write_document(
                REPO_ROOT,
                events(),
                materialization_commit_sha=MATERIALIZATION_SHA,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_REF,
            )
        self.assertIsInstance(verification, CheckpointWriteVerification)
        self.assertEqual(verification.commit_sha, MATERIALIZATION_SHA)
        self.assertFalse(verification.as_dict()["runtime_confirms_governed_branch_or_ref"])


if __name__ == "__main__":
    unittest.main()
