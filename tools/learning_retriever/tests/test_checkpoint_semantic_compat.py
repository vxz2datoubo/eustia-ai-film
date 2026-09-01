from pathlib import Path
import unittest

from learning_retriever.checkpoint_compiler import _compile_checkpoint_core

ROOT = Path(__file__).resolve().parents[3]
CONTINUITY = (ROOT / "07_连续性与生产状态/连续性与当前生产状态.md").read_text(encoding="utf-8")
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
BASELINE = "5454103847"
NEW_REF = "5500000001"


def evt(rid, kind, parent, **extra):
    data = {
        "revision_id": rid,
        "work_item_id": WORK_ITEM,
        "event_type": kind,
        "source_ref": NEW_REF,
        "parent_revision": parent,
        "changed": [], "preserved": [], "revoked": [], "experimental": [],
    }
    data.update(extra)
    return data


def compile_core(events):
    return _compile_checkpoint_core(
        CONTINUITY,
        events,
        expected_work_item_id=WORK_ITEM,
        expected_baseline_checkpoint_ref=BASELINE,
        proposed_checkpoint_ref=NEW_REF,
    )


class CheckpointSemanticCompatibilityTests(unittest.TestCase):
    def test_lock_can_add_locked_and_experimental_deltas_without_collapsing_categories(self):
        proposal = compile_core([
            evt("R1", "LOCK", None, changed=["new_lock"], experimental=["test_only_variant"]),
            evt("R2", "CHECKPOINT", "R1"),
        ])
        self.assertIn("new_lock", proposal.proposed_state["locked_constraints"])
        self.assertIn("test_only_variant", proposal.proposed_state["experimental_constraints"])
        self.assertNotIn("test_only_variant", proposal.proposed_state["locked_constraints"])

    def test_omission_preserves_existing_effective_constraints(self):
        proposal = compile_core([evt("R1", "CHECKPOINT", None)])
        self.assertIn("scarf_clothesline_geometry", proposal.proposed_state["locked_constraints"])
        self.assertIn("mass_laundry_collision", proposal.proposed_state["preserved_constraints"])

    def test_revoke_removes_only_explicitly_named_constraint(self):
        proposal = compile_core([
            evt("R1", "REVOKE", None, revoked=["clothes_on_chest"]),
            evt("R2", "CHECKPOINT", "R1"),
        ])
        self.assertNotIn("clothes_on_chest", proposal.proposed_state["preserved_constraints"])
        self.assertIn("clothes_on_chest", proposal.proposed_state["revoked_constraints"])
        self.assertIn("mass_laundry_collision", proposal.proposed_state["preserved_constraints"])


if __name__ == "__main__":
    unittest.main()
