from pathlib import Path
import inspect
import unittest

import yaml

from learning_retriever.feature_compiler import (
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_DATA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8")
)


class SubjectAuthorityFacadeTests(unittest.TestCase):
    def compile_or_none(self, text: str):
        try:
            return compile_director_features(text)
        except FeatureCompilationError as exc:
            if str(exc) == "NO_RECOGNIZED_DIRECTOR_FEATURES":
                return None
            raise

    def assert_no_actor_route(self, text: str) -> dict:
        task = compile_retrieval_task(
            text,
            route_data=ROUTE_DATA,
            strict=False,
        )
        self.assertNotIn("TARGET_ORIENTED_SPATIAL_BINDING", task.get("hard_routes") or [])
        self.assertNotIn("facing_to_target", task.get("relation_type") or [])
        self.assertNotIn("kneeling_to_target", task.get("relation_type") or [])
        self.assertNotIn("gaze_to_target", task.get("relation_type") or [])
        self.assertFalse(task["feature_compiler_receipt"]["caller_actor_terms_supported"])
        self.assertEqual(
            task["feature_compiler_receipt"]["actor_terms_source"],
            "PROJECT_INDEX.canonical.character_db",
        )
        self.assertEqual(
            task["feature_compiler_receipt"]["actor_subject_binding"],
            "per_target_event_actor_identity_v3",
        )
        return task

    def test_public_compiler_has_no_actor_term_injection_surface(self):
        feature_params = inspect.signature(compile_director_features).parameters
        task_params = inspect.signature(compile_retrieval_task).parameters
        self.assertNotIn("known_actor_terms", feature_params)
        self.assertNotIn("known_actor_terms", task_params)
        with self.assertRaises(TypeError):
            compile_director_features("钟楼面向圣女。", known_actor_terms=("钟楼",))
        with self.assertRaises(TypeError):
            compile_retrieval_task(
                "钟楼面向圣女。",
                route_data=ROUTE_DATA,
                known_actor_terms=("钟楼",),
            )

    def test_canonical_name_and_pronoun_are_token_bound_not_suffix_bound(self):
        self.assert_no_actor_route("英格兰面向圣女。")
        self.assert_no_actor_route("吉他面向舞台。")
        result = compile_director_features("格兰面向圣女。")
        self.assertIn("facing_to_target", result.relation_type)
        result = compile_director_features("他面向圣女。")
        self.assertIn("facing_to_target", result.relation_type)

    def test_all_preposed_direction_markers_validate_subject(self):
        for text in (
            "钟楼朝着圣女跪下。",
            "摄影机对着圣女跪下。",
            "雕像向着圣女跪拜。",
            "教堂面朝圣女跪下。",
        ):
            with self.subTest(text=text):
                self.assert_no_actor_route(text)

        for text in (
            "群众朝着圣女跪下。",
            "信徒向着圣女跪拜。",
            "骑士对着敌人跪下。",
            "菲奥奈面朝圣女跪下。",
        ):
            with self.subTest(text=text):
                result = compile_director_features(text)
                self.assertIn("kneeling_to_target", result.relation_type)

    def test_compound_noun_ending_di_is_not_manner_tail(self):
        for text in (
            "骑士训练基地面向圣女。",
            "祭司驻地面向教会。",
            "骑士出生地面向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_actor_route(text)
        result = compile_director_features("骑士十分郑重地面向圣女。")
        self.assertIn("facing_to_target", result.relation_type)

    def test_camera_agency_survives_elliptical_followup_clause(self):
        for text in (
            "摄影机朝向圣女，随后面向教会。",
            "镜头面向圣女，然后转向大门。",
            "机位朝向圣女，接着面向出口。",
        ):
            with self.subTest(text=text):
                self.assert_no_actor_route(text)

        actor = compile_director_features("凯姆朝向圣女，随后面向教会。")
        self.assertIn("facing_to_target", actor.relation_type)

    def test_bare_first_clause_imperative_remains_valid(self):
        result = compile_director_features("朝向圣女。")
        self.assertIn("facing_to_target", result.relation_type)
        self.assertIn("target_oriented_action", result.dramatic_function)

    def test_nonhuman_gaze_cannot_reach_actor_target_route(self):
        for text in (
            "雕像看向圣女。",
            "吉他望向舞台。",
            "钟楼注视教会。",
            "摄影机看向圣女。",
        ):
            with self.subTest(text=text):
                self.assert_no_actor_route(text)

        result = compile_director_features("菲奥奈看向圣女。")
        self.assertIn("gaze_to_target", result.relation_type)

    def test_actor_support_is_bound_to_specific_target_bearing_event(self):
        kneel = self.assert_no_actor_route("群众下跪，雕像朝着圣女跪下。")
        self.assertIn("body_orientation", kneel.get("spatial_action_features") or [])

        gaze = self.assert_no_actor_route("菲奥奈观察远处，雕像看向圣女。")
        self.assertIn("gaze_direction", gaze.get("spatial_action_features") or [])

    def test_possessive_actor_observable_is_bounded_positive(self):
        for text in (
            "菲奥奈的目光朝向圣女。",
            "她的视线朝向圣女。",
        ):
            with self.subTest(text=text):
                result = compile_director_features(text)
                self.assertIn("gaze_to_target", result.relation_type)

        self.assert_no_actor_route("英格兰的目光朝向圣女。")
        self.assert_no_actor_route("雕像的视线朝向圣女。")

    def test_scene_prefix_localizer_de_preserves_real_human_subject(self):
        result = compile_director_features("礼拜堂中央的年轻祭司面向圣女。")
        self.assertIn("facing_to_target", result.relation_type)

    def test_intervening_nonagent_clause_invalidates_stale_agency(self):
        self.assert_no_actor_route("菲奥奈看向远处，雕像闪现，随后面向圣女。")
        self.assert_no_actor_route("菲奥奈看向远处，摄影机推进，随后面向圣女。")

    def test_cross_clause_target_carry_requires_same_actor_identity(self):
        result = compile_director_features("菲奥奈看向圣女。骑士跪下。凯姆面向圣女。")
        self.assertIn("gaze_to_target", result.relation_type)
        self.assertIn("facing_to_target", result.relation_type)
        self.assertNotIn("kneeling_to_target", result.relation_type)

    def test_deferred_kneel_backfill_requires_same_actor_identity(self):
        result = compile_director_features("群众跪下且骑士看向圣女并面向圣女。")
        self.assertIn("gaze_to_target", result.relation_type)
        self.assertNotIn("kneeling_to_target", result.relation_type)

        production_same_actor = compile_retrieval_task(
            "角色下跪并面向门口圣女。",
            route_data=ROUTE_DATA,
        )
        self.assertIn("kneeling_to_target", production_same_actor.get("relation_type") or [])
        self.assertIn(
            "TARGET_ORIENTED_SPATIAL_BINDING",
            production_same_actor.get("hard_routes") or [],
        )


if __name__ == "__main__":
    unittest.main()
