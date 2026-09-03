from pathlib import Path
import unittest

import yaml

from learning_retriever.entity_semantics import (
    HUMAN_ROLE_HEADS,
    bounded_animate_agent_leader,
    load_canonical_character_terms,
)
from learning_retriever.feature_compiler import (
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
)
from learning_retriever.runtime import DirectorLearningRuntime


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_DATA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8")
)
CANONICAL = load_canonical_character_terms(REPO_ROOT)


def modifier_tail(value: str) -> bool:
    residual = value.strip()
    if not residual:
        return True
    if residual.endswith("地"):
        stem = residual[:-1]
        return 2 <= len(stem) <= 8 and all("\u4e00" <= ch <= "\u9fff" for ch in stem)
    return residual in {"缓缓", "慢慢", "迅速", "突然", "纷纷", "共同", "一起", "一同", "全都", "都"}


class HumanRoleTruthBoundaryTests(unittest.TestCase):
    def compile_or_none(self, text: str):
        try:
            return compile_director_features(text)
        except FeatureCompilationError as exc:
            if str(exc) == "NO_RECOGNIZED_DIRECTOR_FEATURES":
                return None
            raise

    def assert_no_target_facing(self, text: str) -> None:
        result = self.compile_or_none(text)
        if result is None:
            return
        self.assertNotIn("facing_to_target", result.relation_type)
        self.assertNotIn("target_oriented_action", result.dramatic_function)
        self.assertNotIn("locatable_target", result.spatial_action_features)
        task = compile_retrieval_task(
            text,
            route_data=ROUTE_DATA,
            strict=False,
        )
        self.assertNotIn("TARGET_ORIENTED_SPATIAL_BINDING", task.get("hard_routes") or [])

    def test_productive_human_suffix_is_not_identity_evidence(self):
        for leader in ("稻草人", "假人", "雪人", "纸人", "木偶人", "机器人"):
            with self.subTest(leader=leader):
                self.assertFalse(
                    bounded_animate_agent_leader(
                        leader,
                        action="面向",
                        known_actor_terms=CANONICAL,
                        modifier_tail_validator=modifier_tail,
                    )
                )
                self.assert_no_target_facing(f"{leader}面向圣女。")

    def test_nonagent_compound_with_manner_stays_nonagent(self):
        for text in (
            "稻草人缓缓地面向圣女。",
            "木偶人突然回身面向圣女。",
            "纸人慢慢转身面向教会。",
            "人体模型面向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_target_facing(text)

    def test_bounded_open_human_roles_remain_positive(self):
        for role in ("贵族", "骑士", "医生", "调查员", "工程师", "研究者", "祭司"):
            with self.subTest(role=role):
                self.assertIn(role, HUMAN_ROLE_HEADS)
                result = compile_director_features(f"{role}面向圣女。")
                self.assertIn("facing_to_target", result.relation_type)
                self.assertIn("locatable_target", result.spatial_action_features)

    def test_scene_prefix_and_manner_do_not_require_scene_dictionary(self):
        result = compile_director_features(
            "礼拜堂中央年轻祭司十分郑重地面向圣女。"
        )
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("body_orientation", result.spatial_action_features)

    def test_dynasty_worldbuilding_prefix_cannot_turn_role_word_into_actor(self):
        for text in (
            "王朝圣女面向教会的历史记载。",
            "前朝圣女面向教会的仪式壁画。",
            "本朝圣女面向教会的制度描述。",
        ):
            with self.subTest(text=text):
                self.assert_no_target_facing(text)

    def test_canonical_named_character_still_works_through_runtime(self):
        self.assertIn("菲奥奈", CANONICAL)
        runtime = DirectorLearningRuntime(REPO_ROOT)
        result = runtime.retrieve("菲奥奈面向圣女。", task_id="ENTITY-RUNTIME-FIONE")
        receipt = result["canonical_runtime_receipt"]
        self.assertEqual(receipt["entity_semantics_authority"], "PROJECT_INDEX.canonical.character_db")
        self.assertFalse(receipt["caller_actor_terms_supported"])
        self.assertGreater(receipt["canonical_character_term_count"], 0)
        self.assertIn("facing_to_target", receipt["compiled_features"]["relation_type"])
        self.assertIn("TARGET_ORIENTED_SPATIAL_BINDING", receipt["hard_routes"])

    def test_turn_word_does_not_launder_unknown_object_identity(self):
        for text in (
            "雕像转身面向圣女。",
            "石碑回身面向圣女。",
            "虚构专名甲转身面向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_target_facing(text)


if __name__ == "__main__":
    unittest.main()
