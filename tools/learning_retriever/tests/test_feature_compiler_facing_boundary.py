from pathlib import Path
import unittest

from learning_retriever.feature_compiler import FeatureCompilationError, compile_director_features


REPO_ROOT = Path(__file__).resolve().parents[3]


def compile_or_none(text: str):
    try:
        return compile_director_features(text)
    except FeatureCompilationError as exc:
        if str(exc) == "NO_RECOGNIZED_DIRECTOR_FEATURES":
            return None
        raise


class FacingBoundaryTests(unittest.TestCase):
    def assert_no_target_facing(self, text: str) -> None:
        result = compile_or_none(text)
        if result is None:
            return
        self.assertNotIn("facing_to_target", result.relation_type)
        self.assertNotIn("target_oriented_action", result.dramatic_function)
        self.assertNotIn("locatable_target", result.spatial_action_features)
        self.assertNotIn("body_orientation_target_fail", result.failure_mechanism)

    def test_dynasty_plus_xiang_does_not_form_cross_token_chaoxiang(self):
        self.assert_no_target_facing("这个王朝向圣女征税。")

    def test_previous_dynasty_plus_xiang_does_not_form_facing(self):
        self.assert_no_target_facing("前朝向圣女征税。")

    def test_current_dynasty_plus_xiang_does_not_form_facing(self):
        self.assert_no_target_facing("本朝向教会征税。")

    def test_real_actor_facing_target_remains_positive(self):
        result = compile_director_features("群众朝向圣女转身。")
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)
        self.assertIn("body_orientation", result.spatial_action_features)
        self.assertIn("locatable_target", result.spatial_action_features)

    def test_open_vocabulary_manner_before_facing_remains_positive(self):
        result = compile_director_features("群众十分虔诚地朝向圣女。")
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)
        self.assertIn("body_orientation", result.spatial_action_features)

    def test_explicit_body_orientation_remains_positive(self):
        result = compile_director_features("身体朝圣女。")
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("body_orientation", result.spatial_action_features)

    def test_elliptical_facing_instruction_remains_positive(self):
        result = compile_director_features("朝向圣女。")
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)

    def test_camera_facing_target_does_not_mint_character_target_relation(self):
        result = compile_or_none("摄影机朝向圣女。")
        if result is None:
            return
        self.assertNotIn("facing_to_target", result.relation_type)
        self.assertNotIn("target_oriented_action", result.dramatic_function)
        self.assertNotIn("body_orientation", result.spatial_action_features)

    def test_preposed_kneel_open_manner_regression_stays_positive(self):
        result = compile_director_features("群众朝着圣女恭敬地跪下。")
        self.assertIn("kneeling_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)
        self.assertIn("locatable_target", result.spatial_action_features)

    def test_determined_target_open_manner_regression_stays_positive(self):
        result = compile_director_features("信徒向着那位圣女十分虔诚地跪拜。")
        self.assertIn("kneeling_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)


if __name__ == "__main__":
    unittest.main()
