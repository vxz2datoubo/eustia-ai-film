from pathlib import Path
import unittest

import yaml

from learning_retriever.feature_compiler import FeatureCompilationError, compile_director_features, compile_retrieval_task


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_DATA = yaml.safe_load((REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8"))


class AnimateAgentCompilerBoundaryTests(unittest.TestCase):
    def compile_or_none(self, text: str):
        try:
            return compile_director_features(text)
        except FeatureCompilationError as exc:
            if str(exc) == "NO_RECOGNIZED_DIRECTOR_FEATURES":
                return None
            raise

    def assert_no_character_facing(self, text: str) -> None:
        result = self.compile_or_none(text)
        if result is None:
            return
        self.assertNotIn("facing_to_target", result.relation_type)
        self.assertNotIn("target_oriented_action", result.dramatic_function)
        self.assertNotIn("locatable_target", result.spatial_action_features)
        self.assertNotIn("body_orientation_target_fail", result.failure_mechanism)

    def assert_character_facing(self, text: str) -> None:
        result = compile_director_features(text)
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)
        self.assertIn("body_orientation", result.spatial_action_features)
        self.assertIn("locatable_target", result.spatial_action_features)

    def test_unseen_human_roles_remain_transfer_positive(self):
        self.assert_character_facing("贵族面向圣女。")
        self.assert_character_facing("骑士朝向敌人。")
        self.assert_character_facing("医生面向伤员。")
        self.assert_character_facing("调查员面向逃犯。")
        self.assert_character_facing("工程师面向同伴。")

    def test_unseen_project_proper_name_can_be_proven_by_embodied_turn(self):
        self.assert_character_facing("菲奥奈转身面向圣女。")
        self.assert_character_facing("菲奥奈缓缓地回身面向圣女。")

    def test_unseen_noncharacters_do_not_mint_character_facing(self):
        for text in (
            "钟楼面向圣女。",
            "教堂面向圣女。",
            "雕像面向圣女。",
            "塔楼面向圣女。",
            "马车面向圣女。",
            "广场面向圣女。",
            "石桥面向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_character_facing(text)

    def test_structural_subject_cannot_be_laundered_by_body_turn_wording(self):
        for text in (
            "钟楼转身面向圣女。",
            "雕像回身面向圣女。",
            "祭坛转身面向圣女。",
            "石碑回身面向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_character_facing(text)

    def test_noncharacter_sentence_cannot_mint_target_spatial_hard_route(self):
        task = compile_retrieval_task("钟楼面向圣女。", route_data=ROUTE_DATA, strict=False)
        self.assertNotIn("TARGET_ORIENTED_SPATIAL_BINDING", task.get("hard_routes") or [])
        self.assertNotIn("facing_to_target", task.get("relation_type") or [])

    def test_dynasty_and_camera_negatives_remain_closed(self):
        for text in (
            "这个王朝向圣女征税。",
            "前朝向圣女征税。",
            "本朝向教会征税。",
            "摄影机朝向圣女。",
            "镜头面向圣女。",
            "机位朝向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_character_facing(text)


if __name__ == "__main__":
    unittest.main()
