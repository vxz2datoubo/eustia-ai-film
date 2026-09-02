from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import yaml

import learning_retriever.director_orchestrator as orchestrator_module
import learning_retriever.runtime as runtime_module
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


def entity(kind: str, position: str, state: str) -> dict:
    return {"kind": kind, "position": position, "state": state}


def entry_entities_fixture() -> dict:
    return {
        "kaim": entity("character", "roof_right", "traverse_ready"),
        "scarf": entity("object", "on_fixed_clothesline_midpoint", "one_end_per_hand"),
        "clothesline": entity("environment_anchor", "fixed_roof_span", "fixed"),
        "window": entity("environment_anchor", "left_building_window", "closed"),
        "woman": entity("character", "window_interior", "approaching_window"),
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
    entry = entry_entities_fixture()
    exit_state = {
        "scarf": entity("object", "left_building", "still_with_kaim_after_exit"),
        "clothesline": entity("environment_anchor", "fixed_roof_span", "fixed"),
        "window": entity("environment_anchor", "left_building_window", "open"),
        "woman": entity("character", "window_interior", "reacting"),
    }
    return {
        "packet_id": "DR-P0-KAIM-SCARF",
        "scene_diagnosis": {
            "dramatic_purpose": "让凯姆以熟练干冷的方式穿过居民生活空间并继续搜索。",
            "audience_knowledge_before": "凯姆正从高位继续搜索偷钱男孩。",
            "audience_knowledge_after": "凯姆已横向穿越并在女人反应期间离开当前master。",
            "material_problem": "必须同时保持围巾与固定晾衣绳拓扑、横向轨迹和消失揭示。",
        },
        "director_intent": {
            "audience_effect": "先读懂熟练动作，再得到生活空间碰撞的干冷幽默，最后以缺席收束。",
            "character_goal": "凯姆不停顿地向左侧继续搜索男孩。",
            "subtext": "意外只是效率优先下的生活摩擦，不让凯姆变成小丑。",
            "success_condition": "动作关系清楚、凯姆始终高效，回master时已经不在。",
        },
        "world_state": {
            "entry": {
                "entities": entry,
                "invariants": [
                    "no_open_sky_prison_city_enclosure",
                    "fixed_clothesline_does_not_translate_with_kaim",
                ],
            },
            "exit": {
                "entities": exit_state,
                "invariants": [
                    "no_open_sky_prison_city_enclosure",
                    "fixed_clothesline_does_not_translate_with_kaim",
                ],
            },
            "explicit_exits_or_removals": ["kaim"],
            "state_changes": [
                "window closed -> open",
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
                "result": "kaim and scarf translate left while clothesline remains fixed",
                "reaction_trigger": "arrival beside window",
                "narrative_function": "skillful traverse through lived-in space",
            },
            {
                "event_id": "E2",
                "agent": "woman",
                "action": "open_window_and_react",
                "target": "window",
                "target_kind": "ENTITY",
                "instrument": None,
                "support_or_contact": ["window"],
                "precondition": "movement/noise beside window",
                "result": "woman reacts toward kaim",
                "reaction_trigger": "attention leaves kaim",
                "narrative_function": "reaction cutaway hides local exit",
            },
            {
                "event_id": "E3",
                "agent": "kaim",
                "action": "exit_during_reaction_cutaway",
                "target": None,
                "target_kind": "NONE",
                "instrument": "scarf",
                "support_or_contact": None,
                "precondition": "attention is on woman",
                "result": "kaim exits before return to master",
                "reaction_trigger": "same-master reveal",
                "narrative_function": "disappearance reveal",
            },
        ],
        "blocking": {
            "initial_positions": {
                "kaim": "roof_right",
                "scarf": "on_fixed_clothesline_midpoint",
                "clothesline": "fixed_roof_span",
                "window": "left_building_window",
                "woman": "window_interior",
            },
            "movement_paths": {
                "kaim": "screen_right_to_screen_left_below_line",
                "scarf": "co_translate_with_kaim_around_fixed_line",
                "woman": "interior_to_open_window",
            },
            "final_positions": {
                "scarf": "left_building",
                "clothesline": "fixed_roof_span",
                "window": "left_building_window",
                "woman": "window_interior",
            },
            "support_contacts": {
                "kaim": ["clothesline"],
                "scarf": ["clothesline"],
                "woman": ["window"],
            },
        },
        "performance": {
            "kaim": {
                "objective": "不断线地继续向左移动和搜索",
                "subtext": "意外很烦但不值得情绪化处理",
                "observable_behavior": ["动作连续", "身体控制稳定", "对白干冷简短"],
            },
            "woman": {
                "objective": "弄清窗外突然发生了什么",
                "subtext": "困惑但反应自然",
                "observable_behavior": ["开窗", "短促观察", "不过演"],
            },
        },
        "cinematic_intent": {
            "contract_id": "DR-P0-KAIM-CINEMATIC",
            "intent": {
                "composition": {
                    "primary_mechanism": "lateral_traverse_readability",
                    "camera_reason": "保持右到左移动、固定晾衣绳和左侧终点同时可读",
                },
                "attention_handoff": {
                    "from_roi": "kaim_at_left_window",
                    "cut_or_transition_event": "woman_reaction",
                    "to_roi": "same_master_left_building",
                    "withheld_information": "kaim_exits_during_reaction",
                    "reveal_on_return": "kaim_already_absent",
                    "next_shot_target": "continuing_search",
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
                "events": ["E1"],
                "exit_state": "kaim arrives beside window",
                "necessity": "同时承担能力展示与空间动作因果",
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
                "events": ["E2", "E3"],
                "exit_state": "same master returns with kaim absent",
                "necessity": "把消失做成剪辑信息而非特效炫技",
                "camera_proposal": {
                    "authority_status": "PROPOSAL_ONLY",
                    "shot_size": "reaction_then_same_master",
                    "orientation": "preserve_master_orientation",
                    "motion": "minimal",
                    "composition": "attention shifts to woman then back to absence",
                    "camera_reason": "the cut hides exit and return reveals absence",
                },
            },
        ],
        "transition": {
            "inherited_entities": ["clothesline"],
            "changed_entities": ["scarf", "window", "woman"],
            "explicit_exits_or_removals": ["kaim"],
            "next_entry_state": {
                "entities": ["scarf", "clothesline", "window", "woman"],
            },
        },
        "constraint_autonomy": {
            "locked_constraints_preserved": list(LOCKED),
            "hard_invariants": [
                "围巾中点只搭在固定粗晾衣绳上，两端分别在凯姆双手",
                "凯姆与围巾一起右向左移动，晾衣绳固定不平移",
                "封闭监牢城市环境不出现开放天空",
                "reaction cutaway后回同一master时凯姆已经消失",
            ],
            "guided_choices": ["女人反应强度保持自然不过演"],
            "free_model_space": ["非关键衣物摆动细节", "背景次要居民微动作"],
            "final_state": "凯姆已离开当前master继续搜索，女人仍在窗口，晾衣绳保持固定。",
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


class DirectorRuntimeOrchestratorFixtureTests(unittest.TestCase):
    """Synthetic context is intentionally useful for validators but never authoritative."""

    def compile_fixture(self, packet: dict | None = None, retrieval: dict | None = None) -> dict:
        return DirectorRuntimeOrchestrator()._compile_untrusted_test_fixture(
            "继续当前凯姆围巾晾衣绳横移这段",
            packet or creative_packet(),
            retrieval or retrieval_result(),
        )

    def assert_code(self, expected: str, fn) -> None:
        with self.assertRaises(DirectorRuntimeError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_current_kaim_fixture_compiles_only_as_untrusted_non_executable_candidate(self):
        result = self.compile_fixture()
        self.assertEqual("UNTRUSTED_TEST_CANDIDATE", result["status"])
        self.assertFalse(result["production_context_trusted"])
        self.assertEqual("UNTRUSTED_TEST_FIXTURE", result["work_item_binding"]["binding_status"])
        self.assertEqual(
            "untrusted_test_fixture_not_world_truth",
            result["work_item_binding"]["world_entry_authority"],
        )
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["deliverable"])
        self.assertFalse(result["learning_context"]["fixture_receipt_is_production_authority"])
        execution = result["minimum_execution_prompt_candidate"]
        self.assertEqual(list(LOCKED), execution["hard_invariant_refs"])
        self.assertEqual([LOCK_SEMANTICS[item] for item in LOCKED], execution["canonical_hard_invariants"])
        self.assertFalse(execution["caller_hard_invariants_are_lock_authority"])
        self.assertEqual(
            "PROPOSAL_ONLY",
            result["director_ir"]["shot_plan"][0]["camera_proposal"]["authority_status"],
        )

    def test_bound_fixture_without_world_baseline_fails_closed(self):
        retrieval = retrieval_result()
        retrieval["canonical_runtime_receipt"]["work_item_context_packet"].pop("world_state_baseline")
        self.assert_code(
            "DIRECTOR_WORLD_BASELINE_UNAVAILABLE",
            lambda: self.compile_fixture(retrieval=retrieval),
        )

    def test_bound_fixture_without_lock_semantics_fails_closed(self):
        retrieval = retrieval_result()
        retrieval["canonical_runtime_receipt"]["work_item_context_packet"].pop("locked_constraint_semantics")
        self.assert_code(
            "DIRECTOR_LOCK_SEMANTICS_UNAVAILABLE",
            lambda: self.compile_fixture(retrieval=retrieval),
        )

    def test_creative_packet_cannot_supply_work_item_authority(self):
        packet = creative_packet()
        packet["work_item_id"] = "FORGED-WORK-ITEM"
        self.assert_code(
            "DIRECTOR_PACKET_AUTHORITY_VIOLATION",
            lambda: self.compile_fixture(packet=packet),
        )

    def test_live_entity_cannot_disappear_by_prompt_omission(self):
        packet = creative_packet()
        packet["world_state"]["exit"]["entities"].pop("scarf")
        self.assert_code("DIRECTOR_WORLD_ENTITY_DROPPED", lambda: self.compile_fixture(packet=packet))

    def test_caller_cannot_invent_entity_in_both_entry_and_exit(self):
        packet = creative_packet()
        ghost = entity("character", "roof_right", "invented")
        packet["world_state"]["entry"]["entities"]["ghost_actor"] = deepcopy(ghost)
        packet["world_state"]["exit"]["entities"]["ghost_actor"] = deepcopy(ghost)
        self.assert_code(
            "DIRECTOR_WORLD_ENTRY_BASELINE_MISMATCH",
            lambda: self.compile_fixture(packet=packet),
        )

    def test_caller_cannot_erase_real_entity_from_both_entry_and_exit(self):
        packet = creative_packet()
        packet["world_state"]["entry"]["entities"].pop("scarf")
        packet["world_state"]["exit"]["entities"].pop("scarf")
        packet["events"][0]["instrument"] = None
        packet["blocking"]["initial_positions"].pop("scarf")
        packet["blocking"]["movement_paths"].pop("scarf")
        packet["blocking"]["support_contacts"].pop("scarf")
        packet["transition"]["changed_entities"].remove("scarf")
        packet["transition"]["next_entry_state"]["entities"].remove("scarf")
        self.assert_code(
            "DIRECTOR_WORLD_ENTRY_BASELINE_MISMATCH",
            lambda: self.compile_fixture(packet=packet),
        )

    def test_event_agent_must_exist_in_world_state(self):
        packet = creative_packet()
        packet["events"][0]["agent"] = "ghost_actor"
        self.assert_code("DIRECTOR_EVENT_ENTITY_UNBOUND", lambda: self.compile_fixture(packet=packet))

    def test_blocking_cannot_move_unknown_entity(self):
        packet = creative_packet()
        packet["blocking"]["movement_paths"]["ghost_actor"] = "nowhere_to_nowhere"
        self.assert_code("DIRECTOR_BLOCKING_ENTITY_UNBOUND", lambda: self.compile_fixture(packet=packet))

    def test_performance_actor_must_be_character_entity(self):
        packet = creative_packet()
        packet["performance"]["scarf"] = {
            "objective": "be dramatic",
            "subtext": "none",
            "observable_behavior": "flap",
        }
        self.assert_code("DIRECTOR_PERFORMANCE_ACTOR_UNBOUND", lambda: self.compile_fixture(packet=packet))

    def test_shot_camera_cannot_mint_locked_authority(self):
        packet = creative_packet()
        packet["shot_plan"][0]["camera_proposal"]["authority_status"] = "LOCKED"
        self.assert_code("DIRECTOR_CAMERA_AUTHORITY_MINT_ATTEMPT", lambda: self.compile_fixture(packet=packet))

    def test_transition_next_entry_must_equal_world_exit_entities(self):
        packet = creative_packet()
        packet["transition"]["next_entry_state"]["entities"].remove("scarf")
        self.assert_code("DIRECTOR_TRANSITION_STATE_MISMATCH", lambda: self.compile_fixture(packet=packet))

    def test_locked_constraint_id_cannot_be_dropped(self):
        packet = creative_packet()
        packet["constraint_autonomy"]["locked_constraints_preserved"].remove(
            "scarf_midpoint_single_drape_over_fixed_thick_line"
        )
        self.assert_code("DIRECTOR_LOCKED_CONSTRAINT_DROPPED", lambda: self.compile_fixture(packet=packet))

    def test_lock_id_rubber_stamp_cannot_drop_material_semantics(self):
        packet = creative_packet()
        packet["constraint_autonomy"]["hard_invariants"] = ["unrelated harmless sentence"]
        result = self.compile_fixture(packet=packet)
        execution = result["minimum_execution_prompt_candidate"]
        self.assertEqual([LOCK_SEMANTICS[item] for item in LOCKED], execution["canonical_hard_invariants"])
        self.assertIn(LOCK_SEMANTICS["scarf_midpoint_single_drape_over_fixed_thick_line"], execution["text"])
        self.assertIn("unrelated harmless sentence", execution["text"])
        self.assertFalse(execution["caller_hard_invariants_are_lock_authority"])

    def test_cinematic_intent_cannot_mint_camera_physical_authority(self):
        packet = creative_packet()
        packet["cinematic_intent"] = {
            "contract_id": "FORGED-CAMERA",
            "intent": {"capture_intent": {"camera_physical_position": "roof_absolute_anchor"}},
            "provenance": {"capture_intent": {"source": "ai_proposal"}},
            "context": {"material_fields": ["capture_intent"]},
        }
        self.assert_code("DIRECTOR_CINEMATIC_INTENT_REJECTED", lambda: self.compile_fixture(packet=packet))

    def test_reasoning_scratchpad_is_not_an_allowed_packet_field(self):
        packet = creative_packet()
        packet["chain_of_thought"] = "hidden reasoning should never enter runtime"
        self.assert_code("DIRECTOR_PACKET_SCHEMA_INVALID", lambda: self.compile_fixture(packet=packet))

    def test_candidate_contract_remains_unregistered(self):
        project_index = yaml.safe_load((PROJECT_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("director_runtime_orchestrator", project_index.get("canonical", {}))
        contract = yaml.safe_load(
            (PROJECT_ROOT / "10_运行时/director_runtime_orchestrator.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual("candidate", contract["status"])
        self.assertEqual("absent", contract["activation"]["PROJECT_INDEX_registration"])

    def test_regression_registry_contains_current_production_case_and_trust_attacks(self):
        suite = yaml.safe_load(
            (PROJECT_ROOT / "11_验收/director_runtime_orchestrator_regression_cases.yaml").read_text(encoding="utf-8")
        )
        cases = {item["id"]: item for item in suite["cases"]}
        self.assertEqual(
            "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            cases["DR-P0-KAIM-SCARF-POSITIVE"]["work_item_id"],
        )
        for case_id in (
            "DR-P0-PROVENANCE-SOURCE-001",
            "DR-P0-PROVENANCE-RUNTIME-BINDING-001",
            "DR-P0-PROVENANCE-RUNTIME-METHOD-001",
            "DR-P0-PROVENANCE-CINEMATIC-001",
            "DR-P0-TEST-SEAM-001",
        ):
            self.assertIn(case_id, cases)


class DirectorRuntimeProductionTrustTests(unittest.TestCase):
    def assert_provenance_rejected(self, fn) -> None:
        with self.assertRaises(DirectorRuntimeError) as ctx:
            fn()
        self.assertEqual("DIRECTOR_RUNTIME_PROVENANCE_SUBSTITUTED", ctx.exception.code)

    def test_orchestrator_has_no_caller_selectable_authority_state(self):
        runtime = DirectorRuntimeOrchestrator()
        self.assertFalse(hasattr(runtime, "learning_runtime"))
        self.assertFalse(hasattr(runtime, "_project_root"))
        with self.assertRaises(TypeError):
            DirectorRuntimeOrchestrator(PROJECT_ROOT)  # type: ignore[call-arg]

    def test_mutating_module_file_locator_fails_before_retrieval(self):
        forged = PROJECT_ROOT / "forged" / "director_orchestrator.py"
        with patch.object(orchestrator_module, "__file__", str(forged)):
            self.assert_provenance_rejected(
                lambda: DirectorRuntimeOrchestrator().compile("继续当前这段", creative_packet())
            )

    def test_replacing_module_runtime_binding_fails_before_receipt_consumption(self):
        class FakeRuntime:
            pass

        with patch.object(orchestrator_module, "DirectorLearningRuntime", FakeRuntime):
            self.assert_provenance_rejected(
                lambda: DirectorRuntimeOrchestrator().compile("继续当前这段", creative_packet())
            )

    def test_replacing_runtime_retrieve_method_fails_before_receipt_consumption(self):
        original = runtime_module.DirectorLearningRuntime.retrieve

        def forged_retrieve(self, *args, **kwargs):
            return retrieval_result()

        try:
            runtime_module.DirectorLearningRuntime.retrieve = forged_retrieve
            self.assert_provenance_rejected(
                lambda: DirectorRuntimeOrchestrator().compile("继续当前这段", creative_packet())
            )
        finally:
            runtime_module.DirectorLearningRuntime.retrieve = original

    def test_replacing_cinematic_compiler_binding_fails_before_retrieval(self):
        def forged_compiler(*args, **kwargs):
            return {"status": "PASS", "execution_overlay": {}}

        with patch.object(orchestrator_module, "compile_cinematic_intent_contract", forged_compiler):
            self.assert_provenance_rejected(
                lambda: DirectorRuntimeOrchestrator().compile("继续当前这段", creative_packet())
            )


if __name__ == "__main__":
    unittest.main()
