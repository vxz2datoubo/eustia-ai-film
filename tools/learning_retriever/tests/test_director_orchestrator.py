from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import yaml

from learning_retriever.director_orchestrator import (
    DirectorRuntimeError,
    DirectorRuntimeOrchestrator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

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

LOCK_SEMANTICS = {
    "scarf_clothesline_geometry": "围巾与固定晾衣绳保持单一明确承重拓扑，不把晾衣绳变成随凯姆移动的绳索。",
    "scarf_midpoint_single_drape_over_fixed_thick_line": "围巾中点只搭过一根固定粗晾衣绳形成单次披挂。",
    "scarf_ends_separate_and_one_end_per_hand": "围巾两端保持分离，凯姆左右手各握一端。",
    "kaim_body_and_hands_remain_below_fixed_line": "凯姆身体与双手在横移期间保持在固定晾衣绳下方。",
    "scarf_and_kaim_co_translate_while_clothesline_stays_fixed": "凯姆与围巾一起从右向左平移，晾衣绳本体固定不平移。",
    "screen_right_to_screen_left_side_on_traverse": "横移主动作保持侧面可读并从画面右向左完成。",
    "no_open_sky_prison_city_enclosure": "监牢城市空间保持封闭感，画面不得打开成自由天空。",
    "disappearance_reveal_return_to_same_master_with_kaim_already_absent": "女人 reaction cutaway 后回到同一 master 时凯姆已经离开，不把离开发生成镜头内显式表演。",
}


def entry_entities_fixture() -> dict:
    return {
        "kaim": {"kind": "character", "position": "roof_right", "state": "traverse_ready"},
        "scarf": {"kind": "object", "position": "on_fixed_clothesline_midpoint", "state": "one_end_per_hand"},
        "clothesline": {"kind": "environment_anchor", "position": "fixed_roof_span", "state": "fixed"},
        "laundry": {"kind": "group", "position": "along_clothesline", "state": "hanging"},
        "wall": {"kind": "environment_anchor", "position": "left_building", "state": "static"},
        "window": {"kind": "environment_anchor", "position": "left_building_window", "state": "closed"},
        "woman": {"kind": "character", "position": "window_interior", "state": "approaching_window"},
    }


def world_entry_baseline() -> dict:
    return {
        "entities": entry_entities_fixture(),
        "invariants": [
            "no_open_sky_prison_city_enclosure",
            "fixed_clothesline_does_not_translate_with_kaim",
        ],
    }


def retrieval_result() -> dict:
    return {
        "canonical_runtime_receipt": {
            "active_work_item_resolution": {
                "resolved_work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            },
            "work_item_context_packet": {
                "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
                "constraints": {"locked": list(LOCKED)},
                "world_state_baseline": world_entry_baseline(),
                "locked_constraint_semantics": dict(LOCK_SEMANTICS),
            },
            "hard_routes": ["TARGET_ORIENTED_SPATIAL_BINDING"],
            "feature_compiler_receipt": {
                "compiler": "Director Feature Compiler",
                "compiled_feature_keys": ["target_oriented_spatial_binding"],
            },
        }
    }


def creative_packet() -> dict:
    entry_entities = entry_entities_fixture()
    exit_entities = {
        "scarf": {"kind": "object", "position": "left_building", "state": "still_with_kaim_after_exit"},
        "clothesline": {"kind": "environment_anchor", "position": "fixed_roof_span", "state": "fixed"},
        "laundry": {"kind": "group", "position": "along_clothesline", "state": "displaced_and_falling"},
        "wall": {"kind": "environment_anchor", "position": "left_building", "state": "static"},
        "window": {"kind": "environment_anchor", "position": "left_building_window", "state": "open"},
        "woman": {"kind": "character", "position": "window_interior", "state": "reacting"},
    }
    return {
        "packet_id": "DR-P0-KAIM-SCARF",
        "scene_diagnosis": {
            "dramatic_purpose": "让凯姆以熟练而干冷的方式穿过居民生活空间，同时继续搜索男孩并形成短暂喜剧呼吸。",
            "audience_knowledge_before": "凯姆正从高位继续搜索偷钱男孩。",
            "audience_knowledge_after": "凯姆已横向穿越到左侧建筑并在女人反应切away期间离开当前master。",
            "material_problem": "动作必须同时保持围巾与晾衣绳拓扑、横向轨迹、人物高手感和消失揭示。",
        },
        "director_intent": {
            "audience_effect": "先相信凯姆动作熟练，再从生活空间碰撞中得到干冷幽默，最后用同一master里的突然缺席形成轻巧收束。",
            "character_goal": "凯姆不停顿地向左侧屋顶继续搜索男孩。",
            "subtext": "这些意外对凯姆只是效率优先下的生活摩擦，不是让他变成小丑。",
            "success_condition": "动作关系清楚、凯姆始终高效、世界生活感存在，回master时凯姆已经不在。",
        },
        "world_state": {
            "entry": {
                "entities": entry_entities,
                "invariants": [
                    "no_open_sky_prison_city_enclosure",
                    "fixed_clothesline_does_not_translate_with_kaim",
                ],
            },
            "exit": {
                "entities": exit_entities,
                "invariants": [
                    "no_open_sky_prison_city_enclosure",
                    "fixed_clothesline_does_not_translate_with_kaim",
                ],
            },
            "explicit_exits_or_removals": ["kaim"],
            "state_changes": [
                "window closed -> open",
                "laundry hanging -> displaced/falling",
                "kaim local scene presence -> explicit exit during reaction cutaway",
            ],
        },
        "events": [
            {
                "event_id": "E1",
                "agent": "kaim",
                "action": "traverse_right_to_left_below_fixed_line",
                "target": "clothesline",
                "target_kind": "ENTITY",
                "instrument": "scarf",
                "support_or_contact": ["clothesline"],
                "precondition": "scarf midpoint is draped over fixed line with one end in each hand",
                "result": "kaim and scarf translate left while the clothesline remains fixed",
                "reaction_trigger": "laundry begins to collide with kaim",
                "narrative_function": "skillful traversal through lived-in space",
            },
            {
                "event_id": "E2",
                "agent": "kaim",
                "action": "collide_through_laundry",
                "target": "laundry",
                "target_kind": "ENTITY",
                "instrument": None,
                "support_or_contact": ["laundry"],
                "precondition": "continued traverse",
                "result": "laundry is displaced without stopping kaim",
                "reaction_trigger": "garment catches around neck/body",
                "narrative_function": "dry physical comedy without clownish loss of competence",
            },
            {
                "event_id": "E3",
                "agent": "kaim",
                "action": "two_foot_wall_buffer",
                "target": "wall",
                "target_kind": "ENTITY",
                "instrument": None,
                "support_or_contact": ["wall"],
                "precondition": "arrival at left building",
                "result": "horizontal momentum is absorbed while kaim remains controlled",
                "reaction_trigger": "woman opens adjacent window",
                "narrative_function": "credible arrival physics",
            },
            {
                "event_id": "E4",
                "agent": "woman",
                "action": "open_window_and_react",
                "target": "window",
                "target_kind": "ENTITY",
                "instrument": None,
                "support_or_contact": ["window"],
                "precondition": "impact/noise beside window",
                "result": "woman looks at kaim and the displaced garment",
                "reaction_trigger": "brief dry dialogue",
                "narrative_function": "reaction cutaway that hides kaim's local exit",
            },
            {
                "event_id": "E5",
                "agent": "kaim",
                "action": "exit_during_reaction_cutaway",
                "target": None,
                "target_kind": "NONE",
                "instrument": "scarf",
                "support_or_contact": None,
                "precondition": "attention is on woman's reaction",
                "result": "kaim leaves the local master frame before return",
                "reaction_trigger": "return to same master",
                "narrative_function": "disappearance reveal",
            },
        ],
        "blocking": {
            "initial_positions": {
                "kaim": "roof_right",
                "scarf": "on_fixed_clothesline_midpoint",
                "clothesline": "fixed_roof_span",
                "woman": "window_interior",
            },
            "movement_paths": {
                "kaim": "screen_right_to_screen_left_below_line",
                "scarf": "co_translate_with_kaim_around_fixed_line",
                "laundry": "local_collision_displacement",
                "woman": "interior_to_open_window",
            },
            "final_positions": {
                "kaim": "offscreen_left_after_cutaway",
                "scarf": "left_building",
                "clothesline": "fixed_roof_span",
                "laundry": "along_clothesline",
                "woman": "window_interior",
            },
            "support_contacts": {
                "kaim": ["clothesline", "wall"],
                "scarf": ["clothesline"],
                "woman": ["window"],
            },
        },
        "performance": {
            "kaim": {
                "objective": "不断线地继续向左移动和搜索",
                "subtext": "意外很烦但不值得情绪化处理",
                "observable_behavior": ["动作连续", "抵墙缓冲受控", "对白干冷简短"],
            },
            "woman": {
                "objective": "弄清窗外突然发生了什么",
                "subtext": "先困惑再否认那件衣服属于自己",
                "observable_behavior": ["开窗", "短促观察", "反应自然不过演"],
            },
        },
        "cinematic_intent": {
            "contract_id": "DR-P0-KAIM-CINEMATIC",
            "intent": {
                "composition": {
                    "primary_mechanism": "lateral_traverse_readability",
                    "camera_reason": "保持右到左移动、固定晾衣绳和左侧抵墙终点同时可读",
                },
                "attention_handoff": {
                    "from_roi": "kaim_at_left_window",
                    "cut_or_transition_event": "woman_reaction",
                    "to_roi": "same_master_left_building",
                    "withheld_information": "kaim_exits_during_reaction",
                    "reveal_on_return": "kaim_already_absent",
                    "next_shot_target": "crowd_and_falling_laundry",
                },
            },
            "provenance": {
                "composition": {"source": "ai_director_proposal_bound_to_current_work_item"},
                "attention_handoff": {"source": "locked_disappearance_reveal_constraint"},
            },
            "context": {
                "material_fields": ["composition", "attention_handoff"],
                "material_attention_reveal": True,
            },
        },
        "shot_plan": [
            {
                "shot_id": "S1",
                "dramatic_function": "建立并完成横向围巾滑行动作链",
                "entry_state": "kaim starts at roof-right traverse setup",
                "events": ["E1", "E2", "E3"],
                "exit_state": "kaim buffered at left wall beside window",
                "necessity": "同时承担能力展示、空间生活感和动作因果",
                "camera_proposal": {
                    "authority_status": "PROPOSAL_ONLY",
                    "shot_size": "wide_to_medium_lateral_readability",
                    "orientation": "side_on",
                    "motion": "follow_lateral_without_depth_drift",
                    "composition": "fixed line readable above kaim",
                    "camera_reason": "preserve spatial causality and right-to-left path",
                },
            },
            {
                "shot_id": "S2",
                "dramatic_function": "用女人reaction隐藏凯姆离开并回同一master揭示缺席",
                "entry_state": "woman opens window next to kaim",
                "events": ["E4", "E5"],
                "exit_state": "same master returns with kaim already absent",
                "necessity": "把消失做成剪辑信息而非特效炫技",
                "camera_proposal": {
                    "authority_status": "PROPOSAL_ONLY",
                    "shot_size": "reaction_then_same_master",
                    "orientation": "preserve_master_orientation",
                    "motion": "minimal",
                    "composition": "attention shifts to woman then back to absence",
                    "camera_reason": "the cut hides exit and the return reveals absence",
                },
            },
        ],
        "transition": {
            "inherited_entities": ["clothesline", "wall"],
            "changed_entities": ["scarf", "laundry", "window", "woman"],
            "explicit_exits_or_removals": ["kaim"],
            "next_entry_state": {
                "entities": ["scarf", "clothesline", "laundry", "wall", "window", "woman"],
            },
        },
        "constraint_autonomy": {
            "locked_constraints_preserved": list(LOCKED),
            "hard_invariants": [
                "围巾中点只搭在固定粗晾衣绳上，两端分别在凯姆双手",
                "凯姆身体与双手始终在固定晾衣绳下方",
                "凯姆与围巾一起右向左移动，晾衣绳固定不平移",
                "封闭监牢城市环境不出现开放天空",
                "reaction cutaway后回同一master时凯姆已经消失",
            ],
            "guided_choices": [
                "衣物碰撞数量和具体次序可由导演模型在不破坏动作因果下调整",
                "女人反应强度保持自然不过演",
            ],
            "free_model_space": ["非关键衣物摆动细节", "背景次要居民微动作"],
            "final_state": "凯姆已离开当前master继续搜索，女人仍在窗口，晾衣绳保持固定，部分衣物被撞落。",
        },
        "provenance": {
            "scene_diagnosis": {"source": "ai_director_candidate_using_current_work_item"},
            "director_intent": {"source": "ai_director_candidate_using_current_work_item"},
            "world_state": {"source": "current_continuity_plus_director_delta"},
            "events": {"source": "ai_director_candidate"},
            "blocking": {"source": "ai_director_candidate"},
            "performance": {"source": "ai_director_candidate"},
            "cinematic_intent": {"source": "existing_cinematic_intent_contract"},
            "shot_plan": {"source": "ai_director_candidate"},
            "transition": {"source": "ai_director_candidate"},
            "constraint_autonomy": {"source": "canonical_locked_constraints_plus_ai_guidance"},
        },
    }


class DirectorRuntimeOrchestratorTests(unittest.TestCase):
    def make_runtime(self, retrieval: dict | None = None):
        patcher = patch("learning_retriever.director_orchestrator.DirectorLearningRuntime")
        runtime_cls = patcher.start()
        self.addCleanup(patcher.stop)
        runtime_cls.return_value.retrieve.return_value = retrieval or retrieval_result()
        orchestrator = DirectorRuntimeOrchestrator()
        return orchestrator, runtime_cls.return_value

    def assert_code(self, expected: str, fn) -> None:
        with self.assertRaises(DirectorRuntimeError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_current_kaim_scarf_case_compiles_as_non_executable_candidate(self):
        orchestrator, learning_runtime = self.make_runtime()
        result = orchestrator.compile("继续当前凯姆围巾晾衣绳横移这段", creative_packet())
        self.assertEqual("CANDIDATE_READY", result["status"])
        self.assertEqual("KAIM-SCARF-CLOTHESLINE-TRAVERSE", result["work_item_binding"]["work_item_id"])
        self.assertEqual("trusted_work_item_context", result["work_item_binding"]["world_entry_authority"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["deliverable"])
        self.assertTrue(result["downstream_gate_required"])
        self.assertEqual(set(LOCKED), set(result["director_ir"]["constraint_autonomy"]["locked_constraints_preserved"]))
        execution = result["minimum_execution_prompt_candidate"]
        self.assertEqual(list(LOCKED), execution["hard_invariant_refs"])
        self.assertEqual([LOCK_SEMANTICS[item] for item in LOCKED], execution["canonical_hard_invariants"])
        self.assertFalse(execution["caller_hard_invariants_are_lock_authority"])
        self.assertEqual("PROPOSAL_ONLY", result["director_ir"]["shot_plan"][0]["camera_proposal"]["authority_status"])
        learning_runtime.retrieve.assert_called_once()

    def test_bound_work_item_without_world_baseline_fails_closed(self):
        retrieval = retrieval_result()
        retrieval["canonical_runtime_receipt"]["work_item_context_packet"].pop("world_state_baseline")
        orchestrator, _ = self.make_runtime(retrieval)
        self.assert_code(
            "DIRECTOR_WORLD_BASELINE_UNAVAILABLE",
            lambda: orchestrator.compile("继续当前这段", creative_packet()),
        )

    def test_bound_work_item_without_lock_semantics_fails_closed(self):
        retrieval = retrieval_result()
        retrieval["canonical_runtime_receipt"]["work_item_context_packet"].pop("locked_constraint_semantics")
        orchestrator, _ = self.make_runtime(retrieval)
        self.assert_code(
            "DIRECTOR_LOCK_SEMANTICS_UNAVAILABLE",
            lambda: orchestrator.compile("继续当前这段", creative_packet()),
        )

    def test_creative_packet_cannot_supply_work_item_authority(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["work_item_id"] = "FORGED-WORK-ITEM"
        self.assert_code(
            "DIRECTOR_PACKET_AUTHORITY_VIOLATION",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_live_entity_cannot_disappear_by_prompt_omission(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["world_state"]["exit"]["entities"].pop("scarf")
        self.assert_code(
            "DIRECTOR_WORLD_ENTITY_DROPPED",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_caller_cannot_invent_entity_in_both_entry_and_exit(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        ghost = {"kind": "character", "position": "roof_right", "state": "invented"}
        packet["world_state"]["entry"]["entities"]["ghost_actor"] = deepcopy(ghost)
        packet["world_state"]["exit"]["entities"]["ghost_actor"] = deepcopy(ghost)
        self.assert_code(
            "DIRECTOR_WORLD_ENTRY_BASELINE_MISMATCH",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_caller_cannot_erase_real_entity_from_both_entry_and_exit(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["world_state"]["entry"]["entities"].pop("scarf")
        packet["world_state"]["exit"]["entities"].pop("scarf")
        packet["events"][0]["instrument"] = None
        packet["events"][0]["support_or_contact"] = ["clothesline"]
        packet["blocking"]["initial_positions"].pop("scarf")
        packet["blocking"]["movement_paths"].pop("scarf")
        packet["blocking"]["final_positions"].pop("scarf")
        packet["blocking"]["support_contacts"].pop("scarf")
        packet["transition"]["changed_entities"].remove("scarf")
        packet["transition"]["next_entry_state"]["entities"].remove("scarf")
        self.assert_code(
            "DIRECTOR_WORLD_ENTRY_BASELINE_MISMATCH",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_event_agent_must_exist_in_world_state(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["events"][0]["agent"] = "ghost_actor"
        self.assert_code(
            "DIRECTOR_EVENT_ENTITY_UNBOUND",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_blocking_cannot_move_unknown_entity(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["blocking"]["movement_paths"]["ghost_actor"] = "nowhere_to_nowhere"
        self.assert_code(
            "DIRECTOR_BLOCKING_ENTITY_UNBOUND",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_performance_actor_must_be_character_entity(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["performance"]["scarf"] = {
            "objective": "be dramatic",
            "subtext": "none",
            "observable_behavior": "flap",
        }
        self.assert_code(
            "DIRECTOR_PERFORMANCE_ACTOR_UNBOUND",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_shot_camera_cannot_mint_locked_authority(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["shot_plan"][0]["camera_proposal"]["authority_status"] = "LOCKED"
        self.assert_code(
            "DIRECTOR_CAMERA_AUTHORITY_MINT_ATTEMPT",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_transition_next_entry_must_equal_world_exit_entities(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["transition"]["next_entry_state"]["entities"].remove("scarf")
        self.assert_code(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_locked_constraint_id_cannot_be_dropped(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["constraint_autonomy"]["locked_constraints_preserved"].remove(
            "scarf_midpoint_single_drape_over_fixed_thick_line"
        )
        self.assert_code(
            "DIRECTOR_LOCKED_CONSTRAINT_DROPPED",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_lock_id_rubber_stamp_cannot_drop_material_semantics(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["constraint_autonomy"]["hard_invariants"] = ["unrelated harmless sentence"]
        result = orchestrator.compile("继续当前这段", packet)
        execution = result["minimum_execution_prompt_candidate"]
        self.assertEqual([LOCK_SEMANTICS[item] for item in LOCKED], execution["canonical_hard_invariants"])
        self.assertIn(LOCK_SEMANTICS["scarf_midpoint_single_drape_over_fixed_thick_line"], execution["text"])
        self.assertIn("unrelated harmless sentence", execution["text"])
        self.assertFalse(execution["caller_hard_invariants_are_lock_authority"])

    def test_cinematic_intent_cannot_mint_camera_physical_authority(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["cinematic_intent"] = {
            "contract_id": "FORGED-CAMERA",
            "intent": {
                "capture_intent": {
                    "camera_physical_position": "roof_absolute_anchor",
                }
            },
            "provenance": {
                "capture_intent": {"source": "ai_proposal"},
            },
            "context": {"material_fields": ["capture_intent"]},
        }
        self.assert_code(
            "DIRECTOR_CINEMATIC_INTENT_REJECTED",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_reasoning_scratchpad_is_not_an_allowed_packet_field(self):
        orchestrator, _ = self.make_runtime()
        packet = creative_packet()
        packet["chain_of_thought"] = "hidden reasoning should never enter runtime"
        self.assert_code(
            "DIRECTOR_PACKET_SCHEMA_INVALID",
            lambda: orchestrator.compile("继续当前这段", packet),
        )

    def test_candidate_contract_remains_unregistered(self):
        project_index = yaml.safe_load((PROJECT_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("director_runtime_orchestrator", project_index.get("canonical", {}))
        contract = yaml.safe_load(
            (PROJECT_ROOT / "10_运行时/director_runtime_orchestrator.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual("candidate", contract["status"])
        self.assertEqual("absent", contract["activation"]["PROJECT_INDEX_registration"])

    def test_regression_registry_contains_current_production_case(self):
        suite = yaml.safe_load(
            (PROJECT_ROOT / "11_验收/director_runtime_orchestrator_regression_cases.yaml").read_text(encoding="utf-8")
        )
        cases = {item["id"]: item for item in suite["cases"]}
        self.assertEqual(
            "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            cases["DR-P0-KAIM-SCARF-POSITIVE"]["work_item_id"],
        )


if __name__ == "__main__":
    unittest.main()
