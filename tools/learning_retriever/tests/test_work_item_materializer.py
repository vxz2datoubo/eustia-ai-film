from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import yaml

import learning_retriever.work_item_materializer as materializer

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "10_运行时/work_item_context_materialization_candidate.yaml"
PROPOSAL_PATH = ROOT / "09_资料证据/当前工作项结构化上下文物化候选提案.yaml"
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
CHECKPOINT = "5454103847"
MAIN = "a" * 40
SOURCE_ISSUE = 19
LOCKED = [
    "scarf_clothesline_geometry",
    "scarf_midpoint_single_drape_over_fixed_thick_line",
    "scarf_ends_separate_and_one_end_per_hand",
    "kaim_body_and_hands_remain_below_fixed_line",
    "scarf_and_kaim_co_translate_while_clothesline_stays_fixed",
    "screen_right_to_screen_left_side_on_traverse",
    "no_open_sky_prison_city_enclosure",
    "disappearance_reveal_return_to_same_master_with_kaim_already_absent",
]
STORY_SCOPE = "03_剧本与改编/当前改编剧本.md#凯姆高位搜索之后的屋顶横向移动/当前制作扩展"

SOURCE_TEXT = {
    "scarf_clothesline_geometry": "fixed thick clothesline rope stays above the character;",
    "scarf_midpoint_single_drape_over_fixed_thick_line": "scarf has one simple draped contact point over the rope, not multiple wraps;",
    "scarf_ends_separate_and_one_end_per_hand": "Kaim grips one scarf end in each hand;",
    "kaim_body_and_hands_remain_below_fixed_line": "Kaim’s hands and entire body remain below the rope;",
    "scarf_and_kaim_co_translate_while_clothesline_stays_fixed": "scarf stays close to Kaim and co-moves with him;",
    "screen_right_to_screen_left_side_on_traverse": "traversal remains a long side-on screen-right -> screen-left glide over the broad market gap;",
    "no_open_sky_prison_city_enclosure": "no visible open sky; background enclosure is cliff wall / prison-city structures.",
    "disappearance_reveal_return_to_same_master_with_kaim_already_absent": "return to the same master only after she clears the garment; Kaim is already absent at that return.",
}
SOURCE_COMMENT_ID = {
    lock_id: (5454103847 if lock_id.startswith("disappearance_") else 5427171891)
    for lock_id in LOCKED
}


def context() -> dict:
    return {
        "schema_version": "2.0", "packet_type": "WorkItemContext", "work_item_id": WORK_ITEM,
        "story_scope_ref": STORY_SCOPE,
        "effective_state_summary": "凯姆利用围巾搭过固定粗晾衣绳从画面右向左横滑，之后女人开窗并在同一master回切时凯姆已经消失。",
        "constraints": {"locked": list(LOCKED), "preserved": ["mass_laundry_collision", "adjacent_woman_opens_window"], "revoked": [], "experimental": [], "unresolved": ["scarf_persistence_and_co_motion_requires_target_model_validation"]},
        "checkpoint_ref": CHECKPOINT, "source_issue": SOURCE_ISSUE,
        "latest_source_checkpoint_ref": CHECKPOINT, "snapshot_fingerprint": "fixed-github-current",
        "verification_basis": "canonical_github_readback_verified_snapshot", "authority_boundary": "coordination_projection_only",
    }


def context_digest(packet=None):
    packet = packet or context()
    return materializer._stable_digest({
        "work_item_id": packet.get("work_item_id"), "story_scope_ref": packet.get("story_scope_ref"),
        "effective_state_summary": packet.get("effective_state_summary"), "constraints": packet.get("constraints"),
        "checkpoint_ref": packet.get("checkpoint_ref"), "source_issue": packet.get("source_issue"),
        "snapshot_fingerprint": packet.get("snapshot_fingerprint"), "verification_basis": packet.get("verification_basis"),
    })


def comments():
    bodies = {
        5427171891: "\n".join(SOURCE_TEXT[x] for x in LOCKED if SOURCE_COMMENT_ID[x] == 5427171891),
        5454103847: "\n".join(SOURCE_TEXT[x] for x in LOCKED if SOURCE_COMMENT_ID[x] == 5454103847),
    }
    return [{"id": cid, "body": body} for cid, body in bodies.items()]


def structured_block(*, work_item_id=WORK_ITEM, status="VERIFIED", checkpoint=CHECKPOINT, semantics=None, packet=None):
    invariants = ["凯姆与围巾移动时固定晾衣绳本体不平移", "监牢城市空间不打开成大面积自由天空"]
    semantics = semantics or dict(SOURCE_TEXT)
    comment_map = {item["id"]: item["body"] for item in comments()}
    source_bindings = {
        lock_id: {
            "source_issue": SOURCE_ISSUE,
            "comment_id": SOURCE_COMMENT_ID[lock_id],
            "source_body_sha256": sha256(comment_map[SOURCE_COMMENT_ID[lock_id]].encode("utf-8")).hexdigest(),
            "exact_text": semantics.get(lock_id, SOURCE_TEXT[lock_id]),
        }
        for lock_id in semantics
    }
    return {
        "work_item_id": work_item_id, "story_scope_ref": STORY_SCOPE, "source_checkpoint_ref": checkpoint,
        "source_context_digest": context_digest(packet), "materialization_status": status,
        "world_state_baseline": {
            "entities": {
                "kaim": {"kind": "character", "position": "confirmed_start_relation", "state": "ready_for_traverse"},
                "scarf": {"kind": "object", "position": "confirmed_contact_relation", "state": "controlled_by_kaim"},
                "clothesline": {"kind": "environment_anchor", "position": "fixed_span", "state": "fixed"},
            },
            "invariants": invariants,
        },
        "authorized_explicit_entries": {"adjacent_woman": {"kind": "character", "entry_condition": "adjacent_woman_opens_window_event", "exact_entry_time_authorized": False, "exact_entry_position_authorized": False}},
        "locked_constraint_semantics": semantics,
        "source_semantic_bindings": source_bindings,
        "provenance": {
            "world_state_entities": {"kaim": ["continuity.active_work_item"], "scarf": ["continuity.active_work_item.locked_constraints"], "clothesline": ["continuity.active_work_item.locked_constraints"]},
            "world_state_invariants": [
                {"invariant": invariants[0], "refs": ["continuity.locked.scarf_and_kaim_co_translate_while_clothesline_stays_fixed"]},
                {"invariant": invariants[1], "refs": ["continuity.locked.no_open_sky_prison_city_enclosure"]},
            ],
            "authorized_explicit_entries": {"adjacent_woman": ["continuity.preserved.adjacent_woman_opens_window"]},
            "locked_constraint_semantics": {lock_id: [f"issue19-comment-{SOURCE_COMMENT_ID[lock_id]}"] for lock_id in semantics},
        },
    }


def continuity_with(block: dict | None) -> str:
    if block is None: return "# continuity without structured context block"
    payload = yaml.safe_dump({"work_item_structured_context": block}, allow_unicode=True, sort_keys=False)
    return f"{materializer.BEGIN}\n```yaml\n{payload}```\n{materializer.END}"


class WorkItemMaterializerTests(unittest.TestCase):
    def harness(self, *, block: dict | None = None, packet: dict | None = None):
        """Explicit unit seam: preserve semantic tests without granting production trust."""
        resolution = MagicMock(); resolution.resolved_work_item_id = WORK_ITEM; resolution.resolution_required = True
        packet = packet or context()
        patches = [
            patch.object(materializer, "_verify_runtime_provenance", return_value=None),
            patch.object(materializer, "_RESOLVE_WORK_ITEM", return_value=resolution),
            patch.object(materializer, "_BUILD_CONTEXT", return_value=packet),
            patch.object(materializer, "_REVALIDATE_SOURCE", return_value={"status": "PASS", "phase": "pre_materialization"}),
            patch.object(materializer, "_current_main_sha", return_value=MAIN),
            patch.object(materializer, "_REMOTE_FILE_TEXT", return_value=continuity_with(block)),
            patch.object(materializer, "_REMOTE_ISSUE_COMMENTS", return_value=comments()),
        ]
        mocks = [item.start() for item in patches]
        for item in patches: self.addCleanup(item.stop)
        return mocks

    def assert_code(self, expected: str, fn) -> None:
        with self.assertRaises(materializer.WorkItemMaterializationError) as caught: fn()
        self.assertEqual(expected, caught.exception.code)

    def test_real_shape_without_canonical_block_is_unavailable_not_profile_inferred(self):
        self.harness(block=None); result = materializer.materialize_current_work_item()
        self.assertEqual("STRUCTURED_CONTEXT_UNAVAILABLE", result.status); self.assertFalse(result.trusted_materialization_available)
        self.assertIsNone(result.world_state_baseline); self.assertEqual({}, result.as_dict()["locked_constraint_semantics"])

    def test_static_kaim_proposal_is_explicitly_non_authoritative(self):
        proposal = yaml.safe_load(PROPOSAL_PATH.read_text(encoding="utf-8")); self.assertEqual("PROPOSAL_ONLY", proposal["proposal_status"])
        self.assertFalse(proposal["runtime_authority"]); self.assertFalse(proposal["may_unlock_director_runtime"])
        self.assertFalse(yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))["trust_boundary"]["static_proposal_can_satisfy_trusted_readback"])

    def test_public_api_accepts_no_caller_authority_arguments(self):
        with self.assertRaises(TypeError): materializer.materialize_current_work_item(ROOT)  # type: ignore[call-arg]
        with self.assertRaises(TypeError): materializer.materialize_current_work_item(work_item_id=WORK_ITEM)  # type: ignore[call-arg]

    def test_verified_canonical_block_produces_ready_immutable_readback(self):
        block = structured_block(); self.harness(block=block); result = materializer.materialize_current_work_item()
        self.assertEqual("STRUCTURED_CONTEXT_READY", result.status); self.assertTrue(result.trusted_materialization_available)
        self.assertEqual(set(LOCKED), set(result.locked_constraint_semantics))
        with self.assertRaises(TypeError): result.world_state_baseline["entities"]["kaim"]["state"] = "forged"

    def test_block_for_other_work_item_fails_closed(self):
        self.harness(block=structured_block(work_item_id="OTHER-WORK-ITEM")); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_WORK_ITEM_MISMATCH", materializer.materialize_current_work_item)

    def test_block_must_match_current_applied_checkpoint(self):
        self.harness(block=structured_block(checkpoint="old-checkpoint")); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_CHECKPOINT_MISMATCH", materializer.materialize_current_work_item)

    def test_candidate_or_unverified_materialization_status_fails_closed(self):
        self.harness(block=structured_block(status="CANDIDATE")); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_STATUS_INVALID", materializer.materialize_current_work_item)

    def test_lock_semantics_require_exact_canonical_lock_set(self):
        missing = {lock_id: SOURCE_TEXT[lock_id] for lock_id in LOCKED[:-1]}
        self.harness(block=structured_block(semantics=missing)); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_COVERAGE_MISMATCH", materializer.materialize_current_work_item)

    def test_semantic_rewrite_with_same_lock_id_fails_source_binding(self):
        block = structured_block(); block["locked_constraint_semantics"][LOCKED[0]] = "softened invented semantic"
        self.harness(block=block); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", materializer.materialize_current_work_item)

    def test_source_body_digest_swap_fails_closed(self):
        block = structured_block(); block["source_semantic_bindings"][LOCKED[0]]["source_body_sha256"] = "0" * 64
        self.harness(block=block); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_LOCK_SOURCE_BINDING_INVALID", materializer.materialize_current_work_item)

    def test_source_context_digest_must_match_fresh_packet(self):
        block = structured_block(); block["source_context_digest"] = "0" * 64
        self.harness(block=block); self.assert_code("WORK_ITEM_STRUCTURED_CONTEXT_SOURCE_CONTEXT_MISMATCH", materializer.materialize_current_work_item)

    def test_runtime_dependency_patch_fails_before_authority_read(self):
        with patch.object(materializer, "resolve_work_item", lambda *_a, **_k: None):
            self.assert_code("WORK_ITEM_MATERIALIZER_RUNTIME_PROVENANCE_SUBSTITUTED", materializer.materialize_current_work_item)

    def test_candidate_remains_unregistered_and_unactivated(self):
        for text in ((ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"), (ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"), (ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8")):
            self.assertNotIn("work_item_context_materialization_candidate", text)
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual("absent", policy["activation"]["PROJECT_INDEX_registration"])


if __name__ == "__main__":
    unittest.main()
