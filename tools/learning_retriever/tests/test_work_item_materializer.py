from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import yaml

import learning_retriever.work_item_materializer as materializer_module
from learning_retriever.work_item_materializer import (
    WorkItemMaterializationError,
    materialize_current_work_item,
)


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "10_运行时/work_item_context_materialization_candidate.yaml"
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
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
PRESERVED = [
    "mass_laundry_collision",
    "clothes_on_chest",
    "medieval_shaping_garment_around_neck",
    "two_foot_wall_arrival_buffer",
    "adjacent_woman_opens_window",
    "kaim_line_你的衣服掉了",
    "woman_line_不是啊不是我的",
    "final_crowd_faces_bell_tower",
    "only_one_child_breaks_attention_upward",
    "kaim_skilled_efficient_dry_not_clownish",
]
SUMMARY = (
    "凯姆在屋顶之间利用围巾搭过固定粗晾衣绳，从画面右向左长距离横滑；"
    "途中撞飞大量衣物，女性束身衣挂到脖颈；抵达左侧建筑双脚缓冲撞墙，女人开窗，"
    "凯姆以干冷对白把衣物罩到她头上并在reaction cutaway期间画外离开；"
    "回同一master时凯姆已经消失；最后群众继续面向钟楼，仅一名小孩注意掉落衣物。"
)


def context() -> dict:
    return {
        "schema_version": "2.0",
        "packet_type": "WorkItemContext",
        "work_item_id": WORK_ITEM,
        "story_scope_ref": "03_剧本与改编/当前改编剧本.md#凯姆高位搜索之后的屋顶横向移动/当前制作扩展",
        "effective_state_summary": SUMMARY,
        "constraints": {
            "locked": list(LOCKED),
            "preserved": list(PRESERVED),
            "revoked": ["over_specified_setup_micro_choreography"],
            "experimental": ["sparse_directing_hard_only_material_narrative_errors"],
            "unresolved": ["scarf_persistence_and_co_motion_requires_target_model_validation"],
        },
        "checkpoint_ref": "5454103847",
        "source_issue": 19,
        "latest_source_checkpoint_ref": "5454103847",
        "snapshot_fingerprint": "fixed-github-current",
        "verification_basis": "canonical_github_readback_verified_snapshot",
        "authority_boundary": "coordination_projection_only",
    }


class WorkItemMaterializerTests(unittest.TestCase):
    def harness(self, packet: dict | None = None):
        resolution = MagicMock()
        resolution.resolved_work_item_id = WORK_ITEM
        resolution.resolution_required = True
        packet = packet or context()
        patches = [
            patch.object(materializer_module, "resolve_work_item", return_value=resolution),
            patch.object(materializer_module, "build_work_item_context_packet", return_value=packet),
            patch.object(
                materializer_module,
                "revalidate_source_revision",
                return_value={"status": "PASS", "phase": "pre_compiler"},
            ),
        ]
        mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        return mocks

    def assert_code(self, expected: str, fn) -> None:
        with self.assertRaises(WorkItemMaterializationError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_positive_current_work_item_materializes_projection_only(self):
        resolve_mock, build_mock, revalidate_mock = self.harness()
        result = materialize_current_work_item()
        self.assertEqual("WORK_ITEM_MATERIALIZATION_CANDIDATE/v1", result["schema"])
        self.assertEqual(WORK_ITEM, result["work_item_id"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["canonical_write_authorized"])
        self.assertFalse(result["learning_writeback_authorized"])
        self.assertFalse(result["maturity_promotion_authorized"])
        receipt = result["materialization_receipt"]
        self.assertTrue(receipt["projection_only"])
        self.assertFalse(receipt["serialized_output_is_authority"])
        self.assertTrue(receipt["fresh_materialization_required_before_consumption"])
        self.assertEqual(set(LOCKED), set(result["locked_constraint_semantics"]))
        self.assertEqual(
            {"kaim", "scarf", "clothesline", "laundry"},
            set(result["world_state_baseline"]["entities"]),
        )
        self.assertNotIn("adjacent_woman", result["world_state_baseline"]["entities"])
        self.assertIn("adjacent_woman", result["authorized_explicit_entries"])
        resolve_mock.assert_called_once()
        build_mock.assert_called_once()
        revalidate_mock.assert_called_once()

    def test_public_api_accepts_no_caller_authority_arguments(self):
        with self.assertRaises(TypeError):
            materialize_current_work_item(ROOT)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            materialize_current_work_item(work_item_id=WORK_ITEM)  # type: ignore[call-arg]

    def test_unknown_current_work_item_fails_closed(self):
        packet = context()
        packet["work_item_id"] = "OTHER-WORK-ITEM"
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_UNSUPPORTED_WORK_ITEM",
            materialize_current_work_item,
        )

    def test_story_scope_drift_fails_closed(self):
        packet = context()
        packet["story_scope_ref"] = "03_剧本与改编/当前改编剧本.md#other"
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_STORY_SCOPE_MISMATCH",
            materialize_current_work_item,
        )

    def test_summary_drift_fails_closed(self):
        packet = context()
        packet["effective_state_summary"] = "凯姆在别处进行完全不同的行动。"
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_SUMMARY_DRIFT",
            materialize_current_work_item,
        )

    def test_missing_lock_fails_closed(self):
        packet = context()
        packet["constraints"]["locked"].pop()
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_LOCK_SET_MISMATCH",
            materialize_current_work_item,
        )

    def test_extra_lock_fails_closed(self):
        packet = context()
        packet["constraints"]["locked"].append("new_unreviewed_lock")
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_LOCK_SET_MISMATCH",
            materialize_current_work_item,
        )

    def test_missing_required_preserved_constraint_fails_closed(self):
        packet = context()
        packet["constraints"]["preserved"].remove("adjacent_woman_opens_window")
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_PRESERVED_CONSTRAINT_MISSING",
            materialize_current_work_item,
        )

    def test_unverified_context_cannot_materialize(self):
        packet = context()
        packet["verification_basis"] = "caller_claimed_verified"
        self.harness(packet)
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_RESOLUTION_FAILED",
            materialize_current_work_item,
        )

    def test_profile_has_exact_lock_semantic_coverage_and_no_future_woman_in_baseline(self):
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        profile = policy["profiles"][WORK_ITEM]
        self.assertEqual(set(LOCKED), set(profile["locked_constraint_semantics"]))
        self.assertNotIn("adjacent_woman", profile["world_state_baseline"]["entities"])
        self.assertIn("adjacent_woman", profile["authorized_explicit_entries"])
        for entity in profile["world_state_baseline"]["entities"].values():
            self.assertTrue(entity["provenance"])
        for item in profile["locked_constraint_semantics"].values():
            self.assertTrue(item["provenance"])

    def test_candidate_is_not_registered_or_activated(self):
        project_index = (ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8")
        read_sets = (ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8")
        write_routes = (ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8")
        for text in (project_index, read_sets, write_routes):
            self.assertNotIn("work_item_context_materialization_candidate", text)
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual("absent", policy["activation"]["PROJECT_INDEX_registration"])
        self.assertEqual("absent", policy["activation"]["read_sets_registration"])
        self.assertEqual("absent", policy["activation"]["write_routes_registration"])

    def test_profile_validation_rejects_future_entry_laundered_into_baseline(self):
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        profile = deepcopy(policy["profiles"][WORK_ITEM])
        profile["world_state_baseline"]["entities"]["adjacent_woman"] = {
            "kind": "character",
            "position": "invented_entry_position",
            "state": "invented_entry_state",
            "provenance": ["continuity.active_work_item.preserved_constraints.adjacent_woman_opens_window"],
        }
        self.assert_code(
            "WORK_ITEM_MATERIALIZER_PROFILE_INVALID",
            lambda: materializer_module._validate_profile(profile, work_item_id=WORK_ITEM),
        )


if __name__ == "__main__":
    unittest.main()
