from __future__ import annotations

import ast
import inspect
from pathlib import Path
import unittest

from learning_retriever.checkpoint_compiler import (
    CheckpointCompilationError,
    apply_proposal_to_document,
    compile_checkpoint_proposal,
    verify_post_write_document,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTINUITY_PATH = REPO_ROOT / "07_连续性与生产状态/连续性与当前生产状态.md"
BASELINE_CHECKPOINT = "5454103847"
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"


def revision(
    revision_id: str,
    event_type: str,
    *,
    parent: str | None,
    changed=None,
    preserved=None,
    revoked=None,
    experimental=None,
    **extra,
):
    payload = {
        "revision_id": revision_id,
        "work_item_id": WORK_ITEM,
        "event_type": event_type,
        "source_ref": f"issue19-{revision_id}",
        "parent_revision": parent,
        "changed": list(changed or []),
        "preserved": list(preserved or []),
        "revoked": list(revoked or []),
        "experimental": list(experimental or []),
    }
    payload.update(extra)
    return payload


class ActiveWorkItemCheckpointCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = CONTINUITY_PATH.read_text(encoding="utf-8")

    def _events(self):
        return [
            revision(
                "R1",
                "MODIFY",
                parent=None,
                changed=["reaction_cutaway_keeps_kaim_offscreen"],
                preserved=["screen_right_to_screen_left_side_on_traverse"],
            ),
            revision(
                "R2",
                "LOCK",
                parent="R1",
                changed=["same_master_return_reveals_kaim_absent"],
            ),
            revision(
                "R3",
                "EXPERIMENT",
                parent="R2",
                changed=["sparser_model_execution_wording"],
            ),
            revision(
                "R4",
                "REVOKE",
                parent="R3",
                revoked=["clothes_on_chest"],
            ),
            revision(
                "R5",
                "CHECKPOINT",
                parent="R4",
                effective_state_summary="凯姆继续以围巾搭过固定晾衣绳横移；reaction cutaway 后回同一 master 时凯姆已经离开。",
                unresolved_failures=["scarf_persistence_and_co_motion_requires_target_model_validation"],
                next_expected_action="run_target_model_AB_for_scarf_persistence",
            ),
        ]

    def _proposal(self):
        return compile_checkpoint_proposal(
            self.before,
            self._events(),
            expected_work_item_id=WORK_ITEM,
            expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
            proposed_checkpoint_ref="issue19-checkpoint-R5",
        )

    def test_issue19_like_revision_series_compiles_pending_snapshot(self):
        proposal = self._proposal()
        state = proposal.proposed_state
        self.assertEqual(proposal.status, "PENDING_WRITE")
        self.assertEqual(proposal.authority_boundary, "proposal_only_no_persistence_authority")
        self.assertEqual(state["work_item_id"], WORK_ITEM)
        self.assertEqual(state["latest_applied_checkpoint_ref"], "issue19-checkpoint-R5")
        self.assertEqual(state["checkpoint_writeback_status"], "pending_write")
        self.assertIsNone(state["writeback_verified_commit"])
        self.assertEqual(state["canonical_merge_status"], "pending_checkpoint_write")
        self.assertFalse(proposal.as_dict()["persistence_verified"])

    def test_omission_preserves_baseline_constraints(self):
        state = self._proposal().proposed_state
        self.assertIn("scarf_clothesline_geometry", state["locked_constraints"])
        self.assertIn("kaim_body_and_hands_remain_below_fixed_line", state["locked_constraints"])
        self.assertIn("mass_laundry_collision", state["preserved_constraints"])
        self.assertIn("two_foot_wall_arrival_buffer", state["preserved_constraints"])
        self.assertIn("reaction_cutaway_keeps_kaim_offscreen", state["preserved_constraints"])

    def test_explicit_revoke_removes_only_named_constraint(self):
        state = self._proposal().proposed_state
        self.assertNotIn("clothes_on_chest", state["preserved_constraints"])
        self.assertIn("clothes_on_chest", state["revoked_constraints"])
        self.assertIn("mass_laundry_collision", state["preserved_constraints"])

    def test_lock_and_experiment_categories_are_distinct(self):
        state = self._proposal().proposed_state
        self.assertIn("same_master_return_reveals_kaim_absent", state["locked_constraints"])
        self.assertIn("sparser_model_execution_wording", state["experimental_constraints"])
        self.assertNotIn("sparser_model_execution_wording", state["locked_constraints"])

    def test_lock_conflict_fails_closed(self):
        events = [
            revision(
                "R1",
                "LOCK",
                parent=None,
                changed=["new_lock"],
                revoked=["new_lock"],
            ),
            revision("R2", "CHECKPOINT", parent="R1"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_LOCK_CONFLICT"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R2",
            )

    def test_non_revoke_event_cannot_silently_revoke_existing_lock(self):
        events = [
            revision(
                "R1",
                "MODIFY",
                parent=None,
                revoked=["scarf_clothesline_geometry"],
            ),
            revision("R2", "CHECKPOINT", parent="R1"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_LOCK_CONFLICT"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R2",
            )

    def test_explicit_revoke_event_can_remove_existing_lock(self):
        events = [
            revision(
                "R1",
                "REVOKE",
                parent=None,
                revoked=["scarf_clothesline_geometry"],
            ),
            revision("R2", "CHECKPOINT", parent="R1"),
        ]
        proposal = compile_checkpoint_proposal(
            self.before,
            events,
            expected_work_item_id=WORK_ITEM,
            expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
            proposed_checkpoint_ref="R2",
        )
        self.assertNotIn("scarf_clothesline_geometry", proposal.proposed_state["locked_constraints"])
        self.assertIn("scarf_clothesline_geometry", proposal.proposed_state["revoked_constraints"])

    def test_revoke_event_rejects_ambiguous_changed_payload(self):
        events = [
            revision(
                "R1",
                "REVOKE",
                parent=None,
                changed=["ambiguous_new_constraint"],
                revoked=["clothes_on_chest"],
            ),
            revision("R2", "CHECKPOINT", parent="R1"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_REVOKE_AMBIGUOUS"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R2",
            )

    def test_duplicate_revision_id_fails_closed(self):
        events = [
            revision("R1", "MODIFY", parent=None),
            revision("R1", "CHECKPOINT", parent="R1"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_REVISION_DUPLICATE"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R2",
            )

    def test_broken_parent_chain_fails_closed(self):
        events = [
            revision("R1", "MODIFY", parent=None),
            revision("R2", "CHECKPOINT", parent="WRONG"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_PARENT_CHAIN_BROKEN"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R2",
            )

    def test_wrong_work_item_fails_closed(self):
        events = self._events()
        events[1]["work_item_id"] = "KAIM-HIGH-SEARCH-30S"
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_WORK_ITEM_MISMATCH"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R5",
            )

    def test_stale_baseline_checkpoint_fails_closed(self):
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_BASELINE_STALE"):
            compile_checkpoint_proposal(
                self.before,
                self._events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref="OLDER-CHECKPOINT",
                proposed_checkpoint_ref="R5",
            )

    def test_terminal_checkpoint_or_close_is_required(self):
        events = [revision("R1", "MODIFY", parent=None)]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_TERMINAL_EVENT_REQUIRED"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R1",
            )

    def test_event_after_terminal_fails_closed(self):
        events = [
            revision("R1", "CHECKPOINT", parent=None),
            revision("R2", "MODIFY", parent="R1"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_EVENT_AFTER_TERMINAL"):
            compile_checkpoint_proposal(
                self.before,
                events,
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R1",
            )

    def test_apply_proposal_is_in_memory_only_and_preserves_outside_text(self):
        proposal = self._proposal()
        after = apply_proposal_to_document(self.before, proposal)
        begin = "<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->"
        end = "<!-- ACTIVE_WORK_ITEM_STATE_END -->"
        before_prefix, before_rest = self.before.split(begin, 1)
        _, before_suffix = before_rest.split(end, 1)
        after_prefix, after_rest = after.split(begin, 1)
        _, after_suffix = after_rest.split(end, 1)
        self.assertEqual(before_prefix, after_prefix)
        self.assertEqual(before_suffix, after_suffix)
        self.assertIn("checkpoint_writeback_status: pending_write", after)

    def test_post_write_verifier_rejects_unrelated_continuity_mutation(self):
        proposal = self._proposal()
        after = apply_proposal_to_document(self.before, proposal)
        tampered = after.replace("# 1. 当前项目阶段", "# 1. 被意外改写的项目阶段", 1)
        with self.assertRaisesRegex(
            CheckpointCompilationError,
            "CHECKPOINT_UNRELATED_CONTINUITY_MUTATION",
        ):
            verify_post_write_document(
                self.before,
                tampered,
                proposal,
                verified_commit_sha="a" * 40,
            )

    def test_post_write_verifier_rejects_wrong_active_block(self):
        proposal = self._proposal()
        after = apply_proposal_to_document(self.before, proposal)
        tampered = after.replace(
            "latest_applied_checkpoint_ref: issue19-checkpoint-R5",
            "latest_applied_checkpoint_ref: WRONG",
            1,
        )
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_POST_WRITE_MISMATCH"):
            verify_post_write_document(
                self.before,
                tampered,
                proposal,
                verified_commit_sha="b" * 40,
            )

    def test_post_write_verifier_requires_concrete_commit_sha(self):
        proposal = self._proposal()
        after = apply_proposal_to_document(self.before, proposal)
        with self.assertRaisesRegex(
            CheckpointCompilationError,
            "CHECKPOINT_VERIFIED_COMMIT_INVALID",
        ):
            verify_post_write_document(
                self.before,
                after,
                proposal,
                verified_commit_sha="looks-good-to-me",
            )

    def test_successful_post_write_receipt_does_not_overclaim_governed_branch(self):
        proposal = self._proposal()
        after = apply_proposal_to_document(self.before, proposal)
        receipt = verify_post_write_document(
            self.before,
            after,
            proposal,
            verified_commit_sha="c" * 40,
        )
        self.assertEqual(receipt["status"], "VERIFIED_POST_WRITE_DOCUMENT")
        self.assertTrue(receipt["outside_active_block_unchanged"])
        self.assertTrue(receipt["active_block_matches_proposal"])
        self.assertFalse(
            receipt["may_be_reported_as_canonical_only_if_orchestrator_confirms_commit_is_on_governed_target_branch"]
        )

    def test_caller_cannot_supply_write_succeeded_shortcut(self):
        signature = inspect.signature(compile_checkpoint_proposal)
        self.assertNotIn("write_succeeded", signature.parameters)
        self.assertNotIn("verified", signature.parameters)
        with self.assertRaises(TypeError):
            compile_checkpoint_proposal(
                self.before,
                self._events(),
                expected_work_item_id=WORK_ITEM,
                expected_baseline_checkpoint_ref=BASELINE_CHECKPOINT,
                proposed_checkpoint_ref="R5",
                write_succeeded=True,
            )

    def test_module_has_no_network_git_or_connector_writer_import(self):
        source_path = REPO_ROOT / "tools/learning_retriever/learning_retriever/checkpoint_compiler.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        forbidden = {"requests", "httpx", "urllib", "socket", "subprocess", "git", "github"}
        self.assertTrue(imports.isdisjoint(forbidden), imports.intersection(forbidden))


if __name__ == "__main__":
    unittest.main()
