from pathlib import Path
import unittest

from learning_retriever.checkpoint_compiler import (
    CheckpointCompilationError,
    compile_checkpoint_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTINUITY = (REPO_ROOT / "07_连续性与生产状态/连续性与当前生产状态.md").read_text(encoding="utf-8")
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
BASELINE = "5454103847"
REVOKED_BASELINE_CONSTRAINT = "broad_strong_textual_constraint_as_default"


def event(revision_id, event_type, parent, **kwargs):
    payload = {
        "revision_id": revision_id,
        "work_item_id": WORK_ITEM,
        "event_type": event_type,
        "source_ref": f"issue19-{revision_id}",
        "parent_revision": parent,
        "changed": [],
        "preserved": [],
        "revoked": [],
        "experimental": [],
    }
    payload.update(kwargs)
    return payload


def compile(events, **kwargs):
    return compile_checkpoint_proposal(
        CONTINUITY,
        events,
        expected_work_item_id=WORK_ITEM,
        expected_baseline_checkpoint_ref=BASELINE,
        proposed_checkpoint_ref=kwargs.pop("proposed_checkpoint_ref", "NEXT"),
        **kwargs,
    )


class CheckpointCompilerHardeningTests(unittest.TestCase):
    def test_revision_event_cannot_mint_story_scope(self):
        events = [
            event("R1", "MODIFY", None, story_scope_ref="03_剧本与改编/恶意覆盖.md"),
            event("R2", "CHECKPOINT", "R1"),
        ]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_EVENT_AUTHORITY_FIELD_FORBIDDEN"):
            compile(events)

    def test_revision_event_cannot_mint_state_or_writeback_status(self):
        forbidden_fields = {
            "status": "CLOSED",
            "checkpoint_writeback_status": "verified",
            "writeback_verified_commit": "a" * 40,
            "canonical_merge_status": "merged",
            "previous_work_item_id": "SOMETHING_ELSE",
        }
        for field, value in forbidden_fields.items():
            with self.subTest(field=field):
                events = [event("R1", "CHECKPOINT", None, **{field: value})]
                with self.assertRaisesRegex(
                    CheckpointCompilationError,
                    "CHECKPOINT_EVENT_AUTHORITY_FIELD_FORBIDDEN",
                ):
                    compile(events)

    def test_first_event_with_unverified_parent_fails_closed(self):
        events = [event("R1", "CHECKPOINT", "UNKNOWN-PARENT")]
        with self.assertRaisesRegex(CheckpointCompilationError, "CHECKPOINT_PARENT_BASELINE_UNKNOWN"):
            compile(events)

    def test_explicit_expected_parent_allows_verified_chain_start(self):
        events = [
            event("R1", "MODIFY", "REV-BASE", changed=["new_verified_delta"]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        proposal = compile(events, expected_parent_revision="REV-BASE")
        self.assertIn("new_verified_delta", proposal.proposed_state["preserved_constraints"])

    def test_modify_cannot_silently_reintroduce_revoked_constraint(self):
        events = [
            event("R1", "MODIFY", None, changed=[REVOKED_BASELINE_CONSTRAINT]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        with self.assertRaisesRegex(
            CheckpointCompilationError,
            "CHECKPOINT_REINTRODUCTION_REQUIRES_ADD_OR_LOCK",
        ):
            compile(events)

    def test_add_can_explicitly_reintroduce_revoked_constraint(self):
        events = [
            event("R1", "ADD", None, changed=[REVOKED_BASELINE_CONSTRAINT]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        state = compile(events).proposed_state
        self.assertIn(REVOKED_BASELINE_CONSTRAINT, state["preserved_constraints"])
        self.assertNotIn(REVOKED_BASELINE_CONSTRAINT, state["revoked_constraints"])

    def test_lock_can_explicitly_reintroduce_revoked_constraint(self):
        events = [
            event("R1", "LOCK", None, changed=[REVOKED_BASELINE_CONSTRAINT]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        state = compile(events).proposed_state
        self.assertIn(REVOKED_BASELINE_CONSTRAINT, state["locked_constraints"])
        self.assertNotIn(REVOKED_BASELINE_CONSTRAINT, state["revoked_constraints"])

    def test_experiment_can_retest_revoked_constraint_without_restoring_effective_state(self):
        events = [
            event("R1", "EXPERIMENT", None, changed=[REVOKED_BASELINE_CONSTRAINT]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        state = compile(events).proposed_state
        self.assertIn(REVOKED_BASELINE_CONSTRAINT, state["experimental_constraints"])
        self.assertIn(REVOKED_BASELINE_CONSTRAINT, state["revoked_constraints"])
        self.assertNotIn(REVOKED_BASELINE_CONSTRAINT, state["preserved_constraints"])
        self.assertNotIn(REVOKED_BASELINE_CONSTRAINT, state["locked_constraints"])

    def test_preserved_field_cannot_resurrect_revoked_constraint(self):
        events = [
            event("R1", "MODIFY", None, preserved=[REVOKED_BASELINE_CONSTRAINT]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        with self.assertRaisesRegex(
            CheckpointCompilationError,
            "CHECKPOINT_PRESERVE_REVOKED_CONFLICT",
        ):
            compile(events)

    def test_same_event_add_and_revoke_is_conflict(self):
        events = [
            event("R1", "MODIFY", None, changed=["x"], revoked=["x"]),
            event("R2", "CHECKPOINT", "R1"),
        ]
        with self.assertRaisesRegex(
            CheckpointCompilationError,
            "CHECKPOINT_EVENT_CONSTRAINT_CONFLICT",
        ):
            compile(events)


if __name__ == "__main__":
    unittest.main()
